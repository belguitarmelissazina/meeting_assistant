"use client";

import {
  forwardRef,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
} from "react";
import { useEditor, EditorContent, type Editor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Table from "@tiptap/extension-table";
import TableRow from "@tiptap/extension-table-row";
import TableHeader from "@tiptap/extension-table-header";
import TableCell from "@tiptap/extension-table-cell";
import { marked } from "marked";
import TurndownService from "turndown";
import { gfm } from "turndown-plugin-gfm";
import { apiUrl } from "../lib/api";

export type SaveState =
  | { kind: "idle" }
  | { kind: "saving" }
  | { kind: "saved"; at: Date }
  | { kind: "error"; message: string };

export interface ReportEditorHandle {
  save: () => Promise<void>;
}

interface Props {
  jobId: string;
  initialMarkdown?: string;
  onStateChange?: (state: SaveState) => void;
}

const turndown = new TurndownService({
  headingStyle: "atx",
  bulletListMarker: "-",
  codeBlockStyle: "fenced",
  emDelimiter: "*",
});
turndown.use(gfm);
// Évite `1\. ` / `\*` / `\_` dans le markdown — l'éditeur WYSIWYG
// garantit la structure, l'échappement n'apporte rien et pollue la sortie.
turndown.escape = (text: string) => text;

// La règle table de turndown-plugin-gfm laisse le tableau en HTML brut dès
// que la 1re ligne ne passe pas son `isHeadingRow` strict (tiptap émet
// `<table class="md-table"><tbody><tr><th><p>…` avec des <p>/blancs). Le
// backend (_md_to_docx) ne lit QUE le GFM `| … |` → docx cassé. On force
// donc une reconstruction GFM déterministe de tout <table>.
turndown.addRule("cellParagraphUnwrap", {
  filter: (node) =>
    node.nodeName === "P" &&
    !!(node as unknown as HTMLElement).closest?.("td, th"),
  replacement: (content) => content,
});

turndown.addRule("gfmTable", {
  filter: "table",
  replacement: (_content, node) => {
    const table = node as unknown as HTMLElement;
    const trs = Array.from(table.querySelectorAll("tr"));
    if (trs.length === 0) return "";
    const rows = trs.map((tr) =>
      Array.from(tr.querySelectorAll("th, td")).map((c) =>
        (c.textContent || "")
          .replace(/\s+/g, " ")
          .trim()
          .replace(/\|/g, "\\|"),
      ),
    );
    const ncols = rows.reduce((m, r) => Math.max(m, r.length), 0);
    if (ncols === 0) return "";
    const pad = (r: string[]) =>
      "| " + Array.from({ length: ncols }, (_, i) => r[i] ?? "").join(" | ") + " |";
    const header = pad(rows[0]);
    const sep = "| " + Array.from({ length: ncols }, () => "---").join(" | ") + " |";
    const body = rows.slice(1).map(pad);
    return "\n\n" + [header, sep, ...body].join("\n") + "\n\n";
  },
});

// Filet de sécurité : aucune balise de tableau ne doit jamais survivre en
// HTML brut dans le markdown, même si la règle `gfmTable` ne s'appliquait pas.
turndown.addRule("tableTagsPassthrough", {
  filter: ["thead", "tbody", "tfoot", "tr", "th", "td"],
  replacement: (content) => content,
});

const ReportEditor = forwardRef<ReportEditorHandle, Props>(function ReportEditor(
  { jobId, initialMarkdown, onStateChange },
  ref,
) {
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastSentRef = useRef<string>(initialMarkdown ?? "");
  const editorRef = useRef<Editor | null>(null);
  const onStateRef = useRef(onStateChange);

  useEffect(() => {
    onStateRef.current = onStateChange;
  }, [onStateChange]);

  const pushState = (s: SaveState) => onStateRef.current?.(s);

  const editor = useEditor({
    extensions: [
      StarterKit,
      Table.configure({ resizable: false, HTMLAttributes: { class: "md-table" } }),
      TableRow,
      TableHeader,
      TableCell,
    ],
    content: marked.parse(initialMarkdown ?? "", {
      async: false,
      gfm: true,
      breaks: false,
    }) as string,
    editorProps: {
      attributes: {
        class: "focus:outline-none min-h-[500px]",
      },
    },
    immediatelyRender: false,
    onUpdate: ({ editor }) => {
      scheduleSave(editor);
    },
  });

  editorRef.current = editor;

  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, []);

  function scheduleSave(ed: Editor) {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => save(ed), 1000);
  }

  async function save(ed: Editor) {
    const html = ed.getHTML();
    const md = turndown.turndown(html);
    if (md === lastSentRef.current) {
      pushState({ kind: "saved", at: new Date() });
      return;
    }
    pushState({ kind: "saving" });
    try {
      const r = await fetch(apiUrl(`/api/jobs/${jobId}/report`), {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ markdown: md }),
      });
      if (!r.ok) {
        const txt = await r.text();
        throw new Error(txt || `HTTP ${r.status}`);
      }
      lastSentRef.current = md;
      pushState({ kind: "saved", at: new Date() });
    } catch (e) {
      pushState({
        kind: "error",
        message: e instanceof Error ? e.message : "Erreur",
      });
    }
  }

  useImperativeHandle(
    ref,
    () => ({
      save: async () => {
        const ed = editorRef.current;
        if (!ed) return;
        if (debounceRef.current) {
          clearTimeout(debounceRef.current);
          debounceRef.current = null;
        }
        await save(ed);
      },
    }),
    [],
  );

  if (!editor) {
    return (
      <p className="text-sm text-ink-muted">Chargement de l&apos;éditeur…</p>
    );
  }

  return (
    <div className="flex flex-col">
      <div className="rounded-2xl border border-surface-border bg-surface-card px-8 py-10 shadow-soft md:px-14 md:py-12 pb-28">
        <EditorContent editor={editor} />
      </div>
      <div className="sticky bottom-5 z-30 mx-auto mt-4 w-fit max-w-full">
        <Toolbar editor={editor} />
      </div>
    </div>
  );
});

