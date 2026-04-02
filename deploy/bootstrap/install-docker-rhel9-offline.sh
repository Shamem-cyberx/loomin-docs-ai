#!/usr/bin/env bash
# Offline Docker Engine + Compose plugin on RHEL 9 using LOCAL RPMs only.
# 1) Copy RPMs from your vendor mirror into RPM_DIR (same major/minor as target host).
# 2) Run: sudo RPM_DIR=/path/to/rpms ./install-docker-rhel9-offline.sh

set -euo pipefail

RPM_DIR="${RPM_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../rpms" 2>/dev/null && pwd)}"

if [[ "${EUID:-}" -ne 0 ]]; then
  echo "Run as root (sudo)." >&2
  exit 1
fi

if [[ ! -d "${RPM_DIR}" ]]; then
  echo "RPM_DIR not found: ${RPM_DIR}" >&2
  echo "Create it and populate with docker-ce, containerd, docker-compose-plugin RPMs." >&2
  exit 1
fi

echo "Installing Docker stack from ${RPM_DIR} (no remote repos)â€¦"
dnf install -y --disablerepo='*' "${RPM_DIR}"/*.rpm

systemctl enable --now docker

if docker compose version >/dev/null 2>&1; then
  docker compose version
else
  echo "Warning: docker compose plugin not found in PATH after install." >&2
fi

echo "Done. Verify: docker run --rm hello-world (only if hello-world image is also sideloaded)."
