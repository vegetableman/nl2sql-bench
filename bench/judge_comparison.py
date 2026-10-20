"""Same-SQL judge comparison: TypeSafe Jev (jev-1.14.0) vs mnemiq's gpt-oss:120b LLM judge.

Items: every (question, SQL) the gpt-oss judge scored in the mnemiq_verified run (judge_calls.log, 132 calls,
with its logged confidence) + every mnemiq_failopen answer on both sets (132, no gpt-oss confidence logged).
  1. `items`: write results/judge-comparison/items.jsonl (bench venv)
  2. engine side: MNEMIQ_VARIANT=jev mnemiq/run.sh py mnemiq/judge_rebuild.py items.jsonl rebuilt.jsonl
     (rebuilds mnemiq's judge schema + render_result(max_rows=5) preview with mnemiq's own code, scores with Jev)
  3. `score`: label every result against gold with the harness `compare` (EX exact; ho14 tie-tolerant, see note),
     write judge_comparison.csv + judge_comparison.md
"""
import csv, json, sys
from collections import defaultdict
import psycopg, yaml
from common import ROOT, load_env, compare
import mnemiq_verifier_analysis as va

OUT = ROOT / "results/judge-comparison"
SETS = {"29": ("run-gptoss120b-mnemiq-r3", "bench/questions.yaml"), "holdout": ("run-gptoss120b-holdout-r3", "bench/questions_holdout.yaml")}
TH = 0.5


def questions():
    return {name: {q["id"]: q for q in yaml.safe_load(open(ROOT / qf))["questions"]} for name, (_, qf) in SETS.items()}


def items():
    qs = questions(); jl = va.judge_lines(); ji = 0; recs = []
    for name, (run, _) in SETS.items():
        for l in open(ROOT / "results" / run / "raw.jsonl"):
            r = json.loads(l)
            if r["system"] in ("mnemiq_verified", "mnemiq_failopen"):
                r["_set"] = name; recs.append(r)
    out = []
    for r in sorted([r for r in recs if r["system"] == "mnemiq_verified"], key=lambda r: r["t_start_epoch"]):
        q = qs[r["_set"]][r["id"]]; mine = []
        while ji < len(jl) and jl[ji]["q"] == q["question"][:70]:
            mine.append(jl[ji]); ji += 1
        assert len(mine) == 1, (r["id"], r["run"], len(mine))
        out.append({"key": f"verified|{r['_set']}|{r['id']}|{r['run']}", "source": "mnemiq_verified", "set": r["_set"], "id": r["id"],
                    "run": r["run"], "question": q["question"], "sql": mine[0]["sql"], "gptoss_conf": mine[0]["conf"],
                    "harness_status": r["status"]})
    assert ji == len(jl) == 132, (ji, len(jl))
    for r in recs:
        if r["system"] == "mnemiq_failopen":
            q = qs[r["_set"]][r["id"]]
            assert r.get("generated"), (r["id"], r["run"])
            out.append({"key": f"failopen|{r['_set']}|{r['id']}|{r['run']}", "source": "mnemiq_failopen", "set": r["_set"], "id": r["id"],
                        "run": r["run"], "question": q["question"], "sql": r["generated"], "gptoss_conf": None,
                        "harness_status": r["status"]})
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "items.jsonl", "w") as f:
        for it in out:
            f.write(json.dumps(it) + "\n")
    print(len(out), "items")


def auroc(pairs):  # pairs: (score, is_correct); P(score_correct > score_wrong), ties 0.5
    pos = [s for s, c in pairs if c]; neg = [s for s, c in pairs if not c]
    if not pos or not neg:
        return None
    return sum(1.0 if p > n else 0.5 if p == n else 0.0 for p in pos for n in neg) / (len(pos) * len(neg))


def confusion(pairs, th=TH):
    c = {"wrong caught": 0, "wrong passed": 0, "correct blocked": 0, "correct passed": 0}
    for s, ok in pairs:
        passed = s >= th  # Verifier defers when confidence < threshold
        c[("correct " if ok else "wrong ") + ("passed" if passed else ("blocked" if ok else "caught"))] += 1
    return c


