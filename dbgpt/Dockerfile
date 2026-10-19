# DB-GPT v0.8.2 official OpenAI-proxy image + Postgres driver (not bundled upstream)
FROM eosphorosai/dbgpt-openai:v0.8.2
RUN (command -v uv >/dev/null && uv pip install --python /opt/.uv.venv/bin/python psycopg2-binary==2.9.10) \
    || /opt/.uv.venv/bin/python -m pip install --no-cache-dir psycopg2-binary==2.9.10
