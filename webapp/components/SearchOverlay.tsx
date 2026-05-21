"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { JobSummary } from "@/components/JobHistory";
import { useJobs } from "@/lib/useJobs";
import { meetingDisplayName } from "@/lib/meetings";

interface Props {
  open: boolean;
  onClose: () => void;
  /** Ouvre le compte rendu sélectionné. */
  onSelect: (id: string) => void;
}

function fmtDate(ms?: number): string {
  if (!ms) return "";
  return new Date(ms).toLocaleDateString("fr-FR", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function dotCls(status: JobSummary["status"]): string {
  if (status === "done") return "bg-accent-green";
  if (status === "error") return "bg-brand";
  if (status === "running" || status === "queued")
    return "bg-accent-blue animate-pulse";
  if (status === "draft") return "bg-accent-yellow";
  return "bg-ink-muted/50";
}

/**
 * Recherche globale en surimpression (façon Claude). Accessible de partout
 * via la sidebar « Rechercher » ou Ctrl+F (quand aucun compte rendu n'est
 * ouvert). Cherche dans le nom des réunions enregistrées et ouvre
 * directement le compte rendu choisi. Vide → liste les plus récentes.
 */
export default function SearchOverlay({ open, onClose, onSelect }: Props) {
  const { jobs } = useJobs();
  const [q, setQ] = useState("");
  const [active, setActive] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLUListElement>(null);

  // Réinitialise à chaque ouverture + focus.
  useEffect(() => {
    if (!open) return;
    setQ("");
    setActive(0);
    requestAnimationFrame(() => inputRef.current?.focus());
  }, [open]);

  const results = useMemo(() => {
    const sorted = [...jobs].sort(
      (a, b) => (b.createdAt ?? 0) - (a.createdAt ?? 0),
    );
    const term = q.trim().toLowerCase();
    if (!term) return sorted.slice(0, 8);
    return sorted
      .filter((j) =>
        meetingDisplayName(j.label, j.calendar?.subject, j.id)
          .toLowerCase()
          .includes(term),
      )
      .slice(0, 30);
  }, [jobs, q]);

  // Garde la sélection dans les bornes quand la liste change.
  useEffect(() => {
    setActive((a) => Math.min(a, Math.max(0, results.length - 1)));
  }, [results.length]);

  // Fait défiler la ligne active dans la vue.
  useEffect(() => {
    const el = listRef.current?.children[active] as HTMLElement | undefined;
    el?.scrollIntoView({ block: "nearest" });
  }, [active]);

  if (!open) return null;

  const choose = (j?: JobSummary) => {
    if (!j) return;
    onSelect(j.id);
    onClose();
  };

  return (
    <div
      className="fixed inset-0 z-[60] flex items-start justify-center bg-black/40 p-4 pt-[12vh] animate-fade-in"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Rechercher une réunion"
        className="w-full max-w-xl overflow-hidden rounded-2xl border border-surface-border bg-surface-card shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-3 border-b border-surface-border px-4 py-3">
          <svg
            className="flex-shrink-0 text-ink-muted"
            width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
          >
            <circle cx="11" cy="11" r="7" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            ref={inputRef}
            type="text"
            value={q}
            onChange={(e) => {
              setQ(e.target.value);
              setActive(0);
            }}
            onKeyDown={(e) => {
              if (e.key === "ArrowDown") {
                e.preventDefault();
                setActive((a) => Math.min(a + 1, results.length - 1));
              } else if (e.key === "ArrowUp") {
                e.preventDefault();
                setActive((a) => Math.max(a - 1, 0));
              } else if (e.key === "Enter") {
                e.preventDefault();
                choose(results[active]);
              } else if (e.key === "Escape") {
                e.preventDefault();
                onClose();
              }
            }}
            placeholder="Rechercher une réunion…"
            className="min-w-0 flex-1 bg-transparent text-sm text-ink placeholder:text-ink-muted/60 focus:outline-none"
          />
          <kbd className="hidden flex-shrink-0 rounded border border-surface-border px-1.5 py-0.5 text-[10px] text-ink-muted sm:block">
            Échap
          </kbd>
        </div>

        <ul ref={listRef} className="max-h-[52vh] overflow-y-auto p-2">
          {results.length === 0 ? (
            <li className="px-3 py-10 text-center text-sm text-ink-muted">
              {q.trim()
                ? "Aucune réunion ne correspond."
                : "Aucune réunion enregistrée."}
            </li>
          ) : (
            <>
              {!q.trim() && (
                <li className="px-3 pb-1 pt-1 text-[11px] font-semibold uppercase tracking-wider text-ink-muted">
                  Récentes
                </li>
              )}
              {results.map((j, i) => (
                <li key={j.id}>
                  <button
                    type="button"
                    onMouseEnter={() => setActive(i)}
                    onClick={() => choose(j)}
                    className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left transition-colors ${
                      i === active ? "bg-brand/10" : "hover:bg-surface"
                    }`}
                  >
                    <span
                      className={`h-2 w-2 flex-shrink-0 rounded-full ${dotCls(
                        j.status,
                      )}`}
                    />
                    <span className="min-w-0 flex-1 truncate text-sm text-ink">
                      {meetingDisplayName(
                        j.label,
                        j.calendar?.subject,
                        j.id.slice(0, 8),
                      )}
                    </span>
                    <span className="flex-shrink-0 text-xs text-ink-muted">
                      {fmtDate(j.createdAt)}
                    </span>
                  </button>
                </li>
              ))}
            </>
          )}
        </ul>

        <div className="flex items-center justify-end gap-3 border-t border-surface-border px-4 py-2 text-[11px] text-ink-muted">
          <span>↑ ↓ naviguer</span>
          <span>↵ ouvrir</span>
        </div>
      </div>
    </div>
  );
}
