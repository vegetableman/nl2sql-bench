"""One client per system. Each .generate(question) returns a dict:
   {sql | cube_query, rows (Cube only, already executed via Cube API), error, raw, llm_usage(optional)}
Latency is measured by the harness around .generate()."""
import html, json, pathlib, random, re, time
import httpx, yaml
from common import ROOT, cube_token

TIMEOUT = httpx.Timeout(180.0, connect=10.0)  # per-socket-op; harness also enforces a wall-clock cap


class WrenClient:
    """WrenAI 0.29.2 – wren-ui REST API  POST /api/v1/generate_sql
    (wraps wren-ai-service POST /v1/asks + polling GET /v1/asks/{id}/result).
    returnSqlDialect=true -> ibis-server translates Wren-SQL into native Postgres SQL."""
    name = "wrenai"

    def __init__(self, env, port=None):
        port = port or env.get('WREN_UI_PORT', '3000')
        self.url = f"http://localhost:{port}/api/v1/generate_sql"

    def generate(self, question):
        r = httpx.post(self.url, json={"question": question, "returnSqlDialect": True}, timeout=TIMEOUT)
        try:
            j = r.json()
        except Exception:
            return {"error": f"HTTP {r.status_code}: {r.text[:300]}"}
        if r.status_code != 200 or not j.get("sql"):
            return {"error": f"HTTP {r.status_code}: {j.get('code', '')} {str(j.get('error') or j)[:400]}", "raw": j}
        return {"sql": j["sql"], "raw": {"threadId": j.get("threadId")}}


class WrenMDLClient(WrenClient):
    """Same WrenAI 0.29.2 API, second stack (wrenai_mdl) whose project carries the semantic layer
    built by bench/wren_mdl.py from wrenai_mdl/mdl/semantic_layer.yaml."""
    name = "wrenai_mdl"

    def __init__(self, env):
        super().__init__(env, port=env.get("WREN_MDL_UI_PORT", "3001"))


class WrenMDLNoReasonClient(WrenMDLClient):
    """Same 2nd stack + same project/MDL as wrenai_mdl, with wren-ai-service setting
    allow_sql_generation_reasoning: false (make wren-mdl-noreason)."""
    name = "wrenai_mdl_noreason"


class DBGPTClient:
    """DB-GPT 0.8.2 – POST /api/v2/chat/completions, chat_mode=chat_data (ChatWithDbExecute),
    chat_param=<datasource name>, stream=false. The generated SQL is embedded in the reply as
    <chart-view content="{...,&quot;sql&quot;: ...}"> (see scene/chat_db/auto_execute/out_parser.py)."""
    name = "dbgpt"

    def __init__(self, env):
        self.url = f"http://localhost:{env.get('DBGPT_PORT', '5670')}/api/v2/chat/completions"
        self.model = env["LLM_MODEL"]
        self.db = env["BENCH_PG_DB"]

    @staticmethod
    def extract_sql(content):
        # DB-GPT 0.8.2 does NOT html-escape the attribute (raw quotes inside content="..."),
        # so take everything up to the closing '" />' and parse it as JSON.
        m = re.search(r'<chart-view\s+content="(.*)"\s*/?>', content or "", re.S)
        if m:
            for cand in (m.group(1), html.unescape(m.group(1))):
                try:
                    j = json.loads(cand, strict=False)
                    sql = j.get("sql")
                    # 0.8.2 html-escapes < > & inside the SQL string even though quotes are raw
                    return (html.unescape(sql) if sql else sql), j.get("err_msg")
                except Exception:
                    pass
            m2 = re.search(r'"sql"\s*:\s*"((?:[^"\\]|\\.)*)"', m.group(1), re.S)
            if m2:
                return html.unescape(json.loads('"' + m2.group(1) + '"', strict=False)), None
        m = re.search(r"```sql\s*(.+?)```", content or "", re.S | re.I)
        return (m.group(1).strip() if m else None), None

    def generate(self, question):
        body = {"model": self.model, "messages": question, "chat_mode": "chat_data",
                "chat_param": self.db, "stream": False, "temperature": 0.0}
        r = httpx.post(self.url, json=body, timeout=TIMEOUT)
        try:
            j = r.json()
        except Exception:
            return {"error": f"HTTP {r.status_code}: {r.text[:300]}"}
        if r.status_code != 200 or not j.get("choices"):
            return {"error": f"HTTP {r.status_code}: {str(j)[:400]}", "raw": j}
        content = j["choices"][0]["message"]["content"]
        sql, err = self.extract_sql(content)
        if not sql:
            return {"error": f"no SQL in reply: {content[:300]}", "raw": {"content": content[:2000]}}
        return {"sql": sql, "raw": {"content": content[:2000], "dbgpt_exec_error": err}}


