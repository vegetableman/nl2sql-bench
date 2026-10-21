"""System `arctic` analysis -> results/<run>/arctic_analysis.md (from raw.jsonl; nothing rerun).
  bench/arctic_analysis.py                       headline A10G run: run-arctic-hf-a10g-r3 + arctic rows of run-gptoss120b-holdout-r3
  bench/arctic_analysis.py --gpu nvidia-l4 --run run-arctic-hf-l4-r3 --holdout-raw results/run-arctic-hf-l4-r3/holdout_partial.jsonl
EX strict/relaxed as scored by the harness; tie rule = misses re-labelled with mnemiq_jev_analysis.label (ho14 gold tie,
ho12 collation), exactly as for vanna_jev. Speed from the client's streaming timings (ttft, generation tok/s);
tokens from the endpoint's usage (completion tokens include the <think> reasoning)."""
import json, sys, pathlib, statistics as st
import psycopg, yaml
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from common import ROOT, load_env
import argparse
ap = argparse.ArgumentParser()
ap.add_argument("--gpu", default="nvidia-a10g")
ap.add_argument("--run", default="run-arctic-hf-a10g-r3")
ap.add_argument("--holdout-raw", default="results/run-gptoss120b-holdout-r3/raw.jsonl")
A = ap.parse_args()
sys.argv = sys.argv[:1]  # mnemiq_jev_analysis reads sys.argv at import
from mnemiq_jev_analysis import label

SETS = [("29", f"results/{A.run}/raw.jsonl", "bench/questions.yaml"), ("holdout", A.holdout_raw, "bench/questions_holdout.yaml")]


def pct(xs, p):
    xs = sorted(xs); k = (len(xs) - 1) * p / 100; f = int(k); c = min(f + 1, len(xs) - 1)
    return xs[f] + (xs[c] - xs[f]) * (k - f) if xs else float("nan")


def main():
    env = load_env(); conn = psycopg.connect(env["BENCH_DB_URL"])
    L = ["# Arctic-Text2SQL-R1-7B (system `arctic`)", "",
         f"Dedicated HF Inference Endpoint (aws us-east-1, 1x {A.gpu}, vLLM), Snowflake's eval prompt, temperature 0, full 11-table DDL. "
         "Latency = harness wall time per question through llm-meter (endpoint already warm; cold start excluded). "
         "Tie rule: misses re-executed and re-labelled (ho14 gold tie / ho12 collation) as for the other systems.", "",
         "| set | attempts | EX strict | EX relaxed | tie rule | timeouts | no-SQL | exec errors | p50 / p95 s | TTFT p50 s | gen tok/s p50 | avg prompt tok | avg output tok (incl. thinking) | max output tok |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    miss = []
    for name, run, qf in SETS:
        qs = {q["id"]: q for q in yaml.safe_load(open(ROOT / qf))["questions"]}
        R = [json.loads(l) for l in open(ROOT / run)]
        R = [r for r in R if r["system"] == "arctic"]
        if not R:
            continue
        tie = 0
        for r in R:
            if r["exact"]:
                tie += 1; continue
            q = qs[r["id"]]; how = r["status"]
            if r["status"] in ("wrong_result", "correct_extra_cols"):
                with conn.cursor() as cur:
                    cur.execute("BEGIN READ ONLY"); cur.execute(q["gold_sql"]); g = cur.fetchall(); conn.rollback()
                try:
                    ok, how = label(conn, env["BENCH_DB_URL"], q, r["generated"], g)
                except Exception as e:
                    conn.rollback(); ok, how = False, f"exec error {str(e)[:60]}"
                tie += ok
            miss.append((name, r, how))
        raw = [r.get("raw") or {} for r in R]
        ct = [x["completion_tokens"] for x in raw if x.get("completion_tokens")]
        pt = [x["prompt_tokens"] for x in raw if x.get("prompt_tokens")]
        tps = [x["tok_per_s"] for x in raw if x.get("tok_per_s")]
        tt = [x["ttft_s"] for x in raw if x.get("ttft_s") is not None]
        lat = [r["latency_s"] for r in R]; n = len(R)
        f = lambda k: sum(r["status"] == k for r in R)
        nosql = sum("no ```sql" in (r.get("error") or "") for r in R)
        L.append(f"| {name} | {n} | {sum(r['exact'] for r in R)}/{n} | {sum(r['relaxed'] for r in R)}/{n} | {tie}/{n} | {f('timeout')} | {nosql} | {f('exec_error')} | "
                 f"{pct(lat,50):.2f} / {pct(lat,95):.2f} | {pct(tt,50):.2f} | {pct(tps,50):.1f} | {st.mean(pt):.0f} | {st.mean(ct):.0f} | {max(ct)} |")
    L += ["", "## Every non-exact attempt", "", "| set | run | id | status | tie-rule label | error / reason | SQL |", "|---|---|---|---|---|---|---|"]
    for name, r, how in miss:
        L.append(f"| {name} | {r['run']} | {r['id']} | {r['status']} | {how} | {(r.get('error') or r.get('reason') or '')[:110].replace('|','/')} | `{(r.get('generated') or '')[:200].replace(chr(10),' ').replace('|','/')}` |")
    # Side view (NOT the headline): timeouts were greedy repetition loops ("The final SQL query is: ```sql ...```" again and
    # again, no EOS). Snowflake's own eval generates up to 8192 tokens and takes the last ```sql block, so it would score
    # these. Offline re-score of each timed-out attempt's partial completion (last complete ```sql block), nothing rerun.
    sys.path.insert(0, str(ROOT / "arctic")); import prompt as P
    L += ["", "## Side view: timed-out attempts re-scored from their partial completion (not the headline)", "",
          "| set | run | id | output tokens at cutoff | last complete ```sql block | label |", "|---|---|---|---|---|---|"]
    for name, r, how in miss:
        if r["status"] != "timeout":
            continue
        comp = ((r.get("raw") or {}).get("completion") or "")
        sql = P.parse_sql(comp[len(P.COT_PREFILL):] if comp.startswith(P.COT_PREFILL) else comp)
        if not r.get("raw"):
            L.append(f"| {name} | {r['run']} | {r['id']} | n/a | n/a | harness-side 180 s cut fired first; partial completion not recorded |"); continue
        if not sql:
            L.append(f"| {name} | {r['run']} | {r['id']} | {r['raw'].get('completion_tokens')} | none | no SQL |"); continue
        qs = {q["id"]: q for q in yaml.safe_load(open(ROOT / dict((a, c) for a, _, c in SETS)[name]))["questions"]}; q = qs[r["id"]]
        with conn.cursor() as cur:
            cur.execute("BEGIN READ ONLY"); cur.execute(q["gold_sql"]); g = cur.fetchall(); conn.rollback()
        try:
            ok, lab_ = label(conn, env["BENCH_DB_URL"], q, sql, g)
        except Exception as e:
            conn.rollback(); ok, lab_ = False, f"exec error {str(e)[:60]}"
        L.append(f"| {name} | {r['run']} | {r['id']} | {r['raw'].get('completion_tokens')} | `{sql[:140].replace(chr(10),' ').replace('|','/')}` | {'RIGHT' if ok else 'wrong'} ({lab_}) |")
    out = ROOT / "results" / A.run / "arctic_analysis.md"; out.write_text("\n".join(L) + "\n"); print("\n".join(L))


if __name__ == "__main__":
    main()
