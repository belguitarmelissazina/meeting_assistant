"use client";

import { useEffect, useState } from "react";
import Sidebar, { type Nav } from "@/components/Sidebar";
import MeetingsHome from "@/components/MeetingsHome";
import MeetingDetail from "@/components/MeetingDetail";
import OnboardingView from "@/components/OnboardingView";
import ReportsPage from "@/components/ReportsPage";
import FoldersPage from "@/components/FoldersPage";
import SearchOverlay from "@/components/SearchOverlay";
import SettingsDialog from "@/components/SettingsDialog";
import ReportFindBar from "@/components/ReportFindBar";
import type { TimelineItem } from "../lib/meetings";

/** Item minimal pour ouvrir un job sélectionné (Récentes / liste / création) —
 *  MeetingDetail recharge les vraies données via son jobId. */
function jobItem(id: string): TimelineItem {
  return {
    key: `job:${id}`,
    title: "Réunion",
    date: new Date(),
    kind: "recorded",
    status: "done",
    jobId: id,
  };
}

export default function Home() {
  // Section active (page de fond). L'app ouvre sur l'Agenda.
  const [nav, setNav] = useState<Nav>("agenda");
  // Réunion ouverte par-dessus la section (détail / compte rendu).
  const [selected, setSelected] = useState<TimelineItem | null>(null);
  // Filtre dossier de la page Comptes rendus : undefined = tous,
  // null = sans dossier, string = un dossier précis.
  const [folderFilter, setFolderFilter] = useState<string | null | undefined>(
    undefined,
  );
  const [searchOpen, setSearchOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);

  useEffect(() => {
    if (localStorage.getItem("sidebar-collapsed") === "1") setCollapsed(true);
  }, []);

  const toggleCollapsed = () =>
    setCollapsed((c) => {
      const n = !c;
      localStorage.setItem("sidebar-collapsed", n ? "1" : "0");
      return n;
    });

  const handleNavigate = (n: Nav) => {
    setSelected(null);
    // Retour sur « Comptes rendus » ou « Dossiers » → on quitte tout drill-down
    // (folderFilter défini ramène à la liste filtrée d'un dossier).
    if (n === "reports" || n === "folders") setFolderFilter(undefined);
    setNav(n);
  };

  const handleNewMeeting = () => {
    setSelected(null);
    setNav("capture");
  };

  const openSearch = () => setSearchOpen(true);

  const handleSelectJob = (id: string) => setSelected(jobItem(id));
  const handleSelectItem = (it: TimelineItem) => setSelected(it);
  const backToNav = () => setSelected(null);

  // Réunion fraîchement créée (capture / agenda) → on la range dans
  // Comptes rendus et on l'ouvre ; « retour » ramène donc à la liste.
  const handleJobCreated = (id: string) => {
    setNav("reports");
    setFolderFilter(undefined);
    setSelected(jobItem(id));
  };

  // Drill-down depuis FoldersPage : on RESTE sur la nav « Dossiers » (la pastille
  // de la sidebar ne doit pas sauter vers « Comptes rendus »). Le routing
  // ci-dessous bascule sur ReportsPage dès qu'un folderFilter est défini.
  const openFolder = (f: string | null) => {
    setSelected(null);
    setFolderFilter(f);
    setNav("folders");
  };

  // Clic sur la pastille « Enregistrement en cours » de la sidebar. On
  // ramène l'utilisateur sur la page Capture : le composant Recorder y
  // détecte automatiquement (au montage) qu'un enregistrement tourne déjà
  // côté backend et reprend l'affichage du timer + bouton « Arrêter ».
  // Pas de routing spécial agenda même si la réunion est liée à un event :
  // l'audio + le calendar.eventId sont déjà mémorisés côté backend, le
  // record/stop produira un job correctement rattaché.
  const handleResumeRecording = () => {
    setSelected(null);
    setFolderFilter(undefined);
    setNav("capture");
  };

  // Fil d'Ariane affiché en haut de MeetingDetail. Dérivé de l'endroit d'où
  // l'utilisatrice a ouvert la réunion ; `undefined` → MeetingDetail retombe
  // sur le bouton « Toutes les réunions ».
  const breadcrumbs = !selected
    ? undefined
    : nav === "folders" && folderFilter !== undefined
    ? [
        {
          label: "Dossiers",
          onClick: () => {
            setSelected(null);
            setFolderFilter(undefined);
          },
        },
        {
          label: folderFilter === null ? "Sans dossier" : folderFilter,
          onClick: () => setSelected(null),
        },
      ]
    : nav === "reports"
    ? [{ label: "Comptes rendus", onClick: () => setSelected(null) }]
    : undefined;

  // Ctrl+F sans réunion ouverte → recherche globale (overlay).
  // (Quand une réunion est ouverte, c'est ReportFindBar qui prend Ctrl+F.)
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (selected) return;
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "f") {
        e.preventDefault();
        setSearchOpen(true);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [selected]);

  return (
    // --sb-w expose la largeur ACTUELLE de la sidebar (76px replié / 288px
    // déplié) aux overlays « fixed » qui doivent rester alignés sur main
    // (typiquement le lecteur audio flottant) — sans ça ils sont centrés
    // sur le viewport entier et se décalent quand on replie/déplie.
    <div
      className="flex h-screen w-full overflow-hidden"
      style={{ ["--sb-w" as string]: collapsed ? "76px" : "288px" }}
    >
      <ReportFindBar enabled={selected !== null} />

      <Sidebar
        collapsed={collapsed}
        onToggleCollapsed={toggleCollapsed}
        nav={nav}
        selectedJobId={selected?.jobId ?? null}
        onNavigate={handleNavigate}
        onNewMeeting={handleNewMeeting}
        onSearch={openSearch}
        onSelectJob={handleSelectJob}
        onDeleted={(id) =>
          setSelected((s) => (s?.jobId === id ? null : s))
        }
        onOpenSettings={() => setSettingsOpen(true)}
        onResumeRecording={handleResumeRecording}
      />

      <SearchOverlay
        open={searchOpen}
        onClose={() => setSearchOpen(false)}
        onSelect={handleSelectJob}
      />

      <main className="relative h-full flex-1 overflow-y-auto">
        <SettingsDialog
          open={settingsOpen}
          onClose={() => setSettingsOpen(false)}
        />

        <div className="mx-auto w-full max-w-[1100px] px-6 pb-16 pt-10 md:px-10">
          {selected ? (
            <MeetingDetail
              key={selected.key}
              item={selected}
              onBack={backToNav}
              breadcrumbs={breadcrumbs}
              onJobCreated={() => {
                /* MeetingDetail gère son job interne. */
              }}
            />
          ) : nav === "capture" ? (
            <OnboardingView onJobCreated={handleJobCreated} />
          ) : nav === "reports" ? (
            <ReportsPage
              folder={undefined}
              selectedId={null}
              onSelect={handleSelectJob}
              onBackToFolders={() => {}}
            />
          ) : nav === "folders" ? (
            folderFilter !== undefined ? (
              <ReportsPage
                folder={folderFilter}
                selectedId={null}
                onSelect={handleSelectJob}
                onBackToFolders={() => setFolderFilter(undefined)}
              />
            ) : (
              <FoldersPage onOpenFolder={openFolder} />
            )
          ) : (
            <MeetingsHome
              onSelect={handleSelectItem}
              onAdHoc={handleNewMeeting}
            />
          )}
        </div>
      </main>
    </div>
  );
}
