# syntax=docker/dockerfile:1
# Build on a networked workstation; deploy image tarballs air-gapped on RHEL 9.
FROM python:3.11-slim-bookworm

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip \
    && pip install --index-url https://download.pytorch.org/whl/cpu torch==2.2.2 \
    && pip install -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1
ENV DATA_DIR=/data
ENV OLLAMA_BASE_URL=http://ollama:11434

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
