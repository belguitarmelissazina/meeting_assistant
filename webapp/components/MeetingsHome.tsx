"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { apiUrl } from "../lib/api";
import {
  type CalendarMeeting,
  type JobSummary,
  type TimelineItem,
  buildTimeline,
  dateChip,
  fmtTime,
  parseGraphDate,
} from "../lib/meetings";
import { useRecordingStatus } from "../lib/useRecordingStatus";

interface Props {
  onSelect: (item: TimelineItem) => void;
  onAdHoc: () => void;
  /** Si défini, on ouvre automatiquement la réunion correspondante dès que
   *  la liste d'events l'a chargée (déclenché par un clic sur notification
   *  Windows « réunion dans 5 min »). Consommé une fois. */
  pendingMeetingId?: string | null;
  /** Callback pour signaler au parent que pendingMeetingId a été traité,
   *  afin qu'il le remette à null (évite de re-déclencher l'ouverture). */
  onPendingHandled?: () => void;
}

type AuthState = "loading" | "signed_out" | "pending" | "signed_in" | "error";

interface LoginResp {
  state: Exclude<AuthState, "loading">;
  account: string | null;
  error: string | null;
  userCode: string | null;
  verificationUri: string | null;
  message: string | null;
}

export default function MeetingsHome({
  onSelect, onAdHoc, pendingMeetingId, onPendingHandled,
}: Props) {
  const [auth, setAuth] = useState<AuthState>("loading");
  const [account, setAccount] = useState<string | null>(null);
  const [login, setLogin] = useState<LoginResp | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [events, setEvents] = useState<CalendarMeeting[]>([]);
  const [jobs, setJobs] = useState<JobSummary[]>([]);
  const [loadingList, setLoadingList] = useState(false);
  const pollRef = useRef<NodeJS.Timeout | null>(null);
  // ⚠ Hissé EN HAUT du composant : ce hook doit être appelé dans le même
  // ordre à chaque render, peu importe la branche d'auth (loading /
  // signed_out / signed_in) — sinon Rules of Hooks → crash.
  const recording = useRecordingStatus();

  const refreshStatus = useCallback(async () => {
    try {
      const r = await fetch(apiUrl("/api/calendar/status"));
      const d = await r.json();
      setAuth(d?.state ?? "error");
      setAccount(d?.account ?? null);
      if (d?.state === "error") setError(d?.error || "Erreur de connexion");
      return d?.state as AuthState;
    } catch {
      setAuth("error");
      setError("Backend injoignable");
      return "error" as const;
    }
  }, []);

  const loadLists = useCallback(async () => {
    setLoadingList(true);
    try {
      const [evR, jbR] = await Promise.all([
        fetch(apiUrl("/api/calendar/upcoming?days=14")),
        fetch(apiUrl("/api/jobs")),
      ]);
      if (evR.status === 401) {
        setAuth("signed_out");
        return;
      }
      if (evR.ok) {
        const d = (await evR.json()) as { meetings: CalendarMeeting[] };
        setEvents(d.meetings ?? []);
      }
      if (jbR.ok) {
        const d = (await jbR.json()) as { jobs: JobSummary[] };
        setJobs(d.jobs ?? []);
      }
    } catch {
      /* ignore — un poll suivant réessaiera */
    } finally {
      setLoadingList(false);
    }
  }, []);

  useEffect(() => {
    refreshStatus();
  }, [refreshStatus]);

  // Charge la timeline dès qu'on est connecté.
  useEffect(() => {
    if (auth === "signed_in") loadLists();
  }, [auth, loadLists]);

  // Si un pendingMeetingId est posé (clic sur notification Windows), on
  // attend que les events soient chargés puis on ouvre la réunion
  // correspondante. Consommé une fois via onPendingHandled.
  useEffect(() => {
    if (!pendingMeetingId || events.length === 0) return;
    const ev = events.find((e) => e.id === pendingMeetingId);
    if (!ev) return;
    const d = parseGraphDate(ev.start) ?? new Date();
    onSelect({
      key: `ev:${ev.id}`,
      title: ev.subject || "(sans objet)",
      date: d,
      kind: "upcoming",
      status: "upcoming",
      meeting: ev,
    });
    onPendingHandled?.();
  }, [pendingMeetingId, events, onSelect, onPendingHandled]);

  // Poll des jobs (statut d'un enregistrement en cours) quand connecté.
  useEffect(() => {
    if (auth !== "signed_in") return;
    const id = setInterval(async () => {
      try {
        const r = await fetch(apiUrl("/api/jobs"));
        if (r.ok) {
          const d = (await r.json()) as { jobs: JobSummary[] };
          setJobs(d.jobs ?? []);
        }
      } catch {
        /* ignore */
      }
    }, 4000);
    return () => clearInterval(id);
  }, [auth]);

  // Poll du device flow pendant la connexion.
  useEffect(() => {
    if (auth !== "pending") {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
      return;
    }
    pollRef.current = setInterval(refreshStatus, 3000);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
      pollRef.current = null;
    };
  }, [auth, refreshStatus]);

  async function connect() {
    setError(null);
    setAuth("loading");
    try {
      const r = await fetch(apiUrl("/api/calendar/login"), { method: "POST" });
      if (!r.ok) throw new Error(await r.text());
      const d = (await r.json()) as LoginResp;
      setLogin(d);
      setAuth(d.state);
      setAccount(d.account);
      if (d.state === "error") setError(d.error || d.message || "Échec");
    } catch (e) {
      setAuth("error");
      setError(e instanceof Error ? e.message : "Connexion impossible");
    }
  }

  async function disconnect() {
    try {
      await fetch(apiUrl("/api/calendar/logout"), { method: "POST" });
    } catch {
      /* ignore */
    }
    setLogin(null);
    setEvents([]);
    setAccount(null);
    setAuth("signed_out");
  }

  // ── Écrans d'auth ────────────────────────────────────────────────────────
  if (auth === "loading") {
    return <Center>Vérification de la connexion…</Center>;
  }

  if (auth === "signed_out" || auth === "error") {
    return (
      <Gate>
        <h1 className="text-2xl font-semibold tracking-tight text-ink">
          Connectez votre agenda
        </h1>
        <p className="mt-3 max-w-md text-sm text-ink-muted">
          Connectez votre compte Microsoft pour voir vos réunions ici, les
          enregistrer et générer leurs comptes rendus. L&apos;app ne lit que
          <span className="font-medium text-ink"> votre</span> agenda.
        </p>
        <button type="button" onClick={connect} className="btn-primary mt-7">
          <MicrosoftIcon />
          Connecter mon agenda Microsoft
        </button>
        {error && <ErrorBox>{error}</ErrorBox>}
        <button
          type="button"
          onClick={onAdHoc}
          className="mt-6 text-xs text-ink-muted underline hover:text-ink"
        >
          Continuer sans agenda (réunion ponctuelle)
        </button>
      </Gate>
    );
  }

  if (auth === "pending") {
    return (
      <Gate>
        <h1 className="text-2xl font-semibold tracking-tight text-ink">
          Connexion Microsoft
        </h1>
        <p className="mt-3 text-sm text-ink-muted">
          Ouvrez la page de connexion et saisissez ce code :
        </p>
        <div className="mt-5 rounded-xl border border-surface-border bg-surface px-6 py-4">
          <span className="font-mono text-3xl font-semibold tracking-[0.3em] text-brand">
            {login?.userCode ?? "…"}
          </span>
        </div>
        <a
          href={login?.verificationUri || "https://microsoft.com/devicelogin"}
          target="_blank"
          rel="noreferrer"
          className="btn-primary mt-5"
        >
          Ouvrir la page de connexion
        </a>
        <p className="mt-5 flex items-center gap-2 text-xs text-ink-muted">
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-accent-blue" />
          En attente de votre validation…
        </p>
        <button
          type="button"
          onClick={disconnect}
          className="mt-4 text-xs text-ink-muted underline hover:text-brand"
        >
          Annuler
        </button>
        {error && <ErrorBox>{error}</ErrorBox>}
      </Gate>
    );
  }

  // ── Agenda (signed_in) ───────────────────────────────────────────────────
  // `jobs` sert uniquement à savoir quelles réunions sont déjà enregistrées
  // (elles disparaissent de l'Agenda et vivent dans l'historique du panneau
  // latéral — pas de doublon). On n'affiche QUE l'agenda à venir ici.
  const { upcoming } = buildTimeline(events, jobs);
  // `recording` est déjà hissé en haut du composant (Rules of Hooks) — on
  // ne fait ici que dériver le eventId pour le passage aux <Row>.
  const recordingEventId =
    recording.recording ? recording.calendar?.eventId ?? null : null;

  const sameDay = (d: Date) => {
    const n = new Date();
    return (
      d.getFullYear() === n.getFullYear() &&
      d.getMonth() === n.getMonth() &&
      d.getDate() === n.getDate()
    );
  };
  const todayItems = upcoming.filter((it) => sameDay(it.date));
  const nextItems = upcoming.filter((it) => !sameDay(it.date));

  return (
    <div className="mx-auto w-full max-w-4xl animate-fade-in">
      <header className="mb-6 flex items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-ink">
            Agenda
          </h1>
          {account && (
            <p className="mt-1 truncate text-[13px] text-ink-muted">{account}</p>
          )}
        </div>
        <div className="flex items-center gap-4 text-sm">
          <button
            type="button"
            onClick={onAdHoc}
            className="rounded-lg border border-surface-border bg-surface-card px-3.5 py-2 font-medium text-ink hover:border-accent-blue"
          >
            + Hors agenda
          </button>
          <button
            type="button"
            onClick={loadLists}
            disabled={loadingList}
            className="text-accent-blue hover:underline disabled:opacity-50"
          >
            {loadingList ? "…" : "Actualiser"}
          </button>
          <button
            type="button"
            onClick={disconnect}
            className="text-ink-muted hover:text-brand hover:underline"
          >
            Déconnecter
          </button>
        </div>
      </header>

      {upcoming.length > 0 ? (
        <>
          {todayItems.length > 0 && (
            <Section label="Aujourd'hui">
              {todayItems.map((it) => (
                <Row
                  key={it.key}
                  item={it}
                  onClick={() => onSelect(it)}
                  recording={
                    recordingEventId !== null &&
                    it.meeting?.id === recordingEventId
                  }
                />
              ))}
            </Section>
          )}
          {nextItems.length > 0 && (
            <Section label="Prochaines réunions">
              {nextItems.map((it) => (
                <Row
                  key={it.key}
                  item={it}
                  onClick={() => onSelect(it)}
                  recording={
                    recordingEventId !== null &&
                    it.meeting?.id === recordingEventId
                  }
                />
              ))}
            </Section>
          )}
        </>
      ) : (
        <Center>
          Aucune réunion d&apos;agenda à enregistrer aujourd&apos;hui ni dans
          les 14 prochains jours.
          <br />
          Vos comptes rendus déjà produits sont dans{" "}
          <strong>« Comptes rendus »</strong> (menu de gauche).
        </Center>
      )}
    </div>
  );
}

