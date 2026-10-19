"""Per-stage latency breakdown of WrenAI asks from wren-ai-service log timestamps.
python bench/stage_latency.py   -> results/stage-latency/{stage_latency.md, stages.csv}

Inputs (results/stage-latency/):  <system>.wren-ai-service.log  (docker logs --timestamps of wren-ai-service)
                                   <system>.meter-events.json      (optional: llm-meter per-request timing)
plus results/<run>/raw.jsonl. The last 87 `POST /v1/asks` blocks of each log are matched in order to the 87 harness
rows (the harness is sequential; earlier blocks are smoke tests).

Stage boundaries (start lines logged by wren-ai-service):
  pre-retrieval     POST /v1/asks              -> "Intent Classification pipeline is running"   (historical-question, SQL-pair, instruction retrieval)
  intent            "Intent Classification"    -> "Ask Retrieval pipeline is running"            (intent LLM call incl. its schema lookup)
  schema retrieval  "Ask Retrieval"            -> "SQL Generation Reasoning" (or "SQL Functions Retrieval" when reasoning is off)
  reasoning         "SQL Generation Reasoning" -> "SQL Functions Retrieval pipeline is running"
  SQL generation    "SQL Functions Retrieval"  -> last GET /v1/asks/<id>/result  (generation LLM call + dry-run validation
                                                (+ correction) + wait until wren-ui's next 1 s poll)
wren-ai-service does not log the moment an ask finishes; it is only observed by wren-ui's 1 s poll (GET .../result).
When llm-meter timing events exist, "poll wait" = last GET - end of the ask's last chat completion (this also contains
the post-LLM dry-run validation, so it is an upper bound on pure polling wait)."""
import csv, datetime as dt, json, re, statistics, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from common import ROOT
D = ROOT / "results" / "stage-latency"
SYSTEMS = {"wrenai_mdl": "run-gptoss120b-wrenmdl-r3", "wrenai_mdl_noreason": "run-gptoss120b-wrenmdl-noreason-r3"}
TS = re.compile(r"^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d+)Z ")


def ts(line):
    m = TS.match(line)
    if not m:
        return None
    s = m.group(1)[:26]
    return dt.datetime.fromisoformat(s).replace(tzinfo=dt.timezone.utc).timestamp()


def blocks(path):
    out, cur = [], None
    for line in open(path, errors="replace"):
        t = ts(line)
        if t is None:
            continue
        if '"POST /v1/asks HTTP' in line:
            cur = {"post": t, "gets": [], "qid": None}; out.append(cur); continue
        if cur is None:
            continue
        m = re.search(r'GET /v1/asks/([0-9a-f-]{36})/result', line)
        if m:
            cur["qid"] = cur["qid"] or m.group(1)
            if m.group(1) == cur["qid"]:
                cur["gets"].append(t)
            continue
        for key, pat in (("intent", "Intent Classification pipeline is running"), ("askret", "Ask Retrieval pipeline is running"),
                         ("reason", "SQL Generation Reasoning pipeline is running"), ("sqlfunc", "SQL Functions Retrieval pipeline is running"),
                         ("gen", "] SQL Generation pipeline is running"), ("correction", "SQLCorrection pipeline is running")):
            if pat in line:
                if key == "correction":
                    cur["n_correction"] = cur.get("n_correction", 0) + 1
                else:
                    cur.setdefault(key, t)
    return out


def med(xs):
    xs = [x for x in xs if x is not None]
    return statistics.median(xs) if xs else None


def f(x):
    return "–" if x is None else f"{x:.2f}"


allrows, summ = [], {}
for s, run in SYSTEMS.items():
    logp = D / f"{s}.wren-ai-service.log"
    if not logp.exists():
        continue
    raw = [json.loads(l) for l in open(ROOT / "results" / run / "raw.jsonl")]
    bl = blocks(logp)[-len(raw):]
    assert len(bl) == len(raw), (s, len(bl), len(raw))
    ev = json.loads((D / f"{s}.meter-events.json").read_text()) if (D / f"{s}.meter-events.json").exists() else None
    for r, b in zip(raw, bl):
        last = b["gets"][-1]
        row = {"system": s, "run": r["run"], "id": r["id"], "status": r["status"], "e2e": r["latency_s"],
               "pre_retrieval": b["intent"] - b["post"] if "intent" in b else None,
               "intent": b["askret"] - b["intent"] if "intent" in b and "askret" in b else None,
               "schema_retrieval": (b.get("reason") or b["sqlfunc"]) - b["askret"] if "askret" in b and "sqlfunc" in b else None,
               "reasoning": b["sqlfunc"] - b["reason"] if "reason" in b and "sqlfunc" in b else (0.0 if "sqlfunc" in b else None),
               "sql_generation_to_last_poll": last - b["sqlfunc"] if "sqlfunc" in b else None,
               "ai_service_span": last - b["post"], "polls": len(b["gets"]),
               "poll_window": last - b["gets"][-2] if len(b["gets"]) > 1 else None,
               "reasoning_ran": "reason" in b, "corrections": b.get("n_correction", 0)}
        row["wren_ui_overhead"] = r["latency_s"] - row["ai_service_span"]
        if "t_start_epoch" in r:
            row["wren_ui_pre"] = b["post"] - r["t_start_epoch"]; row["wren_ui_post"] = r["t_end_epoch"] - last
            assert -0.5 < row["wren_ui_pre"] < 5, (s, r["id"], row["wren_ui_pre"])  # mapping sanity check
        if ev is not None:
            chats = [e for e in ev if e["kind"] == "chat" and b["post"] - 0.5 <= e["t_start"] <= last]
            row["llm_calls_in_window"] = len(chats)
            if chats:
                lend = max(e["t_end"] for e in chats)
                row["poll_wait_after_last_llm"] = last - lend
                row["sql_generation_llm_end"] = lend - b["sqlfunc"] if "sqlfunc" in b else None
                row["llm_busy"] = sum(e["t_end"] - e["t_start"] for e in chats)
                row["poll_wait_share_pct"] = 100 * row["poll_wait_after_last_llm"] / r["latency_s"]
        allrows.append(row)

