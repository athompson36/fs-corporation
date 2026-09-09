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

  async delete<T>(path: string, idempotency?: string): Promise<T> {
    const r = await fetch(this.url(path), {
      method: "DELETE",
      headers: headers(this.settings.token, idempotency),
    });
    if (!r.ok) throw new Error(`${r.status}: ${await r.text()}`);
    const text = await r.text();
    return (text ? JSON.parse(text) : {}) as T;
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

  session() {
    return this.get<SessionInfo>("/api/v1/session");
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

  approveFeed(id: string, url: string) {
    return this.post("/api/v1/feeds", { id, url }, `feed-approve-${id}-${Date.now()}`);
  }

  pauseFeed(sourceId: string) {
    return this.post(`/api/v1/feeds/${encodeURIComponent(sourceId)}/pause`, {}, `feed-pause-${sourceId}-${Date.now()}`);
  }

  revokeFeed(sourceId: string) {
    return this.post(`/api/v1/feeds/${encodeURIComponent(sourceId)}/revoke`, {}, `feed-revoke-${sourceId}-${Date.now()}`);
  }

  pollFeed(sourceId: string) {
    return this.post(`/api/v1/feeds/${encodeURIComponent(sourceId)}/poll`, {}, `feed-poll-${sourceId}-${Date.now()}`);
  }

  modelProfiles() {
    return this.get<{ profiles: Record<string, unknown>[] }>("/api/v1/model-profiles");
  }

  financeSummary() {
    return this.get<{
      billed_cost_gross_cents: number;
      billed_adjustment_cents: number;
      billed_cost_cents: number;
      revenue_cents: number;
      open_budget_period: Record<string, unknown> | null;
    }>("/api/v1/finance/summary");
  }

  financeInvoices() {
    return this.get<{ invoices: Record<string, unknown>[] }>("/api/v1/finance/invoices");
  }

  financeInvoice(invoiceId: string) {
    return this.get<Record<string, unknown>>(
      `/api/v1/finance/invoices/${encodeURIComponent(invoiceId)}`,
    );
  }

  financeBilledCosts(opts?: { includeFullyCredited?: boolean; limit?: number }) {
    const q = new URLSearchParams();
    if (opts?.includeFullyCredited) q.set("include_fully_credited", "true");
    if (opts?.limit != null) q.set("limit", String(opts.limit));
    const suffix = q.toString() ? `?${q}` : "";
    return this.get<{ billed_costs: Record<string, unknown>[] }>(
      `/api/v1/finance/billed-costs${suffix}`,
    );
  }

  createFinanceInvoice(periodStart: string, periodEnd: string) {
    return this.post(
      "/api/v1/finance/invoices",
      { period_start: periodStart, period_end: periodEnd },
      `finance-inv-${Date.now()}`,
    );
  }

  financeAdjustments() {
    return this.get<{ adjustments: Record<string, unknown>[] }>("/api/v1/finance/adjustments");
  }

  postFinanceAdjustment(payload: Record<string, unknown>) {
    return this.post("/api/v1/finance/adjustments", payload, `finance-adj-${Date.now()}`);
  }

  financeBudgetPeriods() {
    return this.get<{ periods: Record<string, unknown>[] }>("/api/v1/finance/budget-periods");
  }

  setFinanceBudgetPeriod(payload: Record<string, unknown>) {
    return this.post("/api/v1/finance/budget-periods", payload, `finance-period-${Date.now()}`);
  }

  closeFinanceBudgetPeriod(periodId: string) {
    return this.post(
      `/api/v1/finance/budget-periods/${encodeURIComponent(periodId)}/close`,
      {},
      `finance-close-${periodId}-${Date.now()}`,
    );
  }

  workerHosts() {
    return this.get<{ hosts: Record<string, unknown>[] }>("/api/v1/worker-hosts");
  }

  createWorkerHost(label: string, baseUrl: string) {
    return this.post<{
      result: {
        id: string;
        label: string;
        base_url: string;
        token: string;
        enabled?: boolean;
        state?: string;
      };
    }>(
      "/api/v1/worker-hosts",
      { label, base_url: baseUrl },
      `worker-host-create-${Date.now()}`,
    );
  }

  enableWorkerHost(hostId: string) {
    return this.post(
      `/api/v1/worker-hosts/${encodeURIComponent(hostId)}/enable`,
      {},
      `worker-host-enable-${hostId}-${Date.now()}`,
    );
  }

  disableWorkerHost(hostId: string) {
    return this.post(
      `/api/v1/worker-hosts/${encodeURIComponent(hostId)}/disable`,
      {},
      `worker-host-disable-${hostId}-${Date.now()}`,
    );
  }

  deleteWorkerHost(hostId: string) {
    return this.delete(
      `/api/v1/worker-hosts/${encodeURIComponent(hostId)}`,
      `worker-host-delete-${hostId}-${Date.now()}`,
    );
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

  reorderDepartments(items: { id: string; display_order: number }[]) {
    return this.post(
      "/api/v1/org/departments/reorder",
      { items },
      `reorder-depts-${Date.now()}`,
    );
  }

  scorecard(periodStart?: string, periodEnd?: string) {
    const params = new URLSearchParams();
    if (periodStart) params.set("period_start", periodStart);
    if (periodEnd) params.set("period_end", periodEnd);
    const q = params.toString();
    return this.get<{ metrics: Record<string, unknown> }>(
      `/api/v1/scorecard${q ? `?${q}` : ""}`,
    );
  }

  objectives(status?: string) {
    const q = status ? `?status=${encodeURIComponent(status)}` : "";
    return this.get<{ items: ObjectiveItem[] }>(`/api/v1/objectives${q}`);
  }

  createObjective(payload: Record<string, unknown>) {
    return this.post("/api/v1/objectives", payload, `objective-${Date.now()}`);
  }

  closeObjective(objectiveId: string) {
    return this.post(
      `/api/v1/objectives/${objectiveId}/close`,
      {},
      `objective-close-${objectiveId}`,
    );
  }

  industryPacks() {
    return this.get<{ industry_packs: IndustryPack[] }>("/api/v1/industry-packs");
  }

  divisions() {
    return this.get<{ divisions: DivisionItem[] }>("/api/v1/divisions");
  }

  proposeDivision(industryPackId: string, name: string, mode: string) {
    return this.post(
      "/api/v1/divisions/proposals",
      { pack_id: industryPackId, name, mode },
      `division-propose-${Date.now()}`,
    );
  }

  activateDivision(divisionId: string) {
    return this.post(
      `/api/v1/divisions/${divisionId}/activate`,
      {},
      `division-activate-${divisionId}`,
    );
  }

  deactivateDivision(divisionId: string) {
    return this.post(
      `/api/v1/divisions/${divisionId}/deactivate`,
      {},
      `division-deactivate-${divisionId}`,
    );
  }

  promotions(status?: string) {
    const q = status ? `?status=${encodeURIComponent(status)}` : "";
    return this.get<{ items: PromotionItem[] }>(`/api/v1/promotions${q}`);
  }

  decidePromotion(promotionId: string, decision: string) {
    return this.post(
      `/api/v1/promotions/${promotionId}/decision`,
      { decision },
      `promo-${promotionId}-${decision}`,
    );
  }

  staffingProposals(status?: string) {
    const q = status ? `?status=${encodeURIComponent(status)}` : "";
    return this.get<{ items: StaffingProposal[] }>(`/api/v1/staffing-proposals${q}`);
  }

  scanStaffingGaps() {
    return this.post("/api/v1/staffing-proposals/scan", {}, `staffing-scan-${Date.now()}`);
  }

  decideStaffingProposal(proposalId: string, decision: string) {
    return this.post(
      `/api/v1/staffing-proposals/${proposalId}/decision`,
      { decision },
      `staffing-${proposalId}-${decision}`,
    );
  }

  crossDepartmentRequests() {
    return this.get<{ items: CrossDeptRequest[] }>("/api/v1/cross-department-requests");
  }

  createCrossDepartmentRequest(payload: Record<string, unknown>) {
    return this.post(
      "/api/v1/cross-department-requests",
      payload,
      `cross-dept-${Date.now()}`,
    );
  }

  acceptCrossDepartmentRequest(requestId: string) {
    return this.post(
      `/api/v1/cross-department-requests/${requestId}/accept`,
      {},
      `cross-dept-accept-${requestId}`,
    );
  }

  activity(status = "open") {
    return this.get<{ items: ActivityItem[] }>(
      `/api/v1/activity?status=${encodeURIComponent(status)}`,
    );
  }

  headquarters() {
    return this.get<{ rooms: Record<string, unknown>[] }>("/api/v1/headquarters");
  }

  createDefaultFloorplan() {
    return this.post("/api/v1/floorplans/default", {}, `floorplan-default-${Date.now()}`);
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

  dispatchOptions(projectId: string) {
    return this.get<DispatchOptions>(`/api/v1/projects/${projectId}/dispatch-options`);
  }

  dispatchRecommend(projectId: string, useLive = true) {
    return this.post<{
      result?: DispatchRecommendResult;
    } & DispatchRecommendResult>(
      `/api/v1/projects/${projectId}/dispatch-recommend`,
      { use_live: useLive },
      `dispatch-rec-${projectId}-${Date.now()}`,
    );
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

  companySettings() {
    return this.get<{ items: CompanySetting[] }>("/api/v1/settings");
  }

  patchCompanySettings(updates: Record<string, SettingValue>) {
    return this.patch<{ result: { items: CompanySetting[] } }>(
      "/api/v1/settings",
      { updates },
      `company-settings-${Date.now()}`,
    );
  }

  resetCompanySettings(keys?: string[], allOverlay = false) {
    return this.post<{ result: { items: CompanySetting[] } }>(
      "/api/v1/settings/reset",
      allOverlay ? { all_overlay: true } : { keys: keys || [] },
      `company-settings-reset-${Date.now()}`,
    );
  }

  secretsStatus() {
    return this.get<{ secrets: SecretStatus[] }>("/api/v1/settings/secrets-status");
  }

  pause() {
    return this.post("/api/v1/company/pause", {}, "pause");
  }

  resume() {
    return this.post("/api/v1/company/resume", {}, "resume");
  }
}

export type SessionInfo = {
  principal_id: string;
  kind: string;
  access_level: string | null;
  scopes: string[];
};

export type SettingValue = string | number | boolean;

export type CompanySetting = {
  key: string;
  value: SettingValue;
  default: SettingValue;
  source: "overlay" | "env" | "default";
  type: "int" | "float" | "string" | "bool" | "enum";
  editable: boolean;
  restart_required: boolean;
  description: string;
  min?: number;
  max?: number;
  enum_values?: string[];
};

export type SecretStatus = {
  name: string;
  configured: boolean;
};

export type DispatchTemplate = { id: string; label: string; body: string };

export type DispatchOptions = {
  project_id: string;
  brief_default: string;
  fields: {
    brief: { templates: DispatchTemplate[] };
    acceptance_criteria: { templates: DispatchTemplate[] };
    department_budgets: {
      min_cents: number;
      max_cents: number;
      presets_cents: number[];
    };
  };
  departments: {
    id: string;
    name: string;
    status: string;
    dispatchable: boolean;
    seat_status: string;
    principal_id?: string | null;
  }[];
};

export type DispatchRecommendResult = {
  source: string;
  live_attempted: boolean;
  brief: string;
  acceptance_criteria: string;
  departments: { id: string; budget_cents: number; recommended: boolean }[];
  notes: string[];
};

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

export type ObjectiveItem = {
  id: string;
  title: string;
  due_at: string;
  status: string;
  division_id?: string | null;
};

export type IndustryPack = {
  id: string;
  industry: string;
  minimal_departments: unknown[];
  full_departments: unknown[];
};

export type DivisionItem = {
  id: string;
  name: string;
  industry_pack_id: string;
  mode: string;
  status: string;
};

export type PromotionItem = {
  id: string;
  employee_id: string;
  from_level: string;
  to_level: string;
  status: string;
};

export type StaffingProposal = {
  id: string;
  kind: string;
  position_id: string;
  cost_estimate_cents: number;
  rationale: string;
  status: string;
};

export type CrossDeptRequest = {
  id: string;
  project_id: string;
  requesting_department_id: string;
  delivering_department_id: string;
  subject: string;
  status: string;
};

export type ActivityItem = {
  id: string;
  kind: string;
  status: string;
  room_id?: string | null;
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
