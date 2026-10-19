"""Verify every gold SQL runs, and that the Cube reference queries reproduce the gold results."""
import sys, yaml, psycopg
from common import ROOT, load_env, compare
from clients import CubeClient

env = load_env()
qs = yaml.safe_load(open(ROOT / "bench" / "questions.yaml"))["questions"]
conn = psycopg.connect(env["BENCH_DB_URL"])
cube = CubeClient(env, mock=True)
bad = 0
print(f"{'id':4} {'gold rows':>9}  cube-reference")
for q in qs:
    try:
        g = conn.execute(q["gold_sql"]).fetchall()
    except Exception as e:
        print(f"{q['id']:4} GOLD FAILED: {e}"); bad += 1; conn.rollback(); continue
    c = "n/a (not expressible)"
    if q["id"] in cube.ref:
        r = cube.generate(q["question"], qid=q["id"])
        if "error" in r:
            c = f"ERROR {r['error'][:120]}"; bad += 1
        else:
            m = compare(g, r["rows"], q.get("order_matters", False), q.get("order_cols"))
            c = "exact match" if m["exact"] else (f"relaxed ({m['reason']})" if m["relaxed"] else f"MISMATCH ({m['reason']})")
            bad += 0 if m["relaxed"] else 1
    elif q.get("cube_expressible"):
        c = "MISSING reference query"; bad += 1
    print(f"{q['id']:4} {len(g):9}  {c}")
print(f"\n{len(qs)} questions, problems: {bad}")
sys.exit(1 if bad else 0)
