"use client";

import { useEffect, useState } from "react";
import { apiUrl } from "./api";

/** Snapshot du recorder global (un seul enregistrement à la fois côté backend). */
export interface RecordingStatus {
  recording: boolean;
  /** Timestamp ms epoch du record/start — sert à reconstituer le timer côté UI. */
  startedAt?: number;
  /** Réunion d'agenda liée à l'enregistrement (si lancé depuis l'agenda). */
  calendar?: {
    eventId?: string;
    subject?: string;
    start?: string;
    end?: string;
    location?: string;
    organizer?: string;
    attendees?: string[];
  } | null;
}

/** Polling global de l'état d'enregistrement.
 *
 *  Pourquoi un poll au lieu d'un EventSource/WS : un seul enregistrement actif
 *  à la fois, 2s de latence est largement acceptable, et ça reste robuste si
 *  le backend reboot pendant que l'app tourne (le hook re-converge tout seul).
 */
export function useRecordingStatus(intervalMs = 2000): RecordingStatus {
  const [status, setStatus] = useState<RecordingStatus>({ recording: false });

  useEffect(() => {
    let cancel = false;
    const tick = async () => {
      try {
        const r = await fetch(apiUrl("/api/record/status"));
        if (!r.ok) return;
        const d = (await r.json()) as RecordingStatus;
        if (!cancel) setStatus(d);
      } catch {
        /* backend KO → on ne change rien ; l'app affiche déjà ses erreurs */
      }
    };
    tick();
    const id = setInterval(tick, intervalMs);
    return () => {
      cancel = true;
      clearInterval(id);
    };
  }, [intervalMs]);

  return status;
}

/** Helper d'affichage : nombre de secondes écoulées depuis startedAt. */
export function recordingElapsedSeconds(s: RecordingStatus): number {
  if (!s.recording || !s.startedAt) return 0;
  return Math.max(0, Math.floor((Date.now() - s.startedAt) / 1000));
}

/** Helper d'affichage : durée formatée MM:SS (ou HH:MM:SS si ≥ 1 h). */
export function formatRecordingDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  const pad = (n: number) => n.toString().padStart(2, "0");
  return h > 0 ? `${pad(h)}:${pad(m)}:${pad(s)}` : `${pad(m)}:${pad(s)}`;
}
