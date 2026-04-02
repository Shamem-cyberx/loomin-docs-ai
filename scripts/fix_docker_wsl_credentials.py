#!/usr/bin/env python3
"""
Fix: docker compose build fails in WSL with:
  failed to solve: error getting credentials - err: exit status 1, out: ``

Docker Desktop often writes credsStore/credHelpers into ~/.docker/config.json for Windows;
the helper path fails inside WSL when BuildKit pulls public images (python, node, nginx).

Run in WSL (once, or after Docker Desktop resets config):
  python3 scripts/fix_docker_wsl_credentials.py

Then: docker compose build backend frontend collab

If that still fails, do not edit home again — use an isolated config (no helper):
  ./scripts/compose-wsl.sh build backend frontend collab
  # or: export DOCKER_CONFIG="$(pwd)/scripts/wsl-docker-config" && docker compose build ...
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    cfg = Path.home() / ".docker" / "config.json"
    if not cfg.is_file():
        print(f"No file at {cfg} — nothing to change.")
        return 0

    raw = cfg.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON in {cfg}: {e}", file=sys.stderr)
        return 1

    if not isinstance(data, dict):
        print(f"Unexpected config shape in {cfg}", file=sys.stderr)
        return 1

    removed: list[str] = []
    for key in ("credsStore", "credHelpers"):
        if key in data:
            del data[key]
            removed.append(key)

    if not removed:
        print(f"No credsStore or credHelpers in {cfg} — already minimal or different layout.")
        print("If builds still fail: ensure Docker Desktop is running and WSL integration is on.")
        return 0

    backup = cfg.with_suffix(".json.bak-wsl-creds")
    backup.write_text(raw, encoding="utf-8")
    cfg.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"Backed up to {backup}")
    print(f"Removed from config.json: {', '.join(removed)}")
    print("Public image pulls should work without the broken helper.")
    print("Next: docker compose build backend frontend collab && docker compose up -d")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
