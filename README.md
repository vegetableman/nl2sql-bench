# nl2sql-bench — WrenAI (out of the box / + semantic layer / + semantic layer, no reasoning) vs DB-GPT vs Cube Core (+LLM adapter: baseline / rich model + SQL API v2)

Same natural-language questions, same Postgres database, same LLM, measured the same way.

| System | How questions reach it | API used by the harness |
|---|---|---|
| **WrenAI 0.29.2 (out of the box)** — system `wrenai` (official docker compose) | NL → SQL; project = tables + PK/FK relationships only | `POST http://localhost:3000/api/v1/generate_sql` `{question, returnSqlDialect:true}` (wren-ui wraps wren-ai-service `/v1/asks` + polling; ibis converts Wren SQL to native Postgres SQL) |
| **WrenAI 0.29.2 + semantic layer** — system `wrenai_mdl` (2nd, identical WrenAI stack, compose project `wrenai-mdl`) | NL → SQL; project additionally carries the MDL in `wrenai_mdl/mdl/semantic_layer.yaml` (see below) | `POST http://localhost:3001/api/v1/generate_sql` (same API) |
| **WrenAI 0.29.2 + semantic layer, no reasoning** — system `wrenai_mdl_noreason` (same 2nd stack, switched with `make wren-mdl-noreason`) | identical to `wrenai_mdl` except wren-ai-service setting `allow_sql_generation_reasoning: false` | `POST http://localhost:3001/api/v1/generate_sql` |
| **DB-GPT 0.8.2** (official `dbgpt-openai` image + psycopg2) | NL → SQL (chat_data mode) | `POST http://localhost:5670/api/v2/chat/completions` `{chat_mode:"chat_data", chat_param:"chinook", stream:false}`; SQL is parsed out of the `<chart-view content=…>` block in the reply |
| **Cube Core 1.8.8 + LLM adapter (baseline)** — system `cube` | Cube Core has **no OSS NL interface** (the AI API / D3 is Cube Cloud-only; OSS v1.8.8 api-gateway only has `/v1/load, /sql, /meta, /cubesql, /dry-run, …`). The harness gives the same LLM the `/v1/meta` model + join list and asks for a Cube REST query JSON (1 self-correction retry on Cube errors) | `POST http://localhost:4000/cubejs-api/v1/load` |
| **Cube Core 1.8.8 + rich model + LLM adapter v2 (harness-built)** — system `cube_v2` (service `cube_v2`, REST :4001, SQL API :15432) | same LLM gets the *views* of `cube_v2/model` (with descriptions) from `/v1/meta` and writes ONE Cube SQL API query (Postgres dialect, `MEASURE()`, push-down/post-processing); 1 repair retry on Cube errors | Cube SQL API (Postgres wire protocol) at `localhost:15432` — executed by Cube, never directly on Postgres |

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
make wren-mdl-noreason           # switch 2nd stack to the no-reasoning variant, then:
make bench SYSTEMS=wrenai_mdl_noreason REPEATS=3
make wren-mdl-restore            # switch back (wrenai_mdl); config.yaml is re-rendered byte-identically
.venv/bin/python bench/stage_latency.py   # per-stage latency from wren-ai-service logs (see below)
make report                      # combined 5-system report → results/combined_summary.md + results/summary.png
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
docker-compose.yml          postgres, llm-meter, ollama, dbgpt, cube, cube_v2   (network nl2sql-net)
wrenai/                     upstream WrenAI 0.29.2 compose + override joining nl2sql-net; .env/config.yaml are rendered
wrenai_mdl/                 2nd WrenAI stack (symlinked compose, own override/.env/config.yaml) + mdl/semantic_layer.yaml, mdl/deployed_mdl.json
dbgpt/                      Dockerfile (+psycopg2) and dbgpt-bench.toml
cube/model/cubes/chinook.yml  generic Chinook semantic model (12 cubes incl. a `manager` self-join cube)
meter/                      llm-meter proxy
db/                         Chinook SQL + read-only role
bench/questions.yaml        29 questions (8 easy / 9 medium / 12 hard) with gold SQL
bench/cube_reference_queries.yaml  hand-written Cube REST queries proving the baseline model covers 23/29 questions
cube_v2/model/              cube_v2 model (cubes/ + views/)    bench/cube_v2_reference_sql.yaml + verify_cube_v2.py  SQL API references (29/29)
bench/harness.py            runner, scoring, report     bench/clients.py  per-system API clients
bench/setup_connections.py  connects tools to the DB    bench/verify_gold.py, bench/probe.py
bench/wren_mdl.py           builds/deploys the Wren semantic layer   bench/combine.py  combined 5-system report + summary.png
bench/stage_latency.py      per-stage WrenAI latency from wren-ai-service logs (+ llm-meter timing events)
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

