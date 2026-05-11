"use client";

import { useEffect, useState } from "react";
import Sidebar from "@/components/Sidebar";
import JobPanel from "@/components/JobPanel";
import OnboardingView from "@/components/OnboardingView";
import SettingsDialog from "@/components/SettingsDialog";

export default function Home() {
  const [jobId, setJobId] = useState<string | null>(null);
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
    setJobId(null);
    setComposing(true);
    setOpen(false);
  };

  const handleSelect = (id: string) => {
    setComposing(false);
    setJobId(id);
    setOpen(false);
  };

  const showOnboarding = composing || jobId === null;

  return (
    <div className="relative h-screen w-full overflow-hidden">
      <Sidebar
        open={sidebarOpen}
        onClose={() => setOpen(false)}
        selectedId={jobId}
        onSelect={handleSelect}
        onNew={handleNew}
        onDeleted={(id) => {
          if (id === jobId) setJobId(null);
        }}
      />

      <main className="relative h-full w-full overflow-y-auto">
        {/* Top-left fixed nav rail: menu + new meeting */}
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
            aria-label="Nouvelle réunion"
            title="Nouvelle réunion"
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
          {showOnboarding ? (
            <OnboardingView
              onJobCreated={(id) => {
                setComposing(false);
                setJobId(id);
              }}
            />
          ) : (
            <JobPanel jobId={jobId} />
          )}
        </div>
      </main>
    </div>
  );
}
