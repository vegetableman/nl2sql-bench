"""Vanna 2.0.2, classic NL->SQL path (vanna.legacy: OpenAI_Chat + ChromaDB_VectorStore -> vn.generate_sql), as a tiny
HTTP service for the harness (:8095). Defaults kept: n_results=10 per collection, allow_llm_to_see_data=False
(an `intermediate_sql` reply returns Vanna's refusal text, no introspection), no retry/self-correction loop, Vanna's
own prompt. Changes from defaults: LLM = gpt-oss:120b on Ollama Cloud via llm-meter /vanna/ (temperature 0, vs
Vanna's 0.7 default); Chroma embedding = nomic-embed-text via the meter (OpenAI-compatible) instead of Chroma's
bundled all-MiniLM-L6-v2. Training (first start only, store vanna/state/chroma): the 11 CREATE TABLE statements in
vanna/training/ddl.sql. Nothing else -- no questions, no gold SQL, no docs. Vanna only generates; the harness executes.
"""
import json, os, pathlib, sys, time, urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from openai import OpenAI
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from vanna.legacy.chromadb import ChromaDB_VectorStore
from vanna.legacy.openai import OpenAI_Chat

HERE = pathlib.Path(__file__).parent
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

    def get_related_ddl(self, question, **kw):
        d = super().get_related_ddl(question, **kw)
        self.last["ddl_tables"] = [x.split("(", 1)[0].replace("CREATE TABLE", "").strip() for x in d]
        return d

    def log(self, message, title="Info"):  # quiet (Vanna prints prompts by default)
        pass


store = HERE / "state" / "chroma"; fresh = not store.exists()
vn = Vanna(config={"model": MODEL, "temperature": 0, "path": str(store),
                   "embedding_function": OpenAIEmbeddingFunction(api_key="ollama", api_base=METER, model_name=EMBED)})
u = urllib.parse.urlparse(os.environ["BENCH_DB_URL"])
vn.connect_to_postgres(host=u.hostname, dbname=u.path.lstrip("/"), user=urllib.parse.unquote(u.username),
                       password=urllib.parse.unquote(u.password or ""), port=u.port or 5432)
if fresh:
    for ddl in (HERE / "training" / "ddl.sql").read_text().strip().split("\n\n"):
        vn.train(ddl=ddl)
print(f"vanna ready: dialect={vn.dialect} ddl_trained={len(vn.get_training_data())} fresh={fresh} port={PORT}", flush=True)


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
        try:
            sql = vn.generate_sql(q)
            self._send(200, {"sql": sql, "llm_response": vn.last.get("llm_response"), "llm_calls": vn.last.get("llm_calls"),
                             "ddl_tables": vn.last.get("ddl_tables"), "seconds": round(time.time() - t, 3)})
        except Exception as e:
            self._send(500, {"error": f"{type(e).__name__}: {str(e)[:400]}", "llm_calls": vn.last.get("llm_calls")})

    def log_message(self, *a):
        pass


ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
