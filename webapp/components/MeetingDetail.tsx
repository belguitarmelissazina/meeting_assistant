"use client";

import { useEffect, useRef, useState } from "react";
import JobPanel from "@/components/JobPanel";
import Recorder from "@/components/Recorder";
import Uploader from "@/components/Uploader";
import TranscriptView from "@/components/TranscriptView";
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

export type Crumb = { label: string; onClick: () => void };

interface Props {
  item: TimelineItem;
  onBack: () => void;
  onJobCreated: (id: string) => void;
  /** Fil d'Ariane affiché à la place du bouton « Toutes les réunions ».
   *  Quand la réunion est ouverte depuis un drill-down (ex. Dossiers >
   *  réunions DIA), on affiche le chemin cliquable plutôt qu'un retour
   *  générique. */
  breadcrumbs?: Crumb[];
}

interface JobMeta {
  label?: string;
  createdAt?: number;
  calendar?: JobCalendarSnapshot | null;
  audioAvailable?: boolean;
  /** True quand on sait que turns.json existe pour ce job (UI peut activer
   *  l'onglet Transcript / mode côte-à-côte). Réunions anciennes : false. */
  hasTurns?: boolean;
}

/** Onglet actif dans MeetingDetail. Le Transcript ne peut être actif que
 *  s'il a été ouvert via le bouton « + Transcript » ; sinon on tombe sur
 *  le rapport par défaut. */
type ActiveTab = "report" | "transcript";
const TRANSCRIPT_OPEN_KEY = "meeting-transcript-tab-open";

