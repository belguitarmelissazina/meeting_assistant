"use client";

import { useEffect, useState } from "react";
import JobHistory from "@/components/JobHistory";
import ThemeToggle from "@/components/ThemeToggle";

interface Props {
  open: boolean;
  onClose: () => void;
  selectedId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDeleted?: (id: string) => void;
}

export default function Sidebar({
  open,
  onClose,
  selectedId,
  onSelect,
  onNew,
  onDeleted,
}: Props) {
  const [query, setQuery] = useState("");

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        aria-hidden={!open}
        className={`fixed inset-0 z-30 bg-black/45 backdrop-blur-[2px] transition-opacity duration-200 ${
          open ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
      />

      {/* Panel */}
      <aside
        aria-hidden={!open}
        className={`fixed left-0 top-0 z-40 flex h-screen w-[320px] flex-col border-r border-surface-border bg-surface-card shadow-2xl transition-transform duration-250 ease-out ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {/* Brand + close */}
        <div className="px-5 pt-5 pb-4">
          <div className="flex items-center gap-3">
            <div
              className="h-9 w-9 rounded-xl shadow-soft ring-1 ring-black/5"
              style={{
                background:
                  "linear-gradient(135deg, rgb(var(--brand)), rgb(var(--accent-blue)))",
              }}
              aria-hidden
            />
            <div className="min-w-0 flex-1">
              <h1 className="truncate text-sm font-semibold text-ink">Réunions</h1>
              <p className="truncate text-xs text-ink-muted">
                Enregistrement · Synthèse
              </p>
            </div>
            <button
              type="button"
              onClick={onNew}
              aria-label="Nouvelle réunion"
              title="Nouvelle réunion"
              className="flex h-8 w-8 items-center justify-center rounded-lg text-ink-muted transition-colors hover:bg-surface hover:text-ink"
            >
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 20h9" />
                <path d="M16.5 3.5a2.121 2.121 0 1 1 3 3L7 19l-4 1 1-4 12.5-12.5z" />
              </svg>
            </button>
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

        {/* Primary CTA */}
        <div className="px-4 pb-3">
          <button
            type="button"
            onClick={onNew}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-brand px-4 py-2.5 text-sm font-medium text-white shadow-sm transition-all duration-200 hover:bg-brand-dark hover:shadow-md hover:-translate-y-0.5 active:translate-y-0"
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            Nouvelle réunion
          </button>
        </div>

        {/* Search */}
        <div className="px-4 pb-3">
          <div className="relative">
            <svg
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-muted"
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <circle cx="11" cy="11" r="7" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Rechercher une réunion…"
              className="w-full rounded-lg border border-surface-border bg-surface py-2 pl-9 pr-3 text-sm text-ink placeholder:text-ink-muted/60 transition focus:border-accent-blue focus:outline-none focus:ring-2 focus:ring-accent-blue/20"
            />
          </div>
        </div>

        {/* History */}
        <div className="flex-1 overflow-y-auto px-2 pb-3">
          <JobHistory
            selectedId={selectedId}
            onSelect={onSelect}
            onDeleted={onDeleted}
            filter={query}
          />
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-surface-border px-4 py-3">
          <span className="text-[11px] text-ink-muted">v1.0</span>
          <ThemeToggle />
        </div>
      </aside>
    </>
  );
}
