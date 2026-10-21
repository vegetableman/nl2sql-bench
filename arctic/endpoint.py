"""HF Inference Endpoint for system `arctic` (personal namespace only).
  endpoint.py create [instance_type]   nvidia-l4 x1 aws us-east-1 (fallback nvidia-a10g), scale-to-zero 15 min, vLLM image
  endpoint.py status | wait | pause | resume | info
HF_TOKEN comes from the environment and is never printed. State/timestamps -> arctic/endpoint_log.jsonl."""
import json, sys, time, datetime as dt, pathlib
from huggingface_hub import create_inference_endpoint, get_inference_endpoint, whoami

NAME = "arctic-text2sql-r1-7b-bench"
VLLM = "vllm/vllm-openai:v0.32.0"
LOG = pathlib.Path(__file__).parent / "endpoint_log.jsonl"


def ns():
    w = whoami()
    assert w.get("type") == "user", "personal namespace only"
    return w["name"]


def log(**kw):
    kw["t_utc"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    LOG.open("a").write(json.dumps(kw) + "\n"); print(json.dumps(kw), flush=True)


def ep():
    return get_inference_endpoint(NAME, namespace=ns())


def main():
    cmd = sys.argv[1]
    if cmd == "create":
        for it in ([sys.argv[2]] if len(sys.argv) > 2 else ["nvidia-l4", "nvidia-a10g"]):
            try:
                e = create_inference_endpoint(NAME, repository="Snowflake/Arctic-Text2SQL-R1-7B", framework="pytorch",
                    task="text-generation", accelerator="gpu", vendor="aws", region="us-east-1", instance_type=it,
                    instance_size="x1", min_replica=0, max_replica=1, scale_to_zero_timeout=15,
                    custom_image={"vLLM": {"url": VLLM, "port": 8000}}, namespace=ns(), type="authenticated")
                log(event="created", instance_type=it, status=e.status, url=e.url); return
            except Exception as ex:
                log(event="create_error", instance_type=it, error=f"{type(ex).__name__}: {str(ex)[-500:]}")
        sys.exit(1)
    e = ep()
    if cmd == "status":
        log(event="status", status=e.status, url=e.url, instance=e.raw.get("compute", {}))
    elif cmd == "info":
        print(json.dumps({k: e.raw.get(k) for k in ("compute", "model", "status", "provider", "type")}, indent=1, default=str))
    elif cmd == "wait":
        t = time.time(); last = None
        while time.time() - t < 3600:
            e.fetch()
            if e.status != last:
                log(event="status", status=e.status, msg=(e.raw.get("status") or {}).get("message")); last = e.status
            if e.status == "running":
                return
            if e.status in ("failed", "updateFailed"):
                sys.exit(2)
            time.sleep(15)
        sys.exit(3)
    elif cmd == "pause":
        e.pause(); time.sleep(5); e.fetch(); log(event="paused", status=e.status)
    elif cmd == "resume":
        e.resume(); log(event="resume", status=e.status)


if __name__ == "__main__":
    main()
