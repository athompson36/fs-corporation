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
  if (import.meta.env.PROD && typeof window !== "undefined") {
    return "";
  }
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

  async patch<T>(path: string, payload: object, idempotency?: string): Promise<T> {
    const r = await fetch(this.url(path), {
      method: "PATCH",
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

  localRepos() {
    return this.get<{
      root: string;
      present: boolean;
      candidates: {
        id: string;
        path: string;
        has_git: boolean;
        remote_url: string | null;
        enrolled: boolean;
      }[];
    }>("/api/v1/local-repos");
  }

  health() {
    return this.get<{ ok: boolean; version?: string; db?: string }>("/api/v1/health");
  }

  workersStatus() {
    return this.get<Record<string, unknown>>("/api/v1/workers/status");
  }

  workerCard(employeeId: string) {
    return this.get<WorkerCard>(`/api/v1/workers/${employeeId}/card`);
  }

  setWorkerSprite(employeeId: string, sprite: Record<string, unknown>) {
    return this.post(
      `/api/v1/workers/${employeeId}/sprite`,
      sprite,
      `worker-sprite-${employeeId}-${Date.now()}`,
    );
  }

  updateWorkerProfile(employeeId: string, profile: Record<string, unknown>) {
    return this.patch(
      `/api/v1/workers/${employeeId}/profile`,
      profile,
      `worker-profile-${employeeId}-${Date.now()}`,
    );
  }

  modelStatus() {
    return this.get<Record<string, unknown>>("/api/v1/model/status");
  }

  githubStatus() {
    return this.get<Record<string, unknown>>("/api/v1/github/status");
  }

  pushStatus() {
    return this.get<Record<string, unknown>>("/api/v1/push/status");
  }

  chatdevStatus() {
    return this.get<Record<string, unknown>>("/api/v1/chatdev/status");
  }

  feeds() {
    return this.get<{ feeds: Record<string, unknown>[] }>("/api/v1/feeds");
  }

  slos() {
    return this.get<Record<string, unknown>>("/api/v1/slos");
  }

  project(id: string) {
    return this.get<Record<string, unknown>>(`/api/v1/projects/${id}`);
  }

  org() {
    return this.get<{ departments: OrgDepartment[] }>("/api/v1/org");
  }

  createDepartment(payload: Record<string, unknown>) {
    return this.post("/api/v1/org/departments", payload, `create-dept-${Date.now()}`);
  }

  updateDepartment(departmentId: string, payload: Record<string, unknown>) {
    return this.patch(`/api/v1/org/departments/${departmentId}`, payload, `update-dept-${Date.now()}`);
  }

  retireDepartment(departmentId: string) {
    return this.post(
      `/api/v1/org/departments/${departmentId}/retire`,
      {},
      `retire-dept-${Date.now()}`,
    );
  }

  createPosition(departmentId: string, title: string) {
    return this.post(
      "/api/v1/org/positions",
      { department_id: departmentId, title },
      `create-pos-${Date.now()}`,
    );
  }

  appointHead(departmentId: string, principalId: string) {
    return this.post(
      "/api/v1/org/heads",
      { department_id: departmentId, principal_id: principalId },
      `appoint-head-${Date.now()}`,
    );
  }

  vacateHead(departmentId: string) {
    return this.post(
      "/api/v1/org/heads",
      { department_id: departmentId, vacate: true },
      `vacate-head-${Date.now()}`,
    );
  }

  assignPosition(positionId: string, principalId: string, reportsToSeatId?: string) {
    return this.post(
      "/api/v1/org/assignments",
      {
        position_id: positionId,
        principal_id: principalId,
        reports_to_seat_id: reportsToSeatId || undefined,
      },
      `assign-position-${Date.now()}`,
    );
  }

  releaseAssignment(assignmentId: string) {
    return this.post(
      "/api/v1/org/assignments",
      { assignment_id: assignmentId, release: true },
      `release-assignment-${Date.now()}`,
    );
  }

  headInbox() {
    return this.get<{ items: HeadDispatch[] }>("/api/v1/inbox/head");
  }

  assignDispatch(dispatchId: string, assignee: string, action: string, costCents: number) {
    return this.post(
      `/api/v1/dispatches/${dispatchId}/assign`,
      { assignee, action, cost_cents: costCents },
      `assign-${dispatchId}-${assignee}`,
    );
  }

  activateDepartment(projectId: string, departmentId: string) {
    return this.post(
      `/api/v1/projects/${projectId}/departments/${departmentId}/activate`,
      {},
      `activate-${projectId}-${departmentId}`,
    );
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

  assignGithub(projectId: string, upstream: string) {
    return this.post(`/api/v1/projects/${projectId}/github-assign`, { upstream }, `gh-assign-${projectId}`);
  }

  dispatchBrief(
    projectId: string,
    brief: string,
    departmentBudgets: Record<string, number>,
    acceptance_criteria: string,
  ) {
    return this.post(`/api/v1/projects/${projectId}/dispatch-brief`, {
      brief, department_budgets: departmentBudgets, acceptance_criteria,
    }, `dispatch-${projectId}`);
  }

  pushSubscriptions() {
    return this.get<{ subscriptions: { id: string; endpoint: string; created_at: string; status: string }[] }>(
      "/api/v1/push/subscriptions",
    );
  }

  pushNotify(subject: string) {
    return this.post<{
      result?: { deliveries?: { id: string; status: string; subject?: string }[] };
      deliveries?: { id: string; status: string; subject?: string }[];
    }>(
      "/api/v1/push/notify",
      { kind: "owner_inbox", subject, test: true },
      `push-test-${Date.now()}`,
    );
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

export type OrgAssignment = {
  id: string;
  position_id: string;
  department_id: string;
  principal_id: string;
  status: string;
};

export type OrgDepartment = {
  id: string;
  name: string;
  initially_active: number | boolean;
  origin?: string;
  status?: string;
  display_order?: number;
  parent_department_id?: string | null;
  seat: {
    id?: string;
    status: string;
    principal_id: string | null;
    title: string;
  };
  assignments: OrgAssignment[];
  positions?: { id: string; title: string; status: string }[];
};

export type HeadDispatch = {
  id: string;
  project_id: string;
  department_id: string;
  head_principal_id: string | null;
  brief: string;
  acceptance_criteria: string;
  budget_cents: number;
  status: string;
};

export type WorkerCard = {
  identity: {
    id: string;
    display_name: string;
    position_id: string;
    headline: string | null;
    background: string;
    attributes: Record<string, unknown>;
  };
  viewpoint: string | null;
  strengths: string[];
  skills: { id: string; name: string; platform: string }[];
  position_assignments: {
    id: string;
    position_id: string;
    department_id: string;
    title: string;
  }[];
  sprite: {
    sprite_set: string;
    body: string | null;
    palette: string | null;
    accessories: Record<string, unknown> | unknown[];
  } | null;
  sprite_placeholder: { kind: "neutral"; label: string };
};
