"""mnemiq_jev (TypeSafe Jev judge, fail-closed) vs mnemiq_verified (gpt-oss judge, 1200 tok) on the same harness runs.

Joins the harness records with the per-call `BENCH-JEV` lines that patches/jev-judge.patch writes to mnemiq/serve-jev.log
(committed copy: results/run-gptoss120b-mnemiq-r3/jev_calls.log), in order (the harness is sequential). Every declined
answer's SQL (from the log line) is executed the way mnemiq does (DuckDB over the same Postgres) and labelled against gold
with the harness `compare` -- ho14 tie-tolerant and ho12 collation-tolerant exactly as in bench/judge_comparison.py.
Writes results/run-gptoss120b-mnemiq-r3/jev_analysis.md.
"""
import ast, json, re
from collections import Counter, defaultdict
import psycopg, yaml
from common import ROOT, load_env, compare
import mnemiq_verifier_analysis as va

LOG = ROOT / "mnemiq/serve-jev.log"
if not LOG.exists():
    LOG = ROOT / "results/run-gptoss120b-mnemiq-r3/jev_calls.log"
SETS = [("29", "run-gptoss120b-mnemiq-r3", "bench/questions.yaml"), ("holdout", "run-gptoss120b-holdout-r3", "bench/questions_holdout.yaml")]
LINE = re.compile(r"BENCH-JEV (.*?) q=(.*?) sql=(\".*\")\s*$")
PRICE = 0.042 / 1e6


def jev_lines():
    out = []
    for l in open(LOG, encoding="utf-8"):
        m = LINE.search(l)
        if m:
            kv = dict(x.split("=", 1) for x in m[1].split() if "=" in x)
            out.append({**kv, "q": ast.literal_eval(m[2]), "sql": json.loads(m[3])})
    return out


def label(conn, dsn, q, sql, gold):
    rows, where = va.execute(conn, dsn, sql)
    if rows is None:
        return False, f"exec failed ({where})"
    om, oc = q.get("order_matters", False), q.get("order_cols")
    if compare(gold, rows, om, oc)["exact"]:
        return True, "exact"
    if compare(gold, rows)["exact"]:
        try:
            with conn.cursor() as cur:
                cur.execute("BEGIN READ ONLY"); cur.execute(sql); pg = cur.fetchall(); conn.rollback()
            if compare(gold, pg, om, oc)["exact"]:
                return True, "same rows; DuckDB collation order differs, exact on Postgres"
        except Exception:
            conn.rollback()
    alts = va.tie_alternatives(conn, q)
    if alts and any(compare(a, rows, om, oc)["exact"] for a in alts):
        return True, "valid under gold boundary tie"
    return False, "wrong"


