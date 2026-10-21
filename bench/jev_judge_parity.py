"""Parity check: bench/jev_judge.request_body == mnemiq JevJudge(MNEMIQ_JEV_PROMPT=b).request_body for sample inputs.
Run with the mnemiq-jev venv: MNEMIQ_VARIANT=jev2 mnemiq/run.sh py $PWD/bench/jev_judge_parity.py"""
import os, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
os.environ["MNEMIQ_JEV_PROMPT"] = "b"
import pyarrow as pa
import jev_judge as J
from mnemiq.verify.judge import JevJudge
from mnemiq.execute.render import render_result
jj = JevJudge(); ok = True
for n in (0, 3, 50, 51, 212):
    cols = ["name", "total"]; rows = [(f"artist {i}" if i % 7 else None, i * 1.5) for i in range(n)]
    t = pa.table({c: [r[k] for r in rows] for k, c in enumerate(cols)}) if n else pa.table({c: pa.array([], pa.string()) for c in cols})
    pm, pb = render_result(t, max_rows=jj.preview_rows), J.render_result(cols, rows)
    a, b = jj.request_body("q?", "CREATE TABLE x (a INT);", "SELECT 1", pm), J.request_body("q?", "CREATE TABLE x (a INT);", "SELECT 1", pb)
    same = (pm == pb) and (a == b); ok &= same
    print(f"rows={n:3}: preview identical={pm == pb}  request identical={a == b}")
print("PARITY OK" if ok else "PARITY MISMATCH"); sys.exit(0 if ok else 1)
