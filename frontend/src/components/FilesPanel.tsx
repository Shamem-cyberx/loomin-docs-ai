import { useCallback, useEffect, useState } from "react";
import { deleteFile, listFiles, reingestFile, uploadFile, type UploadedFileRow } from "../api";
import styles from "./files.module.css";

type Props = {
  onToast?: (message: string, variant?: "ok" | "err") => void;
};

export function FilesPanel({ onToast }: Props) {
  const [rows, setRows] = useState<UploadedFileRow[]>([]);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const r = await listFiles();
      setRows(r);
    } catch (e) {
      onToast?.(e instanceof Error ? e.message : "List failed", "err");
    } finally {
      setLoading(false);
    }
  }, [onToast]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const onUpload = async (f: File | null) => {
    if (!f) return;
    setBusyId("__up__");
    try {
      const r = await uploadFile(f);
      onToast?.(
        r.deduplicated
          ? r.message ?? `Same file already indexed (${r.chunk_count ?? 0} chunks).`
          : `${f.name}: ${r.ingest_status}${r.chunk_count != null ? ` (${r.chunk_count} chunks)` : ""}`,
        "ok",
      );
      await refresh();
    } catch (e) {
      onToast?.(e instanceof Error ? e.message : "Upload failed", "err");
    } finally {
      setBusyId(null);
    }
  };

  const onDelete = async (id: string) => {
    if (!window.confirm("Remove this file from the library and vector index?")) return;
    setBusyId(id);
    try {
      await deleteFile(id);
      onToast?.("File removed from index and disk.", "ok");
      await refresh();
    } catch (e) {
      onToast?.(e instanceof Error ? e.message : "Delete failed", "err");
    } finally {
      setBusyId(null);
    }
  };

  const onReingest = async (id: string) => {
    setBusyId(id);
    try {
      const r = await reingestFile(id);
      onToast?.(`Re-ingested ${r.filename}: ${r.ingest_status}`, "ok");
      await refresh();
    } catch (e) {
      onToast?.(e instanceof Error ? e.message : "Re-ingest failed", "err");
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className={styles.panel}>
      <p className={styles.hint}>
        PDF, Markdown, and plain text are chunked, embedded, and searchable by the assistant (RAG).
      </p>
      <label className={styles.upload}>
        Upload to library
        <input
          type="file"
          accept=".pdf,.txt,.md,.markdown"
          disabled={busyId === "__up__"}
          onChange={(e) => void onUpload(e.target.files?.[0] ?? null)}
        />
      </label>

      {loading ? (
        <p className={styles.muted}>Loading…</p>
      ) : rows.length === 0 ? (
        <p className={styles.muted}>No files yet. Upload a document to build the index.</p>
      ) : (
        <ul className={styles.list}>
          {rows.map((r) => (
            <li key={r.id} className={styles.row}>
              <div className={styles.meta}>
                <span className={styles.fname}>{r.filename}</span>
                <span className={styles.status}>{r.ingest_status}</span>
                {r.chunk_count != null && (
                  <span className={styles.chunks}>{r.chunk_count} chunks</span>
                )}
              </div>
              <div className={styles.actions}>
                <button
                  type="button"
                  disabled={busyId === r.id}
                  onClick={() => void onReingest(r.id)}
                >
                  Re-ingest
                </button>
                <button
                  type="button"
                  className={styles.danger}
                  disabled={busyId === r.id}
                  onClick={() => void onDelete(r.id)}
                >
                  Remove
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
