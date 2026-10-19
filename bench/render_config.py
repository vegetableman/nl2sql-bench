"""Render WrenAI's .env and config.yaml from the top-level .env so both tools share
LLM model / embedder / upstream (via llm-meter). Never prints secret values."""
import pathlib, re, sys
import yaml
from dotenv import dotenv_values

ROOT = pathlib.Path(__file__).resolve().parents[1]
env = {**dotenv_values(ROOT / ".env.example"), **dotenv_values(ROOT / ".env")}


def render(W, meter, ui_port, ai_port, project=None, settings_override=None):

    # ---- wrenai/.env ----
    txt = (W / ".env.example").read_text()
    subs = {
        "OPENAI_API_KEY": env.get("LLM_API_KEY", ""),  # Wren config refers to this env name
        "GENERATION_MODEL": env["LLM_MODEL"],
        "TELEMETRY_ENABLED": "false",
        "USER_UUID": "6f1c2a8e-3b4d-4e5f-9a1b-2c3d4e5f6a7b",
        "HOST_PORT": ui_port,
        "AI_SERVICE_FORWARD_PORT": ai_port,
    }
    if project:
        subs["COMPOSE_PROJECT_NAME"] = project
    for k, v in subs.items():
        txt, n = re.subn(rf"(?m)^{k}=.*$", lambda m: f"{k}={v}", txt)
        if not n:
            txt += f"\n{k}={v}\n"
    (W / ".env").write_text(txt)

    # ---- wrenai/config.yaml ----
    docs = list(yaml.safe_load_all((W / "config.example.yaml").read_text()))
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
            d["settings"].update(settings_override or {})
    (W / "config.yaml").write_text(yaml.safe_dump_all(docs, sort_keys=False))
    print(f"rendered {W.name}/.env + {W.name}/config.yaml (model={env['LLM_MODEL']}, "
          f"embedder={env['EMBEDDING_MODEL']}, key={'present' if env.get('LLM_API_KEY') else 'MISSING'})")


# Variants of the 2nd (semantic-layer) stack. Same project / MDL / instructions; they differ only in the listed
# wren-ai-service setting, plus the llm-meter prefix so tokens are attributed to the right system.
MDL_VARIANTS = {
    "semantic": {"meter_tool": "wrenmdl", "settings": {}},  # system wrenai_mdl (default)
    "noreason": {"meter_tool": "wrenmdlnr", "settings": {"allow_sql_generation_reasoning": False}},  # wrenai_mdl_noreason
}


def render_mdl(variant):
    v = MDL_VARIANTS[variant]
    render(ROOT / "wrenai_mdl", f"http://host.docker.internal:{env.get('METER_PORT', '8089')}/{v['meter_tool']}/v1",
           env.get("WREN_MDL_UI_PORT", "3001"), env.get("WREN_MDL_AI_PORT", "5556"), project="wrenai-mdl",
           settings_override=v["settings"])
    (ROOT / "wrenai_mdl" / ".variant").write_text(variant + "\n")
    print(f"wrenai_mdl variant: {variant} {v['settings'] or '(upstream defaults)'}")


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--mdl-variant":  # only re-render the 2nd stack
        render_mdl(sys.argv[2]); sys.exit(0)
    # out-of-the-box WrenAI stack (unchanged)
    render(ROOT / "wrenai", "http://llm-meter:8080/wren/v1", env.get("WREN_UI_PORT", "3000"), env.get("WREN_AI_PORT", "5555"))
    # second WrenAI stack holding the semantic-layer (MDL) project; reaches llm-meter via the host port.
    # A plain `make render` always restores the default `semantic` variant (system wrenai_mdl).
    if (ROOT / "wrenai_mdl").exists():
        render_mdl("semantic")