export default ReportEditor;

function Toolbar({ editor }: { editor: Editor }) {
  return (
    <div className="editor-toolbar">
      <ToolBtn
        title="Gras"
        active={editor.isActive("bold")}
        onClick={() => editor.chain().focus().toggleBold().run()}
      >
        <strong>B</strong>
      </ToolBtn>
      <ToolBtn
        title="Italique"
        active={editor.isActive("italic")}
        onClick={() => editor.chain().focus().toggleItalic().run()}
      >
        <em>I</em>
      </ToolBtn>
      <ToolBtn
        title="Barré"
        active={editor.isActive("strike")}
        onClick={() => editor.chain().focus().toggleStrike().run()}
      >
        <span className="line-through">S</span>
      </ToolBtn>
      <Sep />
      <ToolBtn
        title="Titre 1"
        active={editor.isActive("heading", { level: 1 })}
        onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}
      >
        H1
      </ToolBtn>
      <ToolBtn
        title="Titre 2"
        active={editor.isActive("heading", { level: 2 })}
        onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
      >
        H2
      </ToolBtn>
      <ToolBtn
        title="Titre 3"
        active={editor.isActive("heading", { level: 3 })}
        onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
      >
        H3
      </ToolBtn>
      <Sep />
      <ToolBtn
        title="Liste à puces"
        active={editor.isActive("bulletList")}
        onClick={() => editor.chain().focus().toggleBulletList().run()}
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <line x1="9" y1="6" x2="20" y2="6" />
          <line x1="9" y1="12" x2="20" y2="12" />
          <line x1="9" y1="18" x2="20" y2="18" />
          <circle cx="4" cy="6" r="1" fill="currentColor" />
          <circle cx="4" cy="12" r="1" fill="currentColor" />
          <circle cx="4" cy="18" r="1" fill="currentColor" />
        </svg>
      </ToolBtn>
      <ToolBtn
        title="Liste numérotée"
        active={editor.isActive("orderedList")}
        onClick={() => editor.chain().focus().toggleOrderedList().run()}
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <line x1="10" y1="6" x2="21" y2="6" />
          <line x1="10" y1="12" x2="21" y2="12" />
          <line x1="10" y1="18" x2="21" y2="18" />
          <path d="M4 6h1v4" />
          <path d="M4 10h2" />
          <path d="M6 18H4c0-1 2-2 2-3s-1-1.5-2-1" />
        </svg>
      </ToolBtn>
      <ToolBtn
        title="Citation"
        active={editor.isActive("blockquote")}
        onClick={() => editor.chain().focus().toggleBlockquote().run()}
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M3 21c3 0 7-1 7-8V5c0-1.25-.756-2-2-2H4c-1.25 0-2 .75-2 2v8c0 1.25.75 2 2 2h2c0 0 1 0 0 6" />
          <path d="M15 21c3 0 7-1 7-8V5c0-1.25-.757-2-2-2h-4c-1.25 0-2 .75-2 2v8c0 1.25.75 2 2 2h2c0 0 1 0 0 6" />
        </svg>
      </ToolBtn>
      <Sep />
      <ToolBtn
        title="Ajouter une ligne au tableau"
        onClick={() => editor.chain().focus().addRowAfter().run()}
        disabled={!editor.can().addRowAfter()}
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="3" y="3" width="18" height="11" rx="1" />
          <line x1="3" y1="8.5" x2="21" y2="8.5" />
          <line x1="12" y1="18" x2="12" y2="22" />
          <line x1="10" y1="20" x2="14" y2="20" />
        </svg>
      </ToolBtn>
      <ToolBtn
        title="Supprimer la ligne du tableau"
        onClick={() => editor.chain().focus().deleteRow().run()}
        disabled={!editor.can().deleteRow()}
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="3" y="3" width="18" height="11" rx="1" />
          <line x1="3" y1="8.5" x2="21" y2="8.5" />
          <line x1="10" y1="20" x2="14" y2="20" />
        </svg>
      </ToolBtn>
      <Sep />
      <ToolBtn
        title="Annuler"
        onClick={() => editor.chain().focus().undo().run()}
        disabled={!editor.can().undo()}
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M3 7v6h6" />
          <path d="M21 17a9 9 0 0 0-15-6.7L3 13" />
        </svg>
      </ToolBtn>
      <ToolBtn
        title="Rétablir"
        onClick={() => editor.chain().focus().redo().run()}
        disabled={!editor.can().redo()}
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 7v6h-6" />
          <path d="M3 17a9 9 0 0 1 15-6.7L21 13" />
        </svg>
      </ToolBtn>
    </div>
  );
}

function ToolBtn({
  title,
  active,
  disabled,
  onClick,
  children,
}: {
  title: string;
  active?: boolean;
  disabled?: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      title={title}
      aria-label={title}
      onClick={onClick}
      disabled={disabled}
      className={`flex h-8 min-w-8 items-center justify-center rounded-md px-2 text-xs font-medium transition-colors ${
        active
          ? "bg-accent-blue/15 text-accent-blue"
          : "text-ink-muted hover:bg-surface hover:text-ink"
      } disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-transparent disabled:hover:text-ink-muted`}
    >
      {children}
    </button>
  );
}

function Sep() {
  return <span className="mx-1 h-5 w-px bg-surface-border" aria-hidden />;
}
