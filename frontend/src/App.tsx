import TurndownService from "turndown";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { getDefaultDoc, healthCheck, saveDocument } from "./api";
import { AiSidebar } from "./components/AiSidebar";
import { TiptapEditor } from "./components/TiptapEditor";
import styles from "./app.module.css";

export default function App() {
  const [docHtml, setDocHtml] = useState<string | null>(null);
  const [title, setTitle] = useState("Untitled");
  const [model, setModel] = useState("qwen2.5:0.5b");
  const [useRag, setUseRag] = useState(true);
  const [status, setStatus] = useState<string | null>(null);
  const [statusTone, setStatusTone] = useState<"err" | "ok">("err");
  const [apiOk, setApiOk] = useState<boolean | null>(null);
  const [ctxUsage, setCtxUsage] = useState<number | null>(null);
  const [serverCtx, setServerCtx] = useState<number | null>(null);
  const lastHtml = useRef("");
  const mergedCtx =
    ctxUsage != null || serverCtx != null
      ? Math.min(100, Math.max(ctxUsage ?? 0, serverCtx ?? 0))
      : null;

  const setNotice = useCallback((msg: string | null, tone: "err" | "ok" = "err") => {
    setStatusTone(tone);
    setStatus(msg);
  }, []);

  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      const ok = await healthCheck();
      if (!cancelled) setApiOk(ok);
    };
    void run();
    const id = window.setInterval(run, 30_000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, []);

  useEffect(() => {
    getDefaultDoc()
      .then((d) => {
        setDocHtml(d.editor_html || "<p></p>");
        setTitle(d.title || "Untitled");
        lastHtml.current = d.editor_html || "<p></p>";
      })
      .catch((e) => {
        setStatusTone("err");
        setStatus(e instanceof Error ? e.message : "Failed to load doc");
        setDocHtml("<p></p>");
      });
  }, []);

  const debouncedSave = useMemo(() => {
    let t: ReturnType<typeof setTimeout> | undefined;
    return (html: string, docTitle: string) => {
      if (t) clearTimeout(t);
      t = setTimeout(() => {
        void saveDocument(html, docTitle).catch((e) =>
          setNotice(e instanceof Error ? e.message : "Save failed", "err"),
        );
      }, 1500);
    };
  }, [setNotice]);

  const onHtmlChange = useCallback(
    (html: string) => {
      lastHtml.current = html;
      debouncedSave(html, title);
      const est = Math.min(100, Math.round((html.length / 4 / 8192) * 10000) / 100);
      setCtxUsage(est);
    },
    [debouncedSave, title],
  );

  if (docHtml === null) {
    return (
      <div className={styles.boot}>
        <div className={styles.bootSpinner} aria-hidden />
        Loading workspace…
      </div>
    );
  }

  return (
    <div className={styles.layout}>
      <main className={styles.main}>
        <div className={styles.systemStrip}>
          <span className={styles.pill}>
            <span className={`${styles.dot} ${apiOk ? styles.dotOk : apiOk === false ? styles.dotErr : ""}`} />
            <strong>API</strong>
            {apiOk === null ? " checking…" : apiOk ? " reachable" : " unreachable"}
          </span>
          <span>
            Docs save automatically · RAG uses Library files only · Pick a model Ollama actually has
            installed
          </span>
        </div>

        <header className={styles.toolbar}>
          <button
            type="button"
            className={styles.secondary}
            onClick={() => {
              const td = new TurndownService({ headingStyle: "atx" });
              const md = td.turndown(lastHtml.current);
              void navigator.clipboard.writeText(md);
              setNotice("Markdown copied to clipboard", "ok");
              window.setTimeout(() => setNotice(null, "ok"), 2200);
            }}
          >
            Copy as Markdown
          </button>
          <input
            className={styles.titleInput}
            value={title}
            onChange={(e) => {
              const v = e.target.value;
              setTitle(v);
              debouncedSave(lastHtml.current, v);
            }}
            aria-label="Document title"
            placeholder="Document title"
          />
          {status &&
            (statusTone === "ok" ? (
              <span className={styles.statusOk}>{status}</span>
            ) : (
              <span className={styles.status}>{status}</span>
            ))}
        </header>
        <TiptapEditor
          key="loomin-workspace-editor"
          initialHtml={docHtml}
          onHtmlChange={onHtmlChange}
          model={model}
          onStatus={(msg) => (msg ? setNotice(msg, "err") : setNotice(null, "ok"))}
        />
      </main>
      <AiSidebar
        model={model}
        onModelChange={setModel}
        useRag={useRag}
        onUseRagChange={setUseRag}
        contextUsagePercent={mergedCtx}
        onServerContextPercent={setServerCtx}
      />
    </div>
  );
}
