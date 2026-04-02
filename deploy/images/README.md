# Air-gap image tarballs

Place **`docker save` outputs** here so `setup.sh` can `docker load` them on an offline RHEL 9 host before `docker compose up`.

**Easiest:** on a machine with Docker and network access, from the **repository root**:

```bash
chmod +x scripts/export_airgap_images.sh
./scripts/export_airgap_images.sh
```

Expected files (names are conventional; any `*.tar` in this directory is loaded):

| File | Image |
|------|--------|
| `loomin-docs-backend.tar` | `loomin-docs-backend:latest` |
| `loomin-docs-frontend.tar` | `loomin-docs-frontend:latest` |
| `loomin-docs-collab.tar` | `loomin-docs-collab:latest` |
| `ollama-ollama.tar` | `ollama/ollama:latest` |

If you rename tarballs, the image tags inside are unchanged — `docker load` restores the same tags Compose expects.
