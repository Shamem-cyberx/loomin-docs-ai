#!/usr/bin/env bash
# Build app images and docker save them into deploy/images/ for air-gapped RHEL 9 transfer.
# Run on a networked machine with Docker (Linux, WSL2, or macOS). Requires internet to pull
# base layers and ollama/ollama:latest unless those images are already local.
#
# Usage (from repo root):
#   chmod +x scripts/export_airgap_images.sh
#   ./scripts/export_airgap_images.sh
#
# Then copy the whole repo (including deploy/images/*.tar and deploy/ollama/) to the offline host.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

OUT="${ROOT}/deploy/images"
mkdir -p "$OUT"

COMPOSE=(docker compose)
if ! docker compose version >/dev/null 2>&1; then
  if command -v docker-compose >/dev/null 2>&1; then
    COMPOSE=(docker-compose)
  else
    echo "ERROR: Need 'docker compose' or 'docker-compose'" >&2
    exit 1
  fi
fi

echo "==> Building backend, frontend, collab (this pulls base images if missing)..."
DOCKER_BUILDKIT=1 "${COMPOSE[@]}" build --parallel backend frontend collab

echo "==> Ensuring Ollama engine image is present (for bundle profile)..."
docker image inspect ollama/ollama:latest >/dev/null 2>&1 || docker pull ollama/ollama:latest

echo "==> Saving images to ${OUT}/"
docker save -o "${OUT}/loomin-docs-backend.tar" loomin-docs-backend:latest
docker save -o "${OUT}/loomin-docs-frontend.tar" loomin-docs-frontend:latest
docker save -o "${OUT}/loomin-docs-collab.tar" loomin-docs-collab:latest
docker save -o "${OUT}/ollama-ollama.tar" ollama/ollama:latest

echo ""
echo "Done. Tarballs:"
ls -lh "${OUT}/"/*.tar
echo ""
echo "Next: seed deploy/ollama/ (rsync ~/.ollama after ollama pull), add deploy/rpms/*.rpm,"
echo "then archive the repo or USB-copy to the air-gapped RHEL 9 host and run ./setup.sh"