## WrenAI + semantic layer, no reasoning (`wrenai_mdl_noreason`)

One change versus `wrenai_mdl`: wren-ai-service `settings.allow_sql_generation_reasoning: false` (a documented setting in WrenAI
0.29.2's `docker/config.example.yaml`, read by `src/config.py` → `AskService`; when false, `ask.py` skips the
`sql_generation_reasoning` pipeline and calls SQL generation with `sql_generation_reasoning=None`). Intent classification,
retrieval, SQL functions/knowledge retrieval, correction, the project, deployed MDL, instructions, LLM, embeddings and wren-ui
(1 s polling) are unchanged.

How the switch works (`bench/render_config.py --mdl-variant {semantic|noreason}`, Make targets `wren-mdl-noreason` /
`wren-mdl-restore`):
* re-renders `wrenai_mdl/config.yaml`; the only diff is that setting plus the llm-meter prefix (`/wrenmdlnr/` instead of `/wrenmdl/`)
  so tokens are attributed separately (the meter strips the prefix; upstream requests are identical);
* recreates `wren-ai-service` (its qdrant collections are recreated at start, `recreate_index: true`), re-deploys the unchanged
  project and re-indexes the 9 instructions (`bench/wren_mdl.py --redeploy`), and fails unless the deployed MDL hash equals
  `wrenai_mdl/mdl/deployed_mdl.json` (453930b9…) and qdrant holds 9 instructions / 0 SQL pairs;
* writes `wrenai_mdl/.variant`; the harness refuses to run `wrenai_mdl` while `noreason` is live and vice versa.
* `make wren-mdl-restore` (or `make render`) renders the default variant; the restored `wrenai_mdl/config.yaml` has the same sha256
  (4f09a2c0…) as during the `wrenai_mdl` benchmark run (with the same `.env`).

Verification: in the benchmark run the "SQL Generation Reasoning pipeline is running" line appears 0 times in the wren-ai-service log
(vs 87/87 attempts for `wrenai_mdl`); "Intent Classification pipeline" ran 87/87.

**Per-stage latency** (`bench/stage_latency.py` → `results/stage-latency/stage_latency.md`, `stages.csv`): stage boundaries
come from wren-ai-service's "… pipeline is running" log lines; the end of an ask is not logged, it is seen at wren-ui's last
`GET /v1/asks/<id>/result` poll. For the no-reasoning run llm-meter also recorded per-request timing (`GET /meter/events`,
saved as `results/stage-latency/wrenai_mdl_noreason.meter-events.json`), which measures the gap between the last LLM call ending
and the poll that picks the result up. Raw logs are saved next to it.

