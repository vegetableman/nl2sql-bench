"""Engine side of the same-SQL judge comparison (run as: MNEMIQ_VARIANT=jev mnemiq/run.sh py mnemiq/judge_rebuild.py IN OUT).

For each item {key, question, sql} rebuilds EXACTLY what mnemiq's Verifier hands its judge, with mnemiq's own code:
schema = verify.verifier._judge_schema(packet) for the packet `Runtime.ask` would retrieve (same retrieve() arguments,
then the window fitter), preview = execute.render.render_result(table, max_rows=5) of the SQL run through the
runtime's own adapter (DuckDB over the Postgres source). Then scores it with JevJudge.read and records the
noul / latency / tokens from its log line. MNEMIQ_JEV_PROMPT selects the JevJudge request variant. Full result rows are written too, for gold labelling on the bench side.
"""
import json, logging, re, sys, time
from mnemiq.config import Settings, identity_from_settings
from mnemiq.runtime import build_runtime, DEFAULT_RETRIEVAL_K
from mnemiq.semantic.retrieval import retrieve
from mnemiq.verify.verifier import _judge_schema
from mnemiq.execute.render import render_result
from mnemiq.verify.judge import JevJudge


class Grab(logging.Handler):
    def __init__(self):
        super().__init__(); self.last = None
    def emit(self, rec):
        if rec.getMessage().startswith("BENCH-JEV"):
            self.last = rec.getMessage()


def packet_for(rt, question, identity):
    grants = rt.authz.grants_for(identity)
    s = rt.settings
    packet = retrieve(rt.con, question, identity, rt.authz, rt.embedder,
                      k=s.retrieval_k if s else DEFAULT_RETRIEVAL_K,
                      table_facts=rt.snapshot.table_facts if rt.snapshot else (),
                      card_style=s.card_style if s else "cards",
                      definitions=rt.snapshot.definitions if rt.snapshot else (),
                      metrics=rt.snapshot.metrics if rt.snapshot else (),
                      dimensions=rt.snapshot.dimensions if rt.snapshot else (),
                      columns=rt.snapshot.columns if rt.snapshot else (),
                      ontology_index=rt.ontology, snapshot=rt.snapshot, grants=grants)
    packet.history = []
    if rt.fitter is not None:
        packet = rt.fitter.fit(packet, rt.snapshot, grants)
    return packet


def main(inp, out):
    settings = Settings()
    rt = build_runtime(settings)
    identity = identity_from_settings(settings)
    judge = JevJudge()
    grab = Grab(); logging.getLogger("mnemiq.bench").addHandler(grab)
    schemas = {}
    with open(out, "w") as fo:
        for line in open(inp):
            it = json.loads(line)
            rec = {"key": it["key"]}
            if it["question"] not in schemas:
                schemas[it["question"]] = _judge_schema(packet_for(rt, it["question"], identity))
            schema = schemas[it["question"]]
            try:
                table = rt.adapter.execute_arrow(it["sql"])
                preview = render_result(table, max_rows=getattr(judge, "preview_rows", 5))  # as the patched Verifier does
                cols = table.schema.names
                rec["rows"] = [[r[c] for c in cols] for r in table.to_pylist()]
            except Exception as e:
                rec["exec_error"] = f"{type(e).__name__}: {str(e)[:200]}"
                preview = None
            if preview is not None:
                grab.last = None
                jr = judge.read(it["question"], schema, it["sql"], preview)
                rec.update(jev_score=jr.score, jev_fell_open=jr.fell_open, jev_reason=jr.reason)
                m = grab.last or ""
                for k in ("status", "latency_ms", "model", "prompt", "input_tokens"):
                    g = re.search(rf"\b{k}=(\S+)", m); rec[f"jev_{k}"] = g.group(1) if g else None
                if rec.get("jev_status") == "429":
                    fo.write(json.dumps(rec, default=str) + "\n"); print("RATE LIMITED (429) - stopping", flush=True); sys.exit(3)
                if jr.fell_open:
                    fo.write(json.dumps(rec, default=str) + "\n"); print("JEV FELL OPEN:", m[:300], flush=True); sys.exit(4)
            rec["schema_chars"], rec["preview"] = len(schema), preview
            fo.write(json.dumps(rec, default=str) + "\n"); fo.flush()
    print("done", flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
