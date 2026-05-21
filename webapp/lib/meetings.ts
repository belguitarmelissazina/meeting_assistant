/**
 * Types partagés + helpers pour la timeline unifiée (style Granola).
 *
 * Modèle : on fusionne deux sources —
 *  - les événements de l'agenda Microsoft (`/api/calendar/upcoming`)
 *  - les jobs (réunions enregistrées) (`/api/jobs`), qui portent un
 *    `calendar` snapshot s'ils ont été lancés depuis une réunion d'agenda.
 *
 * Clé de liaison : `job.calendar.eventId === event.id`.
 */

export interface GraphAttendee {
  name: string;
  address: string | null;
}

export interface CalendarMeeting {
  id: string;
  subject: string;
  start: string | null;
  end: string | null;
  timeZone?: string | null;
  organizer: { name: string | null; address: string | null };
  location: string | null;
  attendees: GraphAttendee[];
  isOnline: boolean;
  onlineProvider?: string | null;
  preview: string;
}

export interface JobCalendarSnapshot {
  eventId?: string | null;
  subject?: string | null;
  start?: string | null;
  end?: string | null;
  location?: string | null;
  organizer?: string | null;
  attendees?: string[];
}

export type JobState =
  | "draft"
  | "pending"
  | "queued"
  | "running"
  | "done"
  | "error";

export interface JobSummary {
  id: string;
  status: JobState;
  step: string;
  label?: string;
  createdAt?: number;
  source?: "audio" | "transcript";
  calendar?: JobCalendarSnapshot | null;
}

export interface TimelineItem {
  key: string;
  title: string;
  date: Date;
  kind: "upcoming" | "recorded";
  status: "upcoming" | JobState;
  /** Présent pour une réunion à venir (toutes les infos pour la fiche). */
  meeting?: CalendarMeeting;
  /** Présent pour une réunion déjà enregistrée. */
  jobId?: string;
  jobCalendar?: JobCalendarSnapshot | null;
}

// ── Nom affiché d'une réunion ────────────────────────────────────────────────
// Dossier auto = horodaté (FOLDER_FMT côté backend) éventuellement suffixé du
// sujet. Règle : réunion d'agenda → on affiche le SUJET de l'agenda ;
// hors-agenda → le nom daté ; renommée à la main → le nom choisi.
const AUTO_FOLDER_RE = /^\d{4}-\d{2}-\d{2}_\d{2}h\d{2}m\d{2}s/;

export function meetingDisplayName(
  label?: string | null,
  calendarSubject?: string | null,
  fallback = "Réunion",
): string {
  const lbl = (label || "").trim();
  const subj = (calendarSubject || "").trim();
  if (subj && (!lbl || AUTO_FOLDER_RE.test(lbl))) return subj;
  return lbl || subj || fallback;
}

// ── Dates ────────────────────────────────────────────────────────────────────
// Graph renvoie l'heure de Paris sans offset (ex. "2026-05-19T14:00:00.0000000").
// On retire les fractions de seconde pour un parsing fiable ; l'utilisateur est
// sur un PC à l'heure de Paris donc l'affichage local est correct.
export function parseGraphDate(s?: string | null): Date | null {
  if (!s) return null;
  const d = new Date(s.replace(/\.\d+$/, ""));
  return isNaN(d.getTime()) ? null : d;
}

const MONTHS = [
  "JAN", "FÉV", "MAR", "AVR", "MAI", "JUIN",
  "JUIL", "AOÛT", "SEP", "OCT", "NOV", "DÉC",
];

/** Petite puce date façon calendrier (jour + mois court). */
export function dateChip(d: Date): { day: number; month: string } {
  return { day: d.getDate(), month: MONTHS[d.getMonth()] };
}

export function fmtTime(d: Date): string {
  return d.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
}

/** Libellé de section : Aujourd'hui / Hier / Demain / "lundi 19 mai". */
export function daySection(d: Date): string {
  const startOf = (x: Date) =>
    new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime();
  const diff = Math.round((startOf(new Date()) - startOf(d)) / 86_400_000);
  if (diff === 0) return "Aujourd'hui";
  if (diff === 1) return "Hier";
  if (diff === -1) return "Demain";
  return d.toLocaleDateString("fr-FR", {
    weekday: "long",
    day: "numeric",
    month: "long",
  });
}

