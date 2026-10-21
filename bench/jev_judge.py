"""TypeSafe Jev answer check, variant b -- the request mnemiq_jev_v2 sends (mnemiq/patches/jev-judge.patch, JevJudge with
MNEMIQ_JEV_PROMPT=b), as a dependency-free module (stdlib only) shared by the Vanna + Jev systems and the offline
same-SQL scorer. The constants and the `state` shape are copied verbatim from the patch, and bench/jev_judge_parity.py
checks that request_body() here equals JevJudge.request_body() there for the same inputs.

render_result() reproduces mnemiq's render_result footer format (header line, ` | `-joined cells, NULL, 240-char cell cap,
`... showing N of M rows (truncated)` / `(N rows)`), which is what the request's row counts are parsed from.
The API key comes from TYPESAFE_API_KEY and is never returned, logged or printed.
"""
import json, os, re, time, urllib.error, urllib.request

URL = "https://api.typesafe.ai/v1/systemone"
MODEL = os.environ.get("JEV_MODEL", "jev-1.14.0")
QID = "answers_question"
PREVIEW_ROWS = 50          # variant b
THRESHOLD = 0.5
MAX_CELL = 240
INSTRUCTIONS_SQL = ("`sql` was run against the database described by `schema` and returned `result`, which shows "
                    "`result_rows_shown` of `result_total_rows` rows. Judge the SQL logic, not the completeness of the "
                    "shown rows: when `result_preview_truncated` is true the other rows exist but are not shown. Does "
                    "`sql` correctly answer `question`, given `schema`? Check the right tables and joins, every filter "
                    "the question implies, the right aggregation and grain, and the ordering and limit the question "
                    "asks for. A plausible-looking number can still be wrong.")
NOTE = "preview_truncated: true -- judge the correctness of the SQL logic, not the completeness of the preview"
PRICE_PER_INPUT_TOKEN = 0.042 / 1e6


def _cell(v):
    if v is None:
        return "NULL", False
    s = str(v)
    return (s, False) if len(s) <= MAX_CELL else (s[:MAX_CELL - 1] + "…", True)


def render_result(columns, rows, max_rows=PREVIEW_ROWS):
    total = len(rows)
    if total == 0:
        return f"columns: {', '.join(columns)}\n(0 rows)"
    shown = min(total, max_rows); lines = [" | ".join(columns)]; cut = False
    for r in rows[:shown]:
        cells = [_cell(v) for v in r]; cut = cut or any(c for _, c in cells)
        lines.append(" | ".join(t for t, _ in cells))
    lines.append(f"... showing {shown} of {total} rows (truncated)" if shown < total else f"({total} rows)")
    if cut:
        lines.append(f"... some values were longer than {MAX_CELL} characters and end in `…`; "
                     "those are shortened for this prompt, not the stored value")
    return "\n".join(lines)


def _counts(preview):
    last = preview.strip().splitlines()[-3:] if preview else []
    for line in reversed(last):
        m = re.match(r"\.\.\. showing (\d+) of (\d+) rows \(truncated\)", line)
        if m:
            return int(m[1]), int(m[2]), True
        m = re.match(r"\((\d+) rows\)$", line)
        if m:
            return int(m[1]), int(m[1]), False
    return None, None, None


def request_body(question, schema, sql, preview):
    shown, total, truncated = _counts(preview)
    state = {"question": question, "schema": schema, "sql": sql, "result": preview,
             "result_rows_shown": shown, "result_total_rows": total, "result_preview_truncated": truncated}
    if truncated:
        state["note"] = NOTE
    return {"model": MODEL, "state": state, "questions": {QID: {"type": "noul", "instructions": INSTRUCTIONS_SQL}}}


def judge(question, schema, sql, preview, timeout=60.0):
    """-> dict(p, status, fell_open, reason, latency_ms, model, input_tokens, output_tokens). Fail-open on error:
    p=None and fell_open=True (the caller returns the answer)."""
    body = json.dumps(request_body(question, schema, sql, preview)).encode()
    req = urllib.request.Request(URL, data=body, method="POST", headers={
        "Authorization": "Bearer " + os.environ.get("TYPESAFE_API_KEY", ""), "Content-Type": "application/json"})
    t0 = time.perf_counter(); out = {"p": None, "status": None, "fell_open": True, "reason": None}
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            out["status"] = resp.status; payload = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        out.update(status=e.code, reason="error", detail=e.read().decode(errors="replace")[:200]); payload = None
    except Exception as e:
        out.update(reason="error", detail=type(e).__name__); payload = None
    out["latency_ms"] = round((time.perf_counter() - t0) * 1000)
    if payload is None:
        return out
    try:
        ans = payload["answers"][QID]
        if ans.get("type") != "noul":
            raise ValueError("answer type")
        p = float(ans["noul"])
        if not 0.0 <= p <= 1.0:
            raise ValueError("range")
    except Exception:
        out.update(reason="unparsed", detail=json.dumps(sorted(payload) if isinstance(payload, dict) else str(type(payload))))
        return out
    u = payload.get("usage") or {}
    out.update(p=p, fell_open=False, model=payload.get("model"), input_tokens=u.get("input_tokens"), output_tokens=u.get("output_tokens"))
    return out


def log_line(rec, question, sql):
    """BENCH-JEV line in the same shape as the mnemiq patch (no key, no headers)."""
    return (f"BENCH-JEV status={rec.get('status')} latency_ms={rec.get('latency_ms')} model={rec.get('model')} prompt=b "
            f"input_tokens={rec.get('input_tokens')} output_tokens={rec.get('output_tokens')} noul={rec.get('p')} "
            f"reason={rec.get('reason')} q={question[:70]!r} sql={json.dumps(sql)}")
