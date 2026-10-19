"""Health/connectivity probe: hits each system's real API once (works without an LLM key:
expect an auth error from the LLM upstream, which proves the request path is wired)."""
import json, time, httpx
from common import load_env, cube_token
from clients import WrenClient, DBGPTClient, CubeClient

env = load_env()
p = lambda *a: print(*a, flush=True)
chk = [("postgres (via harness URL)", lambda: __import__("psycopg").connect(env["BENCH_DB_URL"]).execute("select count(*) from track").fetchone()[0]),
       ("llm-meter /health", lambda: httpx.get(f"http://localhost:{env['METER_PORT']}/health").json()),
       ("wren-ai-service /health", lambda: httpx.get(f"http://localhost:{env['WREN_AI_PORT']}/health").json()),
       ("wren-ui onboarding", lambda: httpx.post(f"http://localhost:{env['WREN_UI_PORT']}/api/graphql", json={"query": "{ onboardingStatus { status } }"}).json()["data"]),
       ("wren-ui datasource", lambda: httpx.post(f"http://localhost:{env['WREN_UI_PORT']}/api/graphql", json={"query": "{ settings { dataSource { type properties } } }"}).json()["data"]["settings"]["dataSource"]),
       ("dbgpt datasources", lambda: [(d["db_name"], d["type"]) for d in httpx.get(f"http://localhost:{env['DBGPT_PORT']}/api/v2/serve/datasources").json()["data"]]),
       ("cube /v1/meta", lambda: len(httpx.get(f"http://localhost:{env['CUBE_PORT']}/cubejs-api/v1/meta", headers={"Authorization": cube_token(env['CUBEJS_API_SECRET'])}).json()["cubes"])),
       ]
for name, fn in chk:
    try:
        p(f"OK   {name}: {json.dumps(fn(), default=str)[:200]}")
    except Exception as e:
        p(f"FAIL {name}: {e}")
q = "How many tracks are there in total?"
for c in (WrenClient(env), DBGPTClient(env), CubeClient(env)):
    t = time.time()
    try:
        r = c.generate(q)
    except Exception as e:
        r = {"error": f"exception {e}"}
    p(f"API  {c.name:7} {time.time()-t:5.1f}s -> {json.dumps({k: v for k, v in r.items() if k != 'raw'}, default=str)[:400]}")
