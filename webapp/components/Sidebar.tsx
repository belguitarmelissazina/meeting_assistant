"use client";

import { useEffect, useState } from "react";
import ThemeToggle from "@/components/ThemeToggle";
import JobHistory from "@/components/JobHistory";
import { useJobs } from "@/lib/useJobs";
import {
  useRecordingStatus,
  recordingElapsedSeconds,
  formatRecordingDuration,
  type RecordingStatus,
} from "@/lib/useRecordingStatus";
import { apiUrl } from "@/lib/api";

export type Nav = "agenda" | "reports" | "folders" | "capture";

interface Props {
  collapsed: boolean;
  onToggleCollapsed: () => void;
  /** Section active (page de fond, même si une réunion est ouverte par-dessus). */
  nav: Nav;
  /** Réunion ouverte (surligne la ligne « Récentes » correspondante). */
  selectedJobId: string | null;
  onNavigate: (n: Nav) => void;
  onNewMeeting: () => void;
  onSearch: () => void;
  onSelectJob: (id: string) => void;
  /** Une réunion vient d'être supprimée (ferme la fiche si elle était ouverte). */
  onDeleted?: (id: string) => void;
  onOpenSettings: () => void;
  /** Clic sur la pastille « Enregistrement en cours » → ramène l'utilisateur
   *  à la réunion qui enregistre, pour qu'il puisse voir le timer et stopper. */
  onResumeRecording: (status: RecordingStatus) => void;
}

export default function Sidebar({
  collapsed,
  onToggleCollapsed,
  nav,
  selectedJobId,
  onNavigate,
  onNewMeeting,
  onSearch,
  onSelectJob,
  onDeleted,
  onOpenSettings,
  onResumeRecording,
}: Props) {
  const { jobs, folders, reload } = useJobs();
  const [account, setAccount] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);
  const recording = useRecordingStatus();

  useEffect(() => {
    let cancel = false;
    const tick = async () => {
      try {
        const r = await fetch(apiUrl("/api/calendar/status"));
        const d = await r.json();
        if (cancel) return;
        setAccount(d?.account ?? null);
        setConnected(d?.state === "signed_in");
      } catch {
        /* ignore */
      }
    };
    tick();
    const id = setInterval(tick, 10000);
    return () => {
      cancel = true;
      clearInterval(id);
    };
  }, []);

  const recents = [...jobs]
    .sort((a, b) => (b.createdAt ?? 0) - (a.createdAt ?? 0))
    .slice(0, 6);

  return (
    <aside
      className={`relative flex h-screen flex-col border-r border-surface-border bg-surface-card transition-[width] duration-200 ease-out ${
        collapsed ? "w-[76px]" : "w-[288px]"
      }`}
    >
      {/* Header */}
      <div
        className={`flex items-center px-3 pt-4 pb-2 ${
          collapsed ? "justify-center" : "justify-between pl-4"
        }`}
      >
        {!collapsed && (
          <div className="min-w-0">
            <h1 className="truncate text-base font-semibold text-ink">
              Meeting Assistant
            </h1>
          </div>
        )}
        <button
          type="button"
          onClick={onToggleCollapsed}
          aria-label={collapsed ? "Déplier le menu" : "Replier le menu"}
          title={collapsed ? "Déplier" : "Replier"}
          className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg text-ink-muted transition-colors hover:bg-surface hover:text-ink"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="3" width="18" height="18" rx="2" />
            <line x1="9" y1="3" x2="9" y2="21" />
          </svg>
        </button>
      </div>

      {/* Pastille « enregistrement en cours » — visible partout (même
          quand l'utilisateur a navigué ailleurs pendant la captation) pour
          qu'il ne perde jamais le chemin de retour vers le bouton Stop. */}
      {recording.recording && (
        <RecordingChip
          status={recording}
          collapsed={collapsed}
          onClick={() => onResumeRecording(recording)}
        />
      )}

      {/* Actions principales */}
      <div className="space-y-1 px-3 pb-2 pt-1">
        {collapsed ? (
          <RailBtn label="Nouvelle réunion" onClick={onNewMeeting} accent>
            <PlusIcon />
          </RailBtn>
        ) : (
          <button
            type="button"
            onClick={onNewMeeting}
            className="flex w-full items-center gap-2 rounded-lg bg-brand px-3 py-3 text-[15px] font-medium text-white shadow-sm transition-all duration-200 hover:bg-brand-dark hover:-translate-y-0.5"
          >
            <PlusIcon />
            Nouvelle réunion
          </button>
        )}

        <NavRow
          collapsed={collapsed}
          active={false}
          onClick={onSearch}
          label="Rechercher"
          icon={<SearchIcon />}
        />
      </div>

      {/* Navigation */}
      <nav className="space-y-1 border-t border-surface-border px-3 py-3">
        <NavRow
          collapsed={collapsed}
          active={nav === "reports"}
          onClick={() => onNavigate("reports")}
          label="Comptes rendus"
          icon={<ReportIcon />}
        />
        <NavRow
          collapsed={collapsed}
          active={nav === "agenda"}
          onClick={() => onNavigate("agenda")}
          label="Agenda"
          icon={<CalendarIcon />}
        />
        <NavRow
          collapsed={collapsed}
          active={nav === "folders"}
          onClick={() => onNavigate("folders")}
          label="Dossiers"
          icon={<FolderIcon />}
        />
      </nav>

      {/* Récentes */}
      <div className="flex-1 overflow-y-auto px-3 pb-2">
        {!collapsed && recents.length > 0 && (
          <>
            <p className="mb-1 mt-1 px-2 text-xs font-semibold uppercase tracking-wider text-ink-muted">
              Récentes
            </p>
            <JobHistory
              flat
              jobs={recents}
              folders={folders}
              reload={reload}
              selectedId={selectedJobId}
              onSelect={onSelectJob}
              onDeleted={onDeleted}
              query=""
              day={null}
            />
          </>
        )}
      </div>

      {/* Footer */}
      <div className="border-t border-surface-border px-3 py-3">
        {collapsed ? (
          <div className="flex flex-col items-center gap-1">
            <RailBtn label="Paramètres" onClick={onOpenSettings}>
              <GearIcon />
            </RailBtn>
            <ThemeToggle />
          </div>
        ) : (
          <>
            <div className="mb-2 flex items-center gap-2.5 rounded-lg px-1 py-1">
              <span className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full bg-brand/10 text-sm font-semibold uppercase text-brand">
                {account ? account.charAt(0) : "?"}
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-[13px] font-medium text-ink">
                  {account ?? "Hors ligne"}
                </p>
                <p className="truncate text-xs text-ink-muted">
                  {connected ? "Agenda connecté" : "Agenda non connecté"}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={onOpenSettings}
                className="flex flex-1 items-center gap-2 rounded-lg px-2 py-2.5 text-sm font-medium text-ink-muted transition-colors hover:bg-surface hover:text-ink"
              >
                <GearIcon />
                Paramètres
              </button>
              <button
                type="button"
                onClick={() =>
                  window.open(
                    "mailto:genai@yele.fr?subject=" +
                      encodeURIComponent("Retour outil CR"),
                  )
                }
                title="Contactez-nous"
                aria-label="Contactez-nous"
                className="flex h-8 w-8 items-center justify-center rounded-lg text-ink-muted transition-colors hover:bg-surface hover:text-ink"
              >
                <MailIcon />
              </button>
              <ThemeToggle />
            </div>
            <p className="mt-2 px-1 text-[10px] text-ink-muted">v1.0</p>
          </>
        )}
      </div>
    </aside>
  );
}

