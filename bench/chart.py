"""results/<run>/results.csv -> results/summary.png (accuracy + latency per system)."""
import csv, statistics, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from common import load_env
ENV = load_env()
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

run = pathlib.Path(sys.argv[1])
out = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else run.parent / "summary.png"
rows = list(csv.DictReader(open(run / "results.csv")))
systems = list(dict.fromkeys(r["system"] for r in rows))
label = {"wrenai": "WrenAI 0.29.2", "dbgpt": "DB-GPT 0.8.2", "cube": "Cube Core 1.8.8\n+ LLM adapter (harness)"}
T = lambda v: v == "True"


def pct(xs, p):
    xs = sorted(xs); k = (len(xs) - 1) * p / 100; f = int(k); c = min(f + 1, len(xs) - 1)
    return xs[f] + (xs[c] - xs[f]) * (k - f)


fig, ax = plt.subplots(1, 3, figsize=(16, 5))
x = range(len(systems)); w = 0.38
ex = [100 * sum(T(r["exact"]) for r in rows if r["system"] == s) / sum(r["system"] == s for r in rows) for s in systems]
rx = [100 * sum(T(r["relaxed"]) for r in rows if r["system"] == s) / sum(r["system"] == s for r in rows) for s in systems]
b1 = ax[0].bar([i - w / 2 for i in x], ex, w, label="EX strict"); b2 = ax[0].bar([i + w / 2 for i in x], rx, w, label="EX relaxed")
ax[0].bar_label(b1, fmt="%.0f%%"); ax[0].bar_label(b2, fmt="%.0f%%")
ax[0].set_xticks(list(x), [label[s] for s in systems]); ax[0].set_ylim(0, 105); ax[0].set_title("Execution accuracy (all runs)"); ax[0].legend()
diffs = ["easy", "medium", "hard"]; w3 = 0.26
for k, s in enumerate(systems):
    v = []
    for d in diffs:
        R = [r for r in rows if r["system"] == s and r["difficulty"] == d]
        v.append(100 * sum(T(r["exact"]) for r in R) / len(R))
    bb = ax[1].bar([i + (k - 1) * w3 for i in range(3)], v, w3, label=label[s].replace("\n", " "))
    ax[1].bar_label(bb, fmt="%.0f", fontsize=8)
ax[1].set_xticks(range(3), diffs); ax[1].set_ylim(0, 128); ax[1].set_title("EX strict by difficulty (%)"); ax[1].legend(fontsize=7, loc="upper center", ncol=3)
p50 = [pct([float(r["latency_s"]) for r in rows if r["system"] == s], 50) for s in systems]
p95 = [pct([float(r["latency_s"]) for r in rows if r["system"] == s], 95) for s in systems]
c1 = ax[2].bar([i - w / 2 for i in x], p50, w, label="p50"); c2 = ax[2].bar([i + w / 2 for i in x], p95, w, label="p95")
ax[2].bar_label(c1, fmt="%.1fs"); ax[2].bar_label(c2, fmt="%.1fs")
ax[2].set_xticks(list(x), [label[s] for s in systems]); ax[2].set_title("End-to-end latency per question (s)"); ax[2].legend()
n_q = len({r["id"] for r in rows}); n_run = len({r["run"] for r in rows})
fig.suptitle(f"nl2sql-bench — Chinook/Postgres, {n_q} questions x {n_run} runs, LLM {ENV['LLM_MODEL']} via {ENV['LLM_UPSTREAM_BASE']}, embeddings {ENV['EMBEDDING_MODEL']}")
fig.tight_layout(); fig.savefig(out, dpi=130)
print(f"wrote {out}")
