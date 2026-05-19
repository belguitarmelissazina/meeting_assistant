"use client";

import { useEffect, useState } from "react";
import { apiUrl } from "../lib/api";

interface Props {
  open: boolean;
  onClose: () => void;
  onSaved?: (mistralKeySet: boolean) => void;
}

type Status = "idle" | "loading" | "saving" | "saved" | "error";

export default function SettingsDialog({ open, onClose, onSaved }: Props) {
  const [keyInput, setKeyInput] = useState("");
  const [mistralKeySet, setMistralKeySet] = useState(false);
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setStatus("loading");
    setError(null);
    setKeyInput("");
    fetch(apiUrl("/api/settings"))
      .then((r) => r.json())
      .then((data) => {
        setMistralKeySet(Boolean(data?.mistralKeySet));
        setStatus("idle");
      })
      .catch(() => {
        setStatus("error");
        setError("Impossible de charger les paramètres");
      });
  }, [open]);

  async function save(action: "set" | "clear") {
    setStatus("saving");
    setError(null);
    try {
      const r = await fetch(apiUrl("/api/settings"), {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          mistralApiKey: action === "set" ? keyInput.trim() : "",
        }),
      });
      if (!r.ok) throw new Error(await r.text());
      const data = (await r.json()) as { mistralKeySet: boolean };
      setMistralKeySet(data.mistralKeySet);
      setKeyInput("");
      setStatus("saved");
      onSaved?.(data.mistralKeySet);
      setTimeout(() => setStatus("idle"), 1200);
    } catch (e) {
      setStatus("error");
      setError(e instanceof Error ? e.message : "Erreur");
    }
  }

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4 animate-fade-in"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        className="w-full max-w-lg rounded-2xl border border-surface-border bg-surface-card p-7 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-5 flex items-start justify-between gap-4">
          <div>
            <h2 className="text-xl font-semibold text-ink">Paramètres</h2>
            <p className="mt-1 text-sm text-ink-muted">
              Clé stockée localement dans <span className="font-mono text-xs">~/.meeting_assistant</span>.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="inline-flex h-8 w-8 items-center justify-center rounded-full text-ink-muted hover:text-ink"
            aria-label="Fermer"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        <section>
          <div className="mb-2 flex items-center justify-between">
            <label htmlFor="mistral-key" className="text-sm font-semibold text-ink">
              Clé API Mistral
            </label>
            <span
              className={`text-xs ${
                mistralKeySet ? "text-accent-green" : "text-ink-muted"
              }`}
            >
              {mistralKeySet ? "Configurée" : "Non configurée"}
            </span>
          </div>
          <input
            id="mistral-key"
            type="password"
            autoComplete="off"
            spellCheck={false}
            value={keyInput}
            onChange={(e) => setKeyInput(e.target.value)}
            placeholder={mistralKeySet ? "••••••••••••  (laissez vide pour conserver)" : "sk-…"}
            className="w-full rounded-lg border border-surface-border bg-surface px-3 py-2.5 text-sm text-ink placeholder:text-ink-muted/60 transition focus:border-accent-blue focus:outline-none focus:ring-2 focus:ring-accent-blue/20"
          />
          <p className="mt-2 text-xs text-ink-muted">
            Utilisée pour le pipeline « Mistral Large (cloud) ». Obtenir une clé :{" "}
            <span className="font-mono">console.mistral.ai</span>.
          </p>

          <div className="mt-5 flex items-center justify-end gap-2">
            {mistralKeySet && (
              <button
                type="button"
                onClick={() => save("clear")}
                disabled={status === "saving"}
                className="rounded-lg border border-surface-border px-3 py-2 text-sm text-ink-muted hover:text-brand hover:border-brand/40 disabled:opacity-60"
              >
                Supprimer
              </button>
            )}
            <button
              type="button"
              onClick={() => save("set")}
              disabled={status === "saving" || keyInput.trim().length === 0}
              className="rounded-lg bg-accent-blue px-4 py-2 text-sm font-medium text-white shadow-sm hover:brightness-110 disabled:opacity-60"
            >
              {status === "saving"
                ? "Enregistrement…"
                : status === "saved"
                ? "Enregistré ✓"
                : "Enregistrer"}
            </button>
          </div>

          {error && (
            <div className="mt-3 rounded-md border border-brand/30 bg-brand/5 px-3 py-2 text-sm text-brand">
              {error}
            </div>
          )}
        </section>

        <div className="my-6 border-t border-surface-border" />

        <CalendarSettings open={open} />
      </div>
    </div>
  );
}

/**
 * Statut + déconnexion du calendrier Microsoft. La *connexion* (device code)
 * se fait dans l'onglet « Calendrier » de la page d'accueil — on évite ici
 * de dupliquer la machine à états du device flow.
 */
function CalendarSettings({ open }: { open: boolean }) {
  const [state, setState] = useState<
    "loading" | "signed_out" | "pending" | "signed_in" | "error"
  >("loading");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!open) return;
    setState("loading");
    fetch(apiUrl("/api/calendar/status"))
      .then((r) => r.json())
      .then((d) => setState(d?.state ?? "error"))
      .catch(() => setState("error"));
  }, [open]);

  async function disconnect() {
    setBusy(true);
    try {
      await fetch(apiUrl("/api/calendar/logout"), { method: "POST" });
      setState("signed_out");
    } catch {
      /* ignore */
    } finally {
      setBusy(false);
    }
  }

  const connected = state === "signed_in";

  return (
    <section>
      <div className="mb-2 flex items-center justify-between">
        <span className="text-sm font-semibold text-ink">Calendrier Microsoft</span>
        <span
          className={`text-xs ${
            connected ? "text-accent-green" : "text-ink-muted"
          }`}
        >
          {state === "loading"
            ? "…"
            : connected
            ? "Connecté"
            : state === "pending"
            ? "Connexion en cours"
            : "Non connecté"}
        </span>
      </div>
      {!connected && (
        <p className="text-xs text-ink-muted">
          Connectez votre agenda depuis l&apos;onglet{" "}
          <span className="font-medium text-ink">Calendrier</span> de
          l&apos;accueil pour lister vos réunions.
        </p>
      )}
      {connected && (
        <div className="mt-3 flex justify-end">
          <button
            type="button"
            onClick={disconnect}
            disabled={busy}
            className="rounded-lg border border-surface-border px-3 py-2 text-sm text-ink-muted hover:text-brand hover:border-brand/40 disabled:opacity-60"
          >
            {busy ? "Déconnexion…" : "Déconnecter"}
          </button>
        </div>
      )}
    </section>
  );
}
