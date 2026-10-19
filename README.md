# nl2sql-bench — WrenAI vs DB-GPT vs Cube Core (+LLM adapter)

Same natural-language questions, same Postgres database, same LLM, measured the same way.

| System | How questions reach it | API used by the harness |
|---|---|---|
| **WrenAI 0.29.2** (official docker compose) | NL → SQL | `POST http://localhost:3000/api/v1/generate_sql` `{question, returnSqlDialect:true}` (wren-ui wraps wren-ai-service `/v1/asks` + polling; ibis converts Wren SQL to native Postgres SQL) |
| **DB-GPT 0.8.2** (official `dbgpt-openai` image + psycopg2) | NL → SQL (chat_data mode) | `POST http://localhost:5670/api/v2/chat/completions` `{chat_mode:"chat_data", chat_param:"chinook", stream:false}`; SQL is parsed out of the `<chart-view content=…>` block in the reply |
| **Cube Core 1.8.8 + LLM adapter (harness-built)** | Cube Core has **no OSS NL interface** (the AI API / D3 is Cube Cloud-only; OSS v1.8.8 api-gateway only has `/v1/load, /sql, /meta, /cubesql, /dry-run, …`). The harness gives the same LLM the `/v1/meta` model + join list and asks for a Cube REST query JSON (1 self-correction retry on Cube errors) | `POST http://localhost:4000/cubejs-api/v1/load` |

Fairness controls
* One Postgres (Chinook 1.4.5) container; WrenAI, DB-GPT and Cube connect to it as the same **read-only role `bench`**.
* All LLM/embedding traffic of all three goes through **llm-meter** (`meter/`, port 8089), a pass-through OpenAI-compatible proxy that sends chat calls to `LLM_UPSTREAM_BASE` and embedding calls to `EMBEDDING_UPSTREAM_BASE`, and counts tokens per tool (neither tool reports usage in its API). Same chat model for all three (`LLM_MODEL`, default **`gpt-oss:120b` on Ollama Cloud**), temperature 0; same embedding model for Wren and DB-GPT (**`nomic-embed-text`, 768-d, local `ollama` container** — Ollama Cloud has no embeddings API: `/v1/embeddings` 404, `/api/embed` 401).
* Tools run with their default pipelines (WrenAI: intent classification, reasoning, SQL correction; DB-GPT: ChatWithDbExecute).
* Every generated SQL is re-executed by the harness on the same Postgres in a `READ ONLY` transaction (30 s statement timeout) and compared with the gold result.

## Quick start

```bash
cd /workspace/nl2sql-bench
cp .env.example .env            # first time only (make up does this too)
# put your key in .env:  LLM_API_KEY=<Ollama Cloud key>   (chmod 600 .env; .env is git-ignored)
make up                          # docker up + connect WrenAI/DB-GPT to Postgres + deploy/index schema
make verify                      # gold SQL check, Cube reference queries, API probe
make bench REPEATS=3             # real run → results/<timestamp>/{results.csv,summary.md,raw.jsonl}
.venv/bin/python bench/chart.py results/<run>   # → results/summary.png
make mock                        # dry run without any LLM key (mock WrenAI/DB-GPT; Cube via reference queries)
make bench SYSTEMS=wrenai,dbgpt  # subset of systems
make down / make clean           # stop / stop + delete volumes
```

After changing the key or model in `.env`, run `make up` again: it re-renders `wrenai/.env` + `wrenai/config.yaml`,
recreates the containers whose env changed, re-deploys Wren (schema indexing) and re-embeds DB-GPT's schema.

### LLM settings (`.env`)
| var | default | meaning |
|---|---|---|
| `LLM_API_KEY` | *(empty — required)* | key for `LLM_UPSTREAM_BASE`; injected into WrenAI/DB-GPT as `OPENAI_API_KEY` (the env name their OpenAI-compatible clients read) and used by the Cube adapter |
| `LLM_MODEL` | `gpt-oss:120b` | chat model for all systems (name as listed by `GET https://ollama.com/v1/models`) |
| `LLM_UPSTREAM_BASE` | `https://ollama.com/v1` | any OpenAI-compatible endpoint (OpenAI, Groq, OpenRouter, vLLM…) |
| `LLM_CONTEXT_WINDOW` | 128000 | told to WrenAI's litellm config |
| `EMBEDDING_MODEL` / `EMBEDDING_DIM` / `EMBEDDING_UPSTREAM_BASE` | `nomic-embed-text` / 768 / `http://ollama:11434/v1` | embeddings (WrenAI + DB-GPT schema retrieval). For OpenAI use `text-embedding-3-small` / 1536 / `https://api.openai.com/v1` and `STRIP_AUTH_FOR_EMBEDDINGS=0`. Wren's qdrant collections are recreated at ai-service start (`recreate_index: true`), so a dimension change only needs `make up`. |