def score():
    env = load_env(); conn = psycopg.connect(env["BENCH_DB_URL"]); qs = questions()
    its = {json.loads(l)["key"]: json.loads(l) for l in open(OUT / "items.jsonl")}
    reb = {json.loads(l)["key"]: json.loads(l) for l in open(OUT / "rebuilt.jsonl")}
    missing = [k for k in its if k not in reb]
    gold, rows = {}, []
    for k, it in its.items():
        rb = reb.get(k, {}); q = qs[it["set"]][it["id"]]
        if (it["set"], it["id"]) not in gold:
            with conn.cursor() as cur:
                cur.execute("BEGIN READ ONLY"); cur.execute(q["gold_sql"]); gold[(it["set"], it["id"])] = cur.fetchall(); conn.rollback()
        label, how = None, ""
        if "rows" in rb:
            cmp = compare(gold[(it["set"], it["id"])], rb["rows"], q.get("order_matters", False), q.get("order_cols"))
            label, how = cmp["exact"], ("exact" if cmp["exact"] else "relaxed-only" if cmp["relaxed"] else "wrong")
            if not label and compare(gold[(it["set"], it["id"])], rb["rows"])["exact"]:
                # same rows, different order: DuckDB's binary collation vs Postgres' locale collation (ho12
                # "ordered alphabetically"). The harness scores such >100-row answers by re-executing on
                # Postgres, so do the same here.
                try:
                    with conn.cursor() as cur:
                        cur.execute("BEGIN READ ONLY"); cur.execute(it["sql"]); pg = cur.fetchall(); conn.rollback()
                    if compare(gold[(it["set"], it["id"])], pg, q.get("order_matters", False), q.get("order_cols"))["exact"]:
                        label, how = True, "same rows; DuckDB collation order differs, exact on Postgres"
                except Exception:
                    conn.rollback()
            if not label:
                alts = va.tie_alternatives(conn, q)
                if alts and any(compare(a, rb["rows"], q.get("order_matters", False), q.get("order_cols"))["exact"] for a in alts):
                    label, how = True, "valid under gold boundary tie"
        elif "exec_error" in rb:
            label, how = False, "exec error: " + rb["exec_error"][:80]
        rows.append({**{x: it[x] for x in ("source", "set", "id", "run", "harness_status", "gptoss_conf")},
                     "correct": label, "label_detail": how, "jev_noul": rb.get("jev_score"), "jev_fell_open": rb.get("jev_fell_open"),
                     "jev_model": rb.get("jev_model"), "jev_input_tokens": rb.get("jev_input_tokens"), "jev_latency_ms": rb.get("jev_latency_ms"),
                     "schema_chars": rb.get("schema_chars"), "sql": it["sql"]})
    with open(OUT / "judge_comparison.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    ok = [r for r in rows if r["correct"] is not None and r["jev_noul"] is not None and not r["jev_fell_open"]]
    toks = [int(r["jev_input_tokens"]) for r in ok if r["jev_input_tokens"] not in (None, "None")]
    lat = sorted(float(r["jev_latency_ms"]) for r in ok if r["jev_latency_ms"])
    L = ["# Same-SQL judge comparison: TypeSafe Jev vs mnemiq's gpt-oss:120b judge", "",
         "Each item is a (question, SQL) mnemiq produced. Its judge input is rebuilt with mnemiq's own code (`mnemiq/judge_rebuild.py`): "
         "the schema is `_judge_schema` of the packet `Runtime.ask` retrieves (same `retrieve` arguments + window fitter), and the result "
         "is the SQL run through mnemiq's own adapter (DuckDB over the same Postgres) rendered by `render_result(max_rows=5)`, exactly "
         "what the Verifier passes. Correct = EX-exact vs gold with the harness `compare` on the full result. "
         "**ho14: answers that are a valid top 3 under the gold's four-way tie for 3rd place are labelled correct** (known gold flaw). "
         "**ho12: DuckDB returns the same 110 rows as gold but in binary-collation order (Postgres' locale collation ignores spaces); "
         "these are labelled correct when the same SQL is exact on Postgres, which is how the harness scored them.** "
         f"Pass = score >= {TH} (mnemiq's Verifier defers below its 0.5 threshold).", "",
         f"Items: {len(rows)} ({sum(r['source']=='mnemiq_verified' for r in rows)} mnemiq_verified judge calls with logged gpt-oss confidence, "
         f"{sum(r['source']=='mnemiq_failopen' for r in rows)} mnemiq_failopen answers). Scored by Jev: {len(ok)}; missing/unscored: "
         f"{len(rows)-len(ok)}{' ' + str(missing[:5]) if missing else ''}. Correct: {sum(r['correct'] for r in ok)}, wrong: {sum(not r['correct'] for r in ok)}.", "",
         f"Jev calls: {len(ok)}, input tokens (reported by the API's `usage.input_tokens`): {sum(toks):,} total, {sum(toks)/max(1,len(toks)):,.0f} avg; "
         f"cost at $0.042/M input tokens: ${sum(toks)*0.042/1e6:.4f}. Latency p50 {lat[len(lat)//2]:.0f} ms, p95 {lat[int(0.95*(len(lat)-1))]:.0f} ms. "
         f"Model reported: {sorted({r['jev_model'] for r in ok})}.", "",
         "## At threshold 0.5", "",
         "| judge | items | wrong caught | wrong passed | correct blocked | correct passed | AUROC (score vs correct) |", "|---|---|---|---|---|---|---|"]
    ver = [r for r in ok if r["source"] == "mnemiq_verified"]
    for label, sub, key in [("gpt-oss:120b judge (logged, mnemiq_verified calls)", ver, "gptoss_conf"),
                            ("Jev, same mnemiq_verified calls", ver, "jev_noul"),
                            ("Jev, mnemiq_failopen answers", [r for r in ok if r["source"] == "mnemiq_failopen"], "jev_noul"),
                            ("Jev, all items", ok, "jev_noul")]:
        pairs = [(float(r[key]), bool(r["correct"])) for r in sub if r[key] is not None]
        c = confusion(pairs); a = auroc(pairs)
        L.append(f"| {label} | {len(pairs)} | {c['wrong caught']} | {c['wrong passed']} | {c['correct blocked']} | {c['correct passed']} | {'n/a' if a is None else f'{a:.3f}'} |")
    L += ["", "## Threshold sweep (blocked = score below threshold)", "",
          "| threshold | gpt-oss: wrong caught / passed | gpt-oss: correct blocked | Jev (same calls): wrong caught / passed | Jev (same calls): correct blocked | Jev (all): wrong caught / passed | Jev (all): correct blocked |",
          "|---|---|---|---|---|---|---|"]
    for th in (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9):
        g = confusion([(float(r["gptoss_conf"]), bool(r["correct"])) for r in ver], th)
        jv = confusion([(float(r["jev_noul"]), bool(r["correct"])) for r in ver], th)
        ja = confusion([(float(r["jev_noul"]), bool(r["correct"])) for r in ok], th)
        L.append(f"| {th} | {g['wrong caught']} / {g['wrong passed']} | {g['correct blocked']} | {jv['wrong caught']} / {jv['wrong passed']} | {jv['correct blocked']} | {ja['wrong caught']} / {ja['wrong passed']} | {ja['correct blocked']} |")
    L += ["", "## Every wrong answer, and every answer either judge blocks at 0.5", "",
          "| source | set | id | run | correct? | detail | gpt-oss conf | Jev noul | SQL |", "|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(ok, key=lambda r: (r["set"], r["id"], r["source"], str(r["run"]))):
        g = r["gptoss_conf"]; jn = float(r["jev_noul"])
        if (not r["correct"]) or jn < TH or (g is not None and float(g) < TH):
            L.append(f"| {r['source']} | {r['set']} | {r['id']} | {r['run']} | {'yes' if r['correct'] else 'NO'} | {r['label_detail']} | {g if g is not None else '–'} | {jn:.2f} | `{r['sql'][:160].replace('|','/')}` |")
    L += ["", "## Named cases", "", "| case | correct? | gpt-oss conf | Jev noul |", "|---|---|---|---|"]
    named = [("29", "h05", "1"), ("holdout", "ho10", "3"), ("holdout", "ho13", "1"), ("holdout", "ho13", "3")] + [("holdout", "ho14", x) for x in "123"]
    for s, i, rn in named:
        for r in ok:
            if r["set"] == s and r["id"] == i and str(r["run"]) == rn:
                L.append(f"| {r['source']} {i} r{rn} | {'yes' if r['correct'] else 'NO'} ({r['label_detail']}) | {r['gptoss_conf'] if r['gptoss_conf'] is not None else '–'} | {float(r['jev_noul']):.2f} |")
    txt = "\n".join(L) + "\n"
    (OUT / "judge_comparison.md").write_text(txt); print(txt)


if __name__ == "__main__":
    {"items": items, "score": score}[sys.argv[1]]()
