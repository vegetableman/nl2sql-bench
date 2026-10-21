"""Focused chart of the main contenders -> results/contenders.png (from the saved results.csv files; nothing rerun).
Accuracy = EX exact share; held-out counts ho14 answers that are valid under the gold's 3rd-place tie as correct
(mnemiq_jev_analysis.label: re-executed on Postgres, compared against every tie alternative). Latency = p50 wall time.
Arctic ran on its own 7B model on a dedicated HF A10G endpoint (not gpt-oss:120b); the others use gpt-oss:120b on Ollama Cloud."""
import csv, json, sys, pathlib
import psycopg, yaml
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from common import ROOT, load_env
from mnemiq_jev_analysis import label
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

R = ROOT / "results"
# (label, system name in csv, 29 run dir, holdout run dir)
SYS = [("Vanna", "vanna", "run-gptoss120b-vanna-r3", "run-gptoss120b-holdout-r3"),
       ("Vanna + Jev", "vanna_jev", "run-gptoss120b-vanna-r3", "run-gptoss120b-holdout-r3"),
       ("WrenAI\n(semantic, no reasoning)", "wrenai_mdl_noreason", "run-gptoss120b-wrenmdl-noreason-r3", "run-gptoss120b-holdout-r3"),
       ("DB-GPT", "dbgpt", "run-gptoss120b-r3", "run-gptoss120b-holdout-r3"),
       ("mnemiq + Jev", "mnemiq_jev_v2", "run-gptoss120b-mnemiq-jev-v2-r2", "run-gptoss120b-holdout-jev-v2-r2"),
       ("Arctic-Text2SQL-R1-7B\n(HF A10G, own model)", "arctic", "run-arctic-hf-a10g-r3", "run-gptoss120b-holdout-r3")]


def pct(xs, p):
    xs = sorted(xs); k = (len(xs) - 1) * p / 100; f = int(k); c = min(f + 1, len(xs) - 1)
    return xs[f] + (xs[c] - xs[f]) * (k - f)


def main():
    env = load_env(); conn = psycopg.connect(env["BENCH_DB_URL"])
    hq = {q["id"]: q for q in yaml.safe_load(open(ROOT / "bench" / "questions_holdout.yaml"))["questions"]}
    gold = {}
    out = []
    for lab_, s, r29, rho in SYS:
        if not (R / r29 / "results.csv").exists():
            continue
        A = [r for r in csv.DictReader(open(R / r29 / "results.csv")) if r["system"] == s]
        B = [r for r in csv.DictReader(open(R / rho / "results.csv")) if r["system"] == s]
        if not A or not B:
            continue
        tie = 0
        for r in B:
            if r["exact"] == "True":
                tie += 1
            elif r["id"] == "ho14" and r["status"] == "wrong_result":
                q = hq["ho14"]
                if "ho14" not in gold:
                    with conn.cursor() as cur:
                        cur.execute("BEGIN READ ONLY"); cur.execute(q["gold_sql"]); gold["ho14"] = cur.fetchall(); conn.rollback()
                ok, _ = label(conn, env["BENCH_DB_URL"], q, r["generated"], gold["ho14"]); tie += ok
        out.append(dict(label=lab_, s=s, acc29=sum(r["exact"] == "True" for r in A) / len(A), n29=len(A),
                        accho=tie / len(B), nho=len(B), ex29=sum(r["exact"] == "True" for r in A), exho_tie=tie,
                        p29=pct([float(r["latency_s"]) for r in A], 50), pho=pct([float(r["latency_s"]) for r in B], 50)))
    for o in out:
        print(json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in o.items() if k != "label"}))
    fig, ax = plt.subplots(1, 2, figsize=(14 + 1.2 * max(0, len(out) - 5), 5.2)); x = range(len(out)); w = 0.38
    for a, (k1, k2, fmt, title, yl) in zip(ax, [("acc29", "accho", "{:.0%}", "Accuracy (held-out counts ho14 tie)", "share correct"),
                                                ("p29", "pho", "{:.2f}s", "Typical latency (p50)", "seconds")]):
        b1 = a.bar([i - w/2 for i in x], [o[k1] for o in out], w, label="Original 29 ×3")
        b2 = a.bar([i + w/2 for i in x], [o[k2] for o in out], w, label="Held-out 15 ×3")
        a.bar_label(b1, labels=[fmt.format(o[k1]) for o in out], fontsize=7); a.bar_label(b2, labels=[fmt.format(o[k2]) for o in out], fontsize=7)
        a.set_xticks(list(x), [o["label"] for o in out], fontsize=8); a.set_title(title); a.set_ylabel(yl); a.legend(fontsize=8)
    lo = min([0.7] + [min(o["acc29"], o["accho"]) for o in out]); ax[0].set_ylim(0.7 if lo >= 0.7 else max(0.0, (int(lo * 20) / 20) - 0.05), 1.05)
    fig.suptitle("nl2sql-bench: main contenders (gpt-oss:120b, Chinook/Postgres)" +
                 ("; Arctic = its own 7B model on a dedicated HF A10G endpoint" if any(o["s"] == "arctic" for o in out) else ""))
    fig.tight_layout(); fig.savefig(R / "contenders.png", dpi=100); print("wrote results/contenders.png")


if __name__ == "__main__":
    main()
