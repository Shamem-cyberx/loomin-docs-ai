export type Citation = { file: string; chunk_id: string; text: string };

export type LoominResponse = {
  answer: string;
  citations: Citation[];
  request_id: string;
  retrieval_time_ms: number;
  generation_speed_tps: number;
  llm_latency_ms?: number | null;
  context_usage_percent?: number | null;
  session_id?: string | null;
};

const jsonHeaders = { "Content-Type": "application/json" };

/** Turn fetch error bodies like {"detail":"..."} into readable text for the UI. */
export function formatApiErrorMessage(err: unknown): string {
  if (!(err instanceof Error)) return String(err);
  const m = err.message.trim();
  if (m.startsWith("{") && m.includes("detail")) {
    try {
      const j = JSON.parse(m) as { detail?: unknown };
      if (typeof j.detail === "string") return j.detail;
      if (Array.isArray(j.detail) && j.detail.length && typeof j.detail[0] === "object") {
        const parts = (j.detail as { msg?: string }[]).map((x) => x.msg).filter(Boolean);
        if (parts.length) return parts.join("; ");
      }
    } catch {
      /* fall through */
    }
  }
  return m;
}

export async function healthCheck(): Promise<boolean> {
  try {
    const r = await fetch("/health", { method: "GET" });
    if (!r.ok) return false;
    const j = await r.json();
    return j?.status === "ok";
  } catch {
    return false;
  }
}

export async function fetchModels(): Promise<{ models: string[]; default: string }> {
  const r = await fetch("/api/models");
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function chatRag(body: {
  message: string;
  session_id?: string | null;
  use_rag: boolean;
  model?: string | null;
}): Promise<LoominResponse> {
  const r = await fetch("/api/chat", {
    method: "POST",
    headers: jsonHeaders,
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function chatGeneral(body: {
  message: string;
  session_id?: string | null;
  model?: string | null;
}): Promise<LoominResponse> {
  const r = await fetch("/api/chat/general", {
    method: "POST",
    headers: jsonHeaders,
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function editSelection(body: {
  selection: string;
  action: "summarize" | "improve";
  model?: string | null;
  document_html?: string | null;
}): Promise<LoominResponse> {
  const r = await fetch("/api/edit/selection", {
    method: "POST",
    headers: jsonHeaders,
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function getDefaultDoc(): Promise<{
  id: string;
  title: string;
  editor_html: string;
}> {
  const r = await fetch("/api/documents/default");
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function saveDocument(editor_html: string, title?: string): Promise<void> {
  const r = await fetch("/api/documents/default", {
    method: "PUT",
    headers: jsonHeaders,
    body: JSON.stringify({ editor_html, title }),
  });
  if (!r.ok) throw new Error(await r.text());
}

export type UploadFileResponse = {
  ingest_status: string;
  chunk_count?: number | null;
  id?: string;
  filename?: string;
  deduplicated?: boolean;
  existing_file_id?: string;
  message?: string;
};

export async function uploadFile(file: File): Promise<UploadFileResponse> {
  const fd = new FormData();
  fd.append("upload", file);
  const r = await fetch("/api/files/upload", { method: "POST", body: fd });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function newChatSession(): Promise<{ id: string }> {
  const r = await fetch("/api/chat/sessions", { method: "POST" });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export type UploadedFileRow = {
  id: string;
  filename: string;
  ingest_status: string;
  chunk_count: number | null;
  created_at: string | null;
};

export async function listFiles(): Promise<UploadedFileRow[]> {
  const r = await fetch("/api/files");
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function deleteFile(id: string): Promise<void> {
  const r = await fetch(`/api/files/${encodeURIComponent(id)}`, { method: "DELETE" });
  if (!r.ok) throw new Error(await r.text());
}

export async function reingestFile(
  id: string,
): Promise<Pick<UploadedFileRow, "id" | "filename" | "ingest_status" | "chunk_count">> {
  const r = await fetch(`/api/files/${encodeURIComponent(id)}/reingest`, { method: "POST" });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}
