declare global {
  interface Window {
    electronAPI?: { backendUrl: string };
  }
}

const FALLBACK = "http://127.0.0.1:8000";

export function backendUrl(): string {
  if (typeof window !== "undefined" && window.electronAPI?.backendUrl) {
    return window.electronAPI.backendUrl;
  }
  return process.env.NEXT_PUBLIC_BACKEND_URL || FALLBACK;
}

export function apiUrl(path: string): string {
  const base = backendUrl().replace(/\/$/, "");
  return `${base}${path.startsWith("/") ? "" : "/"}${path}`;
}
