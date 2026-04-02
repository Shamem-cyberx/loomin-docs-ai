# Ollama offline bundle

Populate this directory with a full Ollama data directory from a **networked** build machine where you have already executed, for example:

```bash
ollama pull llama3
ollama pull mistral
```

Then archive the host directory:

```bash
rsync -a ~/.ollama/ ./deploy/ollama/
```

`docker-compose.yml` mounts `./deploy/ollama` to `/root/.ollama` inside the `ollama` service so **no model downloads occur at runtime** on the air-gapped host.
