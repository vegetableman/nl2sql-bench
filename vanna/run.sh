#!/usr/bin/env bash
# Vanna service for the bench (:8095). Secrets come from ../.env (sourced, never printed).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
set -a; . "$HERE/../.env"; set +a
case "${1:-serve}" in
  install) cd "$HERE" && uv venv -q -p 3.12 .venv && uv pip install -q -p .venv/bin/python -r requirements.txt ;;
  ddl)     exec "$HERE/.venv/bin/python" "$HERE/build_ddl.py" ;;
  serve)   exec "$HERE/.venv/bin/python" "$HERE/server.py" ;;
esac
