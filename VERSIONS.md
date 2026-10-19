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
| Postgres | 16.4 | postgres@sha256:e62fbf9d3e2b49816a32c400ed2dba83e3b361e6833e624024309c35d334b412 |
| Chinook dataset | v1.4.5 (`Chinook_PostgreSql.sql`) | sha256 e3fde5c1a5b51a2a91429a702c9ca6e69ba56e6c7f5e112724d70c3d03db695e |
| llm-meter (local) | 1.0 (+ timing-only `GET /meter/events`, added before the `wrenai_mdl_noreason` run) | python:3.12-slim + starlette 0.41.3, uvicorn 0.32.1, httpx 0.28.1 |
| Harness | Python 3.12 venv | psycopg 3.2.3, PyYAML 6.0.2, httpx 0.28.1, python-dotenv 1.0.1, matplotlib 3.9.2 |
| Ollama (local, embeddings only) | 0.40.6 | ollama/ollama@sha256:265409e1d931028a8f7d5a32bcbafddd7bffbc6cc629d77efe9560adf692a5e7 |
| Embedding model | nomic-embed-text:latest (768-d) | registry.ollama.ai manifest; model blob sha256:970aa74c0a90ef7482477cf803618e776e173c007bf957f635f1015bfcfef0e6 |
| Chat LLM | gpt-oss:120b on Ollama Cloud (`https://ollama.com/v1`, OpenAI-compatible, Bearer `OLLAMA_API_KEY`) | hosted; version not pinnable by us |
| Docker | 26.1.5 (Debian docker.io), Compose 2.26.1 | |
