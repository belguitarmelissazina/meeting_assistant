"use client";

import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import ReportEditor, { type SaveState } from "./ReportEditor";
import { apiUrl } from "../lib/api";
import { consumeCalendarPrefill } from "../lib/calendarPrefill";

interface Props {
  jobId: string | null;
  /** Masque l'entête interne (titre/statut) quand un parent affiche déjà
   *  l'entête de la réunion (cas MeetingDetail). */
  hideHeader?: boolean;
}

interface MeetingCtx {
  participants?: string;
  entreprises?: string;
  contexte?: string;
}

interface JobStatus {
  id: string;
  status: "draft" | "pending" | "queued" | "running" | "done" | "error";
  step: string;
  label?: string;
  source?: "audio" | "transcript";
  createdAt?: number;
  audioAvailable?: boolean;
  reportMarkdown?: string;
  reportDocxAvailable?: boolean;
  transcriptAvailable?: boolean;
  error?: string;
  context?: MeetingCtx;
}

export default function JobPanel({ jobId, hideHeader }: Props) {
  const [job, setJob] = useState<JobStatus | null>(null);
  const [saveState, setSaveState] = useState<SaveState>({ kind: "idle" });
  // Mini-lecteur audio fixé en bas (overlay) — fermé par défaut pour que le
  // compte rendu soit l'élément principal de la page.
  const [audioOpen, setAudioOpen] = useState(false);

  useEffect(() => {
    if (!jobId) {
      setJob(null);
      return;
    }
    let cancel = false;
    const tick = async () => {
      try {
        const r = await fetch(apiUrl(`/api/jobs/${jobId}`));
        if (!r.ok) return;
        const data = (await r.json()) as JobStatus;
        if (!cancel) setJob(data);
      } catch {
        /* ignore */
      }
    };
    tick();
    const id = setInterval(tick, 1500);
    return () => {
      cancel = true;
      clearInterval(id);
    };
  }, [jobId]);

  useEffect(() => {
    setSaveState({ kind: "idle" });
    setAudioOpen(false);
  }, [jobId]);

  if (!jobId || !job) {
    return null;
  }

  const isDraft = job.status === "draft";
  const isDone = job.status === "done";

  return (
    <div className="flex flex-col animate-fade-in">
      {hideHeader ? (
        <div className="mb-6 flex items-center justify-between gap-4">
          <p className="flex items-center gap-2 text-sm text-ink-muted">
            <StatusDot status={job.status} />
            <span>{isDone ? "Compte-rendu prêt" : job.step}</span>
          </p>
          {isDone && <TopActions job={job} saveState={saveState} onPlayAudio={() => setAudioOpen(true)} />}
        </div>
      ) : (
        <header className="mb-6 flex items-start justify-between gap-6">
          <div className="min-w-0 flex-1">
            <h1 className="truncate text-3xl font-semibold tracking-tight text-ink">
              {job.label || `Réunion ${job.id.slice(0, 8)}`}
            </h1>
            <p className="mt-1.5 flex items-center gap-2 text-sm text-ink-muted">
              <StatusDot status={job.status} />
              <span>{isDone ? "Compte-rendu prêt" : job.step}</span>
            </p>
          </div>
          {isDone && <TopActions job={job} saveState={saveState} onPlayAudio={() => setAudioOpen(true)} />}
        </header>
      )}

      {!isDraft && !isDone && (
        <div className="mb-6">
          <ProgressBar status={job.status} step={job.step} source={job.source} />
        </div>
      )}

      {isDraft ? (
        <>
          {job.audioAvailable && <SlimAudio jobId={job.id} />}
          <DraftForm jobId={job.id} />
        </>
      ) : (
        <>
          {isDone && job.reportMarkdown !== undefined ? (
            <ReportEditor
              key={job.id}
              jobId={job.id}
              initialMarkdown={job.reportMarkdown ?? ""}
              onStateChange={setSaveState}
            />
          ) : (
            <ReportView md={job.reportMarkdown} status={job.status} />
          )}

          {job.status === "error" && (
            <div className="mt-6 rounded-lg border border-brand/30 bg-brand/5 px-4 py-3 text-sm text-brand">
              {job.error ?? "Échec inconnu"}
            </div>
          )}
        </>
      )}

      {isDone && job.audioAvailable && audioOpen && (
        <div className="pointer-events-none fixed inset-x-0 bottom-0 z-40 flex justify-center px-4 pb-4">
          <div className="pointer-events-auto flex w-full max-w-2xl items-center gap-3 rounded-xl border border-surface-border bg-surface-card/95 px-3 py-2 shadow-2xl backdrop-blur">
            <span className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-accent-blue/10 text-accent-blue">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M9 18V5l12-2v13" />
                <circle cx="6" cy="18" r="3" />
                <circle cx="18" cy="16" r="3" />
              </svg>
            </span>
            <audio
              key={job.id}
              controls
              preload="metadata"
              src={apiUrl(`/api/jobs/${job.id}/audio`)}
              className="h-9 min-w-0 flex-1"
            />
            <a
              href={apiUrl(`/api/jobs/${job.id}/audio`)}
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
              onClick={() => setAudioOpen(false)}
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
      )}
    </div>
  );
}

