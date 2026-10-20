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
    "wrenai_mdl_noreason": "run-gptoss120b-wrenmdl-noreason-r3",
    "dbgpt": "run-gptoss120b-r3", "cube": "run-gptoss120b-r3", "cube_v2": "run-gptoss120b-cubev2-r3",
    "router": "run-gptoss120b-router-r3",
    "mnemiq": "run-gptoss120b-mnemiq-r3", "mnemiq_failopen": "run-gptoss120b-mnemiq-r3", "mnemiq_verified": "run-gptoss120b-mnemiq-r3"}
TOK_RUNS = {**ACC_RUNS, "wrenai": "run-gptoss120b-wren-tokens"}  # OOTB Wren tokens were lost in r3 (meter-key bug)
LABEL = {"wrenai": "WrenAI 0.29.2 (out of the box)", "wrenai_mdl": "WrenAI 0.29.2 + semantic layer",
         "wrenai_mdl_noreason": "WrenAI 0.29.2 + semantic layer, no reasoning",
         "dbgpt": "DB-GPT 0.8.2", "cube": "Cube Core 1.8.8 + LLM adapter (baseline)",
         "cube_v2": "Cube Core 1.8.8 + rich model + LLM adapter v2 (harness-built)",
         "router": "Router (cube_v2 → WrenAI semantic, no reasoning)",
         "mnemiq": "mnemiq a453b05 (defaults)", "mnemiq_failopen": "mnemiq a453b05, judge fail-open variant", "mnemiq_verified": "mnemiq a453b05, judge 1200-token variant (fail-closed)"}
SYSTEMS = list(ACC_RUNS)
EMO = {"correct": "✅", "correct_extra_cols": "🟡", "wrong_result": "❌", "exec_error": "💥", "tool_error": "⚠️", "unsupported": "⛔", "timeout": "⏱️", "declined": "🚫"}
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

