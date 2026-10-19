"""Render WrenAI's .env and config.yaml from the top-level .env so both tools share
LLM model / embedder / upstream (via llm-meter). Never prints secret values."""
import pathlib, re, sys
import yaml
from dotenv import dotenv_values

ROOT = pathlib.Path(__file__).resolve().parents[1]
env = {**dotenv_values(ROOT / ".env.example"), **dotenv_values(ROOT / ".env")}
W = ROOT / "wrenai"

# ---- wrenai/.env ----
txt = (W / ".env.example").read_text()
subs = {
    "OPENAI_API_KEY": env.get("LLM_API_KEY", ""),  # Wren config refers to this env name
    "GENERATION_MODEL": env["LLM_MODEL"],
    "TELEMETRY_ENABLED": "false",
    "USER_UUID": "6f1c2a8e-3b4d-4e5f-9a1b-2c3d4e5f6a7b",
    "HOST_PORT": env.get("WREN_UI_PORT", "3000"),
    "AI_SERVICE_FORWARD_PORT": env.get("WREN_AI_PORT", "5555"),
}
for k, v in subs.items():
    txt, n = re.subn(rf"(?m)^{k}=.*$", lambda m: f"{k}={v}", txt)
    if not n:
        txt += f"\n{k}={v}\n"
(W / ".env").write_text(txt)

# ---- wrenai/config.yaml ----
docs = list(yaml.safe_load_all((W / "config.example.yaml").read_text()))
meter = "http://llm-meter:8080/wren/v1"
for d in docs:
    if d.get("type") == "llm":
        d["models"] = [{
            "alias": "default",
            "model": f"openai/{env['LLM_MODEL']}",
            "api_base": meter,
            "api_key_name": "OPENAI_API_KEY",
            "timeout": 120,
            "context_window_size": int(env.get("LLM_CONTEXT_WINDOW", "128000")),
            "kwargs": {"n": 1, "temperature": 0, "max_tokens": 4096},
        }]
    elif d.get("type") == "embedder":
        d["models"] = [{
            "alias": "default",
            "model": f"openai/{env['EMBEDDING_MODEL']}",
            "api_base": meter,
            "api_key_name": "OPENAI_API_KEY",
            "timeout": 120,
        }]
    elif d.get("type") == "document_store":
        d["embedding_model_dim"] = int(env["EMBEDDING_DIM"])
    elif "settings" in d:
        d["settings"]["langfuse_enable"] = False
        d["settings"]["logging_level"] = "INFO"
(W / "config.yaml").write_text(yaml.safe_dump_all(docs, sort_keys=False))
print(f"rendered wrenai/.env + wrenai/config.yaml (model={env['LLM_MODEL']}, "
      f"embedder={env['EMBEDDING_MODEL']}, key={'present' if env.get('LLM_API_KEY') else 'MISSING'})")