export default function MeetingDetail({ item, onBack, onJobCreated, breadcrumbs }: Props) {
  // Job lié : soit déjà enregistré (item.jobId), soit créé ici via Recorder.
  const [jobId, setJobId] = useState<string | null>(item.jobId ?? null);
  // Affiché entre le clic « Arrêter » et la création du job (finalisation
  // backend) → écran clair « Génération du compte rendu ».
  const [generating, setGenerating] = useState(false);
  // Vraies métadonnées du job (label, date, snapshot agenda) — l'item peut
  // être un bouchon (sélection depuis le panneau). On va chercher la source.
  const [jobMeta, setJobMeta] = useState<JobMeta | null>(null);

  // Système d'onglets façon navigateur :
  //  - Le Compte rendu est TOUJOURS présent en onglet, c'est le contenu
  //    principal (non fermable).
  //  - Le Transcript est OPTIONNEL : ouvert via un bouton « + Transcript »,
  //    fermable via la croix sur l'onglet. État persisté en localStorage
  //    pour que l'utilisatrice retrouve son layout d'une réunion à l'autre.
  //  - L'onglet actif détermine ce qui s'affiche dans la zone principale.
  //    Quand on ferme le Transcript actif, on retombe sur le Compte rendu.
  const [transcriptTabOpen, setTranscriptTabOpenState] = useState(false);
  const [activeTab, setActiveTab] = useState<ActiveTab>("report");
  useEffect(() => {
    if (localStorage.getItem(TRANSCRIPT_OPEN_KEY) === "1") {
      setTranscriptTabOpenState(true);
    }
  }, []);
  const openTranscriptTab = () => {
    setTranscriptTabOpenState(true);
    setActiveTab("transcript");
    localStorage.setItem(TRANSCRIPT_OPEN_KEY, "1");
  };
  const closeTranscriptTab = () => {
    setTranscriptTabOpenState(false);
    setActiveTab("report");
    localStorage.setItem(TRANSCRIPT_OPEN_KEY, "0");
  };

  // Audio partagé entre JobPanel (lecteur visible) et TranscriptView (sync).
  // Le <audio> est mounté UNE SEULE FOIS au niveau MeetingDetail dès qu'on
  // a un job audio dispo — comme ça la TranscriptView peut s'y accrocher
  // (timeupdate, seek) même quand le lecteur n'est pas visuellement ouvert.
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [audioOpen, setAudioOpen] = useState(false);

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
      .then(async (d) => {
        if (!cancel && d) {
          // Ping turns.json pour savoir si la vue Transcript est dispo
          // (réunions d'avant la v0.4 → pas de turns.json conservé).
          let hasTurns = false;
          try {
            const tr = await fetch(apiUrl(`/api/jobs/${jobId}/turns`));
            if (tr.ok) {
              const td = await tr.json();
              hasTurns = Boolean(td?.hasTurns);
            }
          } catch { /* ignore */ }
          if (cancel) return;
          setJobMeta({
            label: d.label,
            createdAt: d.createdAt,
            calendar: d.calendar ?? null,
            audioAvailable: Boolean(d.audioAvailable),
            hasTurns,
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
      {breadcrumbs && breadcrumbs.length > 0 ? (
        <nav className="mb-5 flex items-center gap-1.5 text-sm">
          {breadcrumbs.map((c, i) => (
            <span key={i} className="flex items-center gap-1.5">
              <button
                type="button"
                onClick={c.onClick}
                className="text-ink-muted transition-colors hover:text-ink"
              >
                {c.label}
              </button>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-ink-muted/60">
                <polyline points="9 18 15 12 9 6" />
              </svg>
            </span>
          ))}
          <span className="font-medium text-ink truncate">{title}</span>
        </nav>
      ) : (
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
      )}

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

      {/* Barre d'onglets — visible seulement quand le job est terminé ET
          qu'on a un transcript par tours (vraies réunions enregistrées dans
          l'app, pas les uploads de transcript Teams).
          Compte rendu = toujours là ; Transcript = optionnel (bouton + pour
          ouvrir, croix sur l'onglet pour fermer). */}
      {jobId && jobMeta?.hasTurns && (
        <div className="mb-4 flex items-end gap-0 border-b border-surface-border">
          <TabPill
            active={activeTab === "report"}
            onClick={() => setActiveTab("report")}
            label="Compte rendu"
          />
          {transcriptTabOpen && (
            <TabPill
              active={activeTab === "transcript"}
              onClick={() => setActiveTab("transcript")}
              label="Transcript"
              onClose={closeTranscriptTab}
            />
          )}
          {!transcriptTabOpen && (
            <button
              type="button"
              onClick={openTranscriptTab}
              className="ml-2 mb-1 inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium text-ink-muted transition-colors hover:bg-surface hover:text-ink"
              title="Ouvrir le transcript dans un onglet"
            >
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="12" y1="5" x2="12" y2="19" />
                <line x1="5" y1="12" x2="19" y2="12" />
              </svg>
              Transcript
            </button>
          )}
        </div>
      )}

      <div className={jobId && jobMeta?.hasTurns ? "" : "border-t border-surface-border pt-6"}>
        {jobId ? (
          activeTab === "transcript" && transcriptTabOpen && jobMeta?.hasTurns ? (
            <TranscriptView
              jobId={jobId}
              attendees={attendees}
              audioRef={audioRef}
              onWantAudio={() => setAudioOpen(true)}
            />
          ) : (
            <JobPanel
              jobId={jobId}
              hideHeader
              audioRef={audioRef}
              audioOpen={audioOpen}
              onOpenAudio={() => setAudioOpen(true)}
              onCloseAudio={() => setAudioOpen(false)}
              onDeleted={() => {
                setJobId(null);
                setJobMeta(null);
                setGenerating(false);
              }}
            />
          )
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

      {/* Audio partagé : monté UNE FOIS pour que TranscriptView puisse s'y
          accrocher (timeupdate, seek) même quand le lecteur n'est pas
          visuellement ouvert. Le wrapper fixed n'est rendu que si audioOpen,
          mais l'élément <audio> reste accessible via le ref. */}
      {jobId && jobMeta?.audioAvailable && (
        <SharedAudioOverlay
          jobId={jobId}
          audioRef={audioRef}
          open={audioOpen}
          onClose={() => setAudioOpen(false)}
        />
      )}
    </div>
  );
}

/** Onglet façon navigateur : pastille en haut avec une croix de fermeture
 *  optionnelle (uniquement les onglets fermables — le Compte rendu ne l'est
 *  pas, c'est le contenu de base). L'onglet actif a un fond plein, les
 *  inactifs sont neutres. */
function TabPill({
  active, onClick, label, onClose,
}: {
  active: boolean;
  onClick: () => void;
  label: string;
  onClose?: () => void;
}) {
  return (
    <div
      className={`flex items-center gap-1 rounded-t-lg border-b-2 px-3 py-2 transition-colors ${
        active
          ? "border-brand bg-surface-card text-ink shadow-sm"
          : "border-transparent text-ink-muted hover:text-ink hover:bg-surface-card/50"
      }`}
    >
      <button
        type="button"
        onClick={onClick}
        className="text-sm font-medium"
      >
        {label}
      </button>
      {onClose && (
        <button
          type="button"
          onClick={(e) => {
            // Stop propagation pour ne pas activer l'onglet en même temps
            // que la fermeture (sinon clic X = active + ferme = ré-active
            // un autre onglet incohérent).
            e.stopPropagation();
            onClose();
          }}
          title="Fermer l'onglet"
          aria-label="Fermer l'onglet"
          className="ml-0.5 flex h-4 w-4 items-center justify-center rounded text-ink-muted/60 transition-colors hover:bg-brand/10 hover:text-brand"
        >
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      )}
    </div>
  );
}

/** Audio HTMLElement TOUJOURS monté quand un job audio est dispo + UI
 *  d'overlay visible seulement quand `open`. Pourquoi tout-le-temps-monté :
 *  TranscriptView attache un listener `timeupdate` au ref pour surligner
 *  le turn courant — il a besoin d'un élément vivant. Le `display:none`
 *  CSS ne désactive pas l'élément, juste son rendu visuel. */
function SharedAudioOverlay({
  jobId, audioRef, open, onClose,
}: {
  jobId: string;
  audioRef: React.RefObject<HTMLAudioElement | null>;
  open: boolean;
  onClose: () => void;
}) {
  return (
    <div
      className="pointer-events-none fixed bottom-24 right-0 z-40 flex justify-center px-4"
      style={{ left: "var(--sb-w, 0px)", display: open ? "flex" : "none" }}
    >
      <div className="pointer-events-auto flex w-full max-w-2xl items-center gap-3 rounded-xl border border-surface-border bg-surface-card/95 px-3 py-2 shadow-2xl backdrop-blur">
        <span className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-accent-blue/10 text-accent-blue">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M9 18V5l12-2v13" />
            <circle cx="6" cy="18" r="3" />
            <circle cx="18" cy="16" r="3" />
          </svg>
        </span>
        <audio
          ref={audioRef}
          key={jobId}
          controls
          preload="metadata"
          src={apiUrl(`/api/jobs/${jobId}/audio`)}
          className="h-9 min-w-0 flex-1"
        />
        <a
          href={apiUrl(`/api/jobs/${jobId}/audio`)}
          download
          title="Télécharger l'audio"
          className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full text-ink-muted transition-colors hover:bg-surface hover:text-accent-blue"
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="7 10 12 15 17 10" />
            <line x1="12" y1="15" x2="12" y2="3" />
          </svg>
        </a>
        <button
          type="button"
          onClick={onClose}
          title="Fermer le lecteur"
          className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full text-ink-muted transition-colors hover:bg-brand/10 hover:text-brand"
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>
    </div>
  );
}

function GeneratingReport() {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center animate-fade-in">
      <span className="mb-6 h-12 w-12 animate-spin rounded-full border-[3px] border-surface-border border-t-brand" />
      <h2 className="text-xl font-semibold text-ink">
        Génération du compte rendu en cours
      </h2>
      <p className="mt-3 max-w-md text-sm text-ink">
        Vous pouvez <span className="font-semibold">réduire la fenêtre</span> —
        une notification Windows vous préviendra dès que c&apos;est prêt.
      </p>
      <p className="mt-3 max-w-md text-xs text-ink-muted/80">
        Si vous quittez l&apos;application avant la fin, l&apos;enregistrement
        audio est conservé mais le compte rendu ne sera pas généré
        automatiquement. Vous pourrez relancer le traitement manuellement
        depuis <span className="font-medium text-ink">Comptes rendus</span>
        {" "}en cliquant sur cette réunion.
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
