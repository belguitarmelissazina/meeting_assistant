"use client";

import { useCallback, useEffect, useState } from "react";
import { apiUrl } from "./api";
import type { JobSummary } from "@/components/JobHistory";

/**
 * Poll partagé des jobs (réunions enregistrées) + dossiers.
 *
 * Utilisé par la sidebar (Récentes), la page Comptes rendus et la page
 * Dossiers. Chaque consommateur a son propre intervalle — c'est le même
 * pattern (léger) que le reste de l'app, mais le code de fetch n'est plus
 * dupliqué dans trois composants.
 */
export function useJobs(intervalMs = 2500) {
  const [jobs, setJobs] = useState<JobSummary[]>([]);
  const [folders, setFolders] = useState<string[]>([]);

  const reload = useCallback(async () => {
    try {
      const [jr, fr] = await Promise.all([
        fetch(apiUrl("/api/jobs")),
        fetch(apiUrl("/api/folders")),
      ]);
      if (jr.ok) {
        const d = (await jr.json()) as { jobs: JobSummary[] };
        setJobs(d.jobs ?? []);
      }
      if (fr.ok) {
        const d = (await fr.json()) as { folders: string[] };
        setFolders(d.folders ?? []);
      }
    } catch {
      /* ignore — un tick suivant réessaiera */
    }
  }, []);

  useEffect(() => {
    reload();
    const id = setInterval(reload, intervalMs);
    return () => clearInterval(id);
  }, [reload, intervalMs]);

  return { jobs, folders, reload };
}
