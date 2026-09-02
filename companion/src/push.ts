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

function isIos(): boolean {
  if (typeof navigator === "undefined") return false;
  return /iPad|iPhone|iPod/.test(navigator.userAgent)
    || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
}

function isStandaloneDisplay(): boolean {
  if (typeof window === "undefined") return false;
  const media = window.matchMedia("(display-mode: standalone)").matches;
  const legacy = Boolean((navigator as Navigator & { standalone?: boolean }).standalone);
  return media || legacy;
}

/** Register Web Push when VAPID is live and this browser supports it. Returns a user-facing status line. */
export async function ensureWebPushRegistration(api: ApiClient): Promise<string> {
  if (isIos() && !isStandaloneDisplay()) {
    return "On iPhone/iPad: Safari Share → Add to Home Screen, then open the home-screen icon (Safari tabs cannot receive Web Push).";
  }
  if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
    return "Push not supported in this browser; companion will keep polling every 15s.";
  }
  let status: PushStatus;
  try {
    status = await api.get<PushStatus>("/api/v1/push/status");
  } catch (e) {
    return `Could not read push status: ${e instanceof Error ? e.message : String(e)}`;
  }
  if (!status.configured || !status.application_server_key) {
    return "VAPID not configured on server; polling every 15s.";
  }
  if (!status.live) {
    return "VAPID keys present but not live; check contact email / private key on the host.";
  }
  let reg: ServiceWorkerRegistration;
  try {
    reg = await navigator.serviceWorker.ready;
  } catch (e) {
    return `Service worker not ready: ${e instanceof Error ? e.message : String(e)}`;
  }
  const existing = await reg.pushManager.getSubscription();
  const endpoint = existing?.endpoint;
  if (endpoint && localStorage.getItem(PUSH_REGISTERED_KEY) === endpoint) {
    return "Push notifications enabled.";
  }
  const permission = await Notification.requestPermission();
  if (permission !== "granted") {
    return "Notification permission denied or dismissed; polling every 15s. Re-enable in system Settings if needed.";
  }
  let subscription = existing;
  if (!subscription) {
    try {
      subscription = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(status.application_server_key) as BufferSource,
      });
    } catch (e) {
      return `Push subscribe failed: ${e instanceof Error ? e.message : String(e)}`;
    }
  }
  const json = subscription.toJSON();
  if (!json.endpoint || !json.keys) {
    return "Could not read push subscription; polling every 15s.";
  }
  try {
    await api.post(
      "/api/v1/push/subscriptions",
      { endpoint: json.endpoint, keys: json.keys },
      `push-${json.endpoint}`,
    );
  } catch (e) {
    return `Server rejected push registration: ${e instanceof Error ? e.message : String(e)}`;
  }
  localStorage.setItem(PUSH_REGISTERED_KEY, json.endpoint);
  return "Push notifications enabled.";
}
