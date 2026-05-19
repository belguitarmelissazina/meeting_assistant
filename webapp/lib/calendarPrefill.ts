/**
 * Petit relais en mémoire pour transporter le contexte d'une réunion choisie
 * dans le calendrier jusqu'au formulaire de traitement (DraftForm).
 *
 * Pourquoi pas des props : le chemin est CalendarPanel → (changement d'onglet)
 * → Recorder → enregistrement → onJobCreated → JobPanel → DraftForm. Faire
 * traverser la donnée à travers cette chaîne asynchrone et profonde alourdit
 * 5 composants. L'app est une SPA (pas de reload entre les deux), un module
 * singleton suffit et reste trivial à raisonner.
 *
 * Sémantique « one-shot » : `consume()` lit ET vide. Si l'utilisateur lance
 * un enregistrement sans passer par le calendrier, il n'y a rien à appliquer.
 */
export interface CalendarPrefill {
  /** Titre de la réunion (sujet) — sert d'aide visuelle, pas envoyé tel quel. */
  subject: string;
  /** Participants, séparés par des virgules (format attendu par le backend). */
  participants: string;
  /** Entreprises devinées depuis les domaines mail (best-effort). */
  entreprises: string;
  /** Contexte composé (objet + organisateur + aperçu du corps). */
  contexte: string;
}

let pending: CalendarPrefill | null = null;

export function setCalendarPrefill(p: CalendarPrefill): void {
  pending = p;
}

/** Lit et vide le prefill en attente (à appeler une seule fois au montage). */
export function consumeCalendarPrefill(): CalendarPrefill | null {
  const p = pending;
  pending = null;
  return p;
}

/** Lit SANS vider — pour afficher un rappel pendant l'enregistrement. */
export function peekCalendarPrefill(): CalendarPrefill | null {
  return pending;
}

/** Annule la réunion sélectionnée (bouton « retirer »). */
export function clearCalendarPrefill(): void {
  pending = null;
}
