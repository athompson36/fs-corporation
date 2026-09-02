/// <reference lib="webworker" />
import { precacheAndRoute } from "workbox-precaching";

declare const self: ServiceWorkerGlobalScope & {
  __WB_MANIFEST: Array<string | { url: string; revision: string | null }>;
};

precacheAndRoute(self.__WB_MANIFEST);

self.addEventListener("push", (event: PushEvent) => {
  let data: Record<string, string> = {};
  try {
    data = event.data ? (event.data.json() as Record<string, string>) : {};
  } catch {
    /* ignore malformed payload */
  }
  const title = data.subject || data.title || "FS-Corporation";
  const body = data.body || data.kind || "";
  event.waitUntil(self.registration.showNotification(title, { body, data }));
});

self.addEventListener("notificationclick", (event: NotificationEvent) => {
  event.notification.close();
  event.waitUntil(self.clients.openWindow("/"));
});
