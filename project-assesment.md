we have designed a rigorous, production-grade assignment that focuses on building a sophisticated, AI-enhanced document editor designed for strictly air-gapped, RHEL 9 environments.
The time expectation is 8–10 hours, and you will have 24 hours from the time you receive this email to submit your repository.
Project Goal: "Loomin-Docs"
Build a real-time Collaborative Text Editor (React) with an integrated AI Assistant Sidebar (Python) that performs RAG, summarization, and document manipulation using a local LLM via Ollama. The final system must be entirely self-contained; the evaluation VM is a clean RHEL 9 instance with no internet access.
1. Frontend: The Professional Editor (React + TypeScript)
Deliver a high-fidelity workspace with:
Rich Text Editor: A central editor  capable of handling Markdown and complex formatting.
AI Side-Panel: A persistent chat interface that can:
Contextual Editing: Select text in the editor and click "Summarize" or "Improve" in the sidebar to update the document.
Model Selector: A dropdown to toggle between different local model profiles (e.g., Llama3 vs Mistral) via Ollama API.
Asset Management: A "Files" tab to upload and manage the local .pdf, .md, and .txt files used for the RAG context.
Token Visualization: A real-time UI indicator showing the percentage of the model's context window consumed by the active document and retrieved snippets.
2. Backend: The Air-Gapped Engine (Python + FastAPI)
Multi-Model RAG Pipeline:
Vector Indexing: Implement FAISS with a local embedding model (e.g., all-MiniLM-L6-v2) to index uploaded files.
Dynamic Context Injection: The assistant must be able to "talk to the files" by retrieving relevant chunks and grounding every response with clickable citations.
State Management: Use a local SQLite database to persist document versions and chat history.
Ollama Integration: The backend must interface with a local Ollama instance. Provide the specific Modelfile used for any custom system prompting.
3. The "Zero-Network" & Docker Challenge (Critical)
The evaluation VM is a blank RHEL 9 machine. You must provide a bootstrap package that includes:
Docker Installation: Provide the necessary RPM packages and a setup.sh script to install the Docker engine and docker-compose on RHEL 9 without an internet connection.
Containerized Environment: A docker-compose.yml that orchestrates the Frontend, Backend, and Ollama.
Image Sideloading: Provide the logic (or pre-saved .tar images) to load the required Docker images onto the target VM.
Model Weights: A strategy to side-load the Ollama model weights (GGUF/Blob) into the containerized volume without an external pull.
4. Security & Observability
PII Sanitization: A local interceptor to catch and mask sensitive patterns (IDs, Keys) before they hit the LLM.
Latency Tracing: Every AI response must return JSON metadata including request_id, Retrieval Time, and Token Generation Speed.
Deliverables
Git Repository: Structured into /frontend, /backend, and /deploy.
The Bootstrap Package: A compressed archive containing the setup.sh, RHEL 9 Docker RPMs, exported Docker image .tar files, and model weights.
Documentation:
README: Step-by-step instructions for the setup.sh on a clean RHEL 9 VM.
Architecture Diagram: A Mermaid/PNG flow showing the communication between the Editor, Backend, and the local Inference Engine.
Verification Test: A Python script that verifies the RAG pipeline's "Faithfulness" (ensuring the model does not hallucinate info not found in the local files).
Please confirm receipt of this email. We are excited to see how you tackle the complexities of air-gapped AI deployment on enterprise Linux.