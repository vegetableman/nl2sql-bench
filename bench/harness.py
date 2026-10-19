"""nl2sql-bench harness: same questions, same DB, same LLM -> WrenAI vs DB-GPT vs Cube(+LLM adapter).

python bench/harness.py [--systems wrenai,dbgpt,cube] [--repeats N] [--mock] [--limit K] [--ids e01,h03]
Outputs results/<run_id>/{results.csv, summary.md, raw.jsonl}
"""
import argparse, concurrent.futures as cf, csv, datetime as dt, json, statistics, sys, time
import httpx, psycopg, yaml
from zoneinfo import ZoneInfo
from common import ROOT, load_env, compare
from clients import WrenClient, WrenMDLClient, WrenMDLNoReasonClient, DBGPTClient, CubeClient, MockSQLClient

METER_KEY = {"wrenai": "wren", "wrenai_mdl": "wrenmdl", "wrenai_mdl_noreason": "wrenmdlnr"}  # llm-meter path prefix per system
LABELS = {"wrenai": "WrenAI 0.29.2 (out of the box)", "wrenai_mdl": "WrenAI 0.29.2 + semantic layer", "wrenai_mdl_noreason": "WrenAI 0.29.2 + semantic layer, no reasoning", "dbgpt": "DB-GPT 0.8.2", "cube": "Cube Core 1.8.8 + LLM adapter (harness-built)"}


def run_sql(conn, sql, limit_rows=100000):
    with conn.cursor() as cur:
        cur.execute("BEGIN READ ONLY")
        try:
            cur.execute(sql)
            rows = cur.fetchmany(limit_rows) if cur.description else []
            return rows
        finally:
            conn.rollback()


def meter_totals(env):
    try:
        return httpx.get(f"http://localhost:{env.get('METER_PORT', '8089')}/meter/totals", timeout=5).json()
    except Exception:
        return {}


def usage_delta(before, after, tool):
    b, a = before.get(tool, {}), after.get(tool, {})
    keys = ("prompt_tokens", "completion_tokens", "embedding_tokens", "chat_requests")
    return {k: a.get(k, 0) - b.get(k, 0) for k in keys} if a else {k: None for k in keys}