L = [f"# nl2sql-bench — combined report ({len(SYSTEMS)} systems)", "",
     f"- Generated {dt.datetime.now(ZoneInfo('Asia/Kolkata')).strftime('%Y-%m-%d %H:%M')} IST by `bench/combine.py` from: "
     + ", ".join(f"`{s}` ← `results/{ACC_RUNS[s]}`" for s in SYSTEMS),
     f"- Chinook on Postgres 16.4, {len(qs)} questions x 3 runs per system; LLM `{ENV['LLM_MODEL']}` via `{ENV['LLM_UPSTREAM_BASE']}`, "
     f"embeddings `{ENV['EMBEDDING_MODEL']}` (local ollama); same scorer, 180 s per-call cap, tokens via llm-meter.",
     "- `wrenai` (OOTB) and `wrenai_mdl` are two separate WrenAI 0.29.2 stacks with identical images/config; the only difference is the "
     "semantic layer in `wrenai_mdl/mdl/semantic_layer.yaml` (descriptions, relationship descriptions, 9 calculated fields, 9 generic instructions; no SQL pairs, no views).",
     "- `wrenai_mdl_noreason` = the same 2nd stack, same project / deployed MDL (hash checked) / instructions, with the single wren-ai-service setting "
     "`allow_sql_generation_reasoning: false` (`make wren-mdl-noreason`; `make wren-mdl-restore` switches back). Intent classification stays on. "
     "Per-stage timings: `results/stage-latency/stage_latency.md`.",
     "- `cube` (baseline) = Cube Core 1.8.8, model `cube/model`, LLM writes one REST `/v1/load` JSON query. `cube_v2` = same Cube release, "
     "richer model `cube_v2/model` (views, subquery dimensions, segments, rolling-window and multi-stage measures), LLM writes one "
     "Cube SQL API query (Postgres wire protocol, push-down on) over the views; both are harness-built adapters with 1 repair retry. "
     "Hand-written reference queries (`make verify`, never shown to the LLM) reproduce gold for 23/29 questions with the baseline "
     "REST model and 29/29 with cube_v2's SQL API.",
     "- `router` = try cube_v2 first (prompt copy that may reply `CANNOT_EXPRESS`), fall back to `wrenai_mdl_noreason` on unsupported / "
     "Cube error / empty result. Does not use gold for routing. Tokens: Cube under llm-meter `/router/`, Wren under `/wrenmdlnr/` "
     "(summed only on fallback). Latency and tokens count both paths when fallback fires.",
     "- OOTB WrenAI tokens come from the separate 1-run re-measure `results/run-gptoss120b-wren-tokens` (r3 lost them to a meter-key bug); all other token numbers come from the accuracy runs.",
     "- The OOTB/DB-GPT/Cube runs, the `wrenai_mdl` run and the `wrenai_mdl_noreason` run were executed sequentially at different times the same day — Ollama Cloud latency may differ between sessions. WrenAI latencies cluster at ~1 s steps (6.06, 7.06 s …) because wren-ui polls the ai-service about once per second, so Wren p50 differences of ~1 s are within that granularity.", "",
     "## Overall", "",
     "| System | EX exact | EX relaxed | wrong | exec err | tool err | timeout | unsupported | declined | p50 s | p95 s | mean s | avg prompt tok | avg completion tok | avg LLM calls | token source |",
     "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
for s in SYSTEMS:
    X = rows[s]; n = len(X); lat = [float(r["latency_s"]) for r in X]
    f = lambda k: sum(r["status"] == k for r in X)
    P = [int(r["prompt_tokens"]) for r in tok[s] if r["prompt_tokens"] not in ("", "None")]
    C = [int(r["completion_tokens"]) for r in tok[s] if r["completion_tokens"] not in ("", "None")]
    K = [int(r["chat_requests"]) for r in tok[s] if r["chat_requests"] not in ("", "None")]
    ex = sum(T(r["exact"]) for r in X); rx = sum(T(r["relaxed"]) for r in X)
    L.append(f"| {LABEL[s]} | {ex}/{n} ({100*ex/n:.0f}%) | {rx}/{n} ({100*rx/n:.0f}%) | {f('wrong_result')} | {f('exec_error')} | {f('tool_error')} | "
             f"{f('timeout')} | {f('unsupported')} | {f('declined')} | {pct(lat,50):.2f} | {pct(lat,95):.2f} | {statistics.mean(lat):.2f} | "
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

# pairwise per-question comparisons
def pairwise(A, B, title):
    global L
    L += ["", f"## {title} (per question, EX exact over 3 runs)", "",
          f"| id | diff | question | {A} | {B} | {A} statuses | {B} statuses | change |", "|---|---|---|---|---|---|---|---|"]
    fixed, broke, better, worse = [], [], [], []
    for q in qs:
        a = [r for r in rows[A] if r["id"] == q["id"]]; b = [r for r in rows[B] if r["id"] == q["id"]]
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


pairwise("wrenai", "wrenai_mdl", "WrenAI: out of the box (wrenai) vs + semantic layer (wrenai_mdl)")
pairwise("cube", "cube_v2", "Cube: baseline (cube) vs rich model + adapter v2 (cube_v2)")
pairwise("wrenai_mdl", "wrenai_mdl_noreason", "WrenAI + semantic layer: with reasoning (wrenai_mdl) vs no reasoning (wrenai_mdl_noreason)")
pairwise("cube_v2", "router", "Cube v2 vs Router (cube_v2 → WrenAI semantic, no reasoning)")

# router fallback summary (from results.csv router_path / fallback_reason)
if "router" in rows:
    RR = rows["router"]
    fb = [r for r in RR if (r.get("fallback_reason") or "").strip()]
    by = {}
    for r in fb:
        by.setdefault(r["fallback_reason"], 0)
        by[r["fallback_reason"]] += 1
    silent = [r for r in RR if not (r.get("fallback_reason") or "").strip() and not T(r["exact"])]
    L += ["", "## Router fallback / silent-wrong", "",
          f"- Fallback rate: {len(fb)}/{len(RR)} ({100*len(fb)/len(RR):.0f}%)",
          f"- Triggers: {', '.join(f'{k}={v}' for k,v in sorted(by.items())) or 'none (Cube answered every attempt)'}",
          f"- Silent-wrong (Cube path, no fallback, not EX exact): {len(silent)}" +
          (": " + ", ".join(f"{r['id']}@r{r['run']}" for r in silent) if silent else ""),
          f"- Fallback attempts latency p50/p95: " +
          (f"{pct([float(r['latency_s']) for r in fb],50):.2f} / {pct([float(r['latency_s']) for r in fb],95):.2f} s" if fb else "n/a"),
          ""]

# failure details for the semantic-layer variants
for S in ("wrenai_mdl", "wrenai_mdl_noreason", "cube_v2", "router", "mnemiq", "mnemiq_failopen", "mnemiq_verified"):
    L += [f"## {LABEL[S]}: every non-exact attempt", "", "| run | id | status | reason / error |", "|---|---|---|---|"]
    for r in rows[S]:
        if not T(r["exact"]):
            L.append(f"| {r['run']} | {r['id']} | {r['status']} | {(r['reason'] or r['error'] or '')[:160].replace('|','/').replace(chr(10),' ')} |")
    L.append("")

stage = R / "stage-latency" / "stage_latency.md"
if stage.exists():
    L += ["## WrenAI per-stage latency (wrenai_mdl vs wrenai_mdl_noreason)", ""] + stage.read_text().split("\n", 2)[2].strip().split("\n") + [""]

L += ["", "## Per question, all systems (status per run)", "", "| id | diff | " + " | ".join(LABEL[s] for s in SYSTEMS) + " |", "|---|---|" + "---|" * len(SYSTEMS)]
for q in qs:
    L.append(f"| {q['id']} | {q['difficulty']} | " + " | ".join(
        " ".join(EMO.get(r["status"], "?") for r in rows[s] if r["id"] == q["id"]) for s in SYSTEMS) + " |")
L += ["", "Legend: ✅ exact, 🟡 extra columns, ❌ wrong result, 💥 SQL exec error, ⚠️ tool/API error, ⏱️ timeout (failure), ⛔ declared unsupported, 🚫 declined (mnemiq deferral, counts as not correct)."]
import holdout_report
L += ["", holdout_report.section()]
_va = ROOT / "results/run-gptoss120b-mnemiq-r3/verifier_analysis.md"  # written by bench/mnemiq_verifier_analysis.py
if _va.exists():
    L += ["", _va.read_text().replace("# mnemiq_verified: verifier outcomes", "## mnemiq_verified: verifier outcomes (29 + holdout)", 1).replace("\n## ", "\n### ")]
(R / "combined_summary.md").write_text("\n".join(L) + "\n")
print("\n".join(L))

# chart
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
short = {"wrenai": "WrenAI 0.29.2\n(out of the box)", "wrenai_mdl": "WrenAI 0.29.2\n+ semantic layer",
         "wrenai_mdl_noreason": "WrenAI 0.29.2\n+ sem. layer,\nno reasoning", "dbgpt": "DB-GPT 0.8.2",
         "cube": "Cube Core 1.8.8\n+ LLM adapter\n(baseline)", "cube_v2": "Cube Core 1.8.8\n+ rich model\n+ adapter v2",
         "router": "Router\n(cube_v2 -> Wren\nnoreason)", "mnemiq": "mnemiq\n(defaults)", "mnemiq_failopen": "mnemiq\n(fail-open\nvariant)", "mnemiq_verified": "mnemiq\n(judge 1200 tok,\nfail-closed)"}
fig, ax = plt.subplots(1, 3, figsize=(34, 6.5)); x = range(len(SYSTEMS)); w = 0.38
ex = [100 * sum(T(r["exact"]) for r in rows[s]) / len(rows[s]) for s in SYSTEMS]
rx = [100 * sum(T(r["relaxed"]) for r in rows[s]) / len(rows[s]) for s in SYSTEMS]
b1 = ax[0].bar([i - w/2 for i in x], ex, w, label="EX strict"); b2 = ax[0].bar([i + w/2 for i in x], rx, w, label="EX relaxed")
ax[0].bar_label(b1, fmt="%.0f%%"); ax[0].bar_label(b2, fmt="%.0f%%")
ax[0].set_xticks(list(x), [short[s] for s in SYSTEMS], fontsize=8); ax[0].set_ylim(0, 108); ax[0].set_title("Execution accuracy (29 q x 3 runs)"); ax[0].legend(loc="lower left")
w4 = 0.8 / len(SYSTEMS)
for k, s in enumerate(SYSTEMS):
    v = [100 * sum(T(r["exact"]) for r in rows[s] if r["difficulty"] == d) / sum(r["difficulty"] == d for r in rows[s]) for d in ("easy", "medium", "hard")]
    bb = ax[1].bar([i + (k - (len(SYSTEMS) - 1) / 2) * w4 for i in range(3)], v, w4, label=short[s].replace("\n", " ")); ax[1].bar_label(bb, fmt="%.0f", fontsize=6)
ax[1].set_xticks(range(3), ["easy", "medium", "hard"]); ax[1].set_ylim(0, 135); ax[1].set_title("EX strict by difficulty (%)"); ax[1].legend(fontsize=7, loc="upper center", ncol=2)
p50 = [pct([float(r["latency_s"]) for r in rows[s]], 50) for s in SYSTEMS]; p95 = [pct([float(r["latency_s"]) for r in rows[s]], 95) for s in SYSTEMS]
c1 = ax[2].bar([i - w/2 for i in x], p50, w, label="p50"); c2 = ax[2].bar([i + w/2 for i in x], p95, w, label="p95")
ax[2].bar_label(c1, fmt="%.1fs"); ax[2].bar_label(c2, fmt="%.1fs")
ax[2].set_xticks(list(x), [short[s] for s in SYSTEMS], fontsize=8); ax[2].set_title("End-to-end latency per question (s)"); ax[2].legend()
fig.suptitle(f"nl2sql-bench — Chinook/Postgres, {len(qs)} questions x 3 runs, LLM {ENV['LLM_MODEL']} (Ollama Cloud), embeddings {ENV['EMBEDDING_MODEL']}")
fig.tight_layout(); fig.savefig(R / "summary.png", dpi=130); print("wrote results/summary.png")
print("wrote", holdout_report.chart())
