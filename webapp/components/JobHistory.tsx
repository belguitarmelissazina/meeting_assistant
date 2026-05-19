"use client";

import { useState } from "react";
import { apiUrl } from "../lib/api";
import { meetingDisplayName } from "../lib/meetings";

export interface JobSummary {
  id: string;
  status: "draft" | "pending" | "queued" | "running" | "done" | "error";
  step: string;
  label?: string;
  createdAt?: number;
  audioAvailable?: boolean;
  folder?: string | null;
  calendar?: { subject?: string | null } | null;
}

interface Props {
  jobs: JobSummary[];
  folders: string[];
  /** Refetch jobs + folders (le propriétaire = Sidebar). */
  reload: () => void;
  selectedId: string | null;
  onSelect: (id: string) => void;
  onDeleted?: (id: string) => void;
  query: string;
  /** Jour sélectionné "YYYY-MM-DD" ou null. */
  day: string | null;
}

export function jobDayKey(ms?: number): string {
  if (!ms) return "";
  const d = new Date(ms);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(
    d.getDate(),
  ).padStart(2, "0")}`;
}

const NO_FOLDER = "::no-folder::"; // clé interne pour "Sans dossier"

export default function JobHistory({
  jobs,
  folders,
  reload,
  selectedId,
  onSelect,
  onDeleted,
  query,
  day,
}: Props) {
  const [confirming, setConfirming] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [renaming, setRenaming] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const [renameBusy, setRenameBusy] = useState(false);
  const [movingId, setMovingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [creatingFolder, setCreatingFolder] = useState(false);
  const [newFolder, setNewFolder] = useState("");
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());
  const [confirmFolder, setConfirmFolder] = useState<string | null>(null);

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

  async function handleDelete(id: string) {
    setDeleting(id);
    const ok = await call(`/api/jobs/${id}`, { method: "DELETE" });
    if (ok) {
      setConfirming(null);
      onDeleted?.(id);
    }
    setDeleting(null);
  }

  async function submitRename(id: string) {
    const label = renameValue.trim();
    if (!label) {
      setRenaming(null);
      return;
    }
    setRenameBusy(true);
    const ok = await call(`/api/jobs/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ label }),
    });
    if (ok) setRenaming(null);
    setRenameBusy(false);
  }

  async function moveTo(id: string, folder: string | null) {
    setMovingId(null);
    await call(`/api/jobs/${id}/folder`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ folder }),
    });
  }

  async function createFolder() {
    const name = newFolder.trim();
    if (!name) return;
    const ok = await call(`/api/folders`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });
    if (ok) {
      setNewFolder("");
      setCreatingFolder(false);
    }
  }

  async function deleteFolder(name: string) {
    const ok = await call(`/api/folders/${encodeURIComponent(name)}`, {
      method: "DELETE",
    });
    if (ok) setConfirmFolder(null);
  }

  // ── Filtrage ───────────────────────────────────────────────────────────
  const q = query.trim().toLowerCase();
  const match = (j: JobSummary) =>
    (!q ||
      meetingDisplayName(j.label, j.calendar?.subject, j.id)
        .toLowerCase()
        .includes(q)) &&
    (!day || jobDayKey(j.createdAt) === day);

  const visible = jobs.filter(match);
  const filtering = Boolean(q || day);

  // ── Regroupement par dossier ───────────────────────────────────────────
  const byFolder = new Map<string, JobSummary[]>();
  for (const j of visible) {
    const k = j.folder || NO_FOLDER;
    const arr = byFolder.get(k);
    if (arr) arr.push(j);
    else byFolder.set(k, [j]);
  }
  // compteur total (non filtré) par dossier → autorise la suppression
  const totalByFolder = new Map<string, number>();
  for (const j of jobs) {
    const k = j.folder || NO_FOLDER;
    totalByFolder.set(k, (totalByFolder.get(k) ?? 0) + 1);
  }

  const groups: { key: string; name: string | null; jobs: JobSummary[] }[] = [];
  const noFolderJobs = byFolder.get(NO_FOLDER) ?? [];
  if (noFolderJobs.length > 0 || (!filtering && jobs.length > 0)) {
    groups.push({ key: NO_FOLDER, name: null, jobs: noFolderJobs });
  }
  for (const f of folders) {
    const list = byFolder.get(f) ?? [];
    if (list.length > 0 || !filtering) {
      groups.push({ key: f, name: f, jobs: list });
    }
  }

  return (
    <div>
      {/* Barre dossiers */}
      <div className="mb-2 flex items-center justify-between px-1">
        <span className="text-[11px] font-semibold uppercase tracking-wider text-ink-muted">
          Historique
        </span>
        <button
          type="button"
          onClick={() => setCreatingFolder((v) => !v)}
          className="flex items-center gap-1 rounded px-1.5 py-0.5 text-[11px] text-accent-blue hover:bg-accent-blue/10"
        >
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
            <line x1="12" y1="11" x2="12" y2="17" />
            <line x1="9" y1="14" x2="15" y2="14" />
          </svg>
          Dossier
        </button>
      </div>

      {creatingFolder && (
        <div className="mb-2 flex items-center gap-1.5 px-1">
          <input
            autoFocus
            value={newFolder}
            onChange={(e) => setNewFolder(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") createFolder();
              if (e.key === "Escape") setCreatingFolder(false);
            }}
            placeholder="Nom du dossier"
            className="min-w-0 flex-1 rounded border border-accent-blue/40 bg-surface-card px-2 py-1 text-sm text-ink focus:border-accent-blue focus:outline-none"
          />
          <button
            type="button"
            onClick={createFolder}
            className="rounded px-2 py-1 text-[11px] font-semibold text-accent-blue hover:bg-accent-blue/10"
          >
            Créer
          </button>
        </div>
      )}

      {error && (
        <div className="mb-2 rounded-md border border-brand/30 bg-brand/5 px-3 py-2 text-xs text-brand">
          {error}
        </div>
      )}

      {jobs.length === 0 ? (
        <div className="px-3 py-6 text-center text-xs text-ink-muted">
          Aucune réunion pour l&apos;instant.
        </div>
      ) : groups.every((g) => g.jobs.length === 0) ? (
        <div className="px-3 py-6 text-center text-xs text-ink-muted">
          Aucun résultat.
        </div>
      ) : (
        <div className="space-y-1">
          {groups.map((g) => {
            const isOpen = !collapsed.has(g.key);
            const total = totalByFolder.get(g.key) ?? 0;
            return (
              <div key={g.key}>
                <div className="group/f flex items-center gap-1 px-1">
                  <button
                    type="button"
                    onClick={() =>
                      setCollapsed((s) => {
                        const n = new Set(s);
                        if (n.has(g.key)) n.delete(g.key);
                        else n.add(g.key);
                        return n;
                      })
                    }
                    className="flex min-w-0 flex-1 items-center gap-1.5 rounded px-1 py-1 text-left text-xs font-semibold text-ink-muted hover:text-ink"
                  >
                    <svg
                      width="12"
                      height="12"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      className={`transition-transform ${isOpen ? "rotate-90" : ""}`}
                    >
                      <polyline points="9 18 15 12 9 6" />
                    </svg>
                    {g.name === null ? (
                      <span>Sans dossier</span>
                    ) : (
                      <span className="flex items-center gap-1 truncate">
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
                        </svg>
                        <span className="truncate">{g.name}</span>
                      </span>
                    )}
                    <span className="text-ink-muted/70">{g.jobs.length}</span>
                  </button>
                  {g.name !== null &&
                    total === 0 &&
                    (confirmFolder === g.name ? (
                      <span className="flex items-center gap-1">
                        <button
                          type="button"
                          onClick={() => deleteFolder(g.name!)}
                          className="rounded px-1.5 py-0.5 text-[10px] font-semibold text-brand hover:bg-brand/10"
                        >
                          Suppr.
                        </button>
                        <button
                          type="button"
                          onClick={() => setConfirmFolder(null)}
                          className="rounded px-1.5 py-0.5 text-[10px] text-ink-muted hover:bg-surface"
                        >
                          ✕
                        </button>
                      </span>
                    ) : (
                      <button
                        type="button"
                        onClick={() => setConfirmFolder(g.name)}
                        title="Supprimer ce dossier vide"
                        className="flex h-6 w-6 items-center justify-center rounded text-ink-muted opacity-0 transition-opacity hover:bg-brand/10 hover:text-brand group-hover/f:opacity-100"
                      >
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <polyline points="3 6 5 6 21 6" />
                          <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
                        </svg>
                      </button>
                    ))}
                </div>

                {isOpen && (
                  <ul className="space-y-0.5">
                    {g.jobs.map((j) => (
                      <JobRow
                        key={j.id}
                        job={j}
                        active={j.id === selectedId}
                        folders={folders}
                        onSelect={onSelect}
                        renaming={renaming === j.id}
                        renameValue={renameValue}
                        setRenameValue={setRenameValue}
                        renameBusy={renameBusy}
                        startRename={() => {
                          setError(null);
                          setConfirming(null);
                          setRenaming(j.id);
                          setRenameValue(j.label || "");
                        }}
                        cancelRename={() => setRenaming(null)}
                        submitRename={() => submitRename(j.id)}
                        confirming={confirming === j.id}
                        deleting={deleting === j.id}
                        askDelete={() => setConfirming(j.id)}
                        cancelDelete={() => setConfirming(null)}
                        doDelete={() => handleDelete(j.id)}
                        menuOpen={movingId === j.id}
                        toggleMenu={() =>
                          setMovingId((v) => (v === j.id ? null : j.id))
                        }
                        moveTo={(f) => moveTo(j.id, f)}
                      />
                    ))}
                    {g.jobs.length === 0 && (
                      <li className="px-3 py-2 text-[11px] italic text-ink-muted/70">
                        Vide — glissez des réunions ici via « Déplacer ».
                      </li>
                    )}
                  </ul>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function JobRow(props: {
  job: JobSummary;
  active: boolean;
  folders: string[];
  onSelect: (id: string) => void;
  renaming: boolean;
  renameValue: string;
  setRenameValue: (v: string) => void;
  renameBusy: boolean;
  startRename: () => void;
  cancelRename: () => void;
  submitRename: () => void;
  confirming: boolean;
  deleting: boolean;
  askDelete: () => void;
  cancelDelete: () => void;
  doDelete: () => void;
  menuOpen: boolean;
  toggleMenu: () => void;
  moveTo: (folder: string | null) => void;
}) {
  const j = props.job;
  const canModify = j.status !== "queued" && j.status !== "running";

  return (
    <li>
      <div
        className={`group relative flex items-center gap-1.5 rounded-lg py-2 pr-2 transition-all duration-200 ${
          props.active
            ? "bg-brand/5 border-l-[3px] border-brand pl-[calc(0.75rem-3px)]"
            : "border-l-[3px] border-transparent pl-[calc(0.75rem-3px)] hover:bg-surface"
        }`}
      >
        {props.renaming ? (
          <div className="flex min-w-0 flex-1 items-center gap-2">
            <input
              autoFocus
              value={props.renameValue}
              onChange={(e) => props.setRenameValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") props.submitRename();
                if (e.key === "Escape") props.cancelRename();
              }}
              disabled={props.renameBusy}
              className="min-w-0 flex-1 rounded border border-accent-blue/40 bg-surface-card px-2 py-1 text-sm text-ink focus:border-accent-blue focus:outline-none"
            />
            <button
              type="button"
              onClick={props.submitRename}
              disabled={props.renameBusy}
              className="rounded px-2 py-1 text-[11px] font-semibold text-accent-blue hover:bg-accent-blue/10 disabled:opacity-60"
            >
              {props.renameBusy ? "…" : "OK"}
            </button>
            <button
              type="button"
              onClick={props.cancelRename}
              disabled={props.renameBusy}
              className="rounded px-2 py-1 text-[11px] text-ink-muted hover:bg-surface"
            >
              ✕
            </button>
          </div>
        ) : (
          <>
            <button
              type="button"
              onClick={() => props.onSelect(j.id)}
              className="flex min-w-0 flex-1 items-center text-left"
            >
              <div className="flex min-w-0 flex-1 items-center gap-2.5">
                <StatusIcon status={j.status} />
                <div className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-medium text-ink">
                    {meetingDisplayName(j.label, j.calendar?.subject, j.id.slice(0, 8))}
                  </span>
                  <span className="mt-0.5 block truncate text-xs text-ink-muted">
                    {formatDate(j.createdAt)} · {j.step}
                  </span>
                </div>
              </div>
            </button>

            {props.confirming ? (
              <div className="flex items-center gap-1">
                <button
                  type="button"
                  onClick={props.doDelete}
                  disabled={props.deleting}
                  className="rounded px-2 py-1 text-[11px] font-semibold text-brand hover:bg-brand/10 disabled:opacity-60"
                >
                  {props.deleting ? "…" : "Confirmer"}
                </button>
                <button
                  type="button"
                  onClick={props.cancelDelete}
                  disabled={props.deleting}
                  className="rounded px-2 py-1 text-[11px] text-ink-muted hover:bg-surface"
                >
                  Annuler
                </button>
              </div>
            ) : (
              <div
                className={`flex items-center gap-0.5 transition-opacity duration-150 ${
                  props.active || props.menuOpen
                    ? "opacity-100"
                    : "opacity-0 group-hover:opacity-100 focus-within:opacity-100"
                }`}
              >
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    if (canModify) props.toggleMenu();
                  }}
                  disabled={!canModify}
                  title="Déplacer vers un dossier"
                  className="flex h-7 w-7 items-center justify-center rounded text-ink-muted transition-colors hover:bg-accent-blue/10 hover:text-accent-blue disabled:cursor-not-allowed disabled:opacity-30"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
                  </svg>
                </button>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    if (canModify) props.startRename();
                  }}
                  disabled={!canModify}
                  title={canModify ? "Renommer" : "Traitement en cours"}
                  className="flex h-6 w-6 items-center justify-center rounded text-ink-muted transition-colors hover:bg-accent-blue/10 hover:text-accent-blue disabled:cursor-not-allowed disabled:opacity-30"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M12 20h9" />
                    <path d="M16.5 3.5a2.121 2.121 0 1 1 3 3L7 19l-4 1 1-4 12.5-12.5z" />
                  </svg>
                </button>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    if (canModify) props.askDelete();
                  }}
                  disabled={!canModify}
                  title={canModify ? "Supprimer cette réunion" : "Traitement en cours"}
                  className="flex h-7 w-7 items-center justify-center rounded text-ink-muted transition-colors hover:bg-brand/10 hover:text-brand disabled:cursor-not-allowed disabled:opacity-30"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="3 6 5 6 21 6" />
                    <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
                    <path d="M10 11v6" />
                    <path d="M14 11v6" />
                    <path d="M9 6V4a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2" />
                  </svg>
                </button>
              </div>
            )}

            {props.menuOpen && (
              <div className="absolute right-2 top-full z-20 mt-1 w-44 rounded-lg border border-surface-border bg-surface-card py-1 shadow-xl">
                <p className="px-3 py-1 text-[10px] font-semibold uppercase tracking-wider text-ink-muted">
                  Déplacer vers
                </p>
                <button
                  type="button"
                  onClick={() => props.moveTo(null)}
                  className={`block w-full px-3 py-1.5 text-left text-xs hover:bg-surface ${
                    !j.folder ? "font-semibold text-accent-blue" : "text-ink"
                  }`}
                >
                  Sans dossier
                </button>
                {props.folders.map((f) => (
                  <button
                    key={f}
                    type="button"
                    onClick={() => props.moveTo(f)}
                    className={`block w-full truncate px-3 py-1.5 text-left text-xs hover:bg-surface ${
                      j.folder === f
                        ? "font-semibold text-accent-blue"
                        : "text-ink"
                    }`}
                  >
                    {f}
                  </button>
                ))}
                {props.folders.length === 0 && (
                  <p className="px-3 py-1.5 text-[11px] italic text-ink-muted">
                    Aucun dossier. Créez-en un.
                  </p>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </li>
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
      <span title={title} aria-label={title} className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-accent-green/15 text-accent-green">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="20 6 9 17 4 12" />
        </svg>
      </span>
    );
  }
  if (status === "error") {
    return (
      <span title={title} aria-label={title} className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-brand/15 text-brand">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
          <line x1="18" y1="6" x2="6" y2="18" />
          <line x1="6" y1="6" x2="18" y2="18" />
        </svg>
      </span>
    );
  }
  if (status === "running" || status === "queued") {
    return (
      <span title={title} aria-label={title} className="flex h-5 w-5 shrink-0 items-center justify-center">
        <span className="h-2.5 w-2.5 rounded-full bg-accent-blue animate-pulse" />
      </span>
    );
  }
  if (status === "draft") {
    return (
      <span title={title} aria-label={title} className="flex h-5 w-5 shrink-0 items-center justify-center">
        <span className="h-2.5 w-2.5 rounded-full" style={{ background: "rgb(var(--accent-yellow))" }} />
      </span>
    );
  }
  return (
    <span title={title} aria-label={title} className="flex h-5 w-5 shrink-0 items-center justify-center">
      <span className="h-2.5 w-2.5 rounded-full border border-ink-muted/60" />
    </span>
  );
}

function formatDate(ms?: number): string {
  if (!ms) return "";
  const d = new Date(ms);
  return d.toLocaleDateString("fr-FR", { day: "2-digit", month: "short" });
}
