"use client";

import { useRef, useState } from "react";
import { apiUrl } from "../lib/api";

interface Props {
  onJobCreated: (id: string) => void;
}

export default function Uploader({ onJobCreated }: Props) {
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
      fd.append("audio", file);
      const r = await fetch(apiUrl("/api/process/upload"), { method: "POST", body: fd });
      if (!r.ok) throw new Error(await r.text());
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
          accept="audio/*,video/mp4"
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
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>
        </div>
        <p className="mt-4 text-sm font-medium text-ink">
          {fileName ?? "Glissez votre audio ici"}
        </p>
        <p className="mt-1 text-xs text-ink-muted">
          ou cliquez pour parcourir
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