keys = list(dict.fromkeys(k for r in allrows for k in r))
with open(D / "stages.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=keys, restval=""); w.writeheader(); w.writerows(allrows)

sysd = [s for s in SYSTEMS if any(r["system"] == s for r in allrows)]
R = lambda s: [r for r in allrows if r["system"] == s]
L = ["# WrenAI per-stage latency (from wren-ai-service log timestamps)", "",
     "Generated by `bench/stage_latency.py`; per-attempt data in `results/stage-latency/stages.csv`. Medians over the 87 attempts per system (seconds).",
     "Stage boundaries are the 'pipeline is running' log lines (see script docstring). wren-ui (`/api/v1/generate_sql`) polls wren-ai-service "
     "every 1 s (`setTimeout(…,1000)` in `wren-ui/src/pages/api/v1/generate_sql.ts`); the harness itself makes one blocking call, it does not poll.", "",
     "| stage (median s) | " + " | ".join(sysd) + " |", "|---|" + "---|" * len(sysd)]
rowsdef = [("pre-retrieval (historical Q / SQL pairs / instructions)", "pre_retrieval"), ("intent classification", "intent"),
           ("schema retrieval (Ask Retrieval)", "schema_retrieval"), ("SQL generation reasoning", "reasoning"),
           ("SQL generation incl. validation, up to wren-ui's last poll", "sql_generation_to_last_poll"),
           ("= wren-ai-service span (POST /v1/asks → last poll)", "ai_service_span"),
           ("wren-ui overhead (e2e − span: ask call, dialect conversion via ibis, response)", "wren_ui_overhead"),
           ("**end-to-end (harness latency)**", "e2e"),
           ("polls per question (GET …/result)", "polls"),
           ("…of which wren-ui before POST /v1/asks", "wren_ui_pre"), ("…of which wren-ui after last poll", "wren_ui_post"),
           ("SQL generation: until end of last LLM call (meter)", "sql_generation_llm_end"),
           ("last poll − end of last LLM call (validation + poll wait)", "poll_wait_after_last_llm"),
           ("…as % of end-to-end", "poll_wait_share_pct"),
           ("LLM calls per question (meter, in ask window)", "llm_calls_in_window"),
           ("time between the last two polls (s)", "poll_window")]
for name, k in rowsdef:
    L.append(f"| {name} | " + " | ".join(f(med([r.get(k) for r in R(s)])) for s in sysd) + " |")
L += ["", "| check | " + " | ".join(sysd) + " |", "|---|" + "---|" * len(sysd)]
for s in sysd:
    pass
L.append("| attempts where 'SQL Generation Reasoning pipeline' ran | " + " | ".join(f"{sum(r['reasoning_ran'] for r in R(s))}/{len(R(s))}" for s in sysd) + " |")
L.append("| attempts where 'Intent Classification pipeline' ran | " + " | ".join(f"{sum(r['intent'] is not None for r in R(s))}/{len(R(s))}" for s in sysd) + " |")
L.append("| SQL correction pipeline runs | " + " | ".join(str(sum(r['corrections'] for r in R(s))) for s in sysd) + " |")
L.append("| mean stage sum (s): pre+intent+schema+reasoning+generation | " + " | ".join(
    f"{statistics.mean(r['pre_retrieval'] + r['intent'] + r['schema_retrieval'] + r['reasoning'] + r['sql_generation_to_last_poll'] for r in R(s) if None not in (r['pre_retrieval'], r['intent'], r['schema_retrieval'], r['reasoning'], r['sql_generation_to_last_poll'])):.2f}" for s in sysd) + " |")
L.append("| mean e2e (s) | " + " | ".join(f"{statistics.mean(r['e2e'] for r in R(s)):.2f}" for s in sysd) + " |")
L += ["", "Polling: the time between the ask actually finishing and wren-ui's next poll is ≤ 1 s per question. "
      "Where meter timing exists, `last poll − end of last LLM call` measures it (upper bound, includes the post-LLM dry-run validation)."]
(D / "stage_latency.md").write_text("\n".join(L) + "\n")
print("\n".join(L))