## Metrics
* **EX exact**: result multiset equals gold (column order free; numbers rounded to 2 dp; dates normalised; row order checked only for `order_matters` questions, on the sort key so ties don't count). **EX relaxed**: additionally allows extra columns.
* **Latency**: wall-clock of the API call (p50/p95 over all questions × repeats). WrenAI's `generate_sql` returns SQL only; DB-GPT's chat_data also executes the SQL inside DB-GPT; Cube adapter = LLM call + Cube execution.
* **Tokens**: prompt/completion per question from llm-meter (embedding tokens separately). Background LLM work a tool does between questions is attributed to the next question.
* Status per attempt: `correct`, `correct_extra_cols`, `wrong_result`, `exec_error`, `tool_error`, `unsupported` (Cube adapter declined).

## Cube v2 (`cube_v2`): rich model + SQL API adapter

**Why the SQL API (not REST, not hybrid).** A REST `/v1/load` query is one aggregation shape (measures × dimensions +
filters), so comparisons against an aggregate of aggregates, per-group top-N, LAG, anti-joins / set differences and
share-of-total over arbitrary groupings cannot be expressed in a single query (the baseline's 15 `unsupported`).
Cube's SQL API (enabled with `CUBEJS_PG_SQL_PORT=15432`; query push-down is on by default since 1.0 and set explicitly,
`CUBESQL_SQL_PUSH_DOWN=true`) turns each `SELECT … FROM <view>` into a Cube query and runs window functions,
subqueries, EXCEPT etc. as post-processing / push-down — still compiled and executed by Cube against Postgres. Every
REST query shape is also expressible as an SQL API query, so a REST fallback would add a second prompt format without
adding coverage; v2 therefore uses the SQL API only. Cube stays at **v1.8.8** (the latest release on Docker Hub on
2026-10-19; no upgrade needed or possible). Tesseract (needed for multi-stage measures) is on by default in 1.8.8
(`CUBEJS_TESSERACT_SQL_PLANNER=true`, also set explicitly).

**Data model** (`cube_v2/model/`, the baseline model `cube/model/` is untouched):
* 13 cubes (`cubes/catalog.yml`, `cubes/sales.yml`) with descriptions on cubes and members: artist, album, genre, media_type,
  track, playlist, playlist_track, employee, `manager` and `support_rep` (both `extends: employee`), customer, invoice, invoice_line.
* Joins: many_to_one along every FK (album→artist, track→album/genre/media_type, playlist_track→playlist/track,
  invoice_line→invoice/track, invoice→customer, customer→support_rep, employee→manager) plus one_to_many where a
  rollup needs it (artist→album, track→invoice_line, customer→invoice). Cube joins are LEFT JOINs; the employees view
  description says the top manager has NULL manager fields.
* Subquery dimensions (`sub_query: true`): `track.units_sold` (COALESCE(units sold, 0)), `customer.lifetime_spend`,
  `customer.invoice_count`, `customer.first_purchase_date`, `customer.last_purchase_date`.
* Derived dimension: `track.duration_minutes` (= milliseconds / 60000.0).
* Measures: count on every cube; track total/avg duration, max/min/avg list price, distinct genres / albums;
  playlist_track count + distinct tracks; customer avg lifetime spend; invoice total_sales, avg invoice total,
  purchasing customers, first/last invoice date; invoice_line revenue (unit_price × quantity), quantity_sold, line count.
* Rolling windows: `invoice.total_sales_running_total` (trailing unbounded), `total_sales_year_to_date` (to_date year),
  `total_sales_trailing_3_months`.
* Multi-stage measures (Tesseract): `invoice.total_sales_prior_month` and `total_sales_prior_year` (time_shift, prior),
  `invoice_line.revenue_share_of_total_pct` (= 100 × revenue / grand total via a hidden helper with `grain: {keep_only: []}`).
  A generic multi-stage `rank` measure was tried and dropped: without naming the dimension to rank over
  (`grain.exclude`), it returned 1 for every row.
* Segments: `track.is_video`, `employee.has_manager`, `customer.is_business`.
* Views (`views/business.yml`) = the business entities the LLM sees: `sales` (line level, with invoice, customer, support
  rep, track, album, artist, genre, media type), `invoices`, `customers`, `tracks`, `albums`, `artists`, `genres`,
  `media_types`, `playlists`, `employees` (with manager). Members from joined cubes get explicit aliases (`artist_name`,
  `support_rep_first_name`, `manager_id`, …).

**Adapter v2 prompt** (`CUBE_V2_SYSTEM` in `bench/clients.py`; the LLM also gets every view's dimensions, measures
and segments with their types and descriptions from `/v1/meta`). It returns `{"sql": …}` or `{"unsupported": …}`.
Rules, in short:
1. Query only the listed views; one view per SELECT, no joins between views.
2. Wrap measures in MEASURE().
3. Selected dimensions go in GROUP BY; a dimensions-only SELECT without GROUP BY is ungrouped.
4. Cube drops GROUP BY keys that are not selected. For one row per entity, select the id in an inner query and only
   the requested columns in an outer query.
5. Window functions, CASE, EXCEPT and similar go in an outer query over a view subquery; no correlated subqueries.
6. Filter measures in an outer WHERE.
7. Use half-open date ranges and DATE_TRUNC grouping, with EXTRACT in an outer query when a number is asked for;
   rolling and prior-period measures need DATE_TRUNC.
8. Return only the requested columns.
9. No LIMIT unless a number is asked for; top-N → ORDER BY … LIMIT N; ties only when asked.
10. View joins are LEFT JOINs.
11. Anti-joins: use EXCEPT or NOT IN.

Rules 4, 5 and 11 come from testing Cube 1.8.8 directly:
* `SELECT name … GROUP BY track_id, name` returned 207 rows, not 212.
* A window function written directly over a view, or a correlated subquery, fails with "Can't detect Cube query".
* **`NOT EXISTS` is planned as `EXISTS`.** `EXPLAIN` shows `Subquery: types=[Exists]` with the NOT dropped, and
  `LEFT JOIN … IS NULL` returns 0. Both give wrong results silently, while `EXCEPT` and `NOT IN` are correct.

**Leakage check.** No member, view, segment or prompt rule is named after a benchmark question, and no question
or gold SQL is in the prompt. `bench/cube_v2_reference_sql.yaml` is used only by `make verify` and `--mock`.
These generic elements line up with what particular questions need (they are what a Chinook modeller would add,
but the author had seen the question set):
* `track.units_sold` and rule 11 → h07, h09
* `customer.lifetime_spend` → h03, h04
* `total_sales_prior_month` → h05
* `revenue_share_of_total_pct` → h11
* `total_sales_year_to_date` → h10
* `duration_minutes` → e04, m05
* `has_manager` / LEFT JOIN rule 10 → h08
* `is_business` → e08
* `distinct_genres` → h06
* rule 4 → e04
* rules 8 and 9 → e07, m07, h10, e04

**Expressibility.** `make verify` runs `bench/verify_cube_v2.py`, which executes the hand-written SQL API query for
every question through cube_v2 and compares it with gold: 29/29 reproduce gold. The baseline REST model covers
23/29 (h03, h04, h05, h07, h09 and h11 are not expressible as one REST query). One caveat: the prior-month measure
uses true calendar shifting, so for January 2024 it returns December 2023's revenue rather than NULL, unlike a LAG
within 2024.

## Cube notes (baseline `cube`)
Not expressible as a single Cube REST query over the model (counted as failures for Cube, listed in the report):
h03 (compare with average of per-customer totals), h04 (per-country top-N/window), h05 (LAG), h07 (anti-join), h09 (set difference), h11 (share of total).
m07 can only be relaxed-correct in Cube (ordering by a measure requires the measure in the result).

## Box-specific notes
* `ollama pull` fails on this box (the CDN host resolves to a non-public 198.18.x address and Ollama refuses the redirect); `scripts/ollama_import.sh` downloads the registry blobs with curl, verifies sha256 and installs them into the container (`make up` falls back to it automatically).
* DB-GPT re-embeds all datasources at startup; calling its `/refresh` endpoint at the same time races and leaves the chroma collection empty, so `setup_connections.py` only refreshes with `--refresh`.
* No systemd: `make docker` starts `dockerd` by hand. Legacy iptables on this VM had `FORWARD DROP`, which silently blocked container↔container traffic; `make netfix` inserts `ACCEPT` for `br-+` bridges in `DOCKER-USER` (legacy table).
* WrenAI's FK auto-detection reads `information_schema.constraint_column_usage`, which hides constraints from a non-owner role, so `setup_connections.py` reads PK/FK from `pg_catalog` and sets them through Wren's own GraphQL mutations (`updateModel`, `saveRelations`).
* Telemetry: Wren `TELEMETRY_ENABLED=false`, Cube `CUBEJS_TELEMETRY=false`, Langfuse disabled.
