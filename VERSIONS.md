# Pinned versions (set up 2026-10-19, IST; switched to Ollama Cloud + local embeddings same day)

| Component | Version | Image digest / source |
|---|---|---|
| WrenAI (product release) | 0.29.2 (latest release with launcher; repo tag `0.29.2`) | compose + config from `Canner/WrenAI@0.29.2/docker/` |
| └ wren-ui | 0.32.3 | ghcr.io/canner/wren-ui@sha256:497d963746d682cb38c28dc109fe365d5898ed7e4456803ce16cc9a02e6a0ee3 |
| └ wren-ai-service | 0.29.3 | ghcr.io/canner/wren-ai-service@sha256:6afc02ce5ab696deef5a287ca3d2b71e0a9467b180dd1b276679095703b7a80f |
| └ wren-engine | 0.22.0 | ghcr.io/canner/wren-engine@sha256:08dd4069452935cb76986dbd090e7776fa0da53bdcc5f94120f2fd005d9ceb91 |
| └ wren-engine-ibis | 0.22.0 | ghcr.io/canner/wren-engine-ibis@sha256:54f1f060d64982c09d9b5f68420a95810a40e37da83449af8f68e8f25ae86940 |
| └ qdrant | v1.15.0 | qdrant/qdrant@sha256:709bd2656bb929b745a956260f61a6395d09f8eed72c5bf2131985ae70f95974 |
| └ wren-bootstrap | 0.1.5 | ghcr.io/canner/wren-bootstrap@sha256:731c3085cee5c87a79b07d27c9d10eb35f4830b0cac46a51ac8e9f6606698ada |
| WrenAI 2nd stack (`wrenai_mdl`) | same 0.29.2 compose/images/digests as above (compose project `wrenai-mdl`, ports 3001/5556) | semantic layer: `wrenai_mdl/mdl/semantic_layer.yaml`; deployed MDL hash in `wrenai_mdl/mdl/deployed_mdl.json`; variant `noreason` (system `wrenai_mdl_noreason`) = same + `allow_sql_generation_reasoning: false` |
| DB-GPT | 0.8.2 (latest release) | eosphorosai/dbgpt-openai@sha256:bd7d35ce7994f0f977007c28c839fffcdc80cfa810fa12ead9aecfd4e9b3d11f + `psycopg2-binary==2.9.10` layer (`dbgpt/Dockerfile`, image `nl2sql-bench/dbgpt:v0.8.2-pg`) |
| Cube Core | v1.8.8 (latest release) | cubejs/cube@sha256:fb9933de67b83c2ff9b1b61017d4f3cbafc8d248906b3e4923f57524b8c634d6 |
| Cube Core (`cube_v2`) | v1.8.8 (same image; latest on Docker Hub 2026-10-19 — not upgraded) | same digest; SQL API on (`CUBEJS_PG_SQL_PORT=15432`, `CUBESQL_SQL_PUSH_DOWN=true`, `CUBEJS_TESSERACT_SQL_PLANNER=true`); model `cube_v2/model` |
| mnemiq (`mnemiq`, `mnemiq_failopen`, `mnemiq_verified`, `mnemiq_jev`) | 0.1.0.dev0 — no releases/tags exist; pinned to commit `a453b05129f365c56a66f303b7e1911311d246fd` (main, 2026-10-19 16:34 -0700) | `agenticfabriq/mnemiq`, Apache-2.0; host Python 3.12.15 service via `uv sync --extra server` (uv.lock), `mnemiq serve --http` on :8090 (:8091 fail-open variant; :8092 `mnemiq_verified`, a separate git worktree of the same commit + `mnemiq/patches/verifier-tokens.patch`, sha256 b8ba4787050c…); duckdb 1.5.4, openai 2.45.0, fastapi 0.141.1; DuckDB extensions vss/fts/postgres_scanner/sqlite_scanner pre-seeded with `mnemiq extensions fetch` (HTTPS) because DuckDB's own INSTALL uses plain http, blocked on this box; launcher `mnemiq/run.sh` |
| Postgres | 16.4 | postgres@sha256:e62fbf9d3e2b49816a32c400ed2dba83e3b361e6833e624024309c35d334b412 |
| Chinook dataset | v1.4.5 (`Chinook_PostgreSql.sql`) | sha256 e3fde5c1a5b51a2a91429a702c9ca6e69ba56e6c7f5e112724d70c3d03db695e |
| llm-meter (local) | 1.0 (+ timing-only `GET /meter/events`, added before the `wrenai_mdl_noreason` run) | python:3.12-slim + starlette 0.41.3, uvicorn 0.32.1, httpx 0.28.1 |
| Harness | Python 3.12 venv | psycopg 3.2.3, PyYAML 6.0.2, httpx 0.28.1, python-dotenv 1.0.1, matplotlib 3.9.2 |
| Ollama (local, embeddings only) | 0.40.6 | ollama/ollama@sha256:265409e1d931028a8f7d5a32bcbafddd7bffbc6cc629d77efe9560adf692a5e7 |
| Embedding model | nomic-embed-text:latest (768-d) | registry.ollama.ai manifest; model blob sha256:970aa74c0a90ef7482477cf803618e776e173c007bf957f635f1015bfcfef0e6 |
| Chat LLM | gpt-oss:120b on Ollama Cloud (`https://ollama.com/v1`, OpenAI-compatible, Bearer `OLLAMA_API_KEY`) | hosted; version not pinnable by us |
| Docker | 26.1.5 (Debian docker.io), Compose 2.26.1 | |
| TypeSafe Jev (`mnemiq_jev` judge) | `jev-1.14.0` (versioned ID; = `jev-preview` on 2026-10-20, `jev-latest` -> 1.13) | hosted API `POST https://api.typesafe.ai/v1/systemone`, one `noul` question per judge call, via `mnemiq/patches/jev-judge.patch` (request variant `MNEMIQ_JEV_PROMPT`: `v1` for mnemiq_jev, `b` = default for mnemiq_jev_v2) (worktree `mnemiq/engine-jev`, same mnemiq commit); key `TYPESAFE_API_KEY` in .env |