# ------------------------------------------------------------------ Cube
CUBE_SYSTEM = """You translate business questions into Cube (cube.dev) REST API queries.
Reply with ONE JSON object only (no prose), using exactly this shape (omit unused keys):
{"measures": ["cube.measure"], "dimensions": ["cube.dimension"],
 "timeDimensions": [{"dimension": "cube.time_dim", "granularity": "day|week|month|quarter|year", "dateRange": ["YYYY-MM-DD","YYYY-MM-DD"]}],
 "filters": [{"member": "cube.member", "operator": "equals|notEquals|contains|notContains|startsWith|endsWith|gt|gte|lt|lte|set|notSet|inDateRange|beforeDate|afterDate", "values": ["string values"]}],
 "order": [["cube.member", "asc|desc"]], "limit": 100, "ungrouped": false}
Rules:
- Use only members listed in the data model below. Joins between cubes are resolved automatically by Cube.
- Filters on measures act like SQL HAVING. All filter values are strings.
- dateRange end is inclusive. Without "granularity" a timeDimension only filters.
- Results are always aggregated (GROUP BY all dimensions) unless "ungrouped": true, which returns raw rows (then do not use measures).
- Return only the columns the question asks for.
- If the question cannot be answered with a single query over this model (e.g. window functions,
  comparisons with an aggregate of aggregates, anti-joins, set difference), reply {"unsupported": "<short reason>"}."""


def _cube_model_text(meta, joins):
    out = []
    for c in meta["cubes"]:
        out.append(f"cube {c['name']}: {c.get('description') or ''}".rstrip())
        for d in c["dimensions"]:
            if d.get("public", True) is False:
                continue
            out.append(f"  dimension {d['name']} ({d['type']}){': ' + d['description'] if d.get('description') else ''}")
        for m in c["measures"]:
            out.append(f"  measure {m['name']} ({m.get('aggType') or m['type']}){': ' + m['description'] if m.get('description') else ''}")
    out.append("joins (many_to_one): " + "; ".join(joins))
    return "\n".join(out)


