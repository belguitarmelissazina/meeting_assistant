"use client";

import { useState } from "react";
import Recorder from "@/components/Recorder";
import Uploader from "@/components/Uploader";
import TranscriptUploader from "@/components/TranscriptUploader";

type Mode = "record" | "upload" | "transcript";

interface Props {
  onJobCreated: (id: string) => void;
  /** Retour à la timeline des réunions. */
  onBack?: () => void;
}

export default function OnboardingView({ onJobCreated, onBack }: Props) {
  const [mode, setMode] = useState<Mode>("record");

  return (
    <div className="flex min-h-[70vh] flex-col items-center justify-center animate-fade-in">
      <div className="w-full max-w-xl">
        {onBack && (
          <button
            type="button"
            onClick={onBack}
            className="mb-6 inline-flex items-center gap-1.5 text-sm text-ink-muted transition-colors hover:text-ink"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="19" y1="12" x2="5" y2="12" />
              <polyline points="12 19 5 12 12 5" />
            </svg>
            Toutes les réunions
          </button>
        )}

        <header className="mb-10 text-center">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-accent-blue">
            Réunion hors agenda
          </p>
          <h1 className="mt-3 text-3xl font-semibold tracking-tight text-ink">
            Capturez votre réunion
          </h1>
          <p className="mt-3 text-sm text-ink-muted">
            Enregistrez en direct, importez un fichier audio, ou partez
            d&apos;un transcript déjà produit. Vous renseignerez le contexte
            juste après.
          </p>
        </header>

        <div className="mb-6 inline-flex w-full rounded-xl border border-surface-border bg-surface-card/60 p-1 shadow-soft backdrop-blur-sm">
          <Tab active={mode === "record"} onClick={() => setMode("record")}>
            <RecordIcon />
            Enregistrer
          </Tab>
          <Tab active={mode === "upload"} onClick={() => setMode("upload")}>
            <UploadIcon />
            Audio
          </Tab>
          <Tab active={mode === "transcript"} onClick={() => setMode("transcript")}>
            <TranscriptIcon />
            Transcript
          </Tab>
        </div>

        <div className="rounded-2xl border border-surface-border bg-surface-card/80 p-8 shadow-soft backdrop-blur-sm">
          {mode === "record" && <Recorder onJobCreated={onJobCreated} />}
          {mode === "upload" && <Uploader onJobCreated={onJobCreated} />}
          {mode === "transcript" && (
            <TranscriptUploader onJobCreated={onJobCreated} />
          )}
        </div>

        <p className="mt-6 text-center text-xs text-ink-muted">
          Les réunions sont enregistrées dans{" "}
          <span className="font-medium text-ink">Documents/Réunions</span>.
        </p>
      </div>
    </div>
  );
}

function Tab({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex flex-1 items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium transition-all duration-200 ${
        active
          ? "bg-surface-card text-brand shadow-sm ring-1 ring-surface-border"
          : "text-ink-muted hover:text-ink"
      }`}
    >
      {children}
    </button>
  );
}

function RecordIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="9" y="2" width="6" height="12" rx="3" />
      <path d="M5 10v2a7 7 0 0 0 14 0v-2" />
      <line x1="12" y1="19" x2="12" y2="22" />
    </svg>
  );
}

function UploadIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="17 8 12 3 7 8" />
      <line x1="12" y1="3" x2="12" y2="15" />
    </svg>
  );
}

function TranscriptIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="8" y1="13" x2="16" y2="13" />
      <line x1="8" y1="17" x2="16" y2="17" />
      <line x1="8" y1="9" x2="10" y2="9" />
    </svg>
  );
}
