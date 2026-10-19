"""Connect WrenAI and DB-GPT to the shared Postgres (idempotent), and check Cube's model.

WrenAI : GraphQL onboarding on wren-ui (saveDataSource -> saveTables -> saveRelations -> deploy)
DB-GPT : POST /api/v2/serve/datasources (type=postgresql)
Cube   : GET /cubejs-api/v1/meta (model is mounted from ./cube/model; DB set via compose env)
Usage: python bench/setup_connections.py [--force] [--only wren|dbgpt|cube]
"""
import argparse, json, sys, time
import httpx
from common import load_env, cube_token

env = load_env()
PG = dict(host=env["BENCH_PG_HOST"], port=int(env["BENCH_PG_PORT"]), database=env["BENCH_PG_DB"],
          user=env["BENCH_PG_USER"], password=env["BENCH_PG_PASSWORD"])
WREN = f"http://localhost:{env.get('WREN_UI_PORT', '3000')}"
DBGPT = f"http://localhost:{env.get('DBGPT_PORT', '5670')}"
CUBE = f"http://localhost:{env.get('CUBE_PORT', '4000')}"


def gql(c, query, variables=None, wren=None):
    r = c.post(f"{wren or WREN}/api/graphql", json={"query": query, "variables": variables or {}}, timeout=180)
    r.raise_for_status()
    j = r.json()
    if j.get("errors"):
        raise RuntimeError(json.dumps(j["errors"])[:800])
    return j["data"]


PG_KEYS_SQL = """
SELECT c.contype, rel.relname, array_agg(a.attname ORDER BY k.ord), frel.relname,
       array_agg(fa.attname ORDER BY k.ord)
FROM pg_constraint c
JOIN pg_class rel ON rel.oid = c.conrelid
JOIN pg_namespace n ON n.oid = rel.relnamespace AND n.nspname = 'public'
CROSS JOIN LATERAL unnest(c.conkey, COALESCE(c.confkey, c.conkey)) WITH ORDINALITY AS k(col, fcol, ord)
JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = k.col
LEFT JOIN pg_class frel ON frel.oid = c.confrelid
LEFT JOIN pg_attribute fa ON fa.attrelid = c.confrelid AND fa.attnum = k.fcol
WHERE c.contype IN ('p', 'f')
GROUP BY c.oid, c.contype, rel.relname, frel.relname
"""


def wren_keys_and_relations(c):
    """WrenAI discovers PK/FK via information_schema views that hide constraints from a
    non-owner (read-only) role, so we read them from pg_catalog and set them through the
    same GraphQL mutations the Wren UI uses (updateModel / saveRelations)."""
    import psycopg
    with psycopg.connect(env["BENCH_DB_URL"]) as conn:
        rows = conn.execute(PG_KEYS_SQL).fetchall()
    q = "{ listModels { id sourceTableName fields { id sourceColumnName } } }"
    models = gql(c, q)["listModels"]
    by_table = {m["sourceTableName"].split(".")[-1]: m for m in models}
    n_pk = 0
    for typ, tbl, cols, _, _ in rows:
        if typ == "p" and len(cols) == 1 and tbl in by_table:
            m = by_table[tbl]
            gql(c, "mutation($w: ModelWhereInput!, $d: UpdateModelInput!){ updateModel(where:$w, data:$d) }",
                {"w": {"id": m["id"]}, "d": {"fields": [f["sourceColumnName"] for f in m["fields"]], "primaryKey": cols[0]}})
            n_pk += 1
    models = gql(c, q)["listModels"]  # refresh field ids
    by_table = {m["sourceTableName"].split(".")[-1]: m for m in models}
    fid = lambda t, col: next(f["id"] for f in by_table[t]["fields"] if f["sourceColumnName"] == col)
    rels = []
    for typ, tbl, cols, ftbl, fcols in rows:
        if typ == "f" and len(cols) == 1 and tbl in by_table and ftbl in by_table:
            rels.append({"fromModelId": by_table[tbl]["id"], "fromColumnId": fid(tbl, cols[0]),
                         "toModelId": by_table[ftbl]["id"], "toColumnId": fid(ftbl, fcols[0]), "type": "MANY_TO_ONE"})
    gql(c, "mutation($d: SaveRelationInput!){ saveRelations(data:$d) }", {"d": {"relations": rels}})
    return n_pk, len(rels)