class CubeClient:
    """Cube Core 1.8.8 has no NL interface (AI API / D3 are Cube Cloud only), so this is a
    HARNESS-BUILT adapter: same LLM (through llm-meter /cube/v1) gets /v1/meta and writes a REST
    query; executed with POST /cubejs-api/v1/load. One self-correction retry on Cube errors."""
    name = "cube"
    label = "Cube Core + LLM adapter (harness-built)"

    def __init__(self, env, mock=False):
        self.base = f"http://localhost:{env.get('CUBE_PORT', '4000')}/cubejs-api/v1"
        self.secret = env["CUBEJS_API_SECRET"]
        self.model = env["LLM_MODEL"]
        self.llm_url = f"http://localhost:{env.get('METER_PORT', '8089')}/cube/v1/chat/completions"
        self.key = env.get("LLM_API_KEY") or ""
        self.mock = mock
        self.ref = yaml.safe_load((ROOT / "bench" / "cube_reference_queries.yaml").read_text())
        self._meta_text = None

    def _h(self):
        return {"Authorization": cube_token(self.secret), "Content-Type": "application/json"}

    def meta_text(self):
        if self._meta_text is None:
            meta = httpx.get(f"{self.base}/meta", headers=self._h(), timeout=60).json()
            joins = []
            for f in (ROOT / "cube" / "model").rglob("*.yml"):
                for c in (yaml.safe_load(f.read_text()) or {}).get("cubes", []):
                    joins += [f"{c['name']} -> {j['name']}" for j in c.get("joins", [])]
            self._meta_text = _cube_model_text(meta, joins)
        return self._meta_text

    def load(self, query, timeout_s=120):
        t0 = time.time()
        while True:
            r = httpx.post(f"{self.base}/load", headers=self._h(), json={"query": query}, timeout=TIMEOUT)
            j = r.json()
            if j.get("error") == "Continue wait" and time.time() - t0 < timeout_s:
                time.sleep(0.5)
                continue
            if r.status_code != 200 or "error" in j:
                raise RuntimeError(str(j.get("error") or j)[:500])
            return j

    @staticmethod
    def columns(query):
        cols = list(query.get("dimensions", []))
        for td in query.get("timeDimensions", []):
            if td.get("granularity"):
                cols.append(f"{td['dimension']}.{td['granularity']}")
        return cols + list(query.get("measures", []))

    def compiled_sql(self, query):
        try:
            r = httpx.post(f"{self.base}/sql", headers=self._h(), json={"query": query}, timeout=60).json()
            return r["sql"]["sql"][0]
        except Exception:
            return None

    def _llm(self, messages):
        hdr = {"Authorization": f"Bearer {self.key}"} if self.key else {}
        r = httpx.post(self.llm_url, headers=hdr, timeout=TIMEOUT, json={
            "model": self.model, "temperature": 0, "response_format": {"type": "json_object"},
            "messages": messages})
        j = r.json()
        if r.status_code != 200:
            raise RuntimeError(f"LLM HTTP {r.status_code}: {str(j.get('error', j))[:300]}")
        return j["choices"][0]["message"]["content"], j.get("usage") or {}

    def generate(self, question, qid=None):
        if self.mock:
            q = self.ref.get(qid)
            if q is None:
                return {"error": "unsupported: not expressible in Cube model (reference)"}
            return self._run(q)
        msgs = [{"role": "system", "content": CUBE_SYSTEM + "\n\nData model:\n" + self.meta_text()},
                {"role": "user", "content": question}]
        last_err = None
        for attempt in range(2):
            try:
                content, _ = self._llm(msgs)
            except Exception as e:
                return {"error": str(e)}
            try:
                q = json.loads(content)
            except Exception:
                last_err = f"invalid JSON: {content[:200]}"
                msgs += [{"role": "assistant", "content": content}, {"role": "user", "content": f"Error: {last_err}. Reply with valid JSON only."}]
                continue
            if "unsupported" in q:
                return {"error": f"unsupported: {q['unsupported']}", "cube_query": q}
            res = self._run(q)
            if "error" not in res or attempt == 1:
                res["attempts"] = attempt + 1
                return res
            last_err = res["error"]
            msgs += [{"role": "assistant", "content": content}, {"role": "user", "content": f"Cube returned an error: {last_err}. Fix the query and reply with JSON only."}]
        return {"error": last_err}

    def _run(self, q):
        q = json.loads(json.dumps(q, default=str))
        try:
            j = self.load(q)
        except Exception as e:
            return {"error": f"cube: {e}", "cube_query": q}
        cols = self.columns(q)
        rows = [[r.get(c) for c in cols] for r in j.get("data", [])]
        return {"cube_query": q, "rows": rows, "columns": cols}


