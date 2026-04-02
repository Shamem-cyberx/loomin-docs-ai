# Air-gap bootstrap bundle manifest

Ship a single archive (e.g. `loomin-docs-bootstrap.tar.zst`) containing:

| Path | Purpose |
|------|---------|
| `loomin-docs/` | Full Git tree or release snapshot (`frontend/`, `backend/`, `collab/`, `deploy/`, …) |
| `rpms/` | RHEL 9 RPMs for container stack: `containerd`, `docker-ce`, `docker-ce-cli`, `docker-compose-plugin` (exact set pinned to your org mirror) |
| `images/` | `docker save` outputs under `deploy/images/` — run **`scripts/export_airgap_images.sh`** on a builder host, or save the four images listed in `deploy/images/README.md` |
| `ollama-bundle/` | Copy of `~/.ollama` after `ollama pull` on a builder (rename to match `deploy/ollama` in compose) |

On the **evaluation host**:

1. Install RPMs with `dnf install --disablerepo='*' ./rpms/*.rpm` (or your internal repo).
2. `cd loomin-docs && chmod +x setup.sh deploy/bootstrap/install-docker-rhel9-offline.sh` (Docker install script is optional if RPMs already applied).
3. Copy `ollama-bundle/*` into `deploy/ollama/`.
4. Run `./setup.sh` to `docker load` all `deploy/images/*.tar` and `docker compose up -d`.

No runtime `pip`, `npm`, or model downloads occur once images and `deploy/ollama` are populated.