def main():
    env = load_env(); conn = psycopg.connect(env["BENCH_DB_URL"]); jl = jev_lines(); ji = 0
    recs, other = [], defaultdict(dict)
    for name, run, qf in SETS:
        qs = {q["id"]: q for q in yaml.safe_load(open(ROOT / qf))["questions"]}
        for l in open(ROOT / "results" / run / "raw.jsonl"):
            r = json.loads(l)
            if r["system"] == "mnemiq_jev":
                r["_set"], r["_q"] = name, qs[r["id"]]; recs.append(r)
            elif r["system"] in ("mnemiq", "mnemiq_verified", "mnemiq_failopen"):
                other[r["system"]][(name, r["id"], str(r["run"]))] = r["status"]
    recs.sort(key=lambda r: r["t_start_epoch"])
    for r in recs:
        mine = []
        while ji < len(jl) and jl[ji]["q"] == r["_q"]["question"][:70]:
            mine.append(jl[ji]); ji += 1
        r["_jev"] = mine
    gold = {}
    L = ["# mnemiq_jev: TypeSafe Jev as mnemiq's judge (fail-closed, threshold 0.5)", "",
         f"Jev log lines: {len(jl)}; matched to attempts: {ji}; unmatched: {len(jl) - ji}; "
         f"HTTP statuses: {dict(Counter(x.get('status') for x in jl))}; attempts with more than one Jev call: {sum(len(r['_jev']) > 1 for r in recs)}; "
         f"attempts with none: {sum(not r['_jev'] for r in recs)}.", "",
         "Jev calls bypass llm-meter, so they are counted from the log; `input_tokens` is the API's own `usage.input_tokens` (not estimated). "
         "Cost = input tokens x $0.042 per million (output tokens are free).", "",
         "| set | attempts | Jev calls | Jev input tokens (total) | avg per call | est. Jev cost | Jev latency p50 / p95 ms | passed | declined (verification) | judge unavailable | other |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    for name, _, _ in SETS:
        rs = [r for r in recs if r["_set"] == name]; calls = [x for r in rs for x in r["_jev"]]
        toks = [int(x["input_tokens"]) for x in calls if x.get("input_tokens", "None") != "None"]
        lat = sorted(float(x["latency_ms"]) for x in calls if x.get("latency_ms"))
        c = Counter("declined" if (r.get("raw") or {}).get("reason_code") == "verification" else "unavailable" if (r.get("raw") or {}).get("reason_code") == "verifier_unavailable"
                    else "passed" if (r.get("raw") or {}).get("verified") == "judged" else "other" for r in rs)
        L.append(f"| {name} | {len(rs)} | {len(calls)} | {sum(toks):,} | {sum(toks)/max(1,len(toks)):,.0f} | ${sum(toks)*PRICE:.4f} | "
                 f"{(f'{lat[len(lat)//2]:.0f} / {lat[int(0.95*(len(lat)-1))]:.0f}' if lat else 'n/a')} | {c['passed']} | {c['declined']} | {c['unavailable']} | {c['other']} |")
    L += ["", "## Every decline: was its SQL actually right?", "",
          "| set | id | run | Jev noul | SQL right? | how | mnemiq_verified same attempt | mnemiq_failopen same attempt | SQL |", "|---|---|---|---|---|---|---|---|---|"]
    dec_right = dec_wrong = 0
    for r in recs:
        if (r.get("raw") or {}).get("reason_code") != "verification":
            continue
        q = r["_q"]; k = (r["_set"], q["id"])
        if k not in gold:
            with conn.cursor() as cur:
                cur.execute("BEGIN READ ONLY"); cur.execute(q["gold_sql"]); gold[k] = cur.fetchall(); conn.rollback()
        x = r["_jev"][-1] if r["_jev"] else None
        ok, how = label(conn, env["BENCH_DB_URL"], q, x["sql"], gold[k]) if x else (None, "no logged call")
        dec_right += ok is True; dec_wrong += ok is False
        key = (r["_set"], r["id"], str(r["run"]))
        L.append(f"| {r['_set']} | {r['id']} | {r['run']} | {x.get('noul') if x else '–'} | {'RIGHT' if ok else 'wrong' if ok is False else '?'} | {how} | "
                 f"{other['mnemiq_verified'].get(key, '-')} | {other['mnemiq_failopen'].get(key, '-')} | `{(x['sql'] if x else '')[:150].replace('|', '/')}` |")
    passed_wrong = [r for r in recs if r["status"] == "wrong_result"]
    pw = []
    for r in passed_wrong:
        q = r["_q"]; k = (r["_set"], q["id"])
        if k not in gold:
            with conn.cursor() as cur:
                cur.execute("BEGIN READ ONLY"); cur.execute(q["gold_sql"]); gold[k] = cur.fetchall(); conn.rollback()
        ok, how = label(conn, env["BENCH_DB_URL"], q, r["_jev"][-1]["sql"], gold[k]) if r["_jev"] else (None, "?")
        pw.append(f"{r['_set']}:{r['id']} r{r['run']} (noul {r['_jev'][-1].get('noul') if r['_jev'] else '?'}; re-labelled: {'right, ' + how if ok else 'genuinely wrong'})")
    L += ["", f"Declines: {dec_right + dec_wrong}; SQL actually right: **{dec_right}** (correct answers blocked); actually wrong: **{dec_wrong}** (real mistakes caught).", "",
          "Answers passed by Jev and scored `wrong_result` by the harness: " + ("; ".join(pw) or "none"), "",
          "## Per question vs mnemiq_verified and mnemiq_failopen (r1 r2 r3)", "",
          "| set | id | mnemiq_jev | mnemiq_verified | mnemiq_failopen |", "|---|---|---|---|---|"]
    ab = {"correct": "✓", "correct_extra_cols": "≈", "wrong_result": "✗", "declined": "🚫", "tool_error": "⚠", "exec_error": "E", "timeout": "T"}
    by = defaultdict(dict)
    for r in recs:
        by[(r["_set"], r["id"])][str(r["run"])] = r["status"]
    for (name, qid), d in by.items():
        j = "".join(ab.get(d.get(k, "-"), "?") for k in "123")
        v = "".join(ab.get(other["mnemiq_verified"].get((name, qid, k), "-"), "?") for k in "123")
        f = "".join(ab.get(other["mnemiq_failopen"].get((name, qid, k), "-"), "?") for k in "123")
        if not (j == v == f == "✓✓✓"):
            L.append(f"| {name} | {qid} | {j} | {v} | {f} |")
    L += ["", "(Listed only where any of the three is not ✓✓✓. ✓ exact, ✗ wrong, 🚫 declined, ⚠ tool error. Generation differs run to run, "
          "so this is attempt vs attempt; the same-SQL comparison is results/judge-comparison/.)", ""]
    txt = "\n".join(L); (ROOT / "results/run-gptoss120b-mnemiq-r3/jev_analysis.md").write_text(txt); print(txt)


if __name__ == "__main__":
    main()
