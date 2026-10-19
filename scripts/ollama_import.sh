#!/usr/bin/env bash
# Install an Ollama library model into the `ollama` container by downloading the registry
# blobs with curl on the host. Needed on this box: `ollama pull` refuses the CDN redirect
# because the box resolver maps the CDN host to a non-public (198.18.x) address.
set -euo pipefail
MODEL=${1:-nomic-embed-text}; TAG=${2:-latest}
C=$(docker compose ps -q ollama)
W=$(mktemp -d); trap 'rm -rf "$W"' EXIT
curl -sf -H "Accept: application/vnd.docker.distribution.manifest.v2+json" \
  "https://registry.ollama.ai/v2/library/$MODEL/manifests/$TAG" -o "$W/manifest"
docker exec "$C" mkdir -p /root/.ollama/models/blobs "/root/.ollama/models/manifests/registry.ollama.ai/library/$MODEL"
for d in $(python3 -c "import json,sys;m=json.load(open('$W/manifest'));print(' '.join([m['config']['digest']]+[l['digest'] for l in m['layers']]))"); do
  f="$W/${d/:/-}"
  curl -sfL -o "$f" "https://registry.ollama.ai/v2/library/$MODEL/blobs/$d"
  [ "$(sha256sum "$f" | cut -c1-64)" = "${d#sha256:}" ] || { echo "checksum mismatch $d"; exit 1; }
  docker cp "$f" "$C:/root/.ollama/models/blobs/${d/:/-}" >/dev/null
done
docker cp "$W/manifest" "$C:/root/.ollama/models/manifests/registry.ollama.ai/library/$MODEL/$TAG" >/dev/null
docker exec "$C" ollama list | grep -q "^$MODEL" && echo "installed $MODEL:$TAG"