function StatusDot({ status }: { status: JobStatus["status"] }) {
  const map = {
    draft: "bg-accent-blue",
    pending: "bg-ink-muted/60",
    queued: "bg-accent-blue animate-pulse",
    running: "bg-accent-blue animate-pulse",
    done: "bg-accent-green",
    error: "bg-brand",
  } as const;
  return (
    <span
      aria-hidden
      className={`h-2 w-2 rounded-full ${map[status]}`}
    />
  );
}

function TopActions({
  job,
  saveState,
  onPlayAudio,
}: {
  job: JobStatus;
  saveState: SaveState;
  onPlayAudio: () => void;
}) {
  // Les fichiers (compte_rendu.docx, transcript.txt) sont déjà dans le
  // dossier de la réunion (Documents/Réunions/…) → pas de bouton de
  // téléchargement ici. Seule la lecture audio reste utile.
  return (
    <div className="flex items-center gap-2">
      <SaveStatusPill state={saveState} />
      {job.audioAvailable && (
        <button
          type="button"
          onClick={onPlayAudio}
          title="Écouter l'enregistrement"
          aria-label="Écouter l'enregistrement"
          className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-surface-border bg-surface-card text-ink-muted shadow-sm transition-all duration-200 hover:text-accent-blue hover:border-accent-blue hover:shadow-md"
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M3 18v-6a9 9 0 0 1 18 0v6" />
            <path d="M21 19a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3z" />
            <path d="M3 19a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2H3z" />
          </svg>
        </button>
      )}
    </div>
  );
}

function SaveStatusPill({ state }: { state: SaveState }) {
  if (state.kind === "idle") {
    return (
      <span className="hidden text-xs text-ink-muted sm:inline">
        Auto-enregistrement actif
      </span>
    );
  }
  if (state.kind === "saving") {
    return (
      <span className="flex items-center gap-1.5 text-xs text-ink-muted">
        <span className="h-1.5 w-1.5 rounded-full bg-accent-blue animate-pulse" />
        Enregistrement…
      </span>
    );
  }
  if (state.kind === "error") {
    return (
      <span className="text-xs text-brand">Erreur : {state.message}</span>
    );
  }
  return (
    <span className="hidden text-xs text-ink-muted sm:inline">
      Enregistré à{" "}
      {state.at.toLocaleTimeString("fr-FR", {
        hour: "2-digit",
        minute: "2-digit",
      })}
    </span>
  );
}

function SlimAudio({ jobId }: { jobId: string }) {
  return (
    <section className="mb-5 flex items-center gap-3 rounded-xl border border-surface-border bg-surface-card/60 px-3 py-2 shadow-soft backdrop-blur-sm">
      <span className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-accent-blue/10 text-accent-blue">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M9 18V5l12-2v13" />
          <circle cx="6" cy="18" r="3" />
          <circle cx="18" cy="16" r="3" />
        </svg>
      </span>
      <audio
        key={jobId}
        controls
        preload="metadata"
        src={apiUrl(`/api/jobs/${jobId}/audio`)}
        className="min-w-0 flex-1 h-8"
      />
    </section>
  );
}

