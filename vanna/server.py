"""Vanna 2.0.2, classic NL->SQL path (vanna.legacy: OpenAI_Chat + ChromaDB_VectorStore -> vn.generate_sql), as a tiny
HTTP service for the harness (:8095). Defaults kept: n_results=10 per collection, allow_llm_to_see_data=False
(an `intermediate_sql` reply returns Vanna's refusal text, no introspection), no retry/self-correction loop, Vanna's
own prompt. Changes from defaults: LLM = gpt-oss:120b on Ollama Cloud via llm-meter /vanna/ (temperature 0, vs
Vanna's 0.7 default); Chroma embedding = nomic-embed-text via the meter (OpenAI-compatible) instead of Chroma's
bundled all-MiniLM-L6-v2. Training (first start only, store vanna/state/chroma): the 11 CREATE TABLE statements in
vanna/training/ddl.sql. Nothing else -- no questions, no gold SQL, no docs. Vanna only generates; the harness executes.

VANNA_JEV=on|retry (systems vanna_jev / vanna_jev_retry; default off = plain vanna, unchanged): after generate_sql the
SQL is executed here read-only (bench role, READ ONLY transaction, 30 s statement timeout) and checked by TypeSafe Jev
with mnemiq_jev_v2's variant-b request (bench/jev_judge.py; schema = the DDL statements Vanna retrieved for this
question). p < 0.5 -> declined (fail-closed); Jev error/unreadable reply -> answer returned (fail-open); SQL that fails
to execute -> returned unjudged. `retry`: on a decline, ONE more generate_sql with RETRY_TEMPLATE (retrieval still uses
the original question), re-executed and re-judged; < 0.5 again -> declined.
"""
import json, os, pathlib, sys, time, urllib.parse
import psycopg2
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from openai import OpenAI
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from vanna.legacy.chromadb import ChromaDB_VectorStore
from vanna.legacy.openai import OpenAI_Chat

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "bench"))
import jev_judge as J
JEV = os.environ.get("VANNA_JEV", "off")
THRESHOLD = float(os.environ.get("VANNA_JEV_THRESHOLD", J.THRESHOLD))  # smoke-test override only; runs use 0.5
assert JEV in ("off", "on", "retry"), JEV
# The exact text sent as the question on the retry (retrieval keeps the original question):
RETRY_TEMPLATE = ("{question}\n\n"
                  "Note: a previous attempt produced the SQL below, and an automated answer check judged that it probably "
                  "does not answer the question correctly. Re-read the question and the schema and write a corrected SQL query.\n\n"
                  "Previous SQL:\n{prev_sql}")
PORT = int(os.environ.get("VANNA_PORT", "8095"))
METER = f"http://localhost:{os.environ.get('METER_PORT', '8089')}/{os.environ.get('VANNA_METER_PREFIX', 'vanna')}/v1"
MODEL = os.environ.get("LLM_MODEL", "gpt-oss:120b")
EMBED = os.environ.get("EMBEDDING_MODEL", "nomic-embed-text")


class Vanna(ChromaDB_VectorStore, OpenAI_Chat):
    def __init__(self, config):
        ChromaDB_VectorStore.__init__(self, config=config)
        OpenAI_Chat.__init__(self, client=OpenAI(base_url=METER, api_key=os.environ["OLLAMA_API_KEY"], timeout=170), config=config)
        self.last = {}

    def submit_prompt(self, prompt, **kw):  # record what Vanna sent/got; behaviour unchanged
        r = super().submit_prompt(prompt, **kw)
        self.last.setdefault("llm_calls", 0); self.last["llm_calls"] += 1; self.last["llm_response"] = r
        return r

    retrieval_q = None  # set only for the retry: retrieve with the original question, not the hint

    def get_related_ddl(self, question, **kw):
        d = super().get_related_ddl(self.retrieval_q or question, **kw)
        self.last["ddl_tables"] = [x.split("(", 1)[0].replace("CREATE TABLE", "").strip() for x in d]
        self.last["ddl_list"] = d
        return d

    def get_similar_question_sql(self, question, **kw):
        return super().get_similar_question_sql(self.retrieval_q or question, **kw)

    def get_related_documentation(self, question, **kw):
        return super().get_related_documentation(self.retrieval_q or question, **kw)

    def log(self, message, title="Info"):  # quiet (Vanna prints prompts by default)
        pass