CUBE_V2_SYSTEM = """You answer business questions by writing ONE SQL query for Cube's SQL API (Postgres dialect, Cube Core 1.8.8).
The SQL API exposes each Cube VIEW listed below as a table; its dimensions, measures and segments are columns.
Reply with ONE JSON object only, no prose: {"sql": "<query>"}  — or {"unsupported": "<reason>"} if it truly cannot be answered.
Rules:
1. Query only the views listed below, with the column names exactly as listed. Each SELECT ... FROM reads ONE view;
   do not join views. Use subqueries / CTEs over views when several steps are needed.
2. A measure column must be wrapped in MEASURE(column) (SUM/COUNT/AVG/MIN/MAX only if they match the measure type).
   Never aggregate a dimension with SUM/AVG/COUNT to compute a metric that exists as a measure.
3. Grouping: put every selected dimension in GROUP BY when the SELECT has measures. A SELECT of dimensions only,
   without GROUP BY, returns one row per row of the view (ungrouped).
4. Cube ignores GROUP BY keys that are not in the SELECT list. When the result must have one row per entity and names
   can repeat (tracks, albums, customers, employees, playlists), select the entity's id column in an inner query and
   select only the requested columns in an outer query: SELECT name FROM (SELECT x_id, name, ... FROM view ...) t.
5. Post-processing: first read the view in an inner SELECT (subquery or CTE), then apply window functions (RANK,
   LAG, SUM() OVER), CASE, arithmetic, EXCEPT/INTERSECT, non-correlated scalar subqueries, EXTRACT and
   ROUND(CAST(x AS NUMERIC), n) in the OUTER query. Correlated subqueries (referencing an outer alias) are not
   supported by Cube.
6. Filters on measures: compute the measure in a subquery and filter it in the outer WHERE.
7. Dates: filter time columns with half-open ranges, e.g. invoice_date >= '2023-01-01' AND invoice_date < '2024-01-01'.
   Group by period with DATE_TRUNC('month' | 'year', invoice_date); when a year or month NUMBER is asked for, compute
   EXTRACT(...)::int in an outer query over the DATE_TRUNC result. Rolling-window and prior-period measures need a
   DATE_TRUNC grouping on invoice_date in the same SELECT.
8. Return exactly the columns the question asks for, in that order — no extra measures, ids, ranks or helper columns
   in the final SELECT. Use ORDER BY when an order is asked for.
9. Do not add LIMIT unless the question asks for a specific number of results; for "top N" use ORDER BY ... LIMIT N
   (include ties with RANK() only when the question asks for ties).
10. Joins inside a view are LEFT JOINs: e.g. employees without a manager have NULL manager_* columns.
11. Cube 1.8.8 evaluates NOT EXISTS and LEFT JOIN ... IS NULL anti-joins incorrectly. To find rows of A that are not
    in B use EXCEPT or `NOT IN (SELECT ...)`."""


def _cube_v2_model_text(meta):
    out = []
    for c in meta["cubes"]:
        if c.get("type") != "view":
            continue
        out.append(f"VIEW {c['name']}: {(c.get('description') or '').strip()}")
        for d in c["dimensions"]:
            if d.get("public", True) is False:
                continue
            out.append(f"  dimension {d['name'].split('.', 1)[1]} ({d['type']}){': ' + d['description'] if d.get('description') else ''}")
        for m in c["measures"]:
            if m.get("public", True) is False:
                continue
            out.append(f"  measure {m['name'].split('.', 1)[1]} ({m.get('aggType') or m['type']}){': ' + m['description'] if m.get('description') else ''}")
        for sg in c.get("segments", []):
            out.append(f"  segment {sg['name'].split('.', 1)[1]} (boolean, use in WHERE: col IS TRUE){': ' + sg['description'] if sg.get('description') else ''}")
    return "\n".join(out)


