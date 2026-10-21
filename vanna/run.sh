#!/usr/bin/env bash
# Vanna service for the bench (:8095). Secrets come from ../.env (sourced, never printed).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
set -a; . "$HERE/../.env"; set +a
# VANNA_VARIANT: (unset) plain vanna :8095 /vanna/ | jev = vanna_jev :8096 /vannaj/ | jevretry = vanna_jev_retry :8097 /vannajr/.
# Jev variants use their own Chroma store, a byte copy of the trained plain-Vanna store (identical retrieval).
case "${VANNA_VARIANT:-}" in
  jev)      export VANNA_PORT=8096 VANNA_METER_PREFIX=vannaj  VANNA_JEV=on    VANNA_STORE="$HERE/state/chroma-jev" ;;
  jevretry) export VANNA_PORT=8097 VANNA_METER_PREFIX=vannajr VANNA_JEV=retry VANNA_STORE="$HERE/state/chroma-jevretry" ;;
  "") ;;
  *) echo "unknown VANNA_VARIANT=$VANNA_VARIANT" >&2; exit 2 ;;
esac
if [ -n "${VANNA_STORE:-}" ] && [ ! -d "$VANNA_STORE" ]; then
  test -d "$HERE/state/chroma" || { echo "train plain vanna first (make vanna-up)" >&2; exit 2; }
  cp -a "$HERE/state/chroma" "$VANNA_STORE"
fi
case "${1:-serve}" in
  install) cd "$HERE" && uv venv -q -p 3.12 .venv && uv pip install -q -p .venv/bin/python -r requirements.txt ;;
  ddl)     exec "$HERE/.venv/bin/python" "$HERE/build_ddl.py" ;;
  serve)   exec "$HERE/.venv/bin/python" "$HERE/server.py" ;;
esac