function Section({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <section className="mb-8">
      <h2 className="mb-3 text-xs font-semibold uppercase tracking-[0.15em] text-ink-muted">
        {label}
      </h2>
      <ul className="space-y-2">{children}</ul>
    </section>
  );
}

function Row({
  item,
  onClick,
  recording,
}: {
  item: TimelineItem;
  onClick: () => void;
  /** True quand un enregistrement est en cours pour CETTE réunion d'agenda. */
  recording?: boolean;
}) {
  const chip = dateChip(item.date);
  return (
    <li>
      <button
        type="button"
        onClick={onClick}
        className={`group flex w-full items-center gap-4 rounded-xl border px-3 py-3.5 text-left transition-all duration-200 ${
          recording
            ? "border-brand/40 bg-brand/5 hover:bg-brand/10"
            : "border-transparent hover:border-surface-border hover:bg-surface-card/70"
        }`}
      >
        <div className="flex h-14 w-14 flex-shrink-0 flex-col items-center justify-center rounded-lg border border-surface-border bg-surface-card">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-brand">
            {chip.month}
          </span>
          <span className="text-xl font-bold leading-none text-ink">
            {chip.day}
          </span>
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-[15px] font-medium text-ink">{item.title}</p>
          <p className="mt-0.5 text-[13px] text-ink-muted">
            {fmtTime(item.date)}
          </p>
        </div>
        {recording ? (
          <span className="flex items-center gap-1.5 rounded-full bg-brand/15 px-2.5 py-1 text-xs font-medium text-brand">
            <span className="h-1.5 w-1.5 rounded-full bg-brand animate-pulse" />
            Enregistrement…
          </span>
        ) : (
          <StatusBadge status={item.status} />
        )}
      </button>
    </li>
  );
}