function DraftForm({ jobId }: { jobId: string }) {
  // Prefill « one-shot » si l'utilisateur est venu d'une réunion du
  // calendrier. Consommé une seule fois au montage (useState lazy init).
  const [prefill] = useState(() => consumeCalendarPrefill());
  const [participants, setParticipants] = useState(prefill?.participants ?? "");
  const [entreprises, setEntreprises] = useState(prefill?.entreprises ?? "");
  const [contexte, setContexte] = useState(prefill?.contexte ?? "");
  const [llm, setLlm] = useState<"local" | "mistral">("local");
  const [mistralKeySet, setMistralKeySet] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(apiUrl("/api/settings"))
      .then((r) => r.json())
      .then((data) => setMistralKeySet(Boolean(data?.mistralKeySet)))
      .catch(() => setMistralKeySet(false));
  }, []);

  async function submit() {
    setError(null);
    if (llm === "mistral" && !mistralKeySet) {
      setError(
        "Clé API Mistral requise. Ouvre les paramètres pour la renseigner, ou repasse en Local."
      );
      return;
    }
    setBusy(true);
    try {
      const r = await fetch(apiUrl(`/api/jobs/${jobId}/process`), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ participants, entreprises, contexte, llm }),
      });
      if (!r.ok) throw new Error(await r.text());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-1 flex-col">
      <p className="mb-5 text-sm text-ink-muted">
        Écoutez l&apos;enregistrement, renseignez les informations, puis lancez le traitement.
      </p>

      {prefill && (
        <div className="mb-5 flex items-start gap-2 rounded-lg border border-accent-blue/30 bg-accent-blue/5 px-3 py-2.5 text-xs text-ink-muted">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mt-0.5 flex-shrink-0 text-accent-blue">
            <rect x="3" y="4" width="18" height="18" rx="2" />
            <line x1="16" y1="2" x2="16" y2="6" />
            <line x1="8" y1="2" x2="8" y2="6" />
            <line x1="3" y1="10" x2="21" y2="10" />
          </svg>
          <span>
            Pré-rempli depuis votre réunion{" "}
            <span className="font-medium text-ink">« {prefill.subject} »</span>.
            Vérifiez et ajustez si besoin.
          </span>
        </div>
      )}

      <div className="mb-5">
        <label className="mb-1.5 flex items-center justify-between text-sm font-semibold text-ink">
          <span>Contexte de la réunion</span>
          <span className="text-xs text-ink-muted font-normal">
            Sujet, enjeux, décisions attendues…
          </span>
        </label>
        <textarea
          rows={5}
          value={contexte}
          onChange={(e) => setContexte(e.target.value)}
          placeholder="Revue hebdo produit — focus sur le lancement Q2 et les blocages identifiés."
          className="w-full rounded-lg border border-surface-border bg-surface-card px-3 py-2.5 text-sm text-ink placeholder:text-ink-muted/60 transition focus:border-accent-blue focus:outline-none focus:ring-2 focus:ring-accent-blue/20"
        />
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Field
          label="Participants"
          hint="Séparés par des virgules"
          value={participants}
          onChange={setParticipants}
          placeholder="Alice Dupont, Marc Lemoine"
        />
        <Field
          label="Entreprises"
          hint="Organisations impliquées"
          value={entreprises}
          onChange={setEntreprises}
          placeholder="Yele Consulting, RTE"
        />
      </div>

      <div className="mt-3">
        <LlmSelector value={llm} onChange={setLlm} mistralKeySet={mistralKeySet} />
      </div>

      {error && (
        <div className="mt-4 rounded-md border border-brand/30 bg-brand/5 px-4 py-3 text-sm text-brand">
          {error}
        </div>
      )}

      <div className="mt-6 border-t border-surface-border pt-5">
        <button
          type="button"
          onClick={submit}
          disabled={busy}
          className="btn-primary w-full justify-center disabled:opacity-60"
        >
          {busy ? "Envoi…" : "Lancer le traitement"}
        </button>
      </div>
    </div>
  );
}

