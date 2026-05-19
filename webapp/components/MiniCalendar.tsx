"use client";

import { useMemo, useState } from "react";

interface Props {
  /** Jours ayant au moins une réunion, au format "YYYY-MM-DD" (local). */
  marked: Set<string>;
  /** Jour sélectionné "YYYY-MM-DD" ou null (= tous). */
  selected: string | null;
  onSelect: (dayKey: string | null) => void;
}

const MONTHS = [
  "janvier", "février", "mars", "avril", "mai", "juin",
  "juillet", "août", "septembre", "octobre", "novembre", "décembre",
];
const WD = ["L", "M", "M", "J", "V", "S", "D"];

function key(y: number, m: number, d: number): string {
  return `${y}-${String(m + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
}

export default function MiniCalendar({ marked, selected, onSelect }: Props) {
  const today = new Date();
  const [view, setView] = useState({
    y: today.getFullYear(),
    m: today.getMonth(),
  });

  const grid = useMemo(() => {
    const first = new Date(view.y, view.m, 1);
    // getDay(): 0=dim → on veut lundi en tête.
    const lead = (first.getDay() + 6) % 7;
    const daysInMonth = new Date(view.y, view.m + 1, 0).getDate();
    const cells: (number | null)[] = [];
    for (let i = 0; i < lead; i++) cells.push(null);
    for (let d = 1; d <= daysInMonth; d++) cells.push(d);
    while (cells.length % 7 !== 0) cells.push(null);
    return cells;
  }, [view]);

  const todayKey = key(today.getFullYear(), today.getMonth(), today.getDate());

  function shift(delta: number) {
    setView((v) => {
      const d = new Date(v.y, v.m + delta, 1);
      return { y: d.getFullYear(), m: d.getMonth() };
    });
  }

  return (
    <div className="rounded-lg border border-surface-border bg-surface/60 p-2.5">
      <div className="mb-2 flex items-center justify-between">
        <button
          type="button"
          onClick={() => shift(-1)}
          aria-label="Mois précédent"
          className="flex h-6 w-6 items-center justify-center rounded text-ink-muted hover:bg-surface-card hover:text-ink"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="15 18 9 12 15 6" />
          </svg>
        </button>
        <span className="text-xs font-semibold capitalize text-ink">
          {MONTHS[view.m]} {view.y}
        </span>
        <button
          type="button"
          onClick={() => shift(1)}
          aria-label="Mois suivant"
          className="flex h-6 w-6 items-center justify-center rounded text-ink-muted hover:bg-surface-card hover:text-ink"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="9 18 15 12 9 6" />
          </svg>
        </button>
      </div>

      <div className="grid grid-cols-7 gap-0.5">
        {WD.map((w, i) => (
          <div
            key={i}
            className="py-0.5 text-center text-[10px] font-medium text-ink-muted"
          >
            {w}
          </div>
        ))}
        {grid.map((d, i) => {
          if (d === null) return <div key={i} />;
          const k = key(view.y, view.m, d);
          const isMarked = marked.has(k);
          const isSelected = selected === k;
          const isToday = k === todayKey;
          return (
            <button
              key={i}
              type="button"
              onClick={() => onSelect(isSelected ? null : k)}
              className={`relative flex h-7 items-center justify-center rounded text-[11px] transition-colors ${
                isSelected
                  ? "bg-brand font-semibold text-white"
                  : isMarked
                  ? "font-semibold text-ink hover:bg-surface-card"
                  : "text-ink-muted hover:bg-surface-card"
              } ${isToday && !isSelected ? "ring-1 ring-accent-blue/50" : ""}`}
            >
              {d}
              {isMarked && !isSelected && (
                <span className="absolute bottom-0.5 h-1 w-1 rounded-full bg-brand" />
              )}
            </button>
          );
        })}
      </div>

      {selected && (
        <button
          type="button"
          onClick={() => onSelect(null)}
          className="mt-2 w-full rounded py-1 text-[11px] text-accent-blue hover:bg-surface-card"
        >
          Voir toutes les réunions
        </button>
      )}
    </div>
  );
}
