"use client";

import { useEffect, useState } from "react";
import { apiUrl } from "../lib/api";

export interface JobSummary {
  id: string;
  status: "draft" | "pending" | "queued" | "running" | "done" | "error";
  step: string;
  label?: string;
  createdAt?: number;
  audioAvailable?: boolean;
}

interface Props {
  selectedId: string | null;
  onSelect: (id: string) => void;
  onDeleted?: (id: string) => void;
  filter?: string;
}

export default function JobHistory({ selectedId, onSelect, onDeleted, filter }: Props) {
  const [jobs, setJobs] = useState<JobSummary[]>([]);
  const [confirming, setConfirming] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [renaming, setRenaming] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const [renameBusy, setRenameBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = async () => {
    try {
      const r = await fetch(apiUrl("/api/jobs"));
      if (!r.ok) return;
      const data = (await r.json()) as { jobs: JobSummary[] };
      setJobs(data.jobs ?? []);
    } catch {
      /* ignore */
    }
  };

  useEffect(() => {
    let cancel = false;
    const tick = async () => {
      if (cancel) return;
      await refresh();
    };
    tick();
    const id = setInterval(tick, 2000);
    return () => {
      cancel = true;
      clearInterval(id);
    };
  }, []);

  async function handleDelete(id: string) {
    setError(null);
    setDeleting(id);
    try {
      const r = await fetch(apiUrl(`/api/jobs/${id}`), { method: "DELETE" });
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
      setConfirming(null);
      if (onDeleted) onDeleted(id);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur");
    } finally {
      setDeleting(null);
    }
  }

  function startRename(job: JobSummary) {
    setError(null);
    setConfirming(null);
    setRenaming(job.id);
    setRenameValue(job.label || "");
  }

  async function submitRename(id: string) {
    const label = renameValue.trim();
    if (!label) {
      setRenaming(null);
      return;
    }
    setError(null);
    setRenameBusy(true);
    try {
      const r = await fetch(apiUrl(`/api/jobs/${id}`), {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ label }),
      });
      if (!r.ok) {
        const msg = await r.text();
        throw new Error(msg || "Renommage impossible");
      }
      setRenaming(null);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur");
    } finally {
      setRenameBusy(false);
    }
  }

  const q = (filter || "").trim().toLowerCase();
  const visibleJobs = q
    ? jobs.filter((j) => (j.label || j.id).toLowerCase().includes(q))
    : jobs;

  if (jobs.length === 0) {
    return (
      <div className="px-3 py-6 text-center text-xs text-ink-muted">
        Aucune réunion pour l'instant.
      </div>
    );
  }

  if (visibleJobs.length === 0) {
    return (
      <div className="px-3 py-6 text-center text-xs text-ink-muted">
        Aucun résultat pour « {filter} ».
      </div>
    );
  }

  return (
    <div>
      {error && (
        <div className="mb-3 rounded-md border border-brand/30 bg-brand/5 px-3 py-2 text-xs text-brand">
          {error}
        </div>
      )}
      <ul className="space-y-0.5">
        {visibleJobs.map((j) => {
          const active = j.id === selectedId;
          const isConfirming = confirming === j.id;
          const isDeleting = deleting === j.id;
          const isRenaming = renaming === j.id;
          const canModify = j.status !== "queued" && j.status !== "running";
          return (
            <li key={j.id}>
              <div
                className={`group flex items-center gap-1.5 rounded-lg py-2 pr-3 transition-all duration-200 ${
                  active
                    ? "bg-brand/5 border-l-[3px] border-brand pl-[calc(0.75rem-3px)]"
                    : "border-l-[3px] border-transparent pl-[calc(0.75rem-3px)] hover:bg-surface"
                }`}
              >
                {isRenaming ? (
                  <div className="flex min-w-0 flex-1 items-center gap-2">
                    <input
                      autoFocus
                      type="text"
                      value={renameValue}
                      onChange={(e) => setRenameValue(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") submitRename(j.id);
                        if (e.key === "Escape") setRenaming(null);
                      }}
                      disabled={renameBusy}
                      className="min-w-0 flex-1 rounded border border-accent-blue/40 bg-surface-card px-2 py-1 text-sm text-ink focus:border-accent-blue focus:outline-none"
                    />
                    <button
                      type="button"
                      onClick={() => submitRename(j.id)}
                      disabled={renameBusy}
                      className="rounded px-2 py-1 text-[11px] font-semibold text-accent-blue hover:bg-accent-blue/10 disabled:opacity-60"
                    >
                      {renameBusy ? "…" : "OK"}
                    </button>
                    <button
                      type="button"
                      onClick={() => setRenaming(null)}
                      disabled={renameBusy}
                      className="rounded px-2 py-1 text-[11px] text-ink-muted hover:bg-surface"
                    >
                      ✕
                    </button>
                  </div>
                ) : (
                  <>
                    <button
                      type="button"
                      onClick={() => onSelect(j.id)}
                      className="flex min-w-0 flex-1 items-center text-left"
                    >
                      <div className="flex min-w-0 flex-1 items-center gap-2.5">
                        <StatusIcon status={j.status} />
                        <div className="min-w-0 flex-1">
                          <span className="block truncate text-sm font-medium text-ink">
                            {j.label || j.id.slice(0, 8)}
                          </span>
                          <span className="mt-0.5 block truncate text-xs text-ink-muted">
                            {formatDate(j.createdAt)} · {j.step}
                          </span>
                        </div>
                      </div>
                    </button>

                    {isConfirming ? (
                      <div className="flex items-center gap-1">
                        <button
                          type="button"
                          onClick={() => handleDelete(j.id)}
                          disabled={isDeleting}
                          className="rounded px-2 py-1 text-[11px] font-semibold text-brand hover:bg-brand/10 disabled:opacity-60"
                        >
                          {isDeleting ? "…" : "Confirmer"}
                        </button>
                        <button
                          type="button"
                          onClick={() => setConfirming(null)}
                          disabled={isDeleting}
                          className="rounded px-2 py-1 text-[11px] text-ink-muted hover:bg-surface"
                        >
                          Annuler
                        </button>
                      </div>
                    ) : (
                      <div
                        className={`flex items-center gap-0.5 transition-opacity duration-150 ${
                          active ? "opacity-100" : "opacity-0 group-hover:opacity-100 focus-within:opacity-100"
                        }`}
                      >
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            if (canModify) startRename(j);
                          }}
                          disabled={!canModify}
                          title={
                            canModify
                              ? "Renommer"
                              : "Traitement en cours"
                          }
                          className="flex h-6 w-6 items-center justify-center rounded text-ink-muted transition-colors hover:bg-accent-blue/10 hover:text-accent-blue disabled:cursor-not-allowed disabled:opacity-30"
                        >
                          <svg
                            width="14"
                            height="14"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          >
                            <path d="M12 20h9" />
                            <path d="M16.5 3.5a2.121 2.121 0 1 1 3 3L7 19l-4 1 1-4 12.5-12.5z" />
                          </svg>
                        </button>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            if (canModify) setConfirming(j.id);
                          }}
                          disabled={!canModify}
                          title={
                            canModify
                              ? "Supprimer cette réunion"
                              : "Traitement en cours"
                          }
                          className="flex h-7 w-7 items-center justify-center rounded text-ink-muted transition-colors hover:bg-brand/10 hover:text-brand disabled:cursor-not-allowed disabled:opacity-30"
                        >
                          <svg
                            width="14"
                            height="14"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          >
                            <polyline points="3 6 5 6 21 6" />
                            <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
                            <path d="M10 11v6" />
                            <path d="M14 11v6" />
                            <path d="M9 6V4a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2" />
                          </svg>
                        </button>
                      </div>
                    )}
                  </>
                )}
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function StatusIcon({ status }: { status: JobSummary["status"] }) {
  const titles: Record<JobSummary["status"], string> = {
    draft: "À traiter",
    pending: "En attente",
    queued: "En file",
    running: "En cours",
    done: "Terminé",
    error: "Erreur",
  };
  const title = titles[status];

  if (status === "done") {
    return (
      <span
        title={title}
        aria-label={title}
        className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-accent-green/15 text-accent-green"
      >
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="20 6 9 17 4 12" />
        </svg>
      </span>
    );
  }

  if (status === "error") {
    return (
      <span
        title={title}
        aria-label={title}
        className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-brand/15 text-brand"
      >
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
          <line x1="18" y1="6" x2="6" y2="18" />
          <line x1="6" y1="6" x2="18" y2="18" />
        </svg>
      </span>
    );
  }

  if (status === "running" || status === "queued") {
    return (
      <span
        title={title}
        aria-label={title}
        className="flex h-5 w-5 shrink-0 items-center justify-center"
      >
        <span className="h-2.5 w-2.5 rounded-full bg-accent-blue animate-pulse" />
      </span>
    );
  }

  if (status === "draft") {
    return (
      <span
        title={title}
        aria-label={title}
        className="flex h-5 w-5 shrink-0 items-center justify-center"
      >
        <span
          className="h-2.5 w-2.5 rounded-full"
          style={{ background: "rgb(var(--accent-yellow))" }}
        />
      </span>
    );
  }

  // pending
  return (
    <span
      title={title}
      aria-label={title}
      className="flex h-5 w-5 shrink-0 items-center justify-center"
    >
      <span className="h-2.5 w-2.5 rounded-full border border-ink-muted/60" />
    </span>
  );
}

function formatDate(ms?: number): string {
  if (!ms) return "";
  const d = new Date(ms);
  return d.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
}
