"use client";

import { useEffect, useRef, useState } from "react";
import { apiUrl } from "@/lib/api";

/** Fenêtre flottante (Electron, always-on-top, sans bordure) qui streame les
 *  suggestions de l'assistant live. Poll /api/record/suggestions ~1,5 s : les
 *  nouvelles recommandations apparaissent en haut au fil de la réunion.
 */
export default function LiveAdvisorWindow() {
  const [items, setItems] = useState<string[]>([]);
  const [recording, setRecording] = useState(true);
  const seen = useRef<Set<string>>(new Set());

  useEffect(() => {
    let cancel = false;
    const poll = async () => {
      try {
        const [sR, stR] = await Promise.all([
          fetch(apiUrl("/api/record/suggestions")),
          fetch(apiUrl("/api/record/status")),
        ]);
        if (cancel) return;
        if (stR.ok) {
          const st = (await stR.json()) as { recording?: boolean };
          setRecording(Boolean(st.recording));
        }
        if (sR.ok) {
          const d = (await sR.json()) as {
            suggestions: { ts: number; items: string[] }[];
          };
          // Groupes -> items uniques, plus récents d'abord.
          const fresh: string[] = [];
          for (const g of [...(d.suggestions || [])].reverse()) {
            for (const it of g.items || []) {
              if (!seen.current.has(it)) {
                seen.current.add(it);
                fresh.push(it);
              }
            }
          }
          if (fresh.length && !cancel) {
            setItems((prev) => [...fresh, ...prev].slice(0, 40));
          }
        }
      } catch {
        /* backend momentanément indispo → on retentera */
      }
    };
    poll();
    const id = setInterval(poll, 1500);
    return () => {
      cancel = true;
      clearInterval(id);
    };
  }, []);

  return (
    <div className="flex h-screen flex-col bg-surface text-ink">
      {/* Header draggable (déplace la fenêtre Electron) */}
      <header
        className="flex items-center gap-2 border-b border-surface-border bg-surface-card px-3 py-2"
        style={{ WebkitAppRegion: "drag" } as React.CSSProperties}
      >
        <span className="relative flex h-2.5 w-2.5">
          {recording && (
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-brand opacity-60" />
          )}
          <span
            className={`relative inline-flex h-2.5 w-2.5 rounded-full ${
              recording ? "bg-brand" : "bg-ink-muted"
            }`}
          />
        </span>
        <h1 className="flex-1 text-xs font-semibold tracking-tight text-ink">
          Assistant live
        </h1>
        <span className="text-[10px] text-ink-muted">
          {recording ? "en écoute" : "en pause"}
        </span>
        <button
          type="button"
          onClick={() => {
            const b = window as unknown as {
              electronAPI?: { advisor?: { close?: () => void } };
            };
            b.electronAPI?.advisor?.close?.();
          }}
          title="Fermer (rouvrable depuis le tray)"
          aria-label="Fermer"
          className="ml-1 flex h-5 w-5 items-center justify-center rounded text-ink-muted hover:bg-surface hover:text-ink"
          style={{ WebkitAppRegion: "no-drag" } as React.CSSProperties}
        >
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </header>

      {/* Flux de suggestions (plus récentes en haut) */}
      <section className="flex-1 space-y-2 overflow-y-auto p-3">
        {items.length === 0 ? (
          <p className="px-1 py-6 text-center text-xs text-ink-muted">
            En écoute… les suggestions apparaîtront ici au fil de la réunion.
          </p>
        ) : (
          items.map((s, i) => (
            <div
              key={`${i}-${s.slice(0, 24)}`}
              className="animate-fade-in rounded-lg border border-brand/25 bg-brand/5 px-3 py-2 text-sm leading-snug text-ink"
            >
              {s}
            </div>
          ))
        )}
      </section>
    </div>
  );
}