def setup_wren(force):
    with httpx.Client() as c:
        st = gql(c, "{ onboardingStatus { status } }")["onboardingStatus"]["status"]
        print(f"[wren] onboarding status: {st}")
        if st == "ONBOARDING_FINISHED" and not force:
            print("[wren] already connected; re-deploying to (re)index schema")
        else:
            gql(c, "mutation($d: DataSourceInput!){ saveDataSource(data:$d){ type } }",
                {"d": {"type": "POSTGRES", "properties": {"displayName": "chinook-bench", **PG, "ssl": False}}})
            print("[wren] data source saved (connection test passed)")
            tables = [t["name"] for t in gql(c, "{ listDataSourceTables { name } }")["listDataSourceTables"]]
            print(f"[wren] tables: {tables}")
            gql(c, "mutation($d: SaveTablesInput!){ saveTables(data:$d) }", {"d": {"tables": tables}})
            n_pk, n_rel = wren_keys_and_relations(c)
            print(f"[wren] set {n_pk} primary keys, saved {n_rel} FK relations (read from pg_catalog)")
        d = gql(c, "mutation{ deploy(force:true) }")["deploy"]
        print(f"[wren] deploy -> {json.dumps(d)[:300]}")
        if d.get("status") == "FAILED":
            print("[wren] NOTE: deploy = schema indexing into qdrant via the embedding model; it fails without a "
                  "valid LLM_API_KEY / reachable embedding model. Set the key, then `make up` (recreates containers with the key) to redeploy.")
        return d


REFRESH = False


def setup_dbgpt(force):
    with httpx.Client(base_url=DBGPT, timeout=180) as c:
        items = c.get("/api/v2/serve/datasources").json()["data"]
        existing = [d for d in items if d.get("db_name") == PG["database"]]
        if existing and not force:
            ds_id = existing[0]["id"]
            if REFRESH:
                r = c.post(f"/api/v2/serve/datasources/{ds_id}/refresh")
                print(f"[dbgpt] schema re-embedding triggered (async) -> HTTP {r.status_code}")
            else:
                # DB-GPT re-embeds every datasource on startup; calling /refresh concurrently with that
                # races (delete_db_profile drops the chroma collection mid-write -> 'Collection ... does
                # not exist', 0/11 chunks). So only refresh on explicit request.
                print(f"[dbgpt] datasource '{PG['database']}' exists (id={ds_id}); schema is embedded at "
                      f"DB-GPT startup (use --refresh to force)")
            return existing[0]
        for d in existing:
            c.delete(f"/api/v2/serve/datasources/{d['id']}")
        r = c.post("/api/v2/serve/datasources", json={
            "type": "postgresql", "description": "Chinook benchmark DB",
            "params": {**PG, "schema": "public", "driver": "postgresql+psycopg2"}})
        j = r.json()
        print(f"[dbgpt] create datasource -> HTTP {r.status_code} success={j.get('success')} "
              f"{'' if j.get('success') else str(j)[:400]}")
        return j


def check_cube():
    r = httpx.get(f"{CUBE}/cubejs-api/v1/meta", headers={"Authorization": cube_token(env["CUBEJS_API_SECRET"])}, timeout=60)
    r.raise_for_status()
    cubes = [c["name"] for c in r.json()["cubes"]]
    print(f"[cube] model loaded: {len(cubes)} cubes {cubes}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--only", choices=["wren", "dbgpt", "cube"])
    ap.add_argument("--refresh", action="store_true", help="DB-GPT: re-embed schema now")
    a = ap.parse_args()
    REFRESH = a.refresh
    ok = True
    for name, fn in [("wren", lambda: setup_wren(a.force)), ("dbgpt", lambda: setup_dbgpt(a.force)), ("cube", check_cube)]:
        if a.only and a.only != name:
            continue
        try:
            fn()
        except Exception as e:
            ok = False
            print(f"[{name}] SETUP ERROR: {e}")
    sys.exit(0 if ok else 1)