### Using a different database
1. Edit `BENCH_PG_HOST/PORT/DB/USER/PASSWORD` (address as seen **from containers**; for a DB on this machine use the host IP / `host.docker.internal`) and `BENCH_DB_URL` (as seen from the harness on the host), e.g.
   `BENCH_DB_URL=postgresql://user:pass@db.example.com:5432/mydb`.
2. `make up` (WrenAI is re-onboarded with `--force` via `cd bench && ../.venv/bin/python setup_connections.py --force`; DB-GPT datasource is named after `BENCH_PG_DB`).
3. Provide a matching question file (`--questions my.yaml`, same format as `bench/questions.yaml`) and, for Cube, a model under `cube/model/` (+ optionally `bench/cube_reference_queries.yaml`).
   Only Postgres is wired today (Wren type `POSTGRES`, DB-GPT `postgresql`, Cube `postgres`).

## Layout
```
docker-compose.yml          postgres, llm-meter, dbgpt, cube   (network nl2sql-net)
wrenai/                     upstream WrenAI 0.29.2 compose + override joining nl2sql-net; .env/config.yaml are rendered
dbgpt/                      Dockerfile (+psycopg2) and dbgpt-bench.toml
cube/model/cubes/chinook.yml  generic Chinook semantic model (12 cubes incl. a `manager` self-join cube)
meter/                      llm-meter proxy
db/                         Chinook SQL + read-only role
bench/questions.yaml        29 questions (8 easy / 9 medium / 12 hard) with gold SQL
bench/cube_reference_queries.yaml  hand-written Cube queries proving the model covers 23/29 questions
bench/harness.py            runner, scoring, report     bench/clients.py  per-system API clients
bench/setup_connections.py  connects tools to the DB    bench/verify_gold.py, bench/probe.py
```

## Metrics
* **EX exact**: result multiset equals gold (column order free; numbers rounded to 2 dp; dates normalised; row order checked only for `order_matters` questions, on the sort key so ties don't count). **EX relaxed**: additionally allows extra columns.
* **Latency**: wall-clock of the API call (p50/p95 over all questions × repeats). WrenAI's `generate_sql` returns SQL only; DB-GPT's chat_data also executes the SQL inside DB-GPT; Cube adapter = LLM call + Cube execution.
* **Tokens**: prompt/completion per question from llm-meter (embedding tokens separately). Background LLM work a tool does between questions is attributed to the next question.
* Status per attempt: `correct`, `correct_extra_cols`, `wrong_result`, `exec_error`, `tool_error`, `unsupported` (Cube adapter declined).

## Cube notes
Not expressible as a single Cube REST query over the model (counted as failures for Cube, listed in the report):
h03 (compare with average of per-customer totals), h04 (per-country top-N/window), h05 (LAG), h07 (anti-join), h09 (set difference), h11 (share of total).
m07 can only be relaxed-correct in Cube (ordering by a measure requires the measure in the result).

## Box-specific notes
* `ollama pull` fails on this box (the CDN host resolves to a non-public 198.18.x address and Ollama refuses the redirect); `scripts/ollama_import.sh` downloads the registry blobs with curl, verifies sha256 and installs them into the container (`make up` falls back to it automatically).
* DB-GPT re-embeds all datasources at startup; calling its `/refresh` endpoint at the same time races and leaves the chroma collection empty, so `setup_connections.py` only refreshes with `--refresh`.
* No systemd: `make docker` starts `dockerd` by hand. Legacy iptables on this VM had `FORWARD DROP`, which silently blocked container↔container traffic; `make netfix` inserts `ACCEPT` for `br-+` bridges in `DOCKER-USER` (legacy table).
* WrenAI's FK auto-detection reads `information_schema.constraint_column_usage`, which hides constraints from a non-owner role, so `setup_connections.py` reads PK/FK from `pg_catalog` and sets them through Wren's own GraphQL mutations (`updateModel`, `saveRelations`).
* Telemetry: Wren `TELEMETRY_ENABLED=false`, Cube `CUBEJS_TELEMETRY=false`, Langfuse disabled.