// ── Pré-remplissage du contexte depuis une réunion ───────────────────────────
const PUBLIC_MAIL = new Set([
  "gmail.com", "outlook.com", "hotmail.com", "hotmail.fr", "live.com",
  "yahoo.com", "yahoo.fr", "icloud.com", "orange.fr", "free.fr",
  "wanadoo.fr", "sfr.fr", "laposte.net", "protonmail.com", "proton.me",
]);

export function guessCompanies(m: CalendarMeeting): string {
  const addrs = [
    m.organizer.address,
    ...m.attendees.map((a) => a.address),
  ].filter(Boolean) as string[];
  const names = new Set<string>();
  for (const a of addrs) {
    const dom = a.split("@")[1]?.toLowerCase();
    if (!dom || PUBLIC_MAIL.has(dom)) continue;
    const core = dom.split(".")[0];
    if (core) names.add(core.charAt(0).toUpperCase() + core.slice(1));
  }
  return Array.from(names).join(", ");
}

export function buildContexte(m: CalendarMeeting): string {
  const lines = [`Réunion : ${m.subject}`];
  if (m.organizer.name) lines.push(`Organisateur : ${m.organizer.name}`);
  if (m.location) lines.push(`Lieu : ${m.location}`);
  if (m.isOnline) lines.push("Réunion en ligne (Teams).");
  const preview = m.preview.trim();
  if (preview) {
    lines.push("");
    // Description complète conservée : le contexte est passé tel quel au
    // system prompt côté backend ; tronquer ici masquerait des infos utiles
    // (agenda, sigles, liens, instructions de l'organisateur).
    lines.push(preview);
  }
  return lines.join("\n");
}

export function attendeeNames(m: CalendarMeeting): string {
  return m.attendees.map((a) => a.name).filter(Boolean).join(", ");
}

// ── Fusion agenda + jobs → timeline ──────────────────────────────────────────
export interface Timeline {
  /** Réunions à venir, pas encore enregistrées (triées par heure croissante). */
  upcoming: TimelineItem[];
  /** Réunions enregistrées (jobs), plus récentes d'abord. */
  recorded: TimelineItem[];
}

export function buildTimeline(
  events: CalendarMeeting[],
  jobs: JobSummary[],
): Timeline {
  const jobByEvent = new Map<string, JobSummary>();
  for (const j of jobs) {
    const eid = j.calendar?.eventId;
    if (eid) jobByEvent.set(eid, j);
  }

  // Le backend a déjà borné la fenêtre (début d'aujourd'hui → +N jours), y
  // compris les réunions déjà terminées ce matin : on les garde toutes (sauf
  // celles déjà enregistrées) pour pouvoir cliquer dessus et les enregistrer.
  const upcoming: TimelineItem[] = [];
  for (const ev of events) {
    if (jobByEvent.has(ev.id)) continue;
    const d = parseGraphDate(ev.start) ?? new Date();
    upcoming.push({
      key: `ev:${ev.id}`,
      title: ev.subject || "(sans objet)",
      date: d,
      kind: "upcoming",
      status: "upcoming",
      meeting: ev,
    });
  }
  upcoming.sort((a, b) => a.date.getTime() - b.date.getTime());

  const recorded: TimelineItem[] = jobs
    .map((j) => {
      const calStart = parseGraphDate(j.calendar?.start);
      const d =
        calStart ?? (j.createdAt ? new Date(j.createdAt) : new Date());
      const title = meetingDisplayName(
        j.label,
        j.calendar?.subject,
        `Réunion ${j.id.slice(0, 8)}`,
      );
      return {
        key: `job:${j.id}`,
        title,
        date: d,
        kind: "recorded" as const,
        status: j.status,
        jobId: j.id,
        jobCalendar: j.calendar ?? null,
      };
    })
    .sort((a, b) => b.date.getTime() - a.date.getTime());

  return { upcoming, recorded };
}
