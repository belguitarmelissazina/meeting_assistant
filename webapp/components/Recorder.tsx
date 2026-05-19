"use client";

import { useEffect, useRef, useState } from "react";
import { apiUrl } from "../lib/api";
import { setCalendarPrefill } from "../lib/calendarPrefill";

/** Réunion d'agenda à laquelle rattacher l'enregistrement (optionnel). */
export interface RecordingMeeting {
  calendar: {
    eventId?: string;
    subject?: string;
    start?: string;
    end?: string;
    location?: string;
    organizer?: string;
    attendees: string[];
  };
  /** Pour ancrer le LLM live + pré-remplir le formulaire de contexte. */
  participants: string;
  entreprises: string;
  contexte: string;
}

interface Props {
  onJobCreated: (id: string) => void;
  /** Si fourni, l'enregistrement est lié à cette réunion d'agenda. */
  meeting?: RecordingMeeting | null;
  /** Appelé dès le clic « Arrêter » (avant la finalisation backend) →
   *  le parent peut afficher un écran « Génération du compte rendu ». */
  onStopStart?: () => void;
  /** Appelé si la finalisation échoue → le parent ré-affiche le Recorder. */
  onStopFailed?: () => void;
}

type State = "idle" | "recording" | "stopping" | "processing";

export default function Recorder({
  onJobCreated,
  meeting,
  onStopStart,
  onStopFailed,
}: Props) {
  const [state, setState] = useState<State>("idle");
  const [duration, setDuration] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (state === "recording") {
      const started = Date.now();
      timerRef.current = setInterval(() => {
        setDuration((Date.now() - started) / 1000);
      }, 200);
    } else if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [state]);

  async function start() {
    setError(null);
    try {
      // On envoie toujours un corps JSON : enableLiveLlm=true conserve le
      // comportement live d'origine ; `calendar` rattache la réunion.
      const body = meeting
        ? {
            enableLiveLlm: true,
            participants: meeting.participants,
            entreprises: meeting.entreprises,
            contexte: meeting.contexte,
            calendar: meeting.calendar,
          }
        : { enableLiveLlm: true };

      const r = await fetch(apiUrl("/api/record/start"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!r.ok) throw new Error(await r.text());

      // Pré-remplit le formulaire de contexte (cas non-live / fallback).
      if (meeting) {
        setCalendarPrefill({
          subject: meeting.calendar.subject || "Réunion",
          participants: meeting.participants,
          entreprises: meeting.entreprises,
          contexte: meeting.contexte,
        });
      }

      setDuration(0);
      setState("recording");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur");
    }
  }

  async function stop() {
    setState("stopping");
    onStopStart?.();
    try {
      const r = await fetch(apiUrl("/api/record/stop"), { method: "POST" });
      if (!r.ok) throw new Error(await r.text());
      const { jobId } = (await r.json()) as { jobId: string };
      onJobCreated(jobId);
      setState("idle");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur");
      setState("idle");
      onStopFailed?.();
    }
  }

  const mm = Math.floor(duration / 60)
    .toString()
    .padStart(2, "0");
  const ss = Math.floor(duration % 60)
    .toString()
    .padStart(2, "0");

  return (
    <div className="space-y-5">
      <div
        className={`flex items-center justify-between rounded-xl border p-5 transition-all duration-300 ${
          state === "recording"
            ? "border-brand/40 bg-brand/5 shadow-soft"
            : "border-surface-border bg-surface"
        }`}
      >
        <div className="flex items-center gap-3">
          {state === "recording" && <span className="pulse-dot" />}
          <div>
            <div className="font-mono text-2xl font-semibold tabular-nums text-ink">
              {mm}:{ss}
            </div>
            <div className="text-xs text-ink-muted transition-colors">
              {state === "idle" && "Prêt"}
              {state === "recording" && "Enregistrement en cours"}
              {state === "stopping" && "Finalisation…"}
              {state === "processing" && "Sauvegarde…"}
            </div>
          </div>
        </div>
        {state === "idle" ? (
          <button className="btn-primary" onClick={start}>
            <span className="h-2.5 w-2.5 rounded-full bg-white" />
            Démarrer
          </button>
        ) : (
          <button
            className="btn-danger"
            onClick={stop}
            disabled={state !== "recording"}
          >
            <span className="h-2.5 w-2.5 rounded-sm bg-white" />
            Arrêter
          </button>
        )}
      </div>

      {error && (
        <div className="rounded-md border border-brand/30 bg-brand/5 px-4 py-3 text-sm text-brand">
          {error}
        </div>
      )}
    </div>
  );
}