function LlmSelector({
  value,
  onChange,
  mistralKeySet,
}: {
  value: "local" | "mistral";
  onChange: (v: "local" | "mistral") => void;
  mistralKeySet: boolean;
}) {
  return (
    <div className="rounded-lg border border-surface-border bg-surface-card p-1">
      <div className="mb-2 px-3 pt-2 text-xs font-medium text-ink-muted">
        Moteur de compte rendu
      </div>
      <div className="grid grid-cols-2 gap-1">
        <LlmOption
          active={value === "local"}
          onClick={() => onChange("local")}
          title="Local"
          subtitle="Modèle embarqué, offline"
        />
        <LlmOption
          active={value === "mistral"}
          onClick={() => onChange("mistral")}
          title="Mistral Large"
          subtitle={
            mistralKeySet ? "API cloud, rapide" : "Clé API requise (paramètres)"
          }
          warning={value === "mistral" && !mistralKeySet}
        />
      </div>
    </div>
  );
}

function LlmOption({
  active,
  onClick,
  title,
  subtitle,
  warning,
}: {
  active: boolean;
  onClick: () => void;
  title: string;
  subtitle: string;
  warning?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex flex-col items-start rounded-md px-3 py-2 text-left transition-all ${
        active
          ? "bg-accent-blue/10 ring-1 ring-accent-blue/40"
          : "hover:bg-surface"
      }`}
    >
      <span
        className={`text-sm font-medium ${
          active ? "text-accent-blue" : "text-ink"
        }`}
      >
        {title}
      </span>
      <span
        className={`mt-0.5 text-xs ${
          warning ? "text-brand" : "text-ink-muted"
        }`}
      >
        {subtitle}
      </span>
    </button>
  );
}


function Field({
  label,
  hint,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  hint: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}) {
  return (
    <div>
      <label className="mb-1.5 flex items-center justify-between text-xs font-medium text-ink">
        <span>{label}</span>
        <span className="text-ink-muted font-normal">{hint}</span>
      </label>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full rounded-lg border border-surface-border bg-surface-card px-3 py-2 text-sm text-ink placeholder:text-ink-muted/60 transition focus:border-accent-blue focus:outline-none focus:ring-2 focus:ring-accent-blue/20"
      />
    </div>
  );
}

function ProgressBar({
  status,
  step,
  source,
}: {
  status: JobStatus["status"];
  step: string;
  source?: JobStatus["source"];
}) {
  const steps =
    source === "transcript"
      ? ["Normalisation", "Compte rendu"]
      : ["Conversion", "Diarisation", "Transcription", "Compte rendu"];
  const idx = steps.findIndex((s) => step.toLowerCase().includes(s.toLowerCase()));
  const pct =
    status === "done" ? 100 : Math.max(8, ((idx + 1) / steps.length) * 100);
  const running = status === "running";
  const errored = status === "error";
  return (
    <div className="space-y-2">
      <div className="h-2 overflow-hidden rounded-full bg-surface ring-1 ring-surface-border">
        <div
          className={`h-full rounded-full transition-all duration-700 ease-out ${
            errored
              ? "bg-brand-dark"
              : running
              ? "shimmer-bar"
              : "bg-accent-green"
          }`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="flex justify-between text-[10px] uppercase tracking-wider">
        {steps.map((s, i) => {
          const active = i <= idx || status === "done";
          return (
            <span
              key={s}
              className={`transition-colors duration-300 ${
                active ? "text-ink font-semibold" : "text-ink-muted"
              }`}
            >
              {s}
            </span>
          );
        })}
      </div>
    </div>
  );
}

function ReportView({
  md,
  status,
}: {
  md?: string;
  status: JobStatus["status"];
}) {
  if (!md) {
    return (
      <p className="text-sm text-ink-muted">
        {status === "done"
          ? "Aucun compte rendu trouvé."
          : "Le compte rendu apparaîtra à la fin du traitement."}
      </p>
    );
  }
  return (
    <article className="ProseMirror max-w-none animate-fade-in rounded-xl border border-surface-border bg-surface-card px-8 py-7">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{md}</ReactMarkdown>
    </article>
  );
}

