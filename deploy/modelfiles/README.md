# Ollama Modelfiles (evaluation & air-gap)

Build these **on a machine that already has the base weights** (or copy `deploy/ollama` from a host where `ollama pull llama3` succeeded):

```bash
cd deploy/modelfiles
ollama create loomin-rag -f Modelfile.loomin-rag
ollama create loomin-chat -f Modelfile.loomin-chat
```

The UI model dropdown lists tags from `GET /api/models` (Ollama `/api/tags`). After creating, you should see `loomin-rag` and `loomin-chat`.

To use **Mistral** as the base, edit each `FROM` line to `mistral` and rebuild.

The FastAPI service still sends its own system strings for RAG/general routes; these Modelfiles provide **reproducible Ollama-side defaults** for auditors or for callers that bypass API layering.
