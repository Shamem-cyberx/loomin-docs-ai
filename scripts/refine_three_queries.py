import json
import urllib.request

BASE = "http://127.0.0.1:8000"


def search(q: str):
    body = json.dumps({"query": q, "top_k": 4}).encode()
    req = urllib.request.Request(
        f"{BASE}/api/rag/search",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    return json.loads(urllib.request.urlopen(req, timeout=60).read().decode())


for q in [
    "Emma cottage enchanted forest where she lives",
    "Sweet Dreams Publishing illustrated title",
    "Emma blue eyes golden curls",
]:
    o = search(q)
    blob = " ".join(c["text"] for c in o["chunks"]).lower()
    print("Q:", q)
    print("  ms:", o["retrieval_time_ms"])
    print("  'blue eyes' in top-4:", "blue eyes" in blob)
    print("  'cottage' and 'forest':", "cottage" in blob and "forest" in blob)
    print("  'sweet dreams' and 'publishing':", "sweet dreams" in blob and "publishing" in blob)
    print()