store = pathlib.Path(os.environ.get("VANNA_STORE", str(HERE / "state" / "chroma"))); fresh = not store.exists()
vn = Vanna(config={"model": MODEL, "temperature": 0, "path": str(store),
                   "embedding_function": OpenAIEmbeddingFunction(api_key="ollama", api_base=METER, model_name=EMBED)})
u = urllib.parse.urlparse(os.environ["BENCH_DB_URL"])
vn.connect_to_postgres(host=u.hostname, dbname=u.path.lstrip("/"), user=urllib.parse.unquote(u.username),
                       password=urllib.parse.unquote(u.password or ""), port=u.port or 5432)
if fresh:
    for ddl in (HERE / "training" / "ddl.sql").read_text().strip().split("\n\n"):
        vn.train(ddl=ddl)
DSN = dict(host=u.hostname, dbname=u.path.lstrip("/"), user=urllib.parse.unquote(u.username),
           password=urllib.parse.unquote(u.password or ""), port=u.port or 5432)


def execute(sql):
    """Read-only execution as the bench role -> (columns, rows) or raises."""
    c = psycopg2.connect(**DSN)
    try:
        c.set_session(readonly=True)
        with c.cursor() as cur:
            cur.execute("SET statement_timeout = 30000"); cur.execute(sql)
            return [d[0] for d in cur.description], cur.fetchall()
    finally:
        c.rollback(); c.close()


def judged_attempt(question, prompt_question):
    """generate_sql (+ execute + Jev) once. Returns the attempt record."""
    vn.retrieval_q = question if prompt_question != question else None
    try:
        sql = vn.generate_sql(prompt_question)
    finally:
        vn.retrieval_q = None
    a = {"sql": sql, "llm_response": (vn.last.get("llm_response") or "")[:2000]}
    try:
        cols, rows = execute(sql)
    except Exception as e:
        a.update(exec_ok=False, exec_error=f"{type(e).__name__}: {str(e)[:200]}", decision="exec_failed_unjudged")
        return a
    a.update(exec_ok=True, rows=len(rows))
    j = J.judge(question, "\n\n".join(vn.last.get("ddl_list") or []), sql, J.render_result(cols, rows))
    print(J.log_line(j, question, sql), flush=True)
    a["jev"] = {k: j.get(k) for k in ("p", "status", "fell_open", "reason", "latency_ms", "model", "input_tokens", "output_tokens")}
    a["decision"] = "fell_open" if j["fell_open"] else "passed" if j["p"] >= THRESHOLD else "declined"
    return a


print(f"vanna ready: dialect={vn.dialect} ddl_trained={len(vn.get_training_data())} fresh={fresh} port={PORT} jev={JEV} threshold={THRESHOLD} meter={METER}", flush=True)


class H(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        b = json.dumps(obj, default=str).encode(); self.send_response(code)
        self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def do_GET(self):
        self._send(200, {"ok": True}) if self.path == "/healthz" else self._send(404, {})

    def do_POST(self):
        if self.path != "/v1/generate":
            return self._send(404, {})
        q = json.loads(self.rfile.read(int(self.headers["Content-Length"])))["question"]
        vn.last = {}; t = time.time()
        if JEV != "off":
            try:
                att = [judged_attempt(q, q)]
                if JEV == "retry" and att[0]["decision"] == "declined":
                    att.append(judged_attempt(q, RETRY_TEMPLATE.format(question=q, prev_sql=att[0]["sql"])))
                final = att[-1]
                self._send(200, {"sql": final["sql"], "declined": final["decision"] == "declined", "decision": final["decision"],
                                 "attempts": att, "llm_calls": vn.last.get("llm_calls"), "ddl_tables": vn.last.get("ddl_tables"),
                                 "seconds": round(time.time() - t, 3)})
            except Exception as e:
                self._send(500, {"error": f"{type(e).__name__}: {str(e)[:400]}", "llm_calls": vn.last.get("llm_calls")})
            return
        try:
            sql = vn.generate_sql(q)
            self._send(200, {"sql": sql, "llm_response": vn.last.get("llm_response"), "llm_calls": vn.last.get("llm_calls"),
                             "ddl_tables": vn.last.get("ddl_tables"), "seconds": round(time.time() - t, 3)})
        except Exception as e:
            self._send(500, {"error": f"{type(e).__name__}: {str(e)[:400]}", "llm_calls": vn.last.get("llm_calls")})

    def log_message(self, *a):
        pass


ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
