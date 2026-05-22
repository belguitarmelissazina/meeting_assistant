"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { apiUrl } from "../lib/api";

/** Un tour de parole tel que produit par le LiveProcessor (turns.json). */
export interface Turn {
  start: number;        // secondes (float)
  end: number;          // secondes (float)
  speaker: string;      // SPEAKER_00, SPEAKER_01, …
  text: string;
}

interface Props {
  jobId: string;
  /** Liste des participants récupérés de l'agenda Teams — proposés dans le
   *  dropdown de renommage des speakers. Vide si réunion hors agenda. */
  attendees: string[];
  /** Audio courant lu par <audio> dans le parent. On reçoit la ref pour
   *  pouvoir seek() au clic d'une ligne, et lire `currentTime` pour
   *  surligner le turn courant. Si null = pas de player → pas de sync. */
  audioRef: React.RefObject<HTMLAudioElement | null>;
  /** Demande au parent d'AFFICHER le lecteur audio (sinon le seek joue
   *  l'audio mais sans contrôles visibles). Appelé au 1er click sur une
   *  ligne — sans ça, l'utilisateur entend mais ne peut pas pause/seeker
   *  manuellement. */
  onWantAudio?: () => void;
}

interface TurnsResponse {
  turns: Turn[];
  speakers: Record<string, string>;
  hasTurns: boolean;
}

/** Formate `seconds` (float) en MM:SS ou HH:MM:SS si ≥ 1 h. */
function fmtTimestamp(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  const pad = (n: number) => n.toString().padStart(2, "0");
  return h > 0 ? `${pad(h)}:${pad(m)}:${pad(s)}` : `${pad(m)}:${pad(s)}`;
}

