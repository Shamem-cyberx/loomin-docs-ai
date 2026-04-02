#!/usr/bin/env bash
# Loomin-Docs air-gapped bootstrap (RHEL 9 + Docker).
# Prereqs: Docker Engine + Compose plugin (or docker-compose) from local RPMs;
# optional: docker load tarballs from deploy/images/

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

log() { printf '%s\n' "$*"; }

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    log "ERROR: '$1' not found in PATH"
    exit 1
  fi
}

require_cmd docker

COMPOSE=(docker compose)
if ! docker compose version >/dev/null 2>&1; then
  if command -v docker-compose >/dev/null 2>&1; then
    COMPOSE=(docker-compose)
  else
    log "ERROR: Neither 'docker compose' nor 'docker-compose' is available"
    exit 1
  fi
fi

if [ ! -d "${ROOT}/deploy/ollama" ]; then
  log "Creating deploy/ollama (Ollama home). Seed from a networked host, e.g.:"
  log "  rsync -a ~/.ollama/ ${ROOT}/deploy/ollama/"
  mkdir -p "${ROOT}/deploy/ollama"
fi

shopt -s nullglob
for tar in "${ROOT}/deploy/images/"*.tar; do
  log "Loading image from ${tar}"
  docker load -i "${tar}"
done
shopt -u nullglob

log "Starting stack…"
# Air-gap: enable bundled Ollama. Host Ollama: USE_HOST_OLLAMA=1 ./setup.sh
if [ "${USE_HOST_OLLAMA:-0}" != "1" ]; then
  export COMPOSE_PROFILES="${COMPOSE_PROFILES:-bundle}"
fi
"${COMPOSE[@]}" up -d

log ""
log "Loomin-Docs is up."
log "  • UI:            http://localhost/"
log "  • API:           http://localhost:8000/"
log "  • Collaboration: ws://localhost:1234  (Hocuspocus; ensure port open in firewall)"
log "  • Ollama:        http://localhost:11434/"
log ""
log "Offline Docker RPM install (optional): sudo RPM_DIR=./deploy/rpms ./deploy/bootstrap/install-docker-rhel9-offline.sh"
log "No pip/npm/model downloads occur at runtime; only what you baked into images and deploy/ollama."
