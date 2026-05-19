"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import JobHistory, { type JobSummary, jobDayKey } from "@/components/JobHistory";
import MiniCalendar from "@/components/MiniCalendar";
import ThemeToggle from "@/components/ThemeToggle";
import { apiUrl } from "../lib/api";

/** "2026-05-18" -> "18 mai" */
function frDay(key: string): string {
  const [y, m, d] = key.split("-").map(Number);
  const dt = new Date(y, m - 1, d);
  return dt.toLocaleDateString("fr-FR", { day: "numeric", month: "short" });
}

interface Props {
  open: boolean;
  onClose: () => void;
  /** Ouvre le panneau (utilisé par le raccourci Ctrl+F). */
  onOpen: () => void;
  /** Ctrl+F focalise la recherche du panneau UNIQUEMENT si true. Quand une
   *  réunion/compte rendu est ouvert, c'est ReportFindBar qui prend Ctrl+F. */
  ctrlFEnabled: boolean;
  selectedId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDeleted?: (id: string) => void;
}

export default function Sidebar({
  open,
  onClose,
  onOpen,
  ctrlFEnabled,
  selectedId,
  onSelect,
  onNew,
  onDeleted,
}: Props) {
  const [query, setQuery] = useState("");
  const [day, setDay] = useState<string | null>(null);
  const [showCal, setShowCal] = useState(false);
  const [jobs, setJobs] = useState<JobSummary[]>([]);
  const [folders, setFolders] = useState<string[]>([]);
  const searchRef = useRef<HTMLInputElement>(null);

  const reload = useCallback(async () => {
    try {
      const [jr, fr] = await Promise.all([
        fetch(apiUrl("/api/jobs")),
        fetch(apiUrl("/api/folders")),
      ]);
      if (jr.ok) {
        const d = (await jr.json()) as { jobs: JobSummary[] };
        setJobs(d.jobs ?? []);
      }
      if (fr.ok) {
        const d = (await fr.json()) as { folders: string[] };
        setFolders(d.folders ?? []);
      }
    } catch {
      /* ignore — un tick suivant réessaiera */
    }
  }, []);

  // Poll régulier (statut des traitements en cours).
  useEffect(() => {
    reload();
    const id = setInterval(reload, 2500);
    return () => clearInterval(id);
  }, [reload]);

  // Échap ferme ; Ctrl/Cmd+F ouvre + focus la recherche.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && open) {
        onClose();
        return;
      }
      if (
        ctrlFEnabled &&
        (e.ctrlKey || e.metaKey) &&
        e.key.toLowerCase() === "f"
      ) {
        e.preventDefault();
        if (!open) onOpen();
        requestAnimationFrame(() => searchRef.current?.focus());
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose, onOpen, ctrlFEnabled]);

  const marked = new Set<string>();
  for (const j of jobs) {
    const k = jobDayKey(j.createdAt);
    if (k) marked.add(k);
  }

  return (
    <>
      <div
        onClick={onClose}
        aria-hidden={!open}
        className={`fixed inset-0 z-30 bg-black/45 backdrop-blur-[2px] transition-opacity duration-200 ${
          open ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
      />

      <aside
        aria-hidden={!open}
        className={`fixed left-0 top-0 z-40 flex h-screen w-[340px] flex-col border-r border-surface-border bg-surface-card shadow-2xl transition-transform duration-250 ease-out ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {/* Brand + close */}
        <div className="px-5 pt-5 pb-3">
          <div className="flex items-center gap-3">
            <div className="min-w-0 flex-1">
              <h1 className="truncate text-sm font-semibold text-ink">Réunions</h1>
              <p className="truncate text-xs text-ink-muted">
                Enregistrement · Synthèse
              </p>
            </div>
            <button
              type="button"
              onClick={onClose}
              aria-label="Fermer le menu"
              title="Fermer"
              className="flex h-8 w-8 items-center justify-center rounded-lg text-ink-muted transition-colors hover:bg-surface hover:text-ink"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
        </div>

        {/* CTA */}
        <div className="px-4 pb-3">
          <button
            type="button"
            onClick={onNew}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-brand px-4 py-2.5 text-sm font-medium text-white shadow-sm transition-all duration-200 hover:bg-brand-dark hover:shadow-md hover:-translate-y-0.5 active:translate-y-0"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            Nouvelle réunion
          </button>
        </div>

        {/* Recherche (Ctrl+F) */}
        <div className="px-4 pb-3">
          <div className="relative">
            <svg
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-muted"
              width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
            >
              <circle cx="11" cy="11" r="7" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
            <input
              ref={searchRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Rechercher  (Ctrl+F)"
              className="w-full rounded-lg border border-surface-border bg-surface py-2 pl-9 pr-3 text-sm text-ink placeholder:text-ink-muted/60 transition focus:border-accent-blue focus:outline-none focus:ring-2 focus:ring-accent-blue/20"
            />
          </div>
        </div>

        {/* Filtre par date — repliable (caché par défaut pour aérer) */}
        <div className="px-4 pb-3">
          <button
            type="button"
            onClick={() => setShowCal((v) => !v)}
            className="flex w-full items-center gap-2 rounded-lg border border-surface-border bg-surface px-3 py-2 text-xs text-ink-muted transition-colors hover:text-ink"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="4" width="18" height="18" rx="2" />
              <line x1="16" y1="2" x2="16" y2="6" />
              <line x1="8" y1="2" x2="8" y2="6" />
              <line x1="3" y1="10" x2="21" y2="10" />
            </svg>
            <span className="flex-1 text-left">
              {day ? `Jour : ${frDay(day)}` : "Filtrer par date"}
            </span>
            {day && (
              <span
                role="button"
                tabIndex={0}
                onClick={(e) => {
                  e.stopPropagation();
                  setDay(null);
                }}
                className="rounded px-1 text-ink-muted hover:text-brand"
                aria-label="Effacer le filtre date"
              >
                ✕
              </span>
            )}
            <svg
              width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
              className={`transition-transform ${showCal ? "rotate-180" : ""}`}
            >
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </button>
          {showCal && (
            <div className="mt-2">
              <MiniCalendar marked={marked} selected={day} onSelect={setDay} />
            </div>
          )}
        </div>

        {/* Historique (dossiers + filtre jour/recherche) */}
        <div className="flex-1 overflow-y-auto px-2 pb-3">
          <JobHistory
            jobs={jobs}
            folders={folders}
            reload={reload}
            selectedId={selectedId}
            onSelect={onSelect}
            onDeleted={onDeleted}
            query={query}
            day={day}
          />
        </div>

        <div className="space-y-2 border-t border-surface-border px-4 py-3">
          <button
            type="button"
            onClick={() =>
              window.open(
                "mailto:genai@yele.fr?subject=" +
                  encodeURIComponent("Retour outil CR"),
              )
            }
            className="flex w-full items-center justify-center gap-2 rounded-lg border border-surface-border bg-surface px-3 py-2 text-sm font-medium text-ink transition-all duration-200 hover:border-accent-blue hover:text-accent-blue hover:shadow-soft"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="2" y="4" width="20" height="16" rx="2" />
              <path d="m22 7-10 6L2 7" />
            </svg>
            Contactez-nous
          </button>
          <div className="flex items-center justify-between">
            <span className="text-[11px] text-ink-muted">v1.0</span>
            <ThemeToggle />
          </div>
        </div>
      </aside>
    </>
  );
}
