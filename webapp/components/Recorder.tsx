"use client";

import { useEffect, useRef, useState } from "react";
import { apiUrl } from "../lib/api";

interface Props {
  onJobCreated: (id: string) => void;
}

type State = "idle" | "recording" | "stopping" | "processing";

export default function Recorder({ onJobCreated }: Props) {
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
      const r = await fetch(apiUrl("/api/record/start"), { method: "POST" });
      if (!r.ok) throw new Error(await r.text());
      setDuration(0);
      setState("recording");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur");
    }
  }

  async function stop() {
    setState("stopping");
    try {
      const r = await fetch(apiUrl("/api/record/stop"), { method: "POST" });
      if (!r.ok) throw new Error(await r.text());
      const { jobId } = (await r.json()) as { jobId: string };
      onJobCreated(jobId);
      setState("idle");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur");
      setState("idle");
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
