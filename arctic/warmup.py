"""Warm the HF endpoint before a timed run (cold start / scale-from-zero is NOT part of benchmark latency):
wait for /v1/models, check the served model id equals ARCTIC_MODEL, then 2 throwaway completions with the bench prompt
on a non-benchmark question. Goes through llm-meter /arctic/ (also checks the route + auth). HF_TOKEN never printed."""
import os, sys, time, pathlib, httpx
sys.path.insert(0, str(pathlib.Path(__file__).parent)); import prompt as P
env = {}
for l in (pathlib.Path(__file__).parents[1] / ".env").read_text().splitlines():
    if "=" in l and not l.lstrip().startswith("#"):
        k, v = l.split("=", 1); env[k.strip()] = v.strip()
base = f"http://localhost:{env.get('METER_PORT', '8089')}/arctic/v1"
H = {"Authorization": f"Bearer {os.environ['HF_TOKEN']}"}
t0 = time.time()
while True:
    try:
        r = httpx.get(f"{base}/models", headers=H, timeout=30)
        if r.status_code == 200:
            ids = [m["id"] for m in r.json()["data"]]; break
        print("models:", r.status_code, r.text[:120])
    except Exception as e:
        print("models: error", type(e).__name__)
    if time.time() - t0 > 1200: sys.exit("endpoint not serving after 20 min")
    time.sleep(15)
print("served models:", ids, "| want:", env.get("ARCTIC_MODEL"))
model = env.get("ARCTIC_MODEL") or ids[0]
for i in range(2):
    t = time.time()
    r = httpx.post(f"{base}/completions", headers=H, timeout=300, json={"model": model, "prompt": P.build_prompt("Which playlists exist? Return their names."),
                   "temperature": 0, "max_tokens": 512, "stop": ["<|im_end|>", "<|endoftext|>"]})
    j = r.json(); u = j.get("usage") or {}
    print(f"warmup {i+1}: HTTP {r.status_code} {time.time()-t:.2f}s usage={u} sql={P.parse_sql(j['choices'][0]['text'])[:100]!r}" if r.status_code == 200 else f"warmup {i+1}: HTTP {r.status_code} {r.text[:200]}")
