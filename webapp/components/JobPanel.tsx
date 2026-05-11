"use client";

import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import ReportEditor, { type SaveState } from "./ReportEditor";
import { apiUrl } from "../lib/api";

interface Props {
  jobId: string | null;
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

export default function JobPanel({ jobId }: Props) {
  const [job, setJob] = useState<JobStatus | null>(null);
  const [saveState, setSaveState] = useState<SaveState>({ kind: "idle" });

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
  }, [jobId]);

  if (!jobId || !job) {
    return null;
  }

  const isDraft = job.status === "draft";
  const isDone = job.status === "done";

  return (
    <div className="flex flex-col animate-fade-in">
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
        {isDone && <TopActions job={job} saveState={saveState} />}
      </header>

      {!isDraft && !isDone && (
        <div className="mb-6">
          <ProgressBar status={job.status} step={job.step} source={job.source} />
        </div>
      )}

      {isDone && job.audioAvailable && (
        <div className="mb-6">
          <SlimAudio jobId={job.id} />
        </div>
      )}

      {isDraft ? (
        <>
          {job.audioAvailable && <SlimAudio jobId={job.id} />}
          <DraftForm jobId={job.id} source={job.source} />
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
}: {
  job: JobStatus;
  saveState: SaveState;
}) {
  const [downloadingKind, setDownloadingKind] = useState<null | "report" | "transcript">(null);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const showTranscriptDownload = job.source === "audio" && job.transcriptAvailable;

  async function download(kind: "report" | "transcript", fallbackExt: string) {
    setDownloadError(null);
    setDownloadingKind(kind);
    try {
      const r = await fetch(apiUrl(`/api/jobs/${job.id}/download?kind=${kind}`));
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
      const blob = await r.blob();
      const cd = r.headers.get("content-disposition") || "";
      const m = /filename="?([^"]+)"?/i.exec(cd);
      const fname = m?.[1] || `${job.label || job.id}${fallbackExt}`;
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = fname;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      setDownloadError(e instanceof Error ? e.message : "Téléchargement impossible");
    } finally {
      setDownloadingKind(null);
    }
  }

  return (
    <div className="flex flex-col items-end gap-1.5">
      <div className="flex items-center gap-2">
        <SaveStatusPill state={saveState} />
        {job.audioAvailable && (
          <a
            href={apiUrl(`/api/jobs/${job.id}/audio`)}
            download
            title="Télécharger l'audio"
            aria-label="Télécharger l'audio"
            className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-surface-border bg-surface-card text-ink-muted shadow-sm transition-all duration-200 hover:text-accent-blue hover:border-accent-blue hover:shadow-md"
          >
            <AudioDownloadIcon />
          </a>
        )}
        {showTranscriptDownload && (
          <button
            type="button"
            onClick={() => download("transcript", ".txt")}
            disabled={downloadingKind !== null}
            title="Télécharger le transcript"
            aria-label="Télécharger le transcript"
            className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-surface-border bg-surface-card text-ink-muted shadow-sm transition-all duration-200 hover:text-accent-blue hover:border-accent-blue hover:shadow-md disabled:opacity-60"
          >
            {downloadingKind === "transcript" ? (
              <span className="h-3 w-3 animate-spin rounded-full border-2 border-accent-blue/30 border-t-accent-blue" />
            ) : (
              <TranscriptDownloadIcon />
            )}
          </button>
        )}
        {job.reportDocxAvailable && (
          <button
            type="button"
            onClick={() => download("report", ".docx")}
            disabled={downloadingKind !== null}
            title="Télécharger en Word"
            aria-label="Télécharger en Word"
            className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-surface-border bg-surface-card text-ink-muted shadow-sm transition-all duration-200 hover:text-accent-blue hover:border-accent-blue hover:shadow-md disabled:opacity-60"
          >
            {downloadingKind === "report" ? (
              <span className="h-3 w-3 animate-spin rounded-full border-2 border-accent-blue/30 border-t-accent-blue" />
            ) : (
              <DownloadIcon />
            )}
          </button>
        )}
      </div>
      {downloadError && (
        <div className="max-w-sm rounded-md border border-brand/30 bg-brand/5 px-3 py-2 text-xs text-brand">
          {downloadError}
        </div>
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

function DraftForm({
  jobId,
  source,
}: {
  jobId: string;
  source?: JobStatus["source"];
}) {
  const [participants, setParticipants] = useState("");
  const [entreprises, setEntreprises] = useState("");
  const [contexte, setContexte] = useState("");
  const [diarize, setDiarize] = useState(true);
  const [llm, setLlm] = useState<"local" | "mistral">("local");
  const [mistralKeySet, setMistralKeySet] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const showDiarizeToggle = source === "audio";

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
        body: JSON.stringify({ participants, entreprises, contexte, diarize, llm }),
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

      {showDiarizeToggle && (
        <div className="mt-5">
          <ToggleRow
            checked={diarize}
            onChange={setDiarize}
            label="Diarisation"
            hint="Identifier les tours de parole par locuteur (+ un peu de temps de traitement)"
          />
        </div>
      )}

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

function ToggleRow({
  checked,
  onChange,
  label,
  hint,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  label: string;
  hint: string;
}) {
  return (
    <label className="flex cursor-pointer items-center justify-between gap-4 rounded-lg border border-surface-border bg-surface-card px-4 py-3">
      <div className="min-w-0">
        <span className="block text-sm font-medium text-ink">{label}</span>
        <span className="mt-0.5 block text-xs text-ink-muted">{hint}</span>
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={`relative inline-flex h-6 w-11 flex-shrink-0 items-center rounded-full transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-accent-blue/30 ${
          checked ? "bg-accent-blue" : "bg-surface-border"
        }`}
      >
        <span
          className={`inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform duration-200 ${
            checked ? "translate-x-5" : "translate-x-0.5"
          }`}
        />
      </button>
    </label>
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

function DownloadIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="7 10 12 15 17 10" />
      <line x1="12" y1="15" x2="12" y2="3" />
    </svg>
  );
}

function AudioDownloadIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 18v-6a9 9 0 0 1 18 0v6" />
      <path d="M21 19a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3z" />
      <path d="M3 19a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2H3z" />
    </svg>
  );
}

function TranscriptDownloadIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="8" y1="13" x2="13" y2="13" />
      <line x1="8" y1="17" x2="13" y2="17" />
      <polyline points="16 15 19 18 16 21" />
    </svg>
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

