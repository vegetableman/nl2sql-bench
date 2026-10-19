"""llm-meter: tiny OpenAI-compatible pass-through proxy that counts tokens per tool.

Both WrenAI and DB-GPT are pointed at http://llm-meter:8080/<tool>/v1 so that
  * they hit exactly the same upstream model/endpoint, and
  * token usage is measured identically (neither tool exposes usage in its API).

Routes
  /{tool}/v1/{path}   forwarded to LLM_UPSTREAM_BASE/{path}
                      (or EMBEDDING_UPSTREAM_BASE when path starts with 'embeddings')
  GET /meter/totals   cumulative counters per tool
  POST /meter/reset   zero the counters
  GET /health
The Authorization header from the caller is forwarded untouched; this proxy never logs it.
"""
import json
import os
import threading
from collections import defaultdict

import httpx
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response, StreamingResponse
from starlette.routing import Route

LLM_UP = os.environ.get("LLM_UPSTREAM_BASE", "https://api.openai.com/v1").rstrip("/")
EMB_UP = os.environ.get("EMBEDDING_UPSTREAM_BASE", LLM_UP).rstrip("/")
_lock = threading.Lock()


def _blank():
    return {"requests": 0, "errors": 0, "chat_requests": 0, "embedding_requests": 0,
            "prompt_tokens": 0, "completion_tokens": 0, "embedding_tokens": 0}


COUNTERS = defaultdict(_blank)
client = httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=20.0))
HOP = {"host", "content-length", "connection", "accept-encoding", "transfer-encoding"}


def _add(tool, usage, kind):
    if not usage:
        return
    with _lock:
        c = COUNTERS[tool]
        if kind == "embeddings":
            c["embedding_tokens"] += int(usage.get("prompt_tokens") or usage.get("total_tokens") or 0)
        else:
            c["prompt_tokens"] += int(usage.get("prompt_tokens") or 0)
            c["completion_tokens"] += int(usage.get("completion_tokens") or 0)


async def proxy(request: Request):
    tool = request.path_params["tool"]
    path = request.path_params["path"]
    kind = "embeddings" if path.startswith("embeddings") else "chat"
    base = EMB_UP if kind == "embeddings" else LLM_UP
    body = await request.body()
    stream = False
    if body and request.method == "POST":
        try:
            j = json.loads(body)
            if j.get("stream"):
                stream = True
                j.setdefault("stream_options", {})["include_usage"] = True
                body = json.dumps(j).encode()
        except Exception:
            pass
    headers = {k: v for k, v in request.headers.items() if k.lower() not in HOP}
    with _lock:
        COUNTERS[tool]["requests"] += 1
        COUNTERS[tool][f"{'embedding' if kind == 'embeddings' else 'chat'}_requests"] += 1
    url = f"{base}/{path}"
    if request.url.query:
        url += "?" + request.url.query
    req = client.build_request(request.method, url, headers=headers, content=body)
    up = await client.send(req, stream=True)
    if up.status_code >= 400:
        with _lock:
            COUNTERS[tool]["errors"] += 1
    rh = {k: v for k, v in up.headers.items() if k.lower() not in HOP | {"content-encoding"}}
    if stream and up.status_code < 400:
        async def gen():
            buf = b""
            async for chunk in up.aiter_raw():
                yield chunk
                buf += chunk
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    line = line.strip()
                    if line.startswith(b"data:") and b'"usage"' in line:
                        try:
                            _add(tool, json.loads(line[5:]).get("usage"), kind)
                        except Exception:
                            pass
            await up.aclose()
        return StreamingResponse(gen(), status_code=up.status_code, headers=rh)
    data = await up.aread()
    await up.aclose()
    try:
        _add(tool, json.loads(data).get("usage"), kind)
    except Exception:
        pass
    return Response(data, status_code=up.status_code, headers=rh)


async def totals(_):
    with _lock:
        return JSONResponse({k: dict(v) for k, v in COUNTERS.items()})


async def reset(_):
    with _lock:
        COUNTERS.clear()
    return JSONResponse({"ok": True})


async def health(_):
    return JSONResponse({"ok": True, "llm_upstream": LLM_UP, "embedding_upstream": EMB_UP})


app = Starlette(routes=[
    Route("/health", health),
    Route("/meter/totals", totals),
    Route("/meter/reset", reset, methods=["POST"]),
    Route("/{tool}/v1/{path:path}", proxy, methods=["GET", "POST", "PUT", "DELETE"]),
])
