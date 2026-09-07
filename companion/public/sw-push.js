/* Push handlers for the generated service worker (loaded via importScripts). */
self.addEventListener("push", (event) => {
  let data = {};
  try {
    data = event.data ? event.data.json() : {};
  } catch {
    /* ignore malformed payload */
  }
  const title = data.subject || data.title || "FS-Corporation";
  const body = data.body || data.kind || "";
  event.waitUntil(self.registration.showNotification(title, { body, data }));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  event.waitUntil(self.clients.openWindow("/"));
});
