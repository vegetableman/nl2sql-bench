# nl2sql-bench — WrenAI (out of the box / + semantic layer) vs DB-GPT vs Cube Core (+LLM adapter)

Same natural-language questions, same Postgres database, same LLM, measured the same way.

| System | How questions reach it | API used by the harness |
|---|---|---|
| **WrenAI 0.29.2 (out of the box)** — system `wrenai` (official docker compose) | NL → SQL; project = tables + PK/FK relationships only | `POST http://localhost:3000/api/v1/generate_sql` `{question, returnSqlDialect:true}` (wren-ui wraps wren-ai-service `/v1/asks` + polling; ibis converts Wren SQL to native Postgres SQL) |
| **WrenAI 0.29.2 + semantic layer** — system `wrenai_mdl` (2nd, identical WrenAI stack, compose project `wrenai-mdl`) | NL → SQL; project additionally carries the MDL in `wrenai_mdl/mdl/semantic_layer.yaml` (see below) | `POST http://localhost:3001/api/v1/generate_sql` (same API) |
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
.venv/bin/python bench/chart.py results/<run>   # single-run chart (make report builds the combined 4-system results/summary.png)
make mock                        # dry run without any LLM key (mock WrenAI/DB-GPT; Cube via reference queries)
make bench SYSTEMS=wrenai,dbgpt  # subset of systems
make wren-mdl                    # (after make up) start 2nd WrenAI stack (:3001/:5556) + build/deploy the semantic layer
make bench SYSTEMS=wrenai_mdl REPEATS=3
make report                      # combined 4-system report → results/combined_summary.md + results/summary.png
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
wrenai_mdl/                 2nd WrenAI stack (symlinked compose, own override/.env/config.yaml) + mdl/semantic_layer.yaml, mdl/deployed_mdl.json
dbgpt/                      Dockerfile (+psycopg2) and dbgpt-bench.toml
cube/model/cubes/chinook.yml  generic Chinook semantic model (12 cubes incl. a `manager` self-join cube)
meter/                      llm-meter proxy
db/                         Chinook SQL + read-only role
bench/questions.yaml        29 questions (8 easy / 9 medium / 12 hard) with gold SQL
bench/cube_reference_queries.yaml  hand-written Cube queries proving the model covers 23/29 questions
bench/harness.py            runner, scoring, report     bench/clients.py  per-system API clients
bench/setup_connections.py  connects tools to the DB    bench/verify_gold.py, bench/probe.py
bench/wren_mdl.py           builds/deploys the Wren semantic layer   bench/combine.py  combined 4-system report + summary.png
```

## WrenAI + semantic layer (`wrenai_mdl`)

Results (all four systems, OOTB vs MDL per question, by difficulty, latency, tokens, variance): `results/combined_summary.md`, `results/summary.png`.

**Why a second stack:** the out-of-the-box project (`wrenai/`, UI :3000, AI :5555, meter prefix `/wren/`) is left exactly as it was
benchmarked. `wrenai_mdl/` reuses the same upstream compose/config files (symlinks to `../wrenai/`), the same image digests, LLM,
embedding model and `config.yaml` pipeline settings; only the compose project (`wrenai-mdl`), host ports (UI **3001**, AI **5556**) and
the llm-meter prefix (`/wrenmdl/`, so tokens are counted separately) differ. It is not attached to `nl2sql-net` (same service names
would collide); it reaches Postgres and llm-meter through `host.docker.internal` (published ports 5432/8089).

**How it is built (`make wren-mdl` → `bench/wren_mdl.py`)** — only WrenAI's own modelling API (the GraphQL mutations the Wren UI calls),
driven from `wrenai_mdl/mdl/semantic_layer.yaml`; idempotent; ends with `deploy` = `SUCCESS` and dumps the deployed MDL to
`wrenai_mdl/mdl/deployed_mdl.json` (hash recorded there):
1. Data source + all 11 tables + 10 primary keys + 11 FK relationships (MANY_TO_ONE from the referencing table), same code as OOTB.
2. `updateModelMetadata`: display name + description for **all 11 models and all 64 columns**, description for all 11 relationships.
3. `createCalculatedField` — 9 per-entity rollups (Wren 0.29.2 allows one aggregate/math function over a column reached through relationships):
   `customer.lifetime_spend` = SUM(invoice.total), `customer.invoice_count` = COUNT(invoice.invoice_id),
   `invoice.units_on_invoice` = SUM(invoice_line.quantity), `track.units_sold` = SUM(invoice_line.quantity),
   `album.track_count` = COUNT(track.track_id), `artist.album_count` = COUNT(album.album_id), `genre.track_count` = COUNT(track.track_id),
   `playlist.track_count` = COUNT(playlist_track.track_id), `employee.supported_customer_count` = COUNT(customer.customer_id).
4. `createInstruction` (global, `isDefault: true`) — 9 generic rules, verbatim in the YAML: revenue definition (line level
   `unit_price*quantity` for catalogue entities, `invoice.total` for customers/countries/periods); track minutes = ms/60000.0; support rep =
   `customer.support_rep_id`, manager = `employee.reports_to`; dates = `invoice.invoice_date` with half-open year ranges; return only the requested
   columns; top-N = `ORDER BY … LIMIT N` (RANK/DENSE_RANK only when ties are asked for); no LIMIT unless a number is asked for; names are
   not unique → group by id too; Postgres rounding `ROUND(CAST(x AS NUMERIC), n)`.

**Not added, and why**
* **SQL pairs: none** (0 in `sql_pairs`). **Views: none** — a Wren view is stored and indexed as a question + SQL (`view_questions`), and the
  obvious candidates (revenue by artist / genre / country / month) would paraphrase benchmark questions.
* Metrics: WrenAI 0.29.2's UI/GraphQL has no metric-creation mutation (metrics exist only in the raw MDL schema), so none were added.
* Row-level calculated fields (line revenue `unit_price*quantity`, full name concat, duration in minutes) cannot be expressed with the
  0.29.2 calculated-field functions; they are described in column descriptions/instructions instead.

**Leakage check:** no element copies or paraphrases any of the 29 benchmark questions or gold SQL. Caveat: the generic rollups and
instructions are things a real modeller of Chinook would add, and some of them coincide with what certain questions need (e.g.
`genre.track_count`, `artist.album_count`, `album.track_count`, `playlist.track_count`, the revenue definition, the ties/LIMIT rules) — that
is the intended benefit of a semantic layer, but it means the comparison measures "WrenAI with a sensible, Chinook-aware model", authored
by someone who had seen the question set.

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