/* ── Sous-composants ──────────────────────────────────────────────────── */

function RecordingChip({
  status,
  collapsed,
  onClick,
}: {
  status: RecordingStatus;
  collapsed: boolean;
  onClick: () => void;
}) {
  // Tick local 1s pour rafraîchir le timer (sinon il sauterait par 2s, vu
  // que useRecordingStatus poll à 2s).
  const [, setNow] = useState(Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);
  const seconds = recordingElapsedSeconds(status);
  const label = formatRecordingDuration(seconds);
  const title = `Enregistrement en cours — ${label}. Cliquez pour revenir à la réunion.`;

  if (collapsed) {
    return (
      <button
        type="button"
        onClick={onClick}
        title={title}
        aria-label={title}
        className="mx-auto mt-2 flex h-10 w-10 items-center justify-center rounded-full border border-brand/30 bg-brand/10 text-brand shadow-sm transition-all hover:bg-brand/15 hover:shadow-md"
      >
        <span className="h-2.5 w-2.5 rounded-full bg-brand animate-pulse" />
      </button>
    );
  }
  return (
    <button
      type="button"
      onClick={onClick}
      title={title}
      className="mx-3 mt-3 flex items-center gap-2.5 rounded-lg border border-brand/30 bg-brand/10 px-3 py-2 text-left text-sm text-brand transition-colors hover:bg-brand/15"
    >
      <span className="flex h-2.5 w-2.5 flex-shrink-0 items-center justify-center">
        <span className="h-2.5 w-2.5 rounded-full bg-brand animate-pulse" />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block text-[12px] font-semibold uppercase tracking-wider">
          Enregistrement
        </span>
        <span className="block truncate text-xs text-brand/90">
          {status.calendar?.subject ?? "Sans agenda"} · {label}
        </span>
      </span>
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="flex-shrink-0">
        <polyline points="9 18 15 12 9 6" />
      </svg>
    </button>
  );
}

function NavRow({
  collapsed,
  active,
  onClick,
  label,
  icon,
}: {
  collapsed: boolean;
  active: boolean;
  onClick: () => void;
  label: string;
  icon: React.ReactNode;
}) {
  if (collapsed) {
    return (
      <RailBtn label={label} onClick={onClick} active={active}>
        {icon}
      </RailBtn>
    );
  }
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-[15px] transition-colors ${
        active
          ? "bg-brand/10 font-medium text-brand"
          : "text-ink-muted hover:bg-surface hover:text-ink"
      }`}
    >
      {icon}
      {label}
    </button>
  );
}

function RailBtn({
  label,
  onClick,
  active,
  accent,
  children,
}: {
  label: string;
  onClick: () => void;
  active?: boolean;
  accent?: boolean;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={label}
      aria-label={label}
      className={`mx-auto flex h-10 w-10 items-center justify-center rounded-lg transition-colors ${
        accent
          ? "bg-brand text-white hover:bg-brand-dark"
          : active
          ? "bg-brand/10 text-brand"
          : "text-ink-muted hover:bg-surface hover:text-ink"
      }`}
    >
      {children}
    </button>
  );
}

/* ── Icônes ───────────────────────────────────────────────────────────── */

function PlusIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="5" y1="12" x2="19" y2="12" />
    </svg>
  );
}
function SearchIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="7" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  );
}
function ReportIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <polyline points="9 15 11 17 15 13" />
    </svg>
  );
}
function CalendarIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="4" width="18" height="18" rx="2" />
      <line x1="16" y1="2" x2="16" y2="6" />
      <line x1="8" y1="2" x2="8" y2="6" />
      <line x1="3" y1="10" x2="21" y2="10" />
    </svg>
  );
}
function FolderIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
    </svg>
  );
}
function GearIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33h0a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51h0a1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82v0a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </svg>
  );
}
function MailIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="4" width="20" height="16" rx="2" />
      <path d="m22 7-10 6L2 7" />
    </svg>
  );
}
