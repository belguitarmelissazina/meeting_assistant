"use client";

import { useEffect, useState } from "react";
import { apiUrl } from "@/lib/api";
import {
  useRecordingStatus,
  recordingElapsedSeconds,
  formatRecordingDuration,
} from "@/lib/useRecordingStatus";
import {
  type CalendarMeeting,
  type JobSummary,
  meetingDisplayName,
} from "@/lib/meetings";

/** Popup riche ancrée à l'icône tray (~340 × 480 px, sans bordure, design
 *  inspiré de OneDrive / Teams). Permet d'agir vite sans ouvrir l'app
 *  entière : voir l'enreg en cours, démarrer une nouvelle réunion,
 *  retomber sur un CR récent.
 *
 *  3 sections + footer icônes :
 *    1. Header  : nom de l'app + bouton ouvrir
 *    2. État    : enreg en cours (pulse rouge + timer + stop) OU prochaine
 *                 réunion d'agenda (pulse bleu + heure + start) OU CTA libre
 *    3. Récents : 4 derniers CR terminés (clic = ouvre l'app sur le CR)
 *    4. Footer  : Ouvrir / Quitter en icônes texte cliquables.
 */
export default function TrayPopup() {
  const status = useRecordingStatus(2000);
  const [upcoming, setUpcoming] = useState<CalendarMeeting[]>([]);
  const [jobs, setJobs] = useState<JobSummary[]>([]);
  const [busy, setBusy] = useState(false);

  // Poll agenda + jobs à 4 s (suffisant pour un popup éphémère).
  useEffect(() => {
    let cancel = false;
    const tick = async () => {
      try {
        const [evR, jbR] = await Promise.all([
          fetch(apiUrl("/api/calendar/upcoming?days=1")),
          fetch(apiUrl("/api/jobs")),
        ]);
        if (cancel) return;
        if (evR.ok) {
          const d = (await evR.json()) as { meetings: CalendarMeeting[] };
          setUpcoming(d.meetings ?? []);
        }
        if (jbR.ok) {
          const d = (await jbR.json()) as { jobs: JobSummary[] };
          setJobs(d.jobs ?? []);
        }
      } catch { /* backend KO → retentera */ }
    };
    tick();
    const id = setInterval(tick, 4000);
    return () => { cancel = true; clearInterval(id); };
  }, []);

  // Tick 1 s pour le timer de l'enregistrement courant.
  const [, setNow] = useState(Date.now());
  useEffect(() => {
    if (!status.recording) return;
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [status.recording]);

  const now = Date.now();
  const recordedEventIds = new Set(jobs.map((j) => j.calendar?.eventId).filter(Boolean));
  const nextMeeting = upcoming
    .map((m) => ({ m, t: Date.parse(m.start || "") }))
    .filter(({ m, t }) => Number.isFinite(t) && t > now - 60_000
                          && t < now + 60 * 60_000
                          && !recordedEventIds.has(m.id))
    .sort((a, b) => a.t - b.t)[0]?.m;

  const recents = [...jobs]
    .filter((j) => j.status === "done")
    .sort((a, b) => (b.createdAt ?? 0) - (a.createdAt ?? 0))
    .slice(0, 4);

  // Bridge IPC vers main process. TOUTES les actions (start, stop, ouvrir
  // l'app, quitter) délèguent au main — c'est lui qui pilote les
  // notifications Windows, l'auto-ouverture de la fenêtre et la logique
  // liveReportReady. Le popup ne fait QUE de l'UI, pas de fetch direct.
  type Bridge = {
    electronAPI?: {
      trayWindow?: {
        openMainApp?: (payload?: { meetingId?: string; jobId?: string }) => void;
        quitApp?: () => void;
        startRecording?: (eventId?: string | null) => void;
        stopRecording?: () => void;
      };
    };
  };
  const w = typeof window !== "undefined" ? (window as unknown as Bridge) : undefined;

  function startRecording(meeting?: CalendarMeeting) {
    setBusy(true);
    w?.electronAPI?.trayWindow?.startRecording?.(meeting?.id ?? null);
    // Le popup se cache de toute façon via le handler IPC côté main —
    // on libère busy au cas où on resterait visible (edge case).
    setTimeout(() => setBusy(false), 500);
  }

  function stopRecording() {
    setBusy(true);
    w?.electronAPI?.trayWindow?.stopRecording?.();
    setTimeout(() => setBusy(false), 500);
  }

  const openMainOnJob = (jobId: string) =>
    w?.electronAPI?.trayWindow?.openMainApp?.({ jobId });
  const openMain = () => w?.electronAPI?.trayWindow?.openMainApp?.();
  const quit = () => w?.electronAPI?.trayWindow?.quitApp?.();

  return (
    // Fenêtre Electron déjà sans bordure (frame:false) ET opaque (pas de
    // transparent:true — cassait les clics sous Windows). Pas besoin de
    // rounded-xl/border ici : la fenêtre OS gère son chrome (= aucun
    // chrome). On garde juste un layout flex sur la hauteur.
    <div className="flex h-screen flex-col bg-surface text-ink">
      {/* ── Header ──────────────────────────────────────────────── */}
      <header className="flex items-center gap-2 px-4 py-3 border-b border-surface-border bg-surface-card">
        <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-lg bg-brand text-white shadow-sm">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
            <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
            <line x1="12" y1="19" x2="12" y2="23" />
            <line x1="8" y1="23" x2="16" y2="23" />
          </svg>
        </div>
        <div className="min-w-0 flex-1">
          <h1 className="truncate text-sm font-semibold tracking-tight text-ink">
            Meeting Assistant
          </h1>
        </div>
        <button
          type="button"
          onClick={openMain}
          title="Ouvrir la fenêtre principale"
          aria-label="Ouvrir la fenêtre principale"
          className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-md text-ink-muted transition-colors hover:bg-surface hover:text-ink"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
            <polyline points="15 3 21 3 21 9" />
            <line x1="10" y1="14" x2="21" y2="3" />
          </svg>
        </button>
      </header>

      {/* ── Bloc principal : état courant ────────────────────────── */}
      <section className="px-4 py-4 border-b border-surface-border">
        {status.recording ? (
          <RecordingBlock
            subject={status.calendar?.subject ?? "Enregistrement hors agenda"}
            elapsed={formatRecordingDuration(recordingElapsedSeconds(status))}
            onStop={stopRecording}
            busy={busy}
          />
        ) : nextMeeting ? (
          <NextMeetingBlock
            meeting={nextMeeting}
            onStart={() => startRecording(nextMeeting)}
            busy={busy}
          />
        ) : (
          <NoActionBlock onStart={() => startRecording()} busy={busy} />
        )}
      </section>

      {/* ── Réunions récentes ────────────────────────────────────── */}
      <section className="flex-1 overflow-y-auto px-2 py-2">
        <p className="px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-ink-muted">
          Réunions récentes
        </p>
        {recents.length === 0 ? (
          <div className="px-2 py-4 text-center">
            <p className="text-xs text-ink-muted">
              Aucune réunion traitée pour l&apos;instant.
            </p>
          </div>
        ) : (
          <ul className="space-y-0.5">
            {recents.map((j) => (
              <li key={j.id}>
                <button
                  type="button"
                  onClick={() => openMainOnJob(j.id)}
                  className="group flex w-full items-center gap-2.5 rounded-md px-2 py-2 text-left transition-colors hover:bg-surface-card"
                >
                  <span className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-md bg-accent-green/10 text-accent-green">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                      <polyline points="14 2 14 8 20 8" />
                      <polyline points="9 13 11 15 15 11" />
                    </svg>
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-xs font-medium text-ink">
                      {meetingDisplayName(
                        j.label,
                        j.calendar?.subject,
                        `Réunion ${j.id.slice(0, 8)}`
                      )}
                    </p>
                    <p className="mt-0.5 text-[10px] text-ink-muted">
                      {j.createdAt
                        ? new Date(j.createdAt).toLocaleString("fr-FR", {
                            day: "numeric", month: "short", hour: "2-digit", minute: "2-digit",
                          })
                        : "—"}
                    </p>
                  </div>
                  <svg
                    className="flex-shrink-0 text-ink-muted/50 opacity-0 transition-opacity group-hover:opacity-100"
                    width="12" height="12" viewBox="0 0 24 24" fill="none"
                    stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"
                  >
                    <polyline points="9 18 15 12 9 6" />
                  </svg>
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* ── Footer : actions icônes ──────────────────────────────── */}
      <footer className="grid grid-cols-2 gap-1 border-t border-surface-border bg-surface-card px-2 py-2">
        <FooterBtn onClick={openMain} label="Ouvrir l'app">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="3" width="18" height="18" rx="2" />
            <line x1="3" y1="9" x2="21" y2="9" />
            <line x1="9" y1="21" x2="9" y2="9" />
          </svg>
        </FooterBtn>
        <FooterBtn onClick={quit} label="Quitter" danger>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
            <polyline points="16 17 21 12 16 7" />
            <line x1="21" y1="12" x2="9" y2="12" />
          </svg>
        </FooterBtn>
      </footer>
    </div>
  );
}

/* ── Sous-composants visuels ───────────────────────────────────── */

function RecordingBlock({
  subject, elapsed, onStop, busy,
}: { subject: string; elapsed: string; onStop: () => void; busy: boolean }) {
  return (
    <div className="rounded-lg border border-brand/30 bg-brand/5 p-3">
      <div className="mb-2 flex items-center gap-2">
        <span className="relative flex h-2.5 w-2.5">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-brand opacity-60" />
          <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-brand" />
        </span>
        <span className="text-[10px] font-semibold uppercase tracking-wider text-brand">
          Enregistrement · {elapsed}
        </span>
      </div>
      <p className="mb-3 truncate text-sm font-medium text-ink">{subject}</p>
      <button
        type="button"
        onClick={onStop}
        disabled={busy}
        className="flex w-full items-center justify-center gap-2 rounded-md bg-brand px-3 py-2 text-sm font-medium text-white shadow-sm transition-all hover:bg-brand-dark hover:shadow disabled:opacity-60"
      >
        <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor">
          <rect x="6" y="6" width="12" height="12" rx="1" />
        </svg>
        Arrêter et générer le compte rendu
      </button>
    </div>
  );
}

function NextMeetingBlock({
  meeting, onStart, busy,
}: { meeting: CalendarMeeting; onStart: () => void; busy: boolean }) {
  const d = meeting.start ? new Date(meeting.start) : null;
  const hh = d ? String(d.getHours()).padStart(2, "0") : "??";
  const mm = d ? String(d.getMinutes()).padStart(2, "0") : "??";
  const inMin = d ? Math.max(0, Math.round((d.getTime() - Date.now()) / 60000)) : 0;
  return (
    <div className="rounded-lg border border-accent-blue/30 bg-accent-blue/5 p-3">
      <div className="mb-2 flex items-center gap-2">
        <span className="flex h-5 w-5 flex-shrink-0 items-center justify-center rounded bg-accent-blue/15 text-accent-blue">
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="4" width="18" height="18" rx="2" />
            <line x1="16" y1="2" x2="16" y2="6" />
            <line x1="8" y1="2" x2="8" y2="6" />
            <line x1="3" y1="10" x2="21" y2="10" />
          </svg>
        </span>
        <span className="text-[10px] font-semibold uppercase tracking-wider text-accent-blue">
          {hh}:{mm} · {inMin > 0 ? `dans ${inMin} min` : "maintenant"}
        </span>
      </div>
      <p className="mb-3 truncate text-sm font-medium text-ink">
        {meeting.subject || "(sans objet)"}
      </p>
      <button
        type="button"
        onClick={onStart}
        disabled={busy}
        className="flex w-full items-center justify-center gap-2 rounded-md bg-accent-blue px-3 py-2 text-sm font-medium text-white shadow-sm transition-all hover:brightness-110 hover:shadow disabled:opacity-60"
      >
        <span className="h-2 w-2 rounded-full bg-white" />
        Démarrer l&apos;enregistrement
      </button>
    </div>
  );
}

function NoActionBlock({ onStart, busy }: { onStart: () => void; busy: boolean }) {
  return (
    <div>
      <div className="mb-3 flex items-start gap-2 text-ink-muted">
        <svg className="mt-0.5 flex-shrink-0" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="3" y="4" width="18" height="18" rx="2" />
          <line x1="16" y1="2" x2="16" y2="6" />
          <line x1="8" y1="2" x2="8" y2="6" />
          <line x1="3" y1="10" x2="21" y2="10" />
        </svg>
        <p className="text-xs">
          Aucune réunion d&apos;agenda imminente.
        </p>
      </div>
      <button
        type="button"
        onClick={onStart}
        disabled={busy}
        className="flex w-full items-center justify-center gap-2 rounded-md border border-surface-border bg-surface-card px-3 py-2 text-sm font-medium text-ink shadow-sm transition-colors hover:border-ink-muted hover:bg-surface disabled:opacity-60"
      >
        <span className="h-2 w-2 rounded-full bg-brand" />
        Nouvelle réunion (hors agenda)
      </button>
    </div>
  );
}

function FooterBtn({
  onClick, label, children, danger,
}: {
  onClick: () => void;
  label: string;
  children: React.ReactNode;
  danger?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex flex-col items-center gap-1 rounded-md px-2 py-2 text-[11px] font-medium transition-colors ${
        danger
          ? "text-ink-muted hover:bg-brand/10 hover:text-brand"
          : "text-ink-muted hover:bg-surface hover:text-ink"
      }`}
    >
      {children}
      {label}
    </button>
  );
}
