"use client";

import { useEffect, useState } from "react";
import Sidebar from "@/components/Sidebar";
import MeetingsHome from "@/components/MeetingsHome";
import MeetingDetail from "@/components/MeetingDetail";
import OnboardingView from "@/components/OnboardingView";
import SettingsDialog from "@/components/SettingsDialog";
import ReportFindBar from "@/components/ReportFindBar";
import type { TimelineItem } from "../lib/meetings";

/** Item minimal pour ouvrir un job sélectionné hors timeline (Sidebar /
 *  enregistrement hors agenda) — MeetingDetail recharge les vraies données. */
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
  const [selected, setSelected] = useState<TimelineItem | null>(null);
  const [composing, setComposing] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem("sidebar-open");
    if (stored === "1") setSidebarOpen(true);
  }, []);

  const setOpen = (v: boolean) => {
    setSidebarOpen(v);
    localStorage.setItem("sidebar-open", v ? "1" : "0");
  };

  const toggleSidebar = () => setOpen(!sidebarOpen);

  const handleNew = () => {
    setSelected(null);
    setComposing(true);
    setOpen(false);
  };

  const handleSelectJob = (id: string) => {
    setComposing(false);
    setSelected(jobItem(id));
    setOpen(false);
  };

  const goHome = () => {
    setSelected(null);
    setComposing(false);
  };

  return (
    <div className="relative h-screen w-full overflow-hidden">
      {/* Ctrl+F dans le compte rendu ouvert (réunion sélectionnée). */}
      <ReportFindBar enabled={selected !== null} />

      <Sidebar
        open={sidebarOpen}
        onClose={() => setOpen(false)}
        onOpen={() => setOpen(true)}
        ctrlFEnabled={selected === null}
        selectedId={selected?.jobId ?? null}
        onSelect={handleSelectJob}
        onNew={handleNew}
        onDeleted={(id) => {
          if (id === selected?.jobId) goHome();
        }}
      />

      <main className="relative h-full w-full overflow-y-auto">
        <div className="fixed left-4 top-4 z-20 flex items-center gap-2">
          <button
            type="button"
            onClick={toggleSidebar}
            aria-label="Ouvrir le menu"
            title="Menu"
            className="nav-icon-btn"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="3" y1="6" x2="21" y2="6" />
              <line x1="3" y1="12" x2="21" y2="12" />
              <line x1="3" y1="18" x2="21" y2="18" />
            </svg>
          </button>
          <button
            type="button"
            onClick={handleNew}
            aria-label="Réunion hors agenda"
            title="Réunion hors agenda"
            className="nav-icon-btn"
          >
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 20h9" />
              <path d="M16.5 3.5a2.121 2.121 0 1 1 3 3L7 19l-4 1 1-4 12.5-12.5z" />
            </svg>
          </button>
          <button
            type="button"
            onClick={() => setSettingsOpen(true)}
            aria-label="Paramètres"
            title="Paramètres"
            className="nav-icon-btn"
          >
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="3" />
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33h0a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51h0a1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82v0a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
            </svg>
          </button>
        </div>

        <SettingsDialog open={settingsOpen} onClose={() => setSettingsOpen(false)} />

        <div className="mx-auto w-full max-w-[1280px] px-6 pb-16 pt-20 md:px-10 lg:px-14">
          {composing ? (
            <OnboardingView onJobCreated={handleSelectJob} onBack={goHome} />
          ) : selected ? (
            <MeetingDetail
              key={selected.key}
              item={selected}
              onBack={goHome}
              onJobCreated={() => {
                /* MeetingDetail gère son job interne ; rien à faire ici. */
              }}
            />
          ) : (
            <MeetingsHome onSelect={setSelected} onAdHoc={handleNew} />
          )}
        </div>
      </main>
    </div>
  );
}
