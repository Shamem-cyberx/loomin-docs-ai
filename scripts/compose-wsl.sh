#!/usr/bin/env bash
# WSL + repo on /mnt/e (Windows drive):
#   1) DOCKER_CONFIG cannot live on drvfs - Buildx chmod on .../buildx/activity fails.
#   2) ~/.docker often has a broken credsStore - use a minimal config without it.
#
# Run (no chmod needed):
#   bash scripts/compose-wsl.sh build backend frontend collab
#   bash scripts/compose-wsl.sh up -d
#
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOCKER_CFG_DIR="${HOME}/.docker-loomin-wsl"
mkdir -p "$DOCKER_CFG_DIR"
REPO_CFG="${ROOT}/scripts/wsl-docker-config/config.json"
if [[ -f "$REPO_CFG" ]]; then
  cp -f "$REPO_CFG" "${DOCKER_CFG_DIR}/config.json"
else
  printf '%s\n' '{"auths":{}}' >"${DOCKER_CFG_DIR}/config.json"
fi
export DOCKER_CONFIG="$DOCKER_CFG_DIR"
cd "$ROOT"
exec docker compose "$@"
