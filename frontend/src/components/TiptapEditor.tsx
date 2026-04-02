import Collaboration from "@tiptap/extension-collaboration";
import CollaborationCursor from "@tiptap/extension-collaboration-cursor";
import Link from "@tiptap/extension-link";
import Placeholder from "@tiptap/extension-placeholder";
import Underline from "@tiptap/extension-underline";
import Highlight from "@tiptap/extension-highlight";
import type { Extensions } from "@tiptap/core";
import { BubbleMenu, EditorContent, useEditor, type Editor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import { HocuspocusProvider } from "@hocuspocus/provider";
import * as Y from "yjs";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { editSelection } from "../api";
import {
  COLLAB_ROOM,
  getCollaborationProfile,
  getCollabWsUrl,
  isCollabEnabled,
} from "../lib/collab";
import { EditorToolbar } from "./EditorToolbar";
import styles from "./editor.module.css";

type Props = {
  initialHtml: string;
  onHtmlChange: (html: string) => void;
  model: string;
  onStatus: (msg: string | null) => void;
};

export function TiptapEditor({ initialHtml, onHtmlChange, model, onStatus }: Props) {
  const [bubbleBusy, setBubbleBusy] = useState<"summarize" | "improve" | null>(null);
  const onHtmlChangeRef = useRef(onHtmlChange);
  onHtmlChangeRef.current = onHtmlChange;
  const collabOn = isCollabEnabled();
  const collabWsUrl = useMemo(() => getCollabWsUrl(), []);
  const profile = useMemo(() => getCollaborationProfile(), []);
  const ydoc = useMemo(() => new Y.Doc(), []);
  const editorRef = useRef<Editor | null>(null);
  const initialHtmlRef = useRef(initialHtml);
  initialHtmlRef.current = initialHtml;

  const [provider, setProvider] = useState<HocuspocusProvider | null>(null);

  useEffect(() => {
    if (!collabOn) return;
    const p = new HocuspocusProvider({
      url: collabWsUrl,
      name: COLLAB_ROOM,
      document: ydoc,
      onSynced: () => {
        queueMicrotask(() => {
          const ed = editorRef.current;
          if (!ed) return;
          const fr = ydoc.getXmlFragment("default");
          const html = initialHtmlRef.current;
          if (fr.length === 0 && html?.trim()) {
            ed.commands.setContent(html, false);
          }
        });
      },
    });
    setProvider(p);
    return () => {
      p.destroy();
      setProvider(null);
    };
  }, [collabOn, collabWsUrl, ydoc]);

  const extensions = useMemo(
    () => {
      const ex: Extensions = [
        StarterKit.configure({
          ...(collabOn && provider ? { history: false } : {}),
          heading: { levels: [1, 2, 3] },
        }),
      ];
      if (collabOn && provider) {
        ex.push(
          Collaboration.configure({ document: ydoc }),
          CollaborationCursor.configure({
            provider,
            user: profile,
          }),
        );
      }
      ex.push(
        Placeholder.configure({
          placeholder:
            "Write here — edits sync in real time when collaboration is on. Library tab: ingest PDF/MD for RAG.",
        }),
        Underline,
        Highlight.configure({ multicolor: false }),
        Link.configure({ openOnClick: true, autolink: true }),
      );
      return ex;
    },
    [collabOn, provider, ydoc, profile],
  );

  const editor = useEditor(
    {
      extensions,
      content: collabOn && provider ? undefined : initialHtml,
      editorProps: {
        attributes: { class: styles.prose },
      },
      onCreate: ({ editor: ed }) => {
        editorRef.current = ed;
      },
      onDestroy: () => {
        editorRef.current = null;
      },
      onUpdate: ({ editor: ed }) => {
        onHtmlChangeRef.current(ed.getHTML());
      },
    },
    [extensions, collabOn, provider, initialHtml],
  );

  const runAction = useCallback(
    async (action: "summarize" | "improve") => {
      if (!editor) return;
      const { from, to } = editor.state.selection;
      if (from === to) return;
      const text = editor.state.doc.textBetween(from, to, " ");
      if (!text.trim()) return;
      setBubbleBusy(action);
      onStatus(`${action}…`);
      try {
        const res = await editSelection({
          selection: text,
          action,
          model,
          document_html: editor.getHTML(),
        });
        editor.chain().focus().deleteRange({ from, to }).insertContentAt(from, res.answer).run();
        onStatus(null);
      } catch (e) {
        onStatus(e instanceof Error ? e.message : "Edit failed");
      } finally {
        setBubbleBusy(null);
      }
    },
    [editor, model, onStatus],
  );

  if (!editor) return <div className={styles.loading}>Loading editor…</div>;

  return (
    <div className={styles.wrap}>
      {collabOn && (
        <div className={styles.collabBadge} title="Hocuspocus + Yjs">
          {provider?.isConnected ? "Live collaboration · connected" : "Live collaboration · connecting…"}
        </div>
      )}
      <EditorToolbar editor={editor} />
      <BubbleMenu editor={editor} tippyOptions={{ duration: 120 }} className={styles.bubble}>
        <button
          type="button"
          disabled={!!bubbleBusy}
          onClick={() => void runAction("summarize")}
        >
          {bubbleBusy === "summarize" ? "…" : "Summarize"}
        </button>
        <button
          type="button"
          disabled={!!bubbleBusy}
          onClick={() => void runAction("improve")}
        >
          {bubbleBusy === "improve" ? "…" : "Improve"}
        </button>
      </BubbleMenu>
      <EditorContent editor={editor} />
    </div>
  );
}
