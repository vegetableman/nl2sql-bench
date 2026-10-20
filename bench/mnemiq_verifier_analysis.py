"""Verifier-outcome analysis for `mnemiq_verified` (judge max_tokens 1200, fail-closed).

Joins the harness records (raw.jsonl) with the per-judge-call log lines written by
mnemiq/patches/verifier-tokens.patch (`BENCH-JUDGE ... conf=... q=... sql=...` in mnemiq/serve-verified.log),
in order (the harness is sequential). For every answer the judge REJECTED or could not read, the SQL the judge
saw is executed read-only and scored against gold with the harness's own `compare` -- first on Postgres, then,
if it is DuckDB dialect, through DuckDB's postgres scanner (mnemiq's own executor, engine-verified venv).
Writes results/run-gptoss120b-mnemiq-r3/verifier_analysis.md; prints the same text.
"""
import csv, json, re, subprocess, sys
from collections import Counter, defaultdict
import psycopg, yaml
from common import ROOT, load_env, compare

LOG = ROOT / "mnemiq/serve-verified.log"  # git-ignored; its BENCH-JUDGE lines are committed as judge_calls.log
if not LOG.exists():
    LOG = ROOT / "results/run-gptoss120b-mnemiq-r3/judge_calls.log"
DUCK_PY = ROOT / "mnemiq/engine-verified/.venv/bin/python"
SETS = [("29", "run-gptoss120b-mnemiq-r3", "bench/questions.yaml"),
        ("holdout", "run-gptoss120b-holdout-r3", "bench/questions_holdout.yaml")]
LINE = re.compile(r"BENCH-JUDGE max_tokens=(\d+) reply_chars=(\d+) conf=(\S+) q=(.*?) sql=(\".*\")\s*$")
DUCK = r'''
import duckdb, json, sys
d = json.load(sys.stdin); con = duckdb.connect()
con.execute("ATTACH '" + d["dsn"].replace("'", "''") + "' AS src (TYPE postgres, READ_ONLY)"); con.execute("USE src.public")
print(json.dumps([list(r) for r in con.execute(d["sql"]).fetchall()], default=str))
'''


def judge_lines():
    out = []
    for l in open(LOG, encoding="utf-8"):
        m = LINE.search(l)
        if m:
            import ast
            out.append({"max_tokens": int(m[1]), "reply_chars": int(m[2]), "conf": None if m[3] == "None" else float(m[3]),
                        "q": ast.literal_eval(m[4]), "sql": json.loads(m[5])})
    return out


def execute(conn, dsn, sql):
    """DuckDB over Postgres first (mnemiq's own executor, so its dialect and arithmetic), then Postgres."""
    p = subprocess.run([str(DUCK_PY), "-c", DUCK], input=json.dumps({"dsn": dsn, "sql": sql}), capture_output=True, text=True, timeout=120)
    if p.returncode == 0:
        return json.loads(p.stdout), "duckdb (mnemiq's executor)"
    dk = next((x for x in p.stderr.splitlines() if "Error" in x), "failed").replace(dsn, "<DSN>")[:120]
    try:
        with conn.cursor() as cur:
            cur.execute("BEGIN READ ONLY")
            try:
                cur.execute(sql); return cur.fetchall(), "postgres (duckdb failed)"
            finally:
                conn.rollback()
    except Exception as e:
        return None, f"duckdb: {dk}; pg: {type(e).__name__}"


def tie_alternatives(conn, q):
    """Gold sets for a `... LIMIT n` gold whose n-th row ties with the next: first n-1 rows + any tied row."""
    sql = q["gold_sql"].strip().rstrip(";"); m = re.search(r"\bLIMIT\s+(\d+)\s*$", sql, re.I)
    if not m:
        return None
    n = int(m[1])
    with conn.cursor() as cur:
        cur.execute("BEGIN READ ONLY"); cur.execute(sql[:m.start()]); full = cur.fetchall(); conn.rollback()
    oc = q.get("order_cols") or [len(full[0]) - 1]; key = lambda r: tuple(r[i] for i in oc)
    if len(full) <= n or key(full[n - 1]) != key(full[n]):
        return None
    head = [r for r in full if key(r) != key(full[n - 1])][: n - 1]
    return [head + [r] for r in full if key(r) == key(full[n - 1])]


