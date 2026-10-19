"""Combined 4-system report: results/combined_summary.md + results/summary.png
python bench/combine.py  (inputs fixed below; all numbers are computed from the results.csv files)"""
import csv, datetime as dt, statistics, pathlib, sys
from zoneinfo import ZoneInfo
import yaml
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from common import load_env, ROOT
ENV = load_env()
R = ROOT / "results"
ACC_RUNS = {  # system -> run dir used for accuracy/latency
    "wrenai": "run-gptoss120b-r3", "wrenai_mdl": "run-gptoss120b-wrenmdl-r3",
    "dbgpt": "run-gptoss120b-r3", "cube": "run-gptoss120b-r3"}
TOK_RUNS = {**ACC_RUNS, "wrenai": "run-gptoss120b-wren-tokens"}  # OOTB Wren tokens were lost in r3 (meter-key bug)
LABEL = {"wrenai": "WrenAI 0.29.2 (out of the box)", "wrenai_mdl": "WrenAI 0.29.2 + semantic layer",
         "dbgpt": "DB-GPT 0.8.2", "cube": "Cube Core 1.8.8 + LLM adapter (harness-built)"}
SYSTEMS = list(ACC_RUNS)
EMO = {"correct": "✅", "correct_extra_cols": "🟡", "wrong_result": "❌", "exec_error": "💥", "tool_error": "⚠️", "unsupported": "⛔", "timeout": "⏱️"}
T = lambda v: v == "True"


def load(run, sys_):
    return [r for r in csv.DictReader(open(R / run / "results.csv")) if r["system"] == sys_]


def pct(xs, p):
    xs = sorted(xs); k = (len(xs) - 1) * p / 100; f = int(k); c = min(f + 1, len(xs) - 1)
    return xs[f] + (xs[c] - xs[f]) * (k - f)


rows = {s: load(ACC_RUNS[s], s) for s in SYSTEMS}
tok = {s: load(TOK_RUNS[s], s) for s in SYSTEMS}
qs = yaml.safe_load(open(ROOT / "bench" / "questions.yaml"))
qs = qs["questions"] if isinstance(qs, dict) else qs
runs = lambda s: sorted({r["run"] for r in rows[s]}, key=int)

