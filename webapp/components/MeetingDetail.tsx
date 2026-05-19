"use client";

import { useEffect, useState } from "react";
import JobPanel from "@/components/JobPanel";
import Recorder from "@/components/Recorder";
import Uploader from "@/components/Uploader";
import { apiUrl } from "../lib/api";
import {
  type TimelineItem,
  type JobCalendarSnapshot,
  attendeeNames,
  buildContexte,
  guessCompanies,
  meetingDisplayName,
  parseGraphDate,
  dateChip,
  fmtTime,
  daySection,
} from "../lib/meetings";

interface Props {
  item: TimelineItem;
  onBack: () => void;
  onJobCreated: (id: string) => void;
}

interface JobMeta {
  label?: string;
  createdAt?: number;
  calendar?: JobCalendarSnapshot | null;
}

export default function MeetingDetail({ item, onBack, onJobCreated }: Props) {
  // Job lié : soit déjà enregistré (item.jobId), soit créé ici via Recorder.
  const [jobId, setJobId] = useState<string | null>(item.jobId ?? null);
  // Affiché entre le clic « Arrêter » et la création du job (finalisation
  // backend) → écran clair « Génération du compte rendu ».
  const [generating, setGenerating] = useState(false);
  // Vraies métadonnées du job (label, date, snapshot agenda) — l'item peut
  // être un bouchon (sélection depuis le panneau). On va chercher la source.
  const [jobMeta, setJobMeta] = useState<JobMeta | null>(null);

  useEffect(() => {
    setJobId(item.jobId ?? null);
  }, [item.jobId]);

  useEffect(() => {
    if (!jobId) {
      setJobMeta(null);
      return;
    }
    let cancel = false;
    fetch(apiUrl(`/api/jobs/${jobId}`))
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (!cancel && d) {
          setJobMeta({
            label: d.label,
            createdAt: d.createdAt,
            calendar: d.calendar ?? null,
          });
        }
      })
      .catch(() => {
        /* ignore — l'entête retombe sur l'item */
      });
    return () => {
      cancel = true;
    };
  }, [jobId]);

  const m = item.meeting; // réunion d'agenda (présente si "upcoming")
  // Snapshot agenda : priorité au job réel, puis à l'item.
  const cal: JobCalendarSnapshot | null =
    jobMeta?.calendar ?? item.jobCalendar ?? null;

  const title =
    m?.subject ||
    meetingDisplayName(jobMeta?.label, cal?.subject, item.title);

  const headerDate =
    parseGraphDate(cal?.start) ??
    (jobMeta?.createdAt ? new Date(jobMeta.createdAt) : null) ??
    item.date;

  const location = m?.location ?? cal?.location ?? null;
  const organizer =
    m?.organizer.name ?? m?.organizer.address ?? cal?.organizer ?? null;
  const attendees: string[] = m
    ? m.attendees.map((a) => a.name).filter(Boolean)
    : cal?.attendees ?? [];
  const isOnline = m?.isOnline ?? false;
  const chip = dateChip(headerDate);

  function handleCreated(id: string) {
    setJobId(id);
    onJobCreated(id);
  }

  return (
    <div className="flex flex-col animate-fade-in">
      <button
        type="button"
        onClick={onBack}
        className="mb-5 inline-flex w-fit items-center gap-1.5 text-sm text-ink-muted transition-colors hover:text-ink"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <line x1="19" y1="12" x2="5" y2="12" />
          <polyline points="12 19 5 12 12 5" />
        </svg>
        Toutes les réunions
      </button>

      {/* Entête réunion */}
      <header className="mb-6 flex items-start gap-4">
        <div className="flex h-14 w-14 flex-shrink-0 flex-col items-center justify-center rounded-xl border border-surface-border bg-surface-card shadow-soft">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-brand">
            {chip.month}
          </span>
          <span className="text-xl font-bold leading-none text-ink">
            {chip.day}
          </span>
        </div>
        <div className="min-w-0 flex-1">
          <h1 className="text-2xl font-semibold tracking-tight text-ink">
            {title}
          </h1>
          <p className="mt-1 text-sm text-ink-muted">
            {daySection(headerDate)} · {fmtTime(headerDate)}
            {isOnline && (
              <span className="ml-2 rounded-full bg-accent-blue/10 px-2 py-0.5 text-[10px] font-medium text-accent-blue">
                Teams
              </span>
            )}
          </p>
        </div>
      </header>

      <div className="mb-6 grid grid-cols-1 gap-3 sm:grid-cols-2">
        {location && (
          <InfoRow label="Lieu / salle" value={location} />
        )}
        {organizer && (
          <InfoRow label="Organisateur" value={organizer} />
        )}
      </div>

      {attendees.length > 0 && (
        <div className="mb-7">
          <p className="mb-2 text-xs font-medium uppercase tracking-wider text-ink-muted">
            Participants ({attendees.length})
          </p>
          <div className="flex flex-wrap gap-1.5">
            {attendees.map((a, i) => (
              <span
                key={`${a}-${i}`}
                className="rounded-full border border-surface-border bg-surface-card px-3 py-1 text-xs text-ink"
              >
                {a}
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="border-t border-surface-border pt-6">
        {jobId ? (
          <JobPanel jobId={jobId} hideHeader />
        ) : generating ? (
          <GeneratingReport />
        ) : (
          <div className="space-y-5">
            <p className="text-sm text-ink-muted">
              Lancez l&apos;enregistrement : le compte rendu sera généré et
              rangé dans cette réunion.
            </p>
            <Recorder
              onJobCreated={handleCreated}
              onStopStart={() => setGenerating(true)}
              onStopFailed={() => setGenerating(false)}
              meeting={
                m
                  ? {
                      calendar: {
                        eventId: m.id,
                        subject: m.subject,
                        start: m.start ?? undefined,
                        end: m.end ?? undefined,
                        location: m.location ?? undefined,
                        organizer:
                          m.organizer.name ?? m.organizer.address ?? undefined,
                        attendees: m.attendees
                          .map((a) => a.name)
                          .filter(Boolean),
                      },
                      participants: attendeeNames(m),
                      entreprises: guessCompanies(m),
                      contexte: buildContexte(m),
                    }
                  : null
              }
            />
            <details className="text-sm">
              <summary className="cursor-pointer text-ink-muted hover:text-ink">
                Importer un fichier audio à la place
              </summary>
              <div className="mt-4">
                <Uploader onJobCreated={handleCreated} />
              </div>
            </details>
          </div>
        )}
      </div>
    </div>
  );
}

function GeneratingReport() {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center animate-fade-in">
      <span className="mb-6 h-12 w-12 animate-spin rounded-full border-[3px] border-surface-border border-t-brand" />
      <h2 className="text-xl font-semibold text-ink">
        Génération du compte rendu…
      </h2>
      <p className="mt-2 max-w-sm text-sm text-ink-muted">
        Finalisation de la transcription et rédaction de la synthèse. Cela
        peut prendre quelques instants — vous pouvez patienter ici.
      </p>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-surface-border bg-surface-card/60 px-3 py-2">
      <p className="text-[11px] font-medium uppercase tracking-wider text-ink-muted">
        {label}
      </p>
      <p className="mt-0.5 truncate text-sm text-ink" title={value}>
        {value}
      </p>
    </div>
  );
}