def tie_verdict(conn, q, pred):
    alts = tie_alternatives(conn, q)
    if alts is None or pred is None:
        return ""
    ok = any(compare(a, pred, q.get("order_matters", False), q.get("order_cols"))["exact"] for a in alts)
    return "valid under gold boundary tie" if ok else "wrong even allowing the tie"


def main():
    env = load_env(); conn = psycopg.connect(env["BENCH_DB_URL"])
    jl = judge_lines(); ji = 0
    recs, fo = [], {}
    for name, run, qf in SETS:
        qs = {q["id"]: q for q in yaml.safe_load(open(ROOT / qf))["questions"]}
        for l in open(ROOT / "results" / run / "raw.jsonl"):
            r = json.loads(l)
            if r["system"] == "mnemiq_failopen":
                fo[(name, r["id"], str(r["run"]))] = r["status"]
            if r["system"] == "mnemiq_verified":
                r["_set"], r["_q"] = name, qs[r["id"]]; recs.append(r)
    recs.sort(key=lambda r: r["t_start_epoch"])
    for r in recs:  # consume this attempt's judge lines (same question prefix, in order)
        mine = []
        while ji < len(jl) and jl[ji]["q"] == r["_q"]["question"][:70]:
            mine.append(jl[ji]); ji += 1
        r["_judge"] = mine
    unmatched = len(jl) - ji
    gold = {}
    rows_out = []
    cnt = defaultdict(Counter)
    for r in recs:
        raw = r.get("raw") or {}; j = r["_judge"][-1] if r["_judge"] else None
        if r["status"] == "declined" and raw.get("reason_code") == "verification":
            cat = "rejected"
        elif raw.get("reason_code") == "verifier_unavailable":
            cat = "unavailable"
        elif raw.get("verified") == "judged" and not raw.get("deferred") and not raw.get("failed"):
            cat = "passed"
        else:
            cat = f"other ({r['status']}: {raw.get('reason_code')})"
        r["_cat"] = cat; cnt[r["_set"]][cat] += 1
        r["_empty"] = sum(1 for x in r["_judge"] if x["reply_chars"] == 0)
        if cat in ("rejected", "unavailable") and j:
            q = r["_q"]; key = (r["_set"], q["id"])
            if key not in gold:
                with conn.cursor() as cur:
                    cur.execute("BEGIN READ ONLY"); cur.execute(q["gold_sql"]); gold[key] = cur.fetchall(); conn.rollback()
            pred, where = execute(conn, env["BENCH_DB_URL"], j["sql"])
            verdict = "exec failed" if pred is None else (lambda c: "RIGHT (exact)" if c["exact"] else "right (extra cols)" if c["relaxed"] else "WRONG")(
                compare(gold[key], pred, q.get("order_matters", False), q.get("order_cols")))
            tv = tie_verdict(conn, q, pred)
            rows_out.append((r["_set"], r["id"], r["run"], cat, j["conf"], verdict + (f" / {tv}" if tv else ""), where,
                             fo.get((r["_set"], r["id"], str(r["run"])), "-"), j["sql"]))
    L = ["# mnemiq_verified: verifier outcomes", "",
         "Judge = mnemiq's `SemanticJudge` with `max_tokens=1200` (patches/verifier-tokens.patch), fail-closed, threshold 0.5. "
         "Per-call data from the patch's log line; SQL of rejected answers re-executed (DuckDB over the same Postgres, i.e. mnemiq's executor) and re-scored against gold by `bench/mnemiq_verifier_analysis.py`.", "",
         f"Judge calls logged: {len(jl)}; matched to attempts: {len(jl) - unmatched}; unmatched: {unmatched}; "
         f"empty replies (reply_chars=0, the finish_reason=length signature): {sum(1 for x in jl if x['reply_chars'] == 0)}; "
         f"calls returning more than one judge line per attempt: {sum(1 for r in recs if len(r['_judge']) > 1)}.", "",
         "| set | attempts | checked & passed | rejected (declined: verification) | unavailable (verifier_unavailable) | other |", "|---|---|---|---|---|---|"]
    for name, _, _ in SETS:
        c = cnt[name]; oth = sum(v for k, v in c.items() if k.startswith("other"))
        L.append(f"| {name} | {sum(c.values())} | {c['passed']} | {c['rejected']} | {c['unavailable']} | {oth} |")
    L += ["", "## Passed by the judge: correctness", "", "| set | passed | of which EX exact | relaxed only | wrong_result | exec_error |", "|---|---|---|---|---|---|"]
    for name, _, _ in SETS:
        p = [r for r in recs if r["_set"] == name and r["_cat"] == "passed"]; s = Counter(r["status"] for r in p)
        L.append(f"| {name} | {len(p)} | {s['correct']} | {s['correct_extra_cols']} | {s['wrong_result']} | {s['exec_error']} |")
    wrong_passed = [r for r in recs if r["_cat"] == "passed" and r["status"] not in ("correct",)]
    wp = []
    for r in wrong_passed:
        pred, _ = execute(conn, env["BENCH_DB_URL"], r["_judge"][-1]["sql"]) if r["_judge"] else (None, "")
        tv = tie_verdict(conn, r["_q"], pred)
        wp.append(f"{r['_set']}:{r['id']} r{r['run']} ({r['status']} as scored, judge conf {r['_judge'][-1]['conf'] if r['_judge'] else '?'}" + (f"; re-executed: {tv}" if tv else "") + ")")
    L += ["", "Non-exact answers the judge passed: " + ("; ".join(wp) or "none"), "",
          "Gold-tie note: ho14's gold (`ORDER BY revenue DESC LIMIT 3`) has a four-way tie for 3rd place (weeks 8, 30, 39, 47, "
          "22.77 each), and the gold arbitrarily keeps one, so a correct query can be scored `wrong_result` depending on the "
          "executor's tie order (it is not even stable between executions). Harness scoring is left unchanged; the "
          "'valid under gold boundary tie' verdicts above re-check against every tie choice with the same `compare`. "
          "No other gold query in either set has a tie at its LIMIT boundary.", ""]
    L += ["## Every rejected / unavailable answer: was its SQL actually right?", "",
          "| set | id | run | outcome | judge conf | SQL vs gold | executed on | mnemiq_failopen same attempt | SQL the judge saw |", "|---|---|---|---|---|---|---|---|---|"]
    for t in rows_out:
        L.append("| " + " | ".join(str(x) for x in t[:8]) + " | `" + t[8].replace("|", "/").replace("\n", " ")[:220] + "` |")
    if not rows_out:
        L.append("| – | – | – | none | – | – | – | – | – |")
    L += ["", "## Per question vs mnemiq_failopen (status per run r1/r2/r3)", "", "| set | id | mnemiq_verified | mnemiq_failopen |", "|---|---|---|---|"]
    ab = {"correct": "✓", "correct_extra_cols": "≈", "wrong_result": "✗", "declined": "🚫", "tool_error": "⚠", "exec_error": "E", "timeout": "T"}
    by = defaultdict(dict)
    for r in recs:
        by[(r["_set"], r["id"])][str(r["run"])] = r["status"]
    for (name, qid), d in by.items():
        v = "".join(ab.get(d.get(k, "-"), "?") for k in ("1", "2", "3")); f = "".join(ab.get(fo.get((name, qid, k), "-"), "?") for k in ("1", "2", "3"))
        if v != "✓✓✓" or f != "✓✓✓":
            L.append(f"| {name} | {qid} | {v} | {f} |")
    L += ["", "(Only questions where either system was not ✓✓✓ are listed; all others were exact in all 3 runs for both. "
          "✓ exact, ≈ extra cols, ✗ wrong, 🚫 declined, ⚠ tool error.)", ""]
    txt = "\n".join(L)
    (ROOT / "results/run-gptoss120b-mnemiq-r3/verifier_analysis.md").write_text(txt)
    print(txt)


if __name__ == "__main__":
    main()
