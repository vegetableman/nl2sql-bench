"""vanna_jev / vanna_jev_retry outcome analysis (from raw.jsonl `raw.attempts`, which carry each attempt's SQL, execution
outcome and Jev reply), plus the offline same-SQL view of plain vanna (jev_offline.jsonl, bench/vanna_jev_offline.py).
Every decline's SQL and every miss is re-executed and labelled against gold (ho14 tie / ho12 collation rules via
mnemiq_jev_analysis.label). Writes results/run-gptoss120b-vanna-r3/vanna_jev_analysis.md."""
import json, sys, pathlib, statistics as st
from collections import Counter
import psycopg, yaml
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from common import ROOT, load_env
import jev_judge as J
from mnemiq_jev_analysis import label

SETS = [("29", "run-gptoss120b-vanna-r3", "bench/questions.yaml"), ("holdout", "run-gptoss120b-holdout-r3", "bench/questions_holdout.yaml")]
SYSTEMS = ["vanna_jev", "vanna_jev_retry"]


def main():
    env = load_env(); conn = psycopg.connect(env["BENCH_DB_URL"]); gold = {}; qs = {}
    recs = []
    for name, run, qf in SETS:
        d = yaml.safe_load(open(ROOT / qf)); qs[name] = {q["id"]: q for q in (d["questions"] if isinstance(d, dict) else d)}
        for l in open(ROOT / "results" / run / "raw.jsonl"):
            r = json.loads(l)
            if r["system"] in SYSTEMS + ["vanna"]:
                r["_set"] = name; recs.append(r)

    def lab(setname, qid, sql):
        q = qs[setname][qid]; k = (setname, qid)
        if k not in gold:
            with conn.cursor() as cur:
                cur.execute("BEGIN READ ONLY"); cur.execute(q["gold_sql"]); gold[k] = cur.fetchall(); conn.rollback()
        try:
            return label(conn, env["BENCH_DB_URL"], q, sql, gold[k])
        except Exception as e:
            conn.rollback(); return False, f"exec error: {str(e)[:60]}"

    L = ["# Vanna + TypeSafe Jev answer check (vanna_jev, vanna_jev_retry)", "",
         "Jev request = mnemiq_jev_v2's variant b (bench/jev_judge.py; parity-checked against the mnemiq patch by bench/jev_judge_parity.py). "
         "Schema = the DDL Vanna retrieved for the question. Threshold 0.5, fail-closed; Jev error -> fail-open; SQL that fails to execute is returned unjudged. "
         "Jev tokens/latency are Jev's own `usage` / measured round trip (Jev bypasses llm-meter). Cost = input tokens x $0.042/M.", "",
         "| set | system | attempts | EX exact | tie-rule | LLM calls/q | Jev calls/q | passed | declined | fell open | exec failed (unjudged) | retried | rescued by retry | Jev input tok | Jev cost | Jev p50/p95 ms |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    dec_rows, miss_rows, retry_rows = [], [], []
    for name, _, _ in SETS:
        for s in SYSTEMS:
            R = [r for r in recs if r["_set"] == name and r["system"] == s]
            if not R:
                continue
            att = [a for r in R for a in ((r.get("raw") or {}).get("attempts") or [])]
            jv = [a["jev"] for a in att if a.get("jev")]
            tok = sum(j.get("input_tokens") or 0 for j in jv); lat = sorted(j["latency_ms"] for j in jv if j.get("latency_ms") is not None)
            dec = Counter((r.get("raw") or {}).get("decision") for r in R)
            tie = 0
            for r in R:
                if r["exact"]:
                    tie += 1; continue
                if r["status"] in ("wrong_result",):
                    ok, how = lab(name, r["id"], r.get("generated") or ""); tie += ok
            retried = [r for r in R if len((r.get("raw") or {}).get("attempts") or []) > 1]
            rescued = [r for r in retried if (r.get("raw") or {}).get("decision") != "declined" and r["exact"]]
            L.append(f"| {name} | {s} | {len(R)} | {sum(r['exact'] for r in R)}/{len(R)} | {tie}/{len(R)} | {st.mean((r.get('raw') or {}).get('llm_calls') or 0 for r in R):.2f} | "
                     f"{len(jv)/len(R):.2f} | {dec['passed']} | {dec['declined']} | {dec['fell_open']} | {dec['exec_failed_unjudged']} | {len(retried)} | {len(rescued)} | "
                     f"{tok:,} | ${tok*J.PRICE_PER_INPUT_TOKEN:.4f} | {(f'{lat[len(lat)//2]} / {lat[int(0.95*(len(lat)-1))]}' if lat else 'n/a')} |")
            for r in R:
                A = (r.get("raw") or {}).get("attempts") or []
                for i, a in enumerate(A):
                    if a.get("decision") == "declined":
                        ok, how = lab(name, r["id"], a["sql"])
                        dec_rows.append(f"| {name} | {s} | {r['id']} | {r['run']} | {i+1} | {a['jev']['p']} | {'RIGHT' if ok else 'wrong'} | {how} | `{a['sql'][:120].replace(chr(10),' ').replace('|','/')}` |")
                if len(A) > 1:
                    ok1, _ = lab(name, r["id"], A[0]["sql"]); ok2, how2 = lab(name, r["id"], A[1]["sql"])
                    retry_rows.append(f"| {name} | {s} | {r['id']} | {r['run']} | {A[0]['jev']['p']} ({'right' if ok1 else 'wrong'}) | "
                                      f"{(A[1].get('jev') or {}).get('p', 'unjudged: ' + str(A[1].get('exec_error',''))[:40])} ({'right' if ok2 else 'wrong'}, {how2}) | {r['status']} |")
                if not r["exact"]:
                    if r["status"] == "declined":
                        continue  # listed with the declines
                    ok, how = lab(name, r["id"], r.get("generated") or "") if r["status"] != "exec_error" else (False, "exec error")
                    last = A[-1] if A else {}
                    miss_rows.append(f"| {name} | {s} | {r['id']} | {r['run']} | {r['status']} | {'RIGHT (' + how + ')' if ok else how} | "
                                     f"{(last.get('jev') or {}).get('p', '-')} | {last.get('decision', '-')} |")
    L += ["", "## Every decline (each declined attempt; retry rows show both)", "",
          "| set | system | id | run | attempt | Jev p | SQL right? | how | SQL |", "|---|---|---|---|---|---|---|---|---|"] + (dec_rows or ["| - | - | - | - | - | - | - | none | |"])
    L += ["", "## Retries (vanna_jev_retry)", "", "| set | system | id | run | 1st: p (SQL) | 2nd: p (SQL) | final status |", "|---|---|---|---|---|---|---|"] + (retry_rows or ["| - | - | - | - | - | none | |"])
    L += ["", "## Every other miss (not a decline)", "", "| set | system | id | run | status | SQL right? | Jev p (last attempt) | decision |", "|---|---|---|---|---|---|---|---|"] + (miss_rows or ["| - | - | - | - | - | none | | |"])
    off = ROOT / "results/run-gptoss120b-vanna-r3/jev_offline.jsonl"
    if off.exists():
        X = [json.loads(l) for l in open(off)]; Jd = [x for x in X if x.get("exec_ok")]
        blk = lambda x: (not x["jev_fell_open"]) and x["jev_p"] < J.THRESHOLD
        tok = sum(x.get("jev_input_tokens") or 0 for x in Jd)
        L += ["", "## Offline same-SQL view: Jev variant b on plain `vanna`'s 132 saved SQLs", "",
              f"Judged {len(Jd)} (1 exec failure not judged, as online); Jev HTTP {sorted({x['jev_status'] for x in Jd})}; fell open {sum(x['jev_fell_open'] for x in Jd)}; "
              f"input tokens {tok:,} (${tok*J.PRICE_PER_INPUT_TOKEN:.4f}).", "",
              "| set | right passed | right BLOCKED | wrong CAUGHT | wrong passed | not judged (exec error) |", "|---|---|---|---|---|---|"]
        for S in ("29", "holdout"):
            Y = [x for x in X if x["set"] == S]; Z = [x for x in Y if x.get("exec_ok")]
            L.append(f"| {S} | {sum(x['right'] and not blk(x) for x in Z)} | {sum(x['right'] and blk(x) for x in Z)} | {sum((not x['right']) and blk(x) for x in Z)} | "
                     f"{sum((not x['right']) and not blk(x) for x in Z)} | {len(Y)-len(Z)} |")
        L += ["", "Plain vanna's known misses under this check: " + "; ".join(
            f"{x['set']}:{x['id']} r{x['run']} ({x['status']}; {'right: ' + x['how'] if x['right'] else x['how'][:40]}) -> "
            + ("not judged" if not x.get("exec_ok") else f"p={x['jev_p']} {'BLOCKED' if blk(x) else 'passed'}")
            for x in X if x["status"] not in ("correct", "correct_extra_cols"))]
    txt = "\n".join(L) + "\n"; (ROOT / "results/run-gptoss120b-vanna-r3/vanna_jev_analysis.md").write_text(txt); print(txt)


if __name__ == "__main__":
    main()
