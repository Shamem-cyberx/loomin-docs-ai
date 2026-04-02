/** WebSocket URL for Hocuspocus (same host as UI, port 1234 by default). */

export function getCollabWsUrl(): string {
  const explicit = import.meta.env.VITE_COLLAB_WS as string | undefined;
  if (explicit) return explicit.replace(/\/$/, "");
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  const port = import.meta.env.VITE_COLLAB_PORT ?? "1234";
  return `${proto}//${window.location.hostname}:${port}`;
}

export function isCollabEnabled(): boolean {
  return import.meta.env.VITE_COLLAB_ENABLED !== "false";
}

export const COLLAB_ROOM = "loomin-main-doc";

export function getCollaborationProfile(): { name: string; color: string } {
  let name = localStorage.getItem("loomin_display_name");
  if (!name) {
    name = `Guest-${Math.random().toString(36).slice(2, 7)}`;
    localStorage.setItem("loomin_display_name", name);
  }
  let color = localStorage.getItem("loomin_color");
  if (!color) {
    color = `#${Math.floor(Math.random() * 0xffffff)
      .toString(16)
      .padStart(6, "0")}`;
    localStorage.setItem("loomin_color", color);
  }
  return { name, color };
}