L = ["# nl2sql-bench — combined report (4 systems)", "",
     f"- Generated {dt.datetime.now(ZoneInfo('Asia/Kolkata')).strftime('%Y-%m-%d %H:%M')} IST by `bench/combine.py` from: "
     + ", ".join(f"`{s}` ← `results/{ACC_RUNS[s]}`" for s in SYSTEMS),
     f"- Chinook on Postgres 16.4, {len(qs)} questions x 3 runs per system; LLM `{ENV['LLM_MODEL']}` via `{ENV['LLM_UPSTREAM_BASE']}`, "
     f"embeddings `{ENV['EMBEDDING_MODEL']}` (local ollama); same scorer, 180 s per-call cap, tokens via llm-meter.",
     "- `wrenai` (OOTB) and `wrenai_mdl` are two separate WrenAI 0.29.2 stacks with identical images/config; the only difference is the "
     "semantic layer in `wrenai_mdl/mdl/semantic_layer.yaml` (descriptions, relationship descriptions, 9 calculated fields, 9 generic instructions; no SQL pairs, no views).",
     "- OOTB WrenAI tokens come from the separate 1-run re-measure `results/run-gptoss120b-wren-tokens` (r3 lost them to a meter-key bug); all other token numbers come from the accuracy runs.",
     "- The OOTB/DB-GPT/Cube runs were executed earlier the same day than the `wrenai_mdl` run — Ollama Cloud latency may differ between sessions. WrenAI latencies cluster at ~1 s steps (6.06, 7.06 s …) because wren-ui polls the ai-service about once per second, so Wren p50 differences of ~1 s are within that granularity.", "",
     "## Overall", "",
     "| System | EX exact | EX relaxed | wrong | exec err | tool err | timeout | unsupported | p50 s | p95 s | mean s | avg prompt tok | avg completion tok | avg LLM calls | token source |",
     "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
for s in SYSTEMS:
    X = rows[s]; n = len(X); lat = [float(r["latency_s"]) for r in X]
    f = lambda k: sum(r["status"] == k for r in X)
    P = [int(r["prompt_tokens"]) for r in tok[s] if r["prompt_tokens"] not in ("", "None")]
    C = [int(r["completion_tokens"]) for r in tok[s] if r["completion_tokens"] not in ("", "None")]
    K = [int(r["chat_requests"]) for r in tok[s] if r["chat_requests"] not in ("", "None")]
    ex = sum(T(r["exact"]) for r in X); rx = sum(T(r["relaxed"]) for r in X)
    L.append(f"| {LABEL[s]} | {ex}/{n} ({100*ex/n:.0f}%) | {rx}/{n} ({100*rx/n:.0f}%) | {f('wrong_result')} | {f('exec_error')} | {f('tool_error')} | "
             f"{f('timeout')} | {f('unsupported')} | {pct(lat,50):.2f} | {pct(lat,95):.2f} | {statistics.mean(lat):.2f} | "
             f"{statistics.mean(P) if P else float('nan'):,.0f} | {statistics.mean(C) if C else float('nan'):,.0f} | {statistics.mean(K) if K else float('nan'):.1f} | "
             f"{TOK_RUNS[s]} ({len(P)} rows) |")

L += ["", "## EX exact by difficulty", "", "| System | easy | medium | hard |", "|---|---|---|---|"]
for s in SYSTEMS:
    c = []
    for d in ("easy", "medium", "hard"):
        X = [r for r in rows[s] if r["difficulty"] == d]; e = sum(T(r["exact"]) for r in X)
        c.append(f"{e}/{len(X)} ({100*e/len(X):.0f}%)")
    L.append(f"| {LABEL[s]} | " + " | ".join(c) + " |")

L += ["", "## Run-to-run variance", "",
      "| System | EX exact per run | mean ± sd (of 29) | questions with mixed outcomes across runs | p50 latency per run (s) |", "|---|---|---|---|---|"]
for s in SYSTEMS:
    per = [sum(T(r["exact"]) for r in rows[s] if r["run"] == k) for k in runs(s)]
    mixed = [q["id"] for q in qs if len({T(r["exact"]) for r in rows[s] if r["id"] == q["id"]}) > 1]
    p50s = [pct([float(r["latency_s"]) for r in rows[s] if r["run"] == k], 50) for k in runs(s)]
    L.append(f"| {LABEL[s]} | {' / '.join(map(str, per))} | {statistics.mean(per):.1f} ± {statistics.stdev(per):.1f} | "
             f"{len(mixed)} ({', '.join(mixed) or '-'}) | {' / '.join(f'{x:.2f}' for x in p50s)} |")

# OOTB vs MDL per question
L += ["", "## WrenAI: out of the box vs + semantic layer (per question, EX exact over 3 runs)", "",
      "| id | diff | question | OOTB | +MDL | OOTB statuses | +MDL statuses | change |", "|---|---|---|---|---|---|---|---|"]
fixed, broke, better, worse = [], [], [], []
for q in qs:
    a = [r for r in rows["wrenai"] if r["id"] == q["id"]]; b = [r for r in rows["wrenai_mdl"] if r["id"] == q["id"]]
    ea, eb = sum(T(r["exact"]) for r in a), sum(T(r["exact"]) for r in b)
    if ea == eb:
        ch = ""
    elif ea == 0 and eb == len(b):
        ch = "**fixed**"; fixed.append(q["id"])
    elif eb == 0 and ea == len(a):
        ch = "**broke**"; broke.append(q["id"])
    elif eb > ea:
        ch = "better"; better.append(q["id"])
    else:
        ch = "worse"; worse.append(q["id"])
    L.append(f"| {q['id']} | {q['difficulty']} | {q['question'][:70]} | {ea}/{len(a)} | {eb}/{len(b)} | "
             f"{' '.join(EMO.get(r['status'],'?') for r in a)} | {' '.join(EMO.get(r['status'],'?') for r in b)} | {ch} |")
L += ["", f"- fixed (0/3 → 3/3): {', '.join(fixed) or 'none'}; broke (3/3 → 0/3): {', '.join(broke) or 'none'}",
      f"- partially better: {', '.join(better) or 'none'}; partially worse: {', '.join(worse) or 'none'}", ""]

# failure details for MDL
L += ["## WrenAI + semantic layer: every non-exact attempt", "", "| run | id | status | reason / error |", "|---|---|---|---|"]
for r in rows["wrenai_mdl"]:
    if not T(r["exact"]):
        L.append(f"| {r['run']} | {r['id']} | {r['status']} | {(r['reason'] or r['error'] or '')[:160].replace('|','/').replace(chr(10),' ')} |")

L += ["", "## Per question, all systems (status per run)", "", "| id | diff | " + " | ".join(LABEL[s] for s in SYSTEMS) + " |", "|---|---|" + "---|" * len(SYSTEMS)]
for q in qs:
    L.append(f"| {q['id']} | {q['difficulty']} | " + " | ".join(
        " ".join(EMO.get(r["status"], "?") for r in rows[s] if r["id"] == q["id"]) for s in SYSTEMS) + " |")
L += ["", "Legend: ✅ exact, 🟡 extra columns, ❌ wrong result, 💥 SQL exec error, ⚠️ tool/API error, ⏱️ timeout (failure), ⛔ declared unsupported."]
(R / "combined_summary.md").write_text("\n".join(L) + "\n")
print("\n".join(L))

# chart
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
short = {"wrenai": "WrenAI 0.29.2\n(out of the box)", "wrenai_mdl": "WrenAI 0.29.2\n+ semantic layer", "dbgpt": "DB-GPT 0.8.2",
         "cube": "Cube Core 1.8.8\n+ LLM adapter (harness)"}
fig, ax = plt.subplots(1, 3, figsize=(19, 5.5)); x = range(len(SYSTEMS)); w = 0.38
ex = [100 * sum(T(r["exact"]) for r in rows[s]) / len(rows[s]) for s in SYSTEMS]
rx = [100 * sum(T(r["relaxed"]) for r in rows[s]) / len(rows[s]) for s in SYSTEMS]
b1 = ax[0].bar([i - w/2 for i in x], ex, w, label="EX strict"); b2 = ax[0].bar([i + w/2 for i in x], rx, w, label="EX relaxed")
ax[0].bar_label(b1, fmt="%.0f%%"); ax[0].bar_label(b2, fmt="%.0f%%")
ax[0].set_xticks(list(x), [short[s] for s in SYSTEMS], fontsize=8); ax[0].set_ylim(0, 108); ax[0].set_title("Execution accuracy (29 q x 3 runs)"); ax[0].legend(loc="lower left")
w4 = 0.2
for k, s in enumerate(SYSTEMS):
    v = [100 * sum(T(r["exact"]) for r in rows[s] if r["difficulty"] == d) / sum(r["difficulty"] == d for r in rows[s]) for d in ("easy", "medium", "hard")]
    bb = ax[1].bar([i + (k - 1.5) * w4 for i in range(3)], v, w4, label=short[s].replace("\n", " ")); ax[1].bar_label(bb, fmt="%.0f", fontsize=7)
ax[1].set_xticks(range(3), ["easy", "medium", "hard"]); ax[1].set_ylim(0, 135); ax[1].set_title("EX strict by difficulty (%)"); ax[1].legend(fontsize=7, loc="upper center", ncol=2)
p50 = [pct([float(r["latency_s"]) for r in rows[s]], 50) for s in SYSTEMS]; p95 = [pct([float(r["latency_s"]) for r in rows[s]], 95) for s in SYSTEMS]
c1 = ax[2].bar([i - w/2 for i in x], p50, w, label="p50"); c2 = ax[2].bar([i + w/2 for i in x], p95, w, label="p95")
ax[2].bar_label(c1, fmt="%.1fs"); ax[2].bar_label(c2, fmt="%.1fs")
ax[2].set_xticks(list(x), [short[s] for s in SYSTEMS], fontsize=8); ax[2].set_title("End-to-end latency per question (s)"); ax[2].legend()
fig.suptitle(f"nl2sql-bench — Chinook/Postgres, {len(qs)} questions x 3 runs, LLM {ENV['LLM_MODEL']} (Ollama Cloud), embeddings {ENV['EMBEDDING_MODEL']}")
fig.tight_layout(); fig.savefig(R / "summary.png", dpi=130); print("wrote results/summary.png")
