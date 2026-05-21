"use client";

import { useEffect, useRef, useState } from "react";
import JobHistory from "@/components/JobHistory";
import { useJobs } from "@/lib/useJobs";

interface Props {
  /** `undefined` = tous, `null` = sans dossier, sinon le dossier filtré. */
  folder?: string | null;
  /** Demande de focus sur la recherche (venant de « Rechercher »). */
  focusSearch?: boolean;
  selectedId: string | null;
  onSelect: (id: string) => void;
  /** Revenir à la page Dossiers (quand on est entré dans un dossier). */
  onBackToFolders: () => void;
}

export default function ReportsPage({
  folder,
  focusSearch,
  selectedId,
  onSelect,
  onBackToFolders,
}: Props) {
  const { jobs, folders, reload } = useJobs();
  const [query, setQuery] = useState("");
  const searchRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (focusSearch) {
      requestAnimationFrame(() => searchRef.current?.focus());
    }
  }, [focusSearch]);

  const inFolder = folder !== undefined;
  const title = !inFolder
    ? "Comptes rendus"
    : folder === null
    ? "Sans dossier"
    : folder;

  return (
    <div className="mx-auto w-full max-w-4xl animate-fade-in">
      {inFolder && (
        <nav className="mb-4 flex items-center gap-1.5 text-sm">
          <button
            type="button"
            onClick={onBackToFolders}
            className="text-ink-muted transition-colors hover:text-ink"
          >
            Dossiers
          </button>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-ink-muted/60">
            <polyline points="9 18 15 12 9 6" />
          </svg>
          <span className="font-medium text-ink">
            {folder === null ? "Sans dossier" : folder}
          </span>
        </nav>
      )}

      <header className="mb-5 flex items-end justify-between gap-4">
        <h1 className="flex items-center gap-2.5 text-3xl font-semibold tracking-tight text-ink">
          {inFolder && folder !== null && (
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-ink-muted">
              <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
            </svg>
          )}
          {title}
        </h1>
      </header>

      <div className="relative mb-5">
        <svg
          className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-ink-muted"
          width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
        >
          <circle cx="11" cy="11" r="7" />
          <line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
        <input
          ref={searchRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Rechercher un compte rendu…  (Ctrl+F)"
          className="w-full rounded-xl border border-surface-border bg-surface-card py-3.5 pl-12 pr-4 text-[15px] text-ink placeholder:text-ink-muted/60 shadow-soft transition focus:border-accent-blue focus:outline-none focus:ring-2 focus:ring-accent-blue/20"
        />
      </div>

      <JobHistory
        flat
        folderFilter={folder}
        jobs={jobs}
        folders={folders}
        reload={reload}
        selectedId={selectedId}
        onSelect={onSelect}
        query={query}
        day={null}
      />
    </div>
  );
}
