export type Settings = {
  baseUrl: string;
  token: string;
  access_level?: string;
  label?: string;
  scopes?: string[];
};

const SETTINGS_KEY = "fs-corp-companion-settings";

/** Build-time default; empty string means same-origin (relative URLs). */
export function defaultApiBase(): string {
  const env = import.meta.env.VITE_API_BASE;
  if (typeof env === "string") return env;
  return "http://127.0.0.1:8000";
}

export function loadSettings(): Settings {
  try {
    const raw = localStorage.getItem(SETTINGS_KEY);
    if (raw) return JSON.parse(raw);
  } catch {
    /* ignore */
  }
  return { baseUrl: defaultApiBase(), token: "" };
}

export function saveSettings(s: Settings) {
  localStorage.setItem(SETTINGS_KEY, JSON.stringify(s));
}

function headers(token: string, idempotency?: string): HeadersInit {
  const h: Record<string, string> = { Authorization: `Bearer ${token}` };
  if (idempotency) h["Idempotency-Key"] = idempotency;
  return h;
}

export class ApiClient {
  constructor(private settings: Settings) {}

  private url(path: string) {
    const base = this.settings.baseUrl.replace(/\/$/, "");
    if (!base) return path;
    return `${base}${path}`;
  }

  async get<T>(path: string): Promise<T> {
    const r = await fetch(this.url(path), { headers: headers(this.settings.token) });
    if (!r.ok) throw new Error(`${r.status}: ${await r.text()}`);
    return r.json();
  }

  async post<T>(path: string, payload: object, idempotency?: string): Promise<T> {
    const r = await fetch(this.url(path), {
      method: "POST",
      headers: { ...headers(this.settings.token, idempotency), "Content-Type": "application/json" },
      body: JSON.stringify({ payload }),
    });
    if (!r.ok) throw new Error(`${r.status}: ${await r.text()}`);
    return r.json();
  }

  dashboard() {
    return this.get<Record<string, unknown>>("/api/v1/dashboard");
  }

  projects() {
    return this.get<{ projects: Record<string, unknown>[] }>("/api/v1/projects");
  }

  project(id: string) {
    return this.get<Record<string, unknown>>(`/api/v1/projects/${id}`);
  }

  decisions() {
    return this.get<{ items: DecisionItem[] }>("/api/v1/decisions/inbox");
  }

  ownerInbox(status?: string) {
    const q = status ? `?status=${status}` : "";
    return this.get<{ items: OwnerRequest[] }>(`/api/v1/owner-inbox${q}`);
  }

  escalateOwner(
    departmentId: string,
    kind: string,
    subject: string,
    body: string,
    projectId?: string,
  ) {
    return this.post(
      "/api/v1/owner-inbox",
      { department_id: departmentId, kind, subject, body, project_id: projectId },
      `escalate-${Date.now()}`,
    );
  }

  respondOwner(id: string, response: string) {
    return this.post(`/api/v1/owner-inbox/${id}/respond`, { response }, `respond-${id}`);
  }

  policyDecision(id: string, decision: string, reason: string) {
    return this.post(`/api/v1/policy-proposals/${id}/decision`, { decision, reason }, `policy-${id}-${decision}`);
  }

  consultantDecision(id: string, decision: string, reason: string) {
    return this.post(`/api/v1/consultant-proposals/${id}/decision`, { decision, reason }, `consultant-${id}-${decision}`);
  }

  enrollProject(id: string, brief: string) {
    return this.post("/api/v1/projects", { id, brief }, `enroll-${id}`);
  }

  dispatchBrief(projectId: string, brief: string, departments: string[], acceptance_criteria: string, budget_cents: number) {
    return this.post(`/api/v1/projects/${projectId}/dispatch-brief`, {
      brief, departments, acceptance_criteria, budget_cents,
    }, `dispatch-${projectId}`);
  }

  pause() {
    return this.post("/api/v1/company/pause", {}, "pause");
  }

  resume() {
    return this.post("/api/v1/company/resume", {}, "resume");
  }
}

export type PairingRedeem = {
  token: string;
  principal_id: string;
  base_url: string;
  access_level: string;
  label: string;
  scopes: string[];
  tailscale_auth_key?: string;
  vpn: { provider: string; status: string };
};

export async function redeemPairing(baseUrl: string, ticket: string): Promise<PairingRedeem> {
  const root = baseUrl.replace(/\/$/, "");
  const r = await fetch(`${root}/api/v1/remote-access/redeem`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ payload: { ticket } }),
  });
  if (!r.ok) throw new Error(`${r.status}: ${await r.text()}`);
  return r.json();
}

export type DecisionItem = {
  id: string;
  kind: string;
  title: string;
  summary: string;
  project_id: string | null;
};

export type OwnerRequest = {
  id: string;
  subject: string;
  body: string;
  kind: string;
  department_id: string;
  status: string;
};