class CubeV2Client:
    """cube_v2: Cube Core 1.8.8 with the richer model in cube_v2/model and its SQL API (Postgres wire protocol,
    query push-down on). HARNESS-BUILT adapter v2: the same LLM (llm-meter prefix /cube2/) gets the views from
    /v1/meta (with descriptions) and writes one SQL API query; it is executed by Cube (never directly on Postgres).
    One repair retry when Cube returns an error."""
    name = "cube_v2"

    def __init__(self, env, mock=False):
        self.base = f"http://localhost:{env.get('CUBE_V2_PORT', '4001')}/cubejs-api/v1"
        self.secret = env["CUBEJS_API_SECRET"]
        self.pg = dict(host="localhost", port=int(env.get("CUBE_V2_SQL_PORT", "15432")), user=env.get("CUBE_SQL_USER", "cube"),
                       password=env.get("CUBE_SQL_PASSWORD", "cube-local"), dbname="db", autocommit=True, connect_timeout=10)
        self.model = env["LLM_MODEL"]
        self.llm_url = f"http://localhost:{env.get('METER_PORT', '8089')}/cube2/v1/chat/completions"
        self.key = env.get("LLM_API_KEY") or ""
        self.mock = mock
        self.ref = yaml.safe_load((ROOT / "bench" / "cube_v2_reference_sql.yaml").read_text())
        self._meta_text = None

    def meta_text(self):
        if self._meta_text is None:
            meta = httpx.get(f"{self.base}/meta", headers={"Authorization": cube_token(self.secret)}, timeout=60).json()
            self._meta_text = _cube_v2_model_text(meta)
        return self._meta_text

    def _llm(self, messages):
        hdr = {"Authorization": f"Bearer {self.key}"} if self.key else {}
        r = httpx.post(self.llm_url, headers=hdr, timeout=TIMEOUT, json={
            "model": self.model, "temperature": 0, "response_format": {"type": "json_object"}, "messages": messages})
        j = r.json()
        if r.status_code != 200:
            raise RuntimeError(f"LLM HTTP {r.status_code}: {str(j.get('error', j))[:300]}")
        return j["choices"][0]["message"]["content"]

    def _run(self, sql):
        import psycopg
        try:
            with psycopg.connect(**self.pg) as c, c.cursor() as cur:
                cur.execute(sql)
                return {"sql": sql, "rows": [list(r) for r in cur.fetchall()], "columns": [d.name for d in cur.description or []]}
        except Exception as e:
            return {"sql": sql, "error": f"cube: {str(e).strip()[:500]}"}

    def generate(self, question, qid=None):
        if self.mock:
            sql = self.ref.get(qid)
            return self._run(sql) if sql else {"error": "unsupported: no reference query"}
        msgs = [{"role": "system", "content": CUBE_V2_SYSTEM + "\n\nViews:\n" + self.meta_text()},
                {"role": "user", "content": question}]
        last = None
        for attempt in range(2):
            try:
                content = self._llm(msgs)
            except Exception as e:
                return {"error": str(e)}
            try:
                j = json.loads(content)
            except Exception:
                last = {"error": f"invalid JSON from LLM: {content[:200]}"}
                msgs += [{"role": "assistant", "content": content}, {"role": "user", "content": "Reply with valid JSON only."}]
                continue
            if "unsupported" in j:
                return {"error": f"unsupported: {j['unsupported']}"}
            sql = (j.get("sql") or "").strip().rstrip(";")
            res = self._run(sql)
            res["attempts"] = attempt + 1
            if "error" not in res:
                return res
            last = res
            msgs += [{"role": "assistant", "content": content},
                     {"role": "user", "content": f"Cube returned an error: {res['error']}\nFix the query and reply with JSON only."}]
        return last


class MockSQLClient:
    """--mock stand-in for WrenAI/DB-GPT (no LLM key needed): returns the gold SQL, except a few
    deliberately broken/wrong answers, with synthetic latency, to exercise scoring/report paths."""

    def __init__(self, name, questions, seed=0):
        self.name = name
        self.gold = {q["question"]: q for q in questions}
        self.rng = random.Random(f"{name}-{seed}")

    def generate(self, question):
        q = self.gold[question]
        time.sleep(self.rng.uniform(0.01, 0.05))
        r = self.rng.random()
        if r < 0.08:
            return {"error": "mock: simulated tool failure"}
        if r < 0.16:
            return {"sql": "SELECT 1 AS wrong_answer"}
        if r < 0.20:
            return {"sql": "SELEC broken sql"}
        return {"sql": q["gold_sql"]}
