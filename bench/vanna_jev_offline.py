"""Same-SQL view: TypeSafe Jev variant b (bench/jev_judge.py, as vanna_jev / mnemiq_jev_v2) on plain Vanna's saved SQLs
(system `vanna`, 29 + holdout, 132 attempts). Schema = the DDL statements that attempt retrieved (raw.ddl_tables, in
order, from vanna/training/ddl.sql). Each SQL is executed read-only; SQL that fails to execute is not judged (as online).
Correctness = harness EX, with ho14 tie-valid and ho12 collation answers re-labelled right (mnemiq_jev_analysis.label).
Writes results/run-gptoss120b-vanna-r3/jev_offline.jsonl (+ prints a summary)."""
import json, os, sys, pathlib
import psycopg, yaml
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from common import ROOT, load_env, compare
import jev_judge as J
from mnemiq_jev_analysis import label

SETS = [("29", "run-gptoss120b-vanna-r3", "bench/questions.yaml"), ("holdout", "run-gptoss120b-holdout-r3", "bench/questions_holdout.yaml")]
OUT = ROOT / "results/run-gptoss120b-vanna-r3/jev_offline.jsonl"
DDL = {d.split("(", 1)[0].replace("CREATE TABLE", "").strip(): d for d in (ROOT / "vanna/training/ddl.sql").read_text().strip().split("\n\n")}


def main():
    env = load_env(); os.environ.setdefault("TYPESAFE_API_KEY", env.get("TYPESAFE_API_KEY", ""))
    conn = psycopg.connect(env["BENCH_DB_URL"]); out = []
    for name, run, qf in SETS:
        d = yaml.safe_load(open(ROOT / qf)); qs = {q["id"]: q for q in (d["questions"] if isinstance(d, dict) else d)}
        for l in open(ROOT / "results" / run / "raw.jsonl"):
            r = json.loads(l)
            if r["system"] != "vanna":
                continue
            q = qs[r["id"]]; sql = r.get("generated") or ""
            schema = "\n\n".join(DDL[t] for t in (r.get("raw") or {}).get("ddl_tables") or [])
            with conn.cursor() as cur:
                cur.execute("BEGIN READ ONLY"); cur.execute(q["gold_sql"]); gold = cur.fetchall(); conn.rollback()
            rec = {"set": name, "id": r["id"], "run": r["run"], "status": r["status"], "sql": sql}
            try:
                with conn.cursor() as cur:
                    cur.execute("BEGIN READ ONLY"); cur.execute("SET LOCAL statement_timeout = 30000"); cur.execute(sql)
                    cols = [c.name for c in cur.description]; rows = cur.fetchall()
                conn.rollback()
            except Exception as e:
                conn.rollback(); rec.update(exec_ok=False, right=False, how=f"exec error: {str(e)[:80]}"); out.append(rec); continue
            ok, how = (True, "exact") if r["status"] in ("correct", "correct_extra_cols") else label(conn, env["BENCH_DB_URL"], q, sql, gold)
            j = J.judge(q["question"], schema, sql, J.render_result(cols, rows))
            rec.update(exec_ok=True, rows=len(rows), right=ok, how=how, **{f"jev_{k}": j.get(k) for k in ("p", "status", "fell_open", "reason", "latency_ms", "input_tokens")})
            out.append(rec)
    OUT.write_text("".join(json.dumps(x, default=str) + "\n" for x in out))
    judged = [x for x in out if x.get("exec_ok")]
    fo = [x for x in judged if x["jev_fell_open"]]
    blk = lambda x: (not x["jev_fell_open"]) and x["jev_p"] < J.THRESHOLD
    print(f"attempts {len(out)}; judged {len(judged)}; exec failed (unjudged) {len(out)-len(judged)}; Jev fell open {len(fo)}; HTTP {sorted({x['jev_status'] for x in judged})}")
    for nm, S in (("29", "29"), ("holdout", "holdout"), ("all", None)):
        X = [x for x in judged if S is None or x["set"] == S]
        print(f"{nm:8} right passed {sum(x['right'] and not blk(x) for x in X):3}  right BLOCKED {sum(x['right'] and blk(x) for x in X):2}  "
              f"wrong CAUGHT {sum((not x['right']) and blk(x) for x in X):2}  wrong passed {sum((not x['right']) and not blk(x) for x in X):2}")
    tok = sum(x.get("jev_input_tokens") or 0 for x in judged)
    print(f"Jev input tokens {tok:,}  cost ${tok*J.PRICE_PER_INPUT_TOKEN:.4f}")
    for x in out:
        if not x["right"] or (x.get("exec_ok") and blk(x)):
            print(f"  {x['set']}:{x['id']} r{x['run']} status={x['status']} right={x['right']} ({x['how']}) p={x.get('jev_p')}")


if __name__ == "__main__":
    main()