function StatusBadge({ status }: { status: TimelineItem["status"] }) {
  const map: Record<string, { label: string; cls: string }> = {
    upcoming: { label: "À enregistrer", cls: "bg-accent-blue/10 text-accent-blue" },
    draft: { label: "À traiter", cls: "bg-accent-blue/10 text-accent-blue" },
    pending: { label: "En cours", cls: "bg-ink-muted/10 text-ink-muted" },
    queued: { label: "En cours", cls: "bg-ink-muted/10 text-ink-muted" },
    running: { label: "En cours", cls: "bg-accent-yellow/15 text-accent-yellow" },
    done: { label: "✓ Compte rendu", cls: "bg-accent-green/15 text-accent-green" },
    error: { label: "Erreur", cls: "bg-brand/10 text-brand" },
  };
  const s = map[status] ?? map.upcoming;
  return (
    <span
      className={`flex-shrink-0 rounded-full px-3 py-1.5 text-xs font-medium ${s.cls}`}
    >
      {s.label}
    </span>
  );
}

function Center({ children }: { children: React.ReactNode }) {
  return (
    <div className="py-16 text-center text-sm text-ink-muted">{children}</div>
  );
}

function Gate({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-[70vh] flex-col items-center justify-center text-center animate-fade-in">
      {children}
    </div>
  );
}

function ErrorBox({ children }: { children: React.ReactNode }) {
  return (
    <div className="mt-5 rounded-md border border-brand/30 bg-brand/5 px-4 py-3 text-sm text-brand">
      {children}
    </div>
  );
}

function MicrosoftIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 23 23" aria-hidden>
      <rect x="1" y="1" width="10" height="10" fill="#f25022" />
      <rect x="12" y="1" width="10" height="10" fill="#7fba00" />
      <rect x="1" y="12" width="10" height="10" fill="#00a4ef" />
      <rect x="12" y="12" width="10" height="10" fill="#ffb900" />
    </svg>
  );
}
