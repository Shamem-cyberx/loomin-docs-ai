import { useCallback, useEffect, useRef, useState } from "react";
import {
  chatGeneral,
  chatRag,
  fetchModels,
  newChatSession,
  type Citation,
  type LoominResponse,
} from "../api";
import { FilesPanel } from "./FilesPanel";
import styles from "./sidebar.module.css";

export type ChatTurn = {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  metrics?: Partial<LoominResponse>;
};

type Tab = "assistant" | "library";

type Props = {
  model: string;
  onModelChange: (m: string) => void;
  useRag: boolean;
  onUseRagChange: (v: boolean) => void;
  contextUsagePercent: number | null;
  onServerContextPercent?: (pct: number | null) => void;
};

export function AiSidebar({
  model,
  onModelChange,
  useRag,
  onUseRagChange,
  contextUsagePercent,
  onServerContextPercent,
}: Props) {
  const [tab, setTab] = useState<Tab>("assistant");
  const [models, setModels] = useState<string[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(() => localStorage.getItem("loomin_session"));
  const [messages, setMessages] = useState<ChatTurn[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [activeCite, setActiveCite] = useState<Citation | null>(null);
  const [toast, setToast] = useState<{ text: string; variant: "ok" | "err" } | null>(null);
  const [busyElapsedS, setBusyElapsedS] = useState(0);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchModels()
      .then((r) => {
        const names = r.models.length ? r.models : ["qwen2.5:0.5b", "tinyllama:latest"];
        setModels(names);
      })
      .catch(() => setModels(["qwen2.5:0.5b", "tinyllama:latest"]));
  }, []);

  useEffect(() => {
    if (models.length > 0 && !models.includes(model)) {
      onModelChange(models[0]);
    }
  }, [models, model, onModelChange]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (!toast) return;
    const t = window.setTimeout(() => setToast(null), 4500);
    return () => window.clearTimeout(t);
  }, [toast]);

  useEffect(() => {
    if (!busy) {
      setBusyElapsedS(0);
      return;
    }
    const t0 = Date.now();
    const id = window.setInterval(() => setBusyElapsedS(Math.floor((Date.now() - t0) / 1000)), 300);
    return () => window.clearInterval(id);
  }, [busy]);

  const ensureSession = useCallback(async () => {
    if (sessionId) return sessionId;
    const s = await newChatSession();
    setSessionId(s.id);
    localStorage.setItem("loomin_session", s.id);
    return s.id;
  }, [sessionId]);

  const onLibraryToast = useCallback((message: string, variant: "ok" | "err" = "ok") => {
    let m = message.trim();
    if (/413|entity too large/i.test(m) || m.includes("<html")) {
      m =
        "Upload was rejected (file too large for proxy or server). Use a smaller PDF or ensure nginx client_max_body_size is raised and the frontend image was rebuilt.";
    } else if (m.length > 420) {
      m = `${m.slice(0, 420)}…`;
    }
    setToast({ text: m, variant });
    setMessages((prev) => [...prev, { role: "assistant", content: `[Library] ${m}` }]);
  }, []);

  const send = async () => {
    const q = input.trim();
    if (!q || busy) return;
    setInput("");
    setBusy(true);
    setMessages((m) => [...m, { role: "user", content: q }]);
    try {
      const sid = await ensureSession();
      const res = useRag
        ? await chatRag({ message: q, session_id: sid, use_rag: true, model })
        : await chatGeneral({ message: q, session_id: sid, model });
      if (res.session_id) {
        setSessionId(res.session_id);
        localStorage.setItem("loomin_session", res.session_id);
      }
      onServerContextPercent?.(res.context_usage_percent ?? null);
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          content: res.answer,
          citations: res.citations,
          metrics: res,
        },
      ]);
    } catch (e) {
      setMessages((m) => [
        ...m,
        { role: "assistant", content: e instanceof Error ? e.message : "Request failed" },
      ]);
    } finally {
      setBusy(false);
    }
  };

  return (
    <aside className={styles.aside}>
      <header className={styles.head}>
        <div className={styles.brandRow}>
          <h1 className={styles.brand}>Loomin-Docs</h1>
          <span className={styles.badge}>local</span>
        </div>
        <p className={styles.sub}>Offline editor, RAG library, and live collaboration</p>
      </header>

      <nav className={styles.tabs} aria-label="Sidebar sections">
        <button
          type="button"
          className={tab === "assistant" ? styles.tabActive : styles.tab}
          onClick={() => setTab("assistant")}
        >
          Assistant
        </button>
        <button
          type="button"
          className={tab === "library" ? styles.tabActive : styles.tab}
          onClick={() => setTab("library")}
        >
          Library
        </button>
      </nav>

      {toast && (
        <div className={toast.variant === "err" ? styles.toastErr : styles.toastOk} role="status">
          {toast.text}
        </div>
      )}

      {tab === "assistant" && (
        <>
          <section className={styles.controls}>
            <label className={styles.label}>
              Model
              <select value={model} onChange={(e) => onModelChange(e.target.value)}>
                {(models.length ? models : ["qwen2.5:0.5b", "tinyllama:latest"]).map((x) => (
                  <option key={x} value={x}>
                    {x}
                  </option>
                ))}
              </select>
            </label>
            <label className={styles.toggle}>
              <input
                type="checkbox"
                checked={useRag}
                onChange={(e) => onUseRagChange(e.target.checked)}
              />
              <span>Document-aware (RAG)</span>
            </label>
          </section>

          {useRag && (
            <div className={styles.ragHint}>
              Answers should follow retrieved snippets; use citations to verify. Empty library → upload in
              Library first.
            </div>
          )}

          <div className={styles.meter}>
            <div className={styles.meterLabel}>
              <span>Context window (estimate)</span>
              <span>{contextUsagePercent != null ? `${contextUsagePercent}%` : "—"}</span>
            </div>
            <div className={styles.meterTrack}>
              <div
                className={styles.meterFill}
                style={{
                  width: `${Math.min(100, contextUsagePercent ?? 0)}%`,
                  background:
                    (contextUsagePercent ?? 0) > 85 ? "var(--danger)" : "var(--accent-dim)",
                }}
              />
            </div>
          </div>

          <div className={styles.chat}>
            {messages.map((msg, i) => (
              <div key={i} className={msg.role === "user" ? styles.user : styles.bot}>
                <div className={styles.role}>{msg.role === "user" ? "You" : "Assistant"}</div>
                <div className={styles.bubbleText}>{msg.content}</div>
                {msg.citations && msg.citations.length > 0 && (
                  <ul className={styles.cites}>
                    {msg.citations.map((c, j) => (
                      <li key={j}>
                        <button
                          type="button"
                          className="cite-link"
                          style={{
                            background: "none",
                            border: "none",
                            padding: 0,
                            textAlign: "left",
                            font: "inherit",
                          }}
                          onClick={() => setActiveCite(c)}
                        >
                          {c.file} · {c.chunk_id}
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
                {msg.metrics && (
                  <div className={styles.meta}>
                    {msg.metrics.retrieval_time_ms != null
                      ? `retrieve ${msg.metrics.retrieval_time_ms} ms · `
                      : ""}
                    {msg.metrics.llm_latency_ms != null ? `llm ${msg.metrics.llm_latency_ms} ms · ` : ""}
                    {msg.metrics.generation_speed_tps != null && msg.metrics.generation_speed_tps > 0
                      ? `${msg.metrics.generation_speed_tps.toFixed(1)} tok/s · `
                      : ""}
                    <span title={msg.metrics.request_id}>id {msg.metrics.request_id?.slice(0, 8)}</span>
                  </div>
                )}
              </div>
            ))}
            <div ref={endRef} />
          </div>

          <div className={styles.compose}>
            {busy && (
              <div className={styles.busyStrip} role="status" aria-live="polite">
                <span className={styles.busyDots} aria-hidden />
                <span className={styles.busyText}>
                  {useRag ? "Retrieving context and generating" : "Generating"}
                  … {busyElapsedS}s
                </span>
                <span className={styles.busySub}>
                  {useRag
                    ? "First RAG call may load embeddings; LLM first load can take 1–3 min on CPU."
                    : "First answer after container start may take 1–3 min while the model loads."}
                </span>
              </div>
            )}
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={useRag ? "Ask about your library (RAG)…" : "General question…"}
              rows={3}
              disabled={busy}
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                  e.preventDefault();
                  void send();
                }
              }}
            />
            <button type="button" className={busy ? `${styles.sendBtn} ${styles.sendBusy}` : styles.sendBtn} disabled={busy} onClick={() => void send()}>
              {busy ? `Working… ${busyElapsedS}s` : "Send"}
            </button>
            <p className={styles.composeHint}>Tip: Ctrl+Enter or ⌘+Enter to send</p>
          </div>
        </>
      )}

      {tab === "library" && <FilesPanel onToast={onLibraryToast} />}

      {activeCite && (
        <div className={styles.citeModal} role="dialog">
          <div className={styles.citeModalInner}>
            <header>
              <strong>{activeCite.file}</strong>
              <span className={styles.muted}> {activeCite.chunk_id}</span>
            </header>
            <pre className={styles.citePre}>{activeCite.text}</pre>
            <button type="button" onClick={() => setActiveCite(null)}>
              Close
            </button>
          </div>
        </div>
      )}
    </aside>
  );
}
