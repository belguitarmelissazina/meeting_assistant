"use client";

import { useRef, useState } from "react";
import { apiUrl } from "../lib/api";

interface Props {
  onJobCreated: (id: string) => void;
}

export default function TranscriptUploader({ onJobCreated }: Props) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  async function upload(file: File) {
    setError(null);
    setBusy(true);
    setFileName(file.name);
    try {
      const fd = new FormData();
      fd.append("transcript", file);
      const r = await fetch(apiUrl("/api/process/upload-transcript"), {
        method: "POST",
        body: fd,
      });
      if (!r.ok) {
        let msg = `Erreur ${r.status}`;
        try {
          const data = await r.json();
          if (data?.detail) msg = String(data.detail);
        } catch {
          /* ignore */
        }
        throw new Error(msg);
      }
      const { jobId } = (await r.json()) as { jobId: string };
      onJobCreated(jobId);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-5">
      <label
        className="group relative flex cursor-pointer flex-col items-center justify-center overflow-hidden rounded-2xl border-2 border-dashed border-surface-border bg-surface px-6 py-14 transition-all duration-300 ease-out hover:border-accent-blue hover:bg-accent-blue/5 hover:shadow-glow"
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          const f = e.dataTransfer.files[0];
          if (f) upload(f);
        }}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".txt,.docx,text/plain,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) upload(f);
          }}
        />
        <div className="relative flex h-14 w-14 items-center justify-center rounded-full bg-accent-blue/10 text-accent-blue transition-transform duration-300 group-hover:-translate-y-1 group-hover:scale-105">
          <svg
            width="28"
            height="28"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="8" y1="13" x2="16" y2="13" />
            <line x1="8" y1="17" x2="16" y2="17" />
            <line x1="8" y1="9" x2="10" y2="9" />
          </svg>
        </div>
        <p className="mt-4 text-sm font-medium text-ink">
          {fileName ?? "Glissez votre transcript ici"}
        </p>
        <p className="mt-1 text-xs text-ink-muted">
          .docx Teams ou .txt formaté — ou cliquez pour parcourir
        </p>
      </label>

      {busy && (
        <div className="flex items-center gap-2 text-sm text-accent-blue">
          <span className="h-3 w-3 animate-spin rounded-full border-2 border-accent-blue border-t-transparent" />
          Envoi…
        </div>
      )}
      {error && (
        <div className="rounded-md border border-brand/30 bg-brand/5 px-4 py-3 text-sm text-brand">
          {error}
        </div>
      )}
    </div>
  );
}