def pct(xs, p):
    xs = sorted(xs)
    if not xs:
        return None
    k = (len(xs) - 1) * p / 100
    f, c = int(k), min(int(k) + 1, len(xs) - 1)
    return xs[f] + (xs[c] - xs[f]) * (k - f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--systems", default="wrenai,dbgpt,cube")
    ap.add_argument("--repeats", type=int, default=1)
    ap.add_argument("--mock", action="store_true", help="no LLM: mock WrenAI/DB-GPT, Cube uses reference queries")
    ap.add_argument("--questions", default=str(ROOT / "bench" / "questions.yaml"))
    ap.add_argument("--ids", default="")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", default="")
    ap.add_argument("--timeout", type=float, default=180.0, help="wall-clock cap per tool call (s); exceeding = status 'timeout'")
    ap.add_argument("--resume", action="store_true", help="append to an existing --out run, skipping (run,id,system) already in raw.jsonl")
    a = ap.parse_args()

    env = load_env()
    qs = yaml.safe_load(open(a.questions))["questions"]
    if a.ids:
        want = set(a.ids.split(","))
        qs = [q for q in qs if q["id"] in want]
    if a.limit:
        qs = qs[: a.limit]
    systems = [s.strip() for s in a.systems.split(",") if s.strip()]
    if not a.mock and not env.get("LLM_API_KEY"):
        sys.exit("LLM_API_KEY is not set (in .env or environment). Use --mock for a dry run.")

    # wrenai_mdl and wrenai_mdl_noreason share the 2nd Wren stack; refuse to run one while the other variant is live
    want = {"wrenai_mdl": "semantic", "wrenai_mdl_noreason": "noreason"}
    live = (ROOT / "wrenai_mdl" / ".variant").read_text().strip() if (ROOT / "wrenai_mdl" / ".variant").exists() else "semantic"
    for s in systems:
        if s in want and not a.mock and want[s] != live:
            sys.exit(f"{s} needs the '{want[s]}' variant of the 2nd Wren stack but '{live}' is live "
                     f"(make {'wren-mdl-restore' if want[s] == 'semantic' else 'wren-mdl-noreason'})")
        if s in want and not a.mock and want[s] == "noreason" and "wrenai_mdl" in systems:
            sys.exit("wrenai_mdl and wrenai_mdl_noreason cannot run in the same invocation")

    clients = {}
    for s in systems:
        if s == "cube":
            clients[s] = CubeClient(env, mock=a.mock)
        elif a.mock:
            clients[s] = MockSQLClient(s, qs)
        else:
            clients[s] = {"wrenai": WrenClient, "wrenai_mdl": WrenMDLClient, "wrenai_mdl_noreason": WrenMDLNoReasonClient, "dbgpt": DBGPTClient}[s](env)

    run_id = a.out or (dt.datetime.now().strftime("%Y%m%d-%H%M%S") + ("-mock" if a.mock else ""))
    out = ROOT / "results" / run_id
    out.mkdir(parents=True, exist_ok=True)
    conn = psycopg.connect(env["BENCH_DB_URL"])
    gold = {}
    for q in qs:
        gold[q["id"]] = run_sql(conn, q["gold_sql"])

    rows, done = [], set()
    if a.resume and (out / "raw.jsonl").exists():
        for line in open(out / "raw.jsonl"):
            r = json.loads(line)
            r.pop("raw", None); r.pop("compiled_sql", None)
            r.setdefault("rate_limit_retries", 0)
            rows.append(r)
            done.add((r["run"], r["id"], r["system"]))
        print(f"resuming: {len(done)} attempts already recorded")
    raw = open(out / "raw.jsonl", "a" if a.resume else "w")
    pool = cf.ThreadPoolExecutor(max_workers=8)
    for rep in range(1, a.repeats + 1):
        for q in qs:
            for s in systems:
                if (rep, q["id"], s) in done:
                    continue
                c = clients[s]
                rl_retries = 0
                while True:
                    before = meter_totals(env)
                    t_wall0 = time.time()
                    t0 = time.perf_counter()
                    fut = pool.submit(lambda: c.generate(q["question"], qid=q["id"]) if s == "cube" else c.generate(q["question"]))
                    try:
                        res = fut.result(timeout=a.timeout)
                    except cf.TimeoutError:
                        res = {"error": f"timeout: no response within {a.timeout:.0f}s", "timeout": True}
                    except Exception as e:
                        res = {"error": f"client exception: {e}"}
                    latency = time.perf_counter() - t0
                    e = (res.get("error") or "").lower()
                    if rl_retries < 3 and ("429" in e or "rate limit" in e or "too many requests" in e):
                        rl_retries += 1
                        print(f"   rate-limited ({s} {q['id']}), backing off {30 * rl_retries}s", flush=True)
                        time.sleep(30 * rl_retries)
                        continue
                    break
                usage = usage_delta(before, meter_totals(env), METER_KEY.get(s, s))
                rec = {"run": rep, "id": q["id"], "difficulty": q["difficulty"], "system": s,
                       "latency_s": round(latency, 3), "status": "", "exact": False, "relaxed": False,
                       "reason": "", "generated": "", "error": res.get("error", "") or "",
                       "cube_expressible": q.get("cube_expressible", True), "rate_limit_retries": rl_retries, **usage}
                if "cube_query" in res:
                    rec["generated"] = json.dumps(res["cube_query"], ensure_ascii=False)
                elif res.get("sql"):
                    rec["generated"] = res["sql"]
                pred = None
                if res.get("timeout") or rec["error"].startswith("client exception: ") and "timed out" in rec["error"].lower():
                    rec["status"] = "timeout"
                elif rec["error"]:
                    rec["status"] = "unsupported" if rec["error"].startswith("unsupported") else "tool_error"
                elif "rows" in res:
                    pred = res["rows"]
                else:
                    try:
                        pred = run_sql(conn, res["sql"])
                    except Exception as e:
                        rec["status"] = "exec_error"
                        rec["error"] = f"{type(e).__name__}: {str(e).strip()[:300]}"
                if pred is not None:
                    cmp = compare(gold[q["id"]], pred, q.get("order_matters", False), q.get("order_cols"))
                    rec.update(exact=cmp["exact"], relaxed=cmp["relaxed"], reason=cmp["reason"],
                               status="correct" if cmp["exact"] else ("correct_extra_cols" if cmp["relaxed"] else "wrong_result"))
                rows.append(rec)
                raw.write(json.dumps({**rec, "t_start_epoch": round(t_wall0, 3), "t_end_epoch": round(t_wall0 + latency, 3), "raw": res.get("raw"), "compiled_sql": (c.compiled_sql(res["cube_query"]) if s == "cube" and res.get("cube_query") and not a.mock else None)}, ensure_ascii=False, default=str) + "\n")
                raw.flush()
                print(f"[run {rep}] {q['id']:4} {s:7} {rec['status']:18} {latency:6.2f}s {rec['error'][:90]}", flush=True)
    raw.close()

    rows.sort(key=lambda r: (r["run"], [q["id"] for q in qs].index(r["id"]) if r["id"] in [q["id"] for q in qs] else 999, systems.index(r["system"]) if r["system"] in systems else 9))
    fields = list(dict.fromkeys(k for r in rows for k in r.keys()))
    with open(out / "results.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, restval="")
        w.writeheader()
        w.writerows(rows)
    md = summary(rows, systems, qs, a, env)
    (out / "summary.md").write_text(md)
    print(f"\nwrote {out}/results.csv, summary.md, raw.jsonl\n")
    print(md)


def summary(rows, systems, qs, a, env):
    L = [f"# nl2sql-bench report ({'MOCK dry-run — numbers are NOT real tool results' if a.mock else 'live run'})", "",
         f"- Report generated: {dt.datetime.now(ZoneInfo('Asia/Kolkata')).strftime('%Y-%m-%d %H:%M')} IST",
         f"- Dataset: Chinook 1.4.5 on Postgres 16.4; {len(qs)} questions x {a.repeats} run(s)",
         f"- LLM: `{env['LLM_MODEL']}` via `{env['LLM_UPSTREAM_BASE']}`, embeddings `{env['EMBEDDING_MODEL']}` (same for all systems, via llm-meter)",
         "- EX(exact) = same result set as gold (column order free; row order checked only when the question requires it).",
         "  EX(relaxed) also accepts extra columns. Latency = wall time of the tool's API call (question -> SQL / result).",
         "  Tokens = measured by llm-meter proxy (chat prompt+completion; embeddings separate).",
         f"- Per-call wall-clock cap {a.timeout:.0f}s: a call exceeding it is recorded as `timeout` and counts as a failure.", ""]
    L += ["| System | EX exact | EX relaxed | wrong result | tool errors | exec errors | timeouts | unsupported | p50 latency s | p95 latency s | avg prompt tok | avg completion tok |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for s in systems:
        R = [r for r in rows if r["system"] == s]
        n = len(R)
        lat = [r["latency_s"] for r in R]
        pt = [r["prompt_tokens"] for r in R if r["prompt_tokens"] is not None]
        ct = [r["completion_tokens"] for r in R if r["completion_tokens"] is not None]
        f = lambda k: sum(1 for r in R if r["status"] == k)
        L.append(f"| {LABELS.get(s, s)} | {sum(r['exact'] for r in R)}/{n} ({100*sum(r['exact'] for r in R)/n:.0f}%) | "
                 f"{sum(r['relaxed'] for r in R)}/{n} ({100*sum(r['relaxed'] for r in R)/n:.0f}%) | {f('wrong_result')} | {f('tool_error')} | {f('exec_error')} | {f('timeout')} | {f('unsupported')} | "
                 f"{pct(lat,50):.2f} | {pct(lat,95):.2f} | {statistics.mean(pt) if pt else 0:.0f} | {statistics.mean(ct) if ct else 0:.0f} |")
    L += ["", "## EX (exact) by difficulty", "", "| System | easy | medium | hard |", "|---|---|---|---|"]
    for s in systems:
        cells = []
        for d in ("easy", "medium", "hard"):
            R = [r for r in rows if r["system"] == s and r["difficulty"] == d]
            cells.append(f"{sum(r['exact'] for r in R)}/{len(R)}" if R else "-")
        L.append(f"| {LABELS.get(s, s)} | " + " | ".join(cells) + " |")
    if "cube" in systems:
        R = [r for r in rows if r["system"] == "cube" and r["cube_expressible"]]
        ne = [q["id"] for q in qs if not q.get("cube_expressible", True)]
        L += ["", f"Cube: EX on the {len({r['id'] for r in R})} questions expressible in the Cube model: "
              f"{sum(r['exact'] for r in R)}/{len(R)}. Not expressible as a single Cube query: {', '.join(ne) or 'none'}."]
    L += ["", "## Per question (status per run)", "", "| id | diff | " + " | ".join(systems) + " |", "|---|---|" + "---|" * len(systems)]
    for q in qs:
        cells = []
        for s in systems:
            R = [r for r in rows if r["system"] == s and r["id"] == q["id"]]
            cells.append(" ".join({"correct": "✅", "correct_extra_cols": "🟡", "wrong_result": "❌", "exec_error": "💥",
                                   "tool_error": "⚠️", "unsupported": "⛔", "timeout": "⏱️"}.get(r["status"], "?") for r in R))
        L.append(f"| {q['id']} | {q['difficulty']} | " + " | ".join(cells) + " |")
    L += ["", "Legend: ✅ exact match, 🟡 match with extra columns, ❌ wrong result, 💥 SQL failed to execute, ⚠️ tool/API error, ⏱️ timeout (no answer within the per-call cap; counted as failure), ⛔ declared unsupported."]
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    main()
