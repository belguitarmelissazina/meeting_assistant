"use client";

import { useCallback, useEffect, useRef, useState } from "react";

interface FindResult {
  activeMatchOrdinal: number;
  matches: number;
  finalUpdate: boolean;
}
interface FindApi {
  start: (
    text: string,
    options?: { forward?: boolean; findNext?: boolean; matchCase?: boolean },
  ) => void;
  stop: () => void;
  onResult: (cb: (r: FindResult) => void) => () => void;
}

function getFindApi(): FindApi | null {
  if (typeof window === "undefined") return null;
  const w = window as unknown as { electronAPI?: { find?: FindApi } };
  return w.electronAPI?.find ?? null;
}

/**
 * Barre de recherche DANS le contenu ouvert (compte rendu / transcript).
 * Activée par Ctrl+F uniquement quand une réunion est ouverte (`enabled`).
 * Utilise la recherche native Chromium via Electron → fonctionne aussi bien
 * dans l'éditeur tiptap (contenteditable) que dans le markdown rendu.
 */
export default function ReportFindBar({ enabled }: { enabled: boolean }) {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [res, setRes] = useState<{ a: number; m: number } | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const api = getFindApi();

  const debRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const clearDeb = useCallback(() => {
    if (debRef.current) {
      clearTimeout(debRef.current);
      debRef.current = null;
    }
  }, []);

  // true seulement pendant la fermeture volontaire → onBlur ne re-focalise
  // pas dans ce cas (sinon on ne pourrait jamais quitter le champ).
  const closingRef = useRef(false);

  // Ouverture : focus + sélection du texte existant (pour le remplacer vite).
  const focusSelectInput = useCallback(() => {
    const el = inputRef.current;
    if (!el) return;
    el.focus();
    el.select();
  }, []);

  const close = useCallback(() => {
    closingRef.current = true;
    clearDeb();
    setOpen(false);
    setRes(null);
    api?.stop();
  }, [api, clearDeb]);

  const run = useCallback(
    (text: string, opts?: { forward?: boolean; findNext?: boolean }) => {
      if (!api) return;
      if (text.trim()) api.start(text, opts);
      else {
        api.stop();
        setRes(null);
      }
    },
    [api],
  );

  // Recherche pendant la frappe : debounce (ne lance pas findInPage à chaque
  // lettre → évite le vol de focus en plein milieu de la saisie).
  const scheduleRun = useCallback(
    (text: string) => {
      clearDeb();
      if (!text.trim()) {
        run(text);
        return;
      }
      debRef.current = setTimeout(() => run(text), 250);
    },
    [run, clearDeb],
  );

  // Résultats (n° courant / total). Le focus est géré par onBlur (ci-dessous).
  useEffect(() => {
    if (!api) return;
    return api.onResult((r) =>
      setRes({ a: r.activeMatchOrdinal, m: r.matches }),
    );
  }, [api]);

  // Nettoyage du timer au démontage.
  useEffect(() => clearDeb, [clearDeb]);

  // Ctrl/Cmd+F → ouvre la barre ; Échap → ferme.
  useEffect(() => {
    if (!enabled || !api) return;
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "f") {
        e.preventDefault();
        closingRef.current = false;
        setOpen(true);
        requestAnimationFrame(focusSelectInput);
        if (q.trim()) run(q);
      } else if (e.key === "Escape" && open) {
        e.preventDefault();
        close();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [enabled, api, open, q, run, close, focusSelectInput]);

  // Réunion fermée → on masque et on nettoie le surlignage.
  useEffect(() => {
    if (!enabled && open) close();
  }, [enabled, open, close]);

  if (!api || !enabled || !open) return null;

  return (
    <div className="fixed right-6 top-4 z-50 flex items-center gap-1 rounded-lg border border-surface-border bg-surface-card px-2 py-1.5 shadow-xl animate-fade-in">
      <svg
        className="text-ink-muted"
        width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
      >
        <circle cx="11" cy="11" r="7" />
        <line x1="21" y1="21" x2="16.65" y2="16.65" />
      </svg>
      <input
        ref={inputRef}
        type="text"
        value={q}
        onChange={(e) => {
          setQ(e.target.value);
          scheduleRun(e.target.value);
        }}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            clearDeb();
            run(q, { forward: !e.shiftKey, findNext: true });
          }
        }}
        onBlur={() => {
          // Tant que la barre est ouverte, on garde le focus dans le champ
          // (findInPage le vole vers le texte trouvé). On ne lâche QUE si on
          // ferme volontairement la barre.
          if (closingRef.current) return;
          setTimeout(() => {
            if (!closingRef.current) inputRef.current?.focus();
          }, 0);
        }}
        placeholder="Rechercher dans le compte rendu…"
        className="w-56 bg-transparent px-1 text-sm text-ink placeholder:text-ink-muted/60 focus:outline-none"
      />
      <span className="min-w-[44px] text-center text-xs tabular-nums text-ink-muted">
        {q.trim() ? (res ? `${res.a}/${res.m}` : "…") : ""}
      </span>
      <button
        type="button"
        onMouseDown={(e) => e.preventDefault()}
        onClick={() => {
          clearDeb();
          run(q, { forward: false, findNext: true });
        }}
        title="Précédent (Maj+Entrée)"
        className="flex h-6 w-6 items-center justify-center rounded text-ink-muted hover:bg-surface hover:text-ink"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="18 15 12 9 6 15" />
        </svg>
      </button>
      <button
        type="button"
        onMouseDown={(e) => e.preventDefault()}
        onClick={() => {
          clearDeb();
          run(q, { forward: true, findNext: true });
        }}
        title="Suivant (Entrée)"
        className="flex h-6 w-6 items-center justify-center rounded text-ink-muted hover:bg-surface hover:text-ink"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>
      <button
        type="button"
        onMouseDown={(e) => e.preventDefault()}
        onClick={close}
        title="Fermer (Échap)"
        className="flex h-6 w-6 items-center justify-center rounded text-ink-muted hover:bg-brand/10 hover:text-brand"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <line x1="18" y1="6" x2="6" y2="18" />
          <line x1="6" y1="6" x2="18" y2="18" />
        </svg>
      </button>
    </div>
  );
}
