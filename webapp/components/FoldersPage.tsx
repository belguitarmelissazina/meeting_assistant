"use client";

import { useState } from "react";
import { apiUrl } from "@/lib/api";
import { useJobs } from "@/lib/useJobs";

interface Props {
  /** Ouvrir un dossier (`null` = « Sans dossier »). */
  onOpenFolder: (folder: string | null) => void;
}

const NO_FOLDER = "::no-folder::";

function fmtDate(ms?: number): string {
  if (!ms) return "—";
  return new Date(ms).toLocaleDateString("fr-FR", {
    day: "numeric",
    month: "short",
  });
}

export default function FoldersPage({ onOpenFolder }: Props) {
  const { jobs, folders, reload } = useJobs();
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [confirm, setConfirm] = useState<string | null>(null);

  async function call(url: string, init: RequestInit) {
    setError(null);
    try {
      const r = await fetch(apiUrl(url), init);
      if (!r.ok) {
        let msg = `Erreur ${r.status}`;
        try {
          const d = await r.json();
          if (d?.detail) msg = String(d.detail);
        } catch {
          /* ignore */
        }
        throw new Error(msg);
      }
      reload();
      return true;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur");
      return false;
    }
  }

  async function createFolder() {
    const n = name.trim();
    if (!n) return;
    const ok = await call("/api/folders", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: n }),
    });
    if (ok) {
      setName("");
      setCreating(false);
    }
  }

  async function deleteFolder(f: string) {
    const ok = await call(`/api/folders/${encodeURIComponent(f)}`, {
      method: "DELETE",
    });
    if (ok) setConfirm(null);
  }

  // Compteur + dernière activité par dossier.
  const stat = new Map<string, { count: number; last: number }>();
  for (const j of jobs) {
    const k = j.folder || NO_FOLDER;
    const s = stat.get(k) ?? { count: 0, last: 0 };
    s.count += 1;
    if (j.createdAt && j.createdAt > s.last) s.last = j.createdAt;
    stat.set(k, s);
  }

  const noFolder = stat.get(NO_FOLDER);

  return (
    <div className="mx-auto w-full max-w-4xl animate-fade-in">
      <header className="mb-6 flex items-end justify-between gap-4">
        <h1 className="text-3xl font-semibold tracking-tight text-ink">
          Dossiers
        </h1>
        <button
          type="button"
          onClick={() => setCreating((v) => !v)}
          className="inline-flex items-center gap-2 rounded-lg border border-surface-border bg-surface-card px-4 py-2 text-sm font-medium text-ink shadow-sm transition-all hover:border-accent-blue hover:text-accent-blue"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
            <line x1="12" y1="11" x2="12" y2="17" />
            <line x1="9" y1="14" x2="15" y2="14" />
          </svg>
          Nouveau dossier
        </button>
      </header>

      {creating && (
        <div className="mb-5 flex items-center gap-2">
          <input
            autoFocus
            value={name}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") createFolder();
              if (e.key === "Escape") setCreating(false);
            }}
            placeholder="Nom du dossier"
            className="min-w-0 flex-1 rounded-lg border border-accent-blue/40 bg-surface-card px-3 py-2 text-sm text-ink focus:border-accent-blue focus:outline-none"
          />
          <button
            type="button"
            onClick={createFolder}
            className="rounded-lg bg-accent-blue px-4 py-2 text-sm font-medium text-white hover:brightness-110"
          >
            Créer
          </button>
          <button
            type="button"
            onClick={() => setCreating(false)}
            className="rounded-lg border border-surface-border px-3 py-2 text-sm text-ink-muted hover:text-ink"
          >
            Annuler
          </button>
        </div>
      )}

      {error && (
        <div className="mb-4 rounded-md border border-brand/30 bg-brand/5 px-4 py-3 text-sm text-brand">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {(noFolder?.count ?? 0) > 0 && (
          <button
            type="button"
            onClick={() => onOpenFolder(null)}
            className="card-interactive flex flex-col items-start text-left"
          >
            <span className="flex h-12 w-12 items-center justify-center rounded-lg bg-ink-muted/10 text-ink-muted">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
              </svg>
            </span>
            <p className="mt-4 text-lg font-semibold text-ink">Sans dossier</p>
            <p className="mt-1 text-[13px] text-ink-muted">
              {noFolder!.count} réunion{noFolder!.count > 1 ? "s" : ""} · maj{" "}
              {fmtDate(noFolder!.last)}
            </p>
          </button>
        )}

        {folders.map((f) => {
          const s = stat.get(f) ?? { count: 0, last: 0 };
          const empty = s.count === 0;
          return (
            <div key={f} className="group relative">
              <button
                type="button"
                onClick={() => onOpenFolder(f)}
                className="card-interactive flex w-full flex-col items-start text-left"
              >
                <span className="flex h-12 w-12 items-center justify-center rounded-lg bg-accent-blue/10 text-accent-blue">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
                  </svg>
                </span>
                <p className="mt-4 truncate text-lg font-semibold text-ink w-full">
                  {f}
                </p>
                <p className="mt-1 text-[13px] text-ink-muted">
                  {s.count} réunion{s.count > 1 ? "s" : ""}
                  {!empty && ` · maj ${fmtDate(s.last)}`}
                </p>
              </button>

              {empty &&
                (confirm === f ? (
                  <div className="absolute right-3 top-3 flex items-center gap-1">
                    <button
                      type="button"
                      onClick={() => deleteFolder(f)}
                      className="rounded px-2 py-1 text-[11px] font-semibold text-brand hover:bg-brand/10"
                    >
                      Suppr.
                    </button>
                    <button
                      type="button"
                      onClick={() => setConfirm(null)}
                      className="rounded px-2 py-1 text-[11px] text-ink-muted hover:bg-surface"
                    >
                      ✕
                    </button>
                  </div>
                ) : (
                  <button
                    type="button"
                    onClick={() => setConfirm(f)}
                    title="Supprimer ce dossier vide"
                    className="absolute right-3 top-3 flex h-7 w-7 items-center justify-center rounded text-ink-muted opacity-0 transition-opacity hover:bg-brand/10 hover:text-brand group-hover:opacity-100"
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="3 6 5 6 21 6" />
                      <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
                    </svg>
                  </button>
                ))}
            </div>
          );
        })}
      </div>

      {folders.length === 0 && (noFolder?.count ?? 0) === 0 && (
        <div className="rounded-2xl border border-dashed border-surface-border px-4 py-20 text-center text-sm text-ink-muted">
          Aucun dossier. Créez-en un pour ranger vos comptes rendus.
        </div>
      )}
    </div>
  );
}
