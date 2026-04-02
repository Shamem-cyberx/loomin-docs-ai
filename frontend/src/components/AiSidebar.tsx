import { useCallback, useEffect, useRef, useState } from "react";
import {
  chatGeneral,
  chatRag,
  fetchModels,
  formatApiErrorMessage,
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

function citationLine(c: Citation, index: number): string {
  const pretty = c.file.replace(/_/g, " ");
  const short = pretty.length > 34 ? `${pretty.slice(0, 31)}…` : pretty;
  const tail = c.chunk_id.includes(":") ? (c.chunk_id.split(":").pop() ?? c.chunk_id) : c.chunk_id;
  return `${index + 1}. ${short} · #${tail}`;
}

function formatTimingLine(m: Partial<LoominResponse>): string {
  const parts: string[] = [];
  if (m.retrieval_time_ms != null) parts.push(`retrieve ${m.retrieval_time_ms} ms`);
  if (m.llm_latency_ms != null) parts.push(`llm ${m.llm_latency_ms} ms`);
  if (m.generation_speed_tps != null && m.generation_speed_tps > 0) {
    parts.push(`${m.generation_speed_tps.toFixed(1)} tok/s`);
  }
  return parts.join(" · ");
}

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

  const startNewChat = useCallback(() => {
    setSessionId(null);
    localStorage.removeItem("loomin_session");
    setMessages([]);
    setActiveCite(null);
  }, []);

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

  const isStaleSessionError = (err: unknown) => {
    const msg = err instanceof Error ? err.message : String(err);
    return /session not found/i.test(msg);
  };

  const send = async () => {
    const q = input.trim();
    if (!q || busy) return;
    setInput("");
    setBusy(true);
    setMessages((m) => [...m, { role: "user", content: q }]);
    try {
      const postChat = (sid: string) =>
        useRag
          ? chatRag({ message: q, session_id: sid, use_rag: true, model })
          : chatGeneral({ message: q, session_id: sid, model });

      let sid = await ensureSession();
      let res: LoominResponse;
      try {
        res = await postChat(sid);
      } catch (e) {
        // localStorage often keeps a session UUID after DB reset (e.g. docker volume wiped).
        if (!isStaleSessionError(e)) throw e;
        setSessionId(null);
        localStorage.removeItem("loomin_session");
        const fresh = await newChatSession();
        setSessionId(fresh.id);
        localStorage.setItem("loomin_session", fresh.id);
        res = await postChat(fresh.id);
      }
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
        { role: "assistant", content: formatApiErrorMessage(e) || "Request failed" },
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
        <div className={styles.assistantMain}>
          <div className={styles.compactStrip} aria-label="Assistant controls">
            <div className={styles.compactRow1}>
              <button type="button" className={styles.compactNewChat} onClick={startNewChat}>
                New chat
              </button>
              <select
                className={styles.modelSelect}
                value={model}
                onChange={(e) => onModelChange(e.target.value)}
                aria-label="Ollama model"
              >
                {(models.length ? models : ["qwen2.5:0.5b", "tinyllama:latest"]).map((x) => (
                  <option key={x} value={x}>
                    {x}
                  </option>
                ))}
              </select>
              <label className={styles.ragMini}>
                <input
                  type="checkbox"
                  checked={useRag}
                  onChange={(e) => onUseRagChange(e.target.checked)}
                />
                RAG
              </label>
            </div>
            <div className={styles.compactRow2}>
              <div className={styles.meterThin}>
                <div
                  className={styles.meterThinFill}
                  style={{
                    width: `${Math.min(100, contextUsagePercent ?? 0)}%`,
                    background:
                      (contextUsagePercent ?? 0) > 85 ? "var(--danger)" : "var(--accent-dim)",
                  }}
                />
              </div>
              <span className={styles.ctxPct} title="Estimated context window use">
                {contextUsagePercent != null ? `${contextUsagePercent}%` : "—"}
              </span>
            </div>
          </div>
          {useRag && (
            <p className={styles.inlineHint}>
              Answers use <strong>Library</strong> uploads only · add files under the Library tab · tap a source to
              preview text
            </p>
          )}

          <div className={styles.chatSection}>
            <div className={styles.chatSectionHead}>
              <span className={styles.chatSectionTitle}>Conversation</span>
              {messages.length > 0 && (
                <span className={styles.chatSectionMeta}>{messages.length} messages</span>
              )}
            </div>
            <div className={styles.chat}>
              {messages.length === 0 && (
                <p className={styles.emptyChat}>
                  No messages yet. Type a question below — with RAG on, answers cite your uploaded documents.
                </p>
              )}
              {messages.map((msg, i) => {
                const libraryNote = msg.role === "assistant" && msg.content.startsWith("[Library]");
                if (msg.role === "user") {
                  return (
                    <article key={i} className={`${styles.msgCard} ${styles.msgUser}`}>
                      <div className={styles.msgCardHead}>
                        <span className={styles.roleLabel}>You</span>
                      </div>
                      <p className={styles.userText}>{msg.content}</p>
                    </article>
                  );
                }
                if (libraryNote) {
                  return (
                    <article key={i} className={`${styles.msgCard} ${styles.msgAssistant}`}>
                      <div className={styles.msgCardHead}>
                        <span className={styles.roleLabel}>Library</span>
                      </div>
                      <p className={styles.assistantAnswer}>{msg.content.replace(/^\[Library\]\s*/, "")}</p>
                    </article>
                  );
                }
                return (
                  <article key={i} className={`${styles.msgCard} ${styles.msgAssistant}`}>
                    <div className={styles.msgCardHead}>
                      <span className={styles.roleLabel}>Assistant</span>
                    </div>
                    <p className={styles.assistantAnswer}>{msg.content}</p>
                    {msg.citations && msg.citations.length > 0 && (
                      <div className={styles.sourcesSection}>
                        <span className={styles.sourceKicker}>Sources</span>
                        <ul className={styles.citeList}>
                          {msg.citations.map((c, j) => (
                            <li key={j}>
                              <button
                                type="button"
                                className={styles.citeBtn}
                                title={`${c.file} — ${c.chunk_id}`}
                                onClick={() => setActiveCite(c)}
                              >
                                {citationLine(c, j)}
                              </button>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {msg.metrics && (
                      <div className={styles.timingInline}>
                        {formatTimingLine(msg.metrics)}
                        {msg.metrics.request_id ? (
                          <>
                            {" "}
                            · id <code title={msg.metrics.request_id}>{msg.metrics.request_id.slice(0, 8)}</code>
                          </>
                        ) : null}
                      </div>
                    )}
                  </article>
                );
              })}
              <div ref={endRef} />
            </div>
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
            <label className={styles.composeLabel}>
              {useRag ? "Ask your documents" : "Message"}
              <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={useRag ? "e.g. What is the Dream Jar made of?" : "Type a question…"}
              rows={3}
              disabled={busy}
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                  e.preventDefault();
                  void send();
                }
              }}
            />
            </label>
            <button type="button" className={busy ? `${styles.sendBtn} ${styles.sendBusy}` : styles.sendBtn} disabled={busy} onClick={() => void send()}>
              {busy ? `Working… ${busyElapsedS}s` : "Send"}
            </button>
            <p className={styles.composeHint}>Tip: Ctrl+Enter or ⌘+Enter to send</p>
          </div>
        </div>
      )}

      {tab === "library" && (
        <div className={styles.libraryMain}>
          <FilesPanel onToast={onLibraryToast} />
        </div>
      )}

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
