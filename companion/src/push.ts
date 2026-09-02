import type { ApiClient } from "./api/client";

const PUSH_REGISTERED_KEY = "fs-corp-push-endpoint";

export type PushStatus = {
  configured?: boolean;
  live?: boolean;
  application_server_key?: string;
};

function urlBase64ToUint8Array(base64: string): Uint8Array {
  const padding = "=".repeat((4 - (base64.length % 4)) % 4);
  const normalized = (base64 + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(normalized);
  const out = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i += 1) out[i] = raw.charCodeAt(i);
  return out;
}

/** Register Web Push when VAPID is live and this browser supports it. Returns a user-facing status line. */
export async function ensureWebPushRegistration(api: ApiClient): Promise<string | null> {
  if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
    return "Push not supported in this browser; polling every 15s.";
  }
  let status: PushStatus;
  try {
    status = await api.get<PushStatus>("/api/v1/push/status");
  } catch {
    return null;
  }
  if (!status.configured || !status.application_server_key) {
    return "VAPID not configured on server; polling every 15s.";
  }
  const reg = await navigator.serviceWorker.ready;
  const existing = await reg.pushManager.getSubscription();
  const endpoint = existing?.endpoint;
  if (endpoint && localStorage.getItem(PUSH_REGISTERED_KEY) === endpoint) {
    return "Push notifications enabled.";
  }
  const permission = await Notification.requestPermission();
  if (permission !== "granted") {
    return "Notification permission denied; polling every 15s.";
  }
  const subscription = existing ?? (await reg.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(status.application_server_key) as BufferSource,
  }));
  const json = subscription.toJSON();
  if (!json.endpoint || !json.keys) {
    return "Could not read push subscription; polling every 15s.";
  }
  await api.post(
    "/api/v1/push/subscriptions",
    { endpoint: json.endpoint, keys: json.keys },
    `push-${json.endpoint}`,
  );
  localStorage.setItem(PUSH_REGISTERED_KEY, json.endpoint);
  return "Push notifications enabled.";
}
