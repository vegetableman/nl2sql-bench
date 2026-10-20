"""Holdout report: markdown section (appended to results/combined_summary.md by combine.py) + results/holdout_summary.png.
All numbers are computed from results/run-gptoss120b-holdout-r3/results.csv."""
import csv, statistics, pathlib
from collections import Counter
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
RUN = ROOT / "results" / "run-gptoss120b-holdout-r3"
ORDER = ["router", "cube_v2", "wrenai_mdl_noreason", "dbgpt", "mnemiq", "mnemiq_failopen"]
LABEL = {"router": "Router (cube_v2 → Wren noreason)", "cube_v2": "cube_v2", "wrenai_mdl_noreason": "WrenAI + semantic, no reasoning",
         "dbgpt": "DB-GPT 0.8.2", "mnemiq": "mnemiq a453b05 (defaults)", "mnemiq_failopen": "mnemiq a453b05, judge fail-open variant"}
SHORT = {"router": "Router\n(cube→Wren)", "cube_v2": "cube_v2", "wrenai_mdl_noreason": "WrenAI\n+ sem.\nnoreason", "dbgpt": "DB-GPT\n0.8.2",
         "mnemiq": "mnemiq\n(defaults)", "mnemiq_failopen": "mnemiq\n(fail-open\nvariant)"}
EMO = {"correct": "✅", "correct_extra_cols": "🟡", "wrong_result": "❌", "exec_error": "💥", "tool_error": "⚠️",
       "unsupported": "⛔", "timeout": "⏱️", "declined": "🚫"}
T = lambda v: v == "True"


def pct(xs, p):
    xs = sorted(xs); k = (len(xs) - 1) * p / 100; f = int(k); c = min(f + 1, len(xs) - 1)
    return xs[f] + (xs[c] - xs[f]) * (k - f)


def load():
    rows = list(csv.DictReader(open(RUN / "results.csv")))
    qs = yaml.safe_load(open(ROOT / "bench" / "questions_holdout.yaml"))["questions"]
    systems = [s for s in ORDER if any(r["system"] == s for r in rows)]
    return rows, qs, systems


def stats(rows, s):
    X = [r for r in rows if r["system"] == s]; n = len(X)
    lat = [float(r["latency_s"]) for r in X]
    num = lambda k: [int(r[k]) for r in X if r.get(k) not in ("", "None", None)]
    st = Counter(r["status"] for r in X)
    return dict(X=X, n=n, ex=sum(T(r["exact"]) for r in X), rx=sum(T(r["relaxed"]) for r in X), p50=pct(lat, 50), p95=pct(lat, 95),
                prompt=statistics.mean(num("prompt_tokens")), llm=statistics.mean(num("chat_requests")), st=st)