## Vanna

* vanna **2.0.2** (PyPI, latest stable on 2026-10-21), extras `chromadb,openai,postgres`; chromadb 1.5.9, openai 3.35.1, psycopg2-binary 2.9.13 (`vanna/requirements.txt`), Python 3.12 venv `vanna/.venv`.
* Path: classic `vanna.legacy` (`ChromaDB_VectorStore` + `OpenAI_Chat`, `generate_sql`), not the 2.x Agent API. LLM gpt-oss:120b via llm-meter `/vanna/` (temperature 0); embeddings nomic-embed-text via the meter; training = `vanna/training/ddl.sql` (11 CREATE TABLEs) only.

## Arctic-Text2SQL-R1-7B (system `arctic`)

* Model **Snowflake/Arctic-Text2SQL-R1-7B** (Qwen2.5-Coder-7B-Instruct + GRPO, Apache-2.0), HF revision `2d73facaf7e15831d0b918d219e0d565f113f592`, **bf16, unquantized** (served from the HF repo, not GGUF).
* Served on a **dedicated Hugging Face Inference Endpoint** `arctic-text2sql-r1-7b-bench` (personal namespace, type `authenticated`): aws us-east-1, **headline: 1x nvidia-a10g** (`aws-us-east-1-nvidia-a10g-x1`; resumed 2026-10-21 09:13:08 UTC, running 09:15:58, paused 10:25:34 UTC by `arctic/bench.sh`'s EXIT trap), min 0 / max 1 replica, scale-to-zero after 15 min. First run (footnote): same endpoint on **1x nvidia-l4** (`aws-us-east-1-nvidia-l4-x1`), created 07:29:52 UTC, paused 09:11:09 UTC (`arctic/endpoint.py`, `arctic/endpoint_log.jsonl`).
* Prompt source: Snowflake **ArcticTraining** `projects/arctic_text2sql_r1/bird_eval/infer.py` (Figure C.1 of arXiv:2505.20315), verbatim except `Database Engine: PostgreSQL` (instead of SQLite) and the Chinook DDL as schema; greedy, **temperature 0**.
* Engine: HF-managed **vLLM** variant, image `vllm/vllm-openai:v0.32.0` (sha256:befccf0e7e4089aa23926bb6f887a85c0d46c2a99e6de5c5ffdf5cb7957c5b34; `/version` reported 0.32.0), served model id `Snowflake/Arctic-Text2SQL-R1-7B`, max_model_len 32768, vLLM defaults otherwise.
* Called with OpenAI `/v1/completions` (raw prompt = Snowflake's eval prompt rendered with the Qwen2.5 chat template + `<think>` pre-fill, `arctic/prompt.py`), temperature 0, max_tokens 4096, stop `<|im_end|>`/`<|endoftext|>`, streamed, through llm-meter `/arctic/` (`ARCTIC_UPSTREAM_BASE` in `.env`; the caller's `HF_TOKEN` is forwarded, never stored or logged). Endpoint management: huggingface_hub 2.2.0 in `arctic/.venv`.
* CPU fallback (smoke test only, not used for results): `ollama-arctic` container (compose profile `arctic`, ollama/ollama 0.40.6), `a-kore/Arctic-Text2SQL-R1-7B:latest` (Ollama id a55cdf92028b, **Q8_0**, 8.1 GB, weights blob sha256:a09d9d570bc883a030f5b1bfae1d88f7cdc73420d78350a36cb6eac03065d571, imported with `scripts/ollama_import_ns.sh`), derived model `arctic-text2sql-bench` (`arctic/Modelfile.tmpl`: pass-through template, temperature 0, repeat_penalty 1, num_ctx 4096, num_predict 2048, num_thread 8).