export default function TranscriptView({ jobId, attendees, audioRef, onWantAudio }: Props) {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [speakersMap, setSpeakersMap] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [empty, setEmpty] = useState(false);
  // Index du turn courant pendant la lecture audio (= surligné en jaune
  // doux). -1 si lecture pas commencée ou en dehors d'un turn (silences).
  const [activeIdx, setActiveIdx] = useState(-1);
  // Quel speaker a son dropdown ouvert (un seul à la fois). null = aucun.
  const [openSpeakerMenu, setOpenSpeakerMenu] = useState<string | null>(null);
  // Refs sur chaque <li> pour scroll automatique vers le turn courant.
  const listRef = useRef<HTMLOListElement | null>(null);

  // ── Chargement initial des turns ───────────────────────────────────────
  useEffect(() => {
    let cancel = false;
    setLoading(true);
    fetch(apiUrl(`/api/jobs/${jobId}/turns`))
      .then((r) => (r.ok ? r.json() : null))
      .then((d: TurnsResponse | null) => {
        if (cancel || !d) return;
        setTurns(d.turns ?? []);
        setSpeakersMap(d.speakers ?? {});
        setEmpty(!d.hasTurns || (d.turns?.length ?? 0) === 0);
      })
      .catch(() => { if (!cancel) setEmpty(true); })
      .finally(() => { if (!cancel) setLoading(false); });
    return () => { cancel = true; };
  }, [jobId]);

  // ── Sync audio → highlight + scroll ────────────────────────────────────
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio || turns.length === 0) return;
    const onTime = () => {
      const t = audio.currentTime;
      // Recherche linéaire (suffisant : qq centaines de turns max pour
      // une réunion d'1 h ; pas la peine d'optimiser avec une binary search).
      let found = -1;
      for (let i = 0; i < turns.length; i++) {
        if (t >= turns[i].start && t < turns[i].end) { found = i; break; }
      }
      setActiveIdx((prev) => {
        if (prev === found) return prev;
        // Scroll seulement quand l'index change ET que l'élément est hors
        // viewport — sinon ça vibre à chaque tick de l'audio.
        if (found >= 0 && listRef.current) {
          const el = listRef.current.children[found] as HTMLElement | undefined;
          if (el) {
            const rect = el.getBoundingClientRect();
            const parentRect = listRef.current.getBoundingClientRect();
            if (rect.top < parentRect.top || rect.bottom > parentRect.bottom) {
              el.scrollIntoView({ block: "center", behavior: "smooth" });
            }
          }
        }
        return found;
      });
    };
    audio.addEventListener("timeupdate", onTime);
    return () => audio.removeEventListener("timeupdate", onTime);
  }, [audioRef, turns]);

  // ── Renommage speaker via dropdown (depuis participants Teams) ─────────
  async function renameSpeaker(label: string, newName: string | null) {
    setOpenSpeakerMenu(null);
    // Optimistic update — UI instantanée même si la PATCH met 100 ms.
    setSpeakersMap((prev) => {
      const next = { ...prev };
      if (newName === null || !newName.trim()) delete next[label];
      else next[label] = newName.trim();
      return next;
    });
    try {
      await fetch(apiUrl(`/api/jobs/${jobId}/speakers`), {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ updates: { [label]: newName ?? "" } }),
      });
    } catch {
      // Si la patch foire, on recharge depuis le backend pour resynchro.
      const r = await fetch(apiUrl(`/api/jobs/${jobId}/turns`));
      if (r.ok) {
        const d = (await r.json()) as TurnsResponse;
        setSpeakersMap(d.speakers ?? {});
      }
    }
  }

  // Liste des labels de speakers UNIQUES présents dans le transcript —
  // sert pour le dropdown (« retirer le nom de Marie » = revertir tous les
  // SPEAKER_XX qui pointaient vers Marie).
  const uniqueLabels = useMemo(() => {
    const set = new Set<string>();
    for (const t of turns) set.add(t.speaker);
    return Array.from(set).sort();
  }, [turns]);

  // Click sur un turn → seek audio + AFFICHE le lecteur (sinon l'utilisateur
  // entend l'audio sans voir les contrôles : pas de pause possible, pas de
  // slider). Le parent (MeetingDetail) reçoit le signal et ouvre l'overlay.
  const seekTo = (sec: number) => {
    const audio = audioRef.current;
    if (!audio) return;
    onWantAudio?.();
    audio.currentTime = sec;
    if (audio.paused) audio.play().catch(() => { /* user blocked autoplay */ });
  };

  // Affichage d'un speaker : le mapping override, sinon le label brut.
  const displaySpeaker = (label: string) => speakersMap[label] || label;

  // Couleur stable par speaker (déterministe à partir du label).
  const speakerColor = (label: string): string => {
    let h = 0;
    for (let i = 0; i < label.length; i++) h = (h * 31 + label.charCodeAt(i)) % 360;
    return `hsl(${h}, 55%, 45%)`;
  };

  // ── Rendu ──────────────────────────────────────────────────────────────
  if (loading) {
    return <p className="text-sm text-ink-muted">Chargement du transcript…</p>;
  }
  if (empty) {
    return (
      <div className="rounded-lg border border-surface-border bg-surface-card/60 px-4 py-6 text-center">
        <p className="text-sm text-ink-muted">
          Pas de transcript par tours disponible pour cette réunion.
        </p>
        <p className="mt-1 text-xs text-ink-muted/80">
          Les réunions enregistrées AVANT la v0.4 n&apos;ont pas conservé le
          fichier `turns.json` qui sert à cette vue.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      {uniqueLabels.length > 0 && (
        <RenameLegend
          labels={uniqueLabels}
          attendees={attendees}
          speakersMap={speakersMap}
          openMenu={openSpeakerMenu}
          onOpen={setOpenSpeakerMenu}
          onRename={renameSpeaker}
          speakerColor={speakerColor}
        />
      )}
      <ol
        ref={listRef}
        className="space-y-2 overflow-y-auto"
        style={{ maxHeight: "calc(100vh - 280px)" }}
      >
        {turns.map((t, i) => (
          <li
            key={`${t.start}-${i}`}
            onClick={() => seekTo(t.start)}
            className={`group flex cursor-pointer gap-3 rounded-lg border px-3 py-2.5 transition-colors ${
              activeIdx === i
                ? "border-brand/40 bg-brand/5"
                : "border-transparent hover:border-surface-border hover:bg-surface-card/60"
            }`}
          >
            <span className="flex-shrink-0 text-[11px] font-medium tabular-nums text-ink-muted">
              {fmtTimestamp(t.start)}
            </span>
            <div className="min-w-0 flex-1">
              <p
                className="text-xs font-semibold uppercase tracking-wider"
                style={{ color: speakerColor(t.speaker) }}
              >
                {displaySpeaker(t.speaker)}
              </p>
              <p className="mt-0.5 text-sm leading-relaxed text-ink">{t.text}</p>
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}

/* ── Légende des speakers + dropdown rename ──────────────────────────── */

function RenameLegend({
  labels,
  attendees,
  speakersMap,
  openMenu,
  onOpen,
  onRename,
  speakerColor,
}: {
  labels: string[];
  attendees: string[];
  speakersMap: Record<string, string>;
  openMenu: string | null;
  onOpen: (s: string | null) => void;
  onRename: (label: string, newName: string | null) => void;
  speakerColor: (label: string) => string;
}) {
  // Liste de noms proposés dans le dropdown = participants Teams MOINS ceux
  // déjà assignés à un autre speaker (évite les doublons accidentels).
  const usedNames = new Set(Object.values(speakersMap));
  const availableAttendees = (forLabel: string) =>
    attendees.filter((a) => !usedNames.has(a) || speakersMap[forLabel] === a);

  return (
    <div className="mb-1 rounded-lg border border-surface-border bg-surface-card/60 px-3 py-2.5">
      <p className="mb-2 text-[11px] font-medium uppercase tracking-wider text-ink-muted">
        Locuteurs détectés ({labels.length})
      </p>
      <div className="flex flex-wrap gap-1.5">
        {labels.map((label) => {
          const isOpen = openMenu === label;
          const display = speakersMap[label] || label;
          const isCustom = !!speakersMap[label];
          return (
            <div key={label} className="relative">
              <button
                type="button"
                onClick={() => onOpen(isOpen ? null : label)}
                className={`flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium transition-colors ${
                  isCustom
                    ? "border-accent-blue/40 bg-accent-blue/10 text-accent-blue"
                    : "border-surface-border bg-surface text-ink hover:border-ink-muted"
                }`}
                title={isCustom ? `${label} → ${display} (cliquer pour changer)` : "Cliquer pour renommer"}
              >
                <span
                  className="h-2 w-2 rounded-full"
                  style={{ background: speakerColor(label) }}
                />
                {display}
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="6 9 12 15 18 9" />
                </svg>
              </button>
              {isOpen && (
                <SpeakerDropdown
                  label={label}
                  current={speakersMap[label]}
                  attendees={availableAttendees(label)}
                  onPick={(name) => onRename(label, name)}
                  onClear={() => onRename(label, null)}
                  onClose={() => onOpen(null)}
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

/** Dropdown ouvert sur un chip speaker :
 *   - Liste des participants Teams (si dispo)
 *   - Input libre pour saisir un nom à la main (TOUJOURS dispo —
 *     réunions hors agenda, compte Microsoft non connecté, ou juste
 *     pour mettre un surnom qui ne matche pas l'invitation)
 *   - Bouton « Retirer » si le label a déjà un nom assigné */
function SpeakerDropdown({
  label,
  current,
  attendees,
  onPick,
  onClear,
  onClose,
}: {
  label: string;
  current: string | undefined;
  attendees: string[];
  onPick: (name: string) => void;
  onClear: () => void;
  onClose: () => void;
}) {
  const [text, setText] = useState(current ?? "");
  const inputRef = useRef<HTMLInputElement | null>(null);

  // Focus auto sur l'input à l'ouverture — permet de taper directement
  // sans passer par la liste si on sait déjà ce qu'on veut écrire.
  useEffect(() => {
    inputRef.current?.focus();
    inputRef.current?.select();
  }, []);

  const submit = () => {
    const v = text.trim();
    if (!v) {
      // Champ vide à la validation = « retirer le nom » (revient au
      // SPEAKER_XX brut). Évite un clic supplémentaire sur le lien
      // « retirer » pour le même résultat.
      onClear();
    } else {
      onPick(v);
    }
  };

  return (
    <div
      className="absolute left-0 top-full z-30 mt-1 min-w-[240px] max-h-[320px] overflow-y-auto rounded-lg border border-surface-border bg-surface-card shadow-lg"
      onMouseLeave={onClose}
    >
      {/* Champ libre : marche TOUJOURS, pas besoin d'agenda Teams. */}
      <div className="border-b border-surface-border p-2">
        <div className="mb-1 text-[10px] font-medium uppercase tracking-wider text-ink-muted">
          Saisir un nom
        </div>
        <div className="flex gap-1.5">
          <input
            ref={inputRef}
            type="text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") { e.preventDefault(); submit(); }
              if (e.key === "Escape") { e.preventDefault(); onClose(); }
            }}
            placeholder="Ex. Marie Dupont"
            className="min-w-0 flex-1 rounded-md border border-surface-border bg-surface px-2 py-1 text-sm text-ink focus:border-accent-blue focus:outline-none focus:ring-1 focus:ring-accent-blue/30"
          />
          <button
            type="button"
            onClick={submit}
            className="rounded-md bg-brand px-2.5 py-1 text-xs font-medium text-white transition-colors hover:bg-brand-dark"
          >
            OK
          </button>
        </div>
      </div>

      {/* Suggestions depuis l'agenda Teams (si fourni). */}
      {attendees.length > 0 && (
        <>
          <div className="border-b border-surface-border px-3 py-1.5 text-[10px] font-medium uppercase tracking-wider text-ink-muted">
            Participants de la réunion
          </div>
          {attendees.map((a) => (
            <button
              key={a}
              type="button"
              onClick={() => onPick(a)}
              className="block w-full px-3 py-1.5 text-left text-sm text-ink hover:bg-surface"
            >
              {a}
            </button>
          ))}
        </>
      )}

      {/* Lien « retirer » seulement si le label a déjà un nom assigné. */}
      {current && (
        <button
          type="button"
          onClick={onClear}
          className="block w-full border-t border-surface-border px-3 py-1.5 text-left text-xs text-brand hover:bg-brand/5"
        >
          ↶ Retirer le nom (revenir à {label})
        </button>
      )}
    </div>
  );
}