def section():
    rows, qs, systems = load()
    S = {s: stats(rows, s) for s in systems}
    L = ["## Held-out set (15 new questions)", "",
         "Source: `bench/questions_holdout.yaml`. Models/prompts/MDL **unchanged** (not tuned to these questions). "
         f"15 q × 3 runs each for {', '.join(f'`{s}`' for s in systems)}.",
         "Results: `results/run-gptoss120b-holdout-r3/`. Chart: `results/holdout_summary.png`.", "",
         "| System | EX exact | EX relaxed | wrong | exec err | tool err | timeout | unsupported | declined | p50 s | p95 s | avg prompt tok | avg LLM calls |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for s in systems:
        t = S[s]; c = t["st"]
        L.append(f"| {LABEL[s]} | {t['ex']}/{t['n']} ({100*t['ex']/t['n']:.0f}%) | {t['rx']}/{t['n']} ({100*t['rx']/t['n']:.0f}%) | "
                 f"{c['wrong_result']} | {c['exec_error']} | {c['tool_error']} | {c['timeout']} | {c['unsupported']} | {c['declined']} | "
                 f"{t['p50']:.2f} | {t['p95']:.2f} | {t['prompt']:,.0f} | {t['llm']:.1f} |")
    if "router" in S:
        R = S["router"]["X"]
        fb = [r for r in R if (r.get("fallback_reason") or "").strip()]; cube = [r for r in R if not (r.get("fallback_reason") or "").strip()]
        trig = Counter(r["fallback_reason"] for r in fb)
        silent = [r for r in cube if not T(r["exact"])]; fbw = [r for r in fb if not T(r["exact"])]
        cl = [float(r["latency_s"]) for r in cube]; fl = [float(r["latency_s"]) for r in fb]
        L += ["", "### Router fallback / silent-wrong (holdout)", "",
              f"- Fallback rate: **{len(fb)}/{len(R)} ({100*len(fb)/len(R):.0f}%)**",
              "- Triggers: " + ", ".join(f"{k}={v}" for k, v in sorted(trig.items())),
              f"- Cube-answered path: EX {sum(T(r['exact']) for r in cube)}/{len(cube)} ({100*sum(T(r['exact']) for r in cube)/len(cube):.0f}%), p50/p95 {pct(cl,50):.2f}/{pct(cl,95):.2f} s",
              f"- Fallback path: EX {sum(T(r['exact']) for r in fb)}/{len(fb)} ({100*sum(T(r['exact']) for r in fb)/len(fb):.0f}%), p50/p95 {pct(fl,50):.2f}/{pct(fl,95):.2f} s",
              f"- Silent-wrong (Cube answered, no fallback, not EX): {len(silent)} — " + ", ".join(f"{r['id']}@r{r['run']}" for r in silent),
              f"- Fell back but Wren still wrong: {len(fbw)} — " + (", ".join(f"{r['id']}@r{r['run']}" for r in fbw) or "none")]
    for s in [x for x in systems if x in ("dbgpt", "mnemiq", "mnemiq_failopen")]:
        miss = [r for r in S[s]["X"] if not T(r["exact"])]
        L += ["", f"### {LABEL[s]}: non-exact attempts (holdout)", "", "| run | id | status | reason / error |", "|---|---|---|---|"]
        L += [f"| {r['run']} | {r['id']} | {r['status']} | {(r['reason'] or r['error'] or '')[:150].replace('|','/').replace(chr(10),' ')} |" for r in miss] or ["| - | - | - | none |"]
    L += ["", "### Per-question statuses (holdout)", "", "| id | diff | question | " + " | ".join(LABEL[s] for s in systems) + " |",
          "|---|---|---|" + "---|" * len(systems)]
    for q in qs:
        L.append(f"| {q['id']} | {q['difficulty']} | {q['question'][:60]} | " + " | ".join(
            " ".join(EMO.get(r["status"], "?") for r in rows if r["system"] == s and r["id"] == q["id"]) for s in systems) + " |")
    L += ["", "Legend: ✅ exact, 🟡 extra columns, ❌ wrong, 💥 exec error, ⚠️ tool/API error, ⏱️ timeout, ⛔ unsupported (Cube), 🚫 declined (mnemiq deferral)."]
    return "\n".join(L) + "\n"


def chart():
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    rows, qs, systems = load(); S = {s: stats(rows, s) for s in systems}
    fig, ax = plt.subplots(1, 3, figsize=(6 + 3.2 * len(systems), 5.4)); x = range(len(systems)); w = 0.38
    b1 = ax[0].bar([i - w/2 for i in x], [100*S[s]["ex"]/S[s]["n"] for s in systems], w, label="EX strict")
    b2 = ax[0].bar([i + w/2 for i in x], [100*S[s]["rx"]/S[s]["n"] for s in systems], w, label="EX relaxed")
    ax[0].bar_label(b1, fmt="%.0f%%", fontsize=8); ax[0].bar_label(b2, fmt="%.0f%%", fontsize=8)
    ax[0].set_xticks(list(x), [SHORT[s] for s in systems], fontsize=8); ax[0].set_ylim(0, 110); ax[0].set_title("Holdout EX accuracy (15 q × 3)"); ax[0].legend(loc="lower left")
    wd = 0.8 / len(systems)
    for k, s in enumerate(systems):
        v = []
        for d in ("easy", "medium", "hard"):
            R = [r for r in S[s]["X"] if r["difficulty"] == d]; v.append(100*sum(T(r["exact"]) for r in R)/len(R) if R else 0)
        bb = ax[1].bar([i + (k - (len(systems)-1)/2) * wd for i in range(3)], v, wd, label=SHORT[s].replace("\n", " ")); ax[1].bar_label(bb, fmt="%.0f", fontsize=6)
    ax[1].set_xticks(range(3), ["easy", "medium", "hard"]); ax[1].set_ylim(0, 135); ax[1].set_title("Holdout EX strict by difficulty (%)"); ax[1].legend(fontsize=7, ncol=2, loc="upper center")
    c1 = ax[2].bar([i - w/2 for i in x], [S[s]["p50"] for s in systems], w, label="p50"); c2 = ax[2].bar([i + w/2 for i in x], [S[s]["p95"] for s in systems], w, label="p95")
    ax[2].bar_label(c1, fmt="%.1fs", fontsize=8); ax[2].bar_label(c2, fmt="%.1fs", fontsize=8)
    ax[2].set_xticks(list(x), [SHORT[s] for s in systems], fontsize=8); ax[2].set_title("Holdout latency (s)"); ax[2].legend()
    fig.suptitle(f"nl2sql-bench HOLD OUT — 15 new Chinook questions × 3 runs ({len(systems)} systems; models/prompts unchanged)")
    fig.tight_layout(); fig.savefig(ROOT / "results" / "holdout_summary.png", dpi=130)
    return ROOT / "results" / "holdout_summary.png"


if __name__ == "__main__":
    print(section()); print("wrote", chart())
