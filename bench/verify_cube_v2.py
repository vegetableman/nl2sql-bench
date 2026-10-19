"""make verify (cube_v2 part): run every hand-written Cube SQL API reference query through cube_v2's SQL API
(Postgres wire protocol, port CUBE_V2_SQL_PORT) and compare with the gold result. Prints which questions the
cube_v2 model can express, and whether each query was answered by Cube."""
import sys, yaml, psycopg
from common import ROOT, load_env, compare

env = load_env()
qs = yaml.safe_load(open(ROOT / "bench" / "questions.yaml"))
qs = qs["questions"] if isinstance(qs, dict) else qs
ref = yaml.safe_load(open(ROOT / "bench" / "cube_v2_reference_sql.yaml"))
gold_conn = psycopg.connect(env["BENCH_DB_URL"], autocommit=True)
cube = lambda: psycopg.connect(host="localhost", port=int(env.get("CUBE_V2_SQL_PORT", "15432")), user=env.get("CUBE_SQL_USER", "cube"),
                               password=env.get("CUBE_SQL_PASSWORD", "cube-local"), dbname="db", autocommit=True)


def rows(conn, sql):
    with conn.cursor() as c:
        c.execute(sql)
        return [list(r) for r in c.fetchall()]


ok = 0
for q in qs:
    sql = ref.get(q["id"])
    if not sql:
        print(f"{q['id']}: no reference query (not expressible)"); continue
    try:
        with cube() as cc:
            pred = rows(cc, sql)
    except Exception as e:
        print(f"{q['id']}: CUBE ERROR {str(e).strip()[:300]}"); continue
    cmp = compare(rows(gold_conn, q["gold_sql"]), pred, q.get("order_matters", False), q.get("order_cols"))
    ok += cmp["exact"]
    print(f"{q['id']}: {'OK ' if cmp['exact'] else 'MISMATCH'} {cmp['reason']}")
print(f"\ncube_v2 reference queries reproducing gold: {ok}/{len(qs)}")
sys.exit(0 if ok else 1)
