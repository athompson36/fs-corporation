import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ApiClient,
  ActivityItem,
  CrossDeptRequest,
  DecisionItem,
  DivisionItem,
  HeadDispatch,
  IndustryPack,
  ObjectiveItem,
  OrgDepartment,
  OwnerRequest,
  PromotionItem,
  StaffingProposal,
  WorkerCard,
  loadSettings,
  redeemPairing,
  saveSettings,
  type Settings,
} from "./api/client";
import { ensureWebPushRegistration } from "./push";
import {
  canApprove,
  canEnroll,
  canEscalate,
  canPause,
  canManageOrganization,
  canRespondInbox,
  canResume,
} from "./scopes";

type Tab =
  | "dashboard"
  | "projects"
  | "organization"
  | "corporate"
  | "decisions"
  | "inbox"
  | "diagnostics"
  | "settings";

type LocalCandidate = {
  id: string;
  path: string;
  has_git: boolean;
  remote_url: string | null;
  enrolled: boolean;
};

type DiagBlock = { label: string; ok: boolean; data?: unknown; error?: string };

function pairingTicketFromHash(): string | null {
  const m = window.location.hash.match(/^#fs-pair=(.+)$/);
  return m ? decodeURIComponent(m[1]) : null;
}

function clearPairingHash() {
  if (window.location.hash.startsWith("#fs-pair=")) {
    window.history.replaceState(null, "", window.location.pathname + window.location.search);
  }
}

export default function App() {
  const [settings, setSettings] = useState<Settings>(loadSettings);
  const [tab, setTab] = useState<Tab>("dashboard");
  const [error, setError] = useState<string | null>(null);
  const [offline, setOffline] = useState(false);
  const [pairing, setPairing] = useState(false);
  const [manualTicket, setManualTicket] = useState("");
  const [dashboard, setDashboard] = useState<Record<string, unknown> | null>(null);
  const [projects, setProjects] = useState<Record<string, unknown>[]>([]);
  const [decisions, setDecisions] = useState<DecisionItem[]>([]);
  const [inbox, setInbox] = useState<OwnerRequest[]>([]);
  const [organization, setOrganization] = useState<OrgDepartment[]>([]);
  const [headInbox, setHeadInbox] = useState<HeadDispatch[]>([]);
  const [selectedProject, setSelectedProject] = useState<string | null>(null);
  const [projectDetail, setProjectDetail] = useState<Record<string, unknown> | null>(null);
  const [ghUpstream, setGhUpstream] = useState("");
  const [ghProjectId, setGhProjectId] = useState("");
  const [ghBusy, setGhBusy] = useState(false);
  const [ghResult, setGhResult] = useState<string | null>(null);
  const [localCandidates, setLocalCandidates] = useState<LocalCandidate[]>([]);
  const [localReposRoot, setLocalReposRoot] = useState<string | null>(null);
  const [diagBlocks, setDiagBlocks] = useState<DiagBlock[]>([]);
  const [diagBusy, setDiagBusy] = useState(false);
  const [pushStatus, setPushStatus] = useState<string | null>(null);
  const [pushSubscriptions, setPushSubscriptions] = useState<{ id: string; endpoint: string }[]>([]);
  const [activateProjectId, setActivateProjectId] = useState("");
  const [activateDepartmentId, setActivateDepartmentId] = useState("");
  const [appointHeadDepartment, setAppointHeadDepartment] = useState("");
  const [appointHeadPrincipal, setAppointHeadPrincipal] = useState("");
  const [vacateHeadDepartment, setVacateHeadDepartment] = useState("");
  const [positionId, setPositionId] = useState("");
  const [positionPrincipal, setPositionPrincipal] = useState("");
  const [positionReportsTo, setPositionReportsTo] = useState("");
  const [releaseAssignmentId, setReleaseAssignmentId] = useState("");
  const [assignDispatchId, setAssignDispatchId] = useState("");
  const [assignAssignee, setAssignAssignee] = useState("");
  const [assignAction, setAssignAction] = useState("");
  const [assignCost, setAssignCost] = useState("");
  const [dispatchBrief, setDispatchBrief] = useState("");
  const [dispatchCriteria, setDispatchCriteria] = useState("");
  const [dispatchBudgets, setDispatchBudgets] = useState("");
  const [scorecardMetrics, setScorecardMetrics] = useState<Record<string, unknown> | null>(null);
  const [objectives, setObjectives] = useState<ObjectiveItem[]>([]);
  const [industryPacks, setIndustryPacks] = useState<IndustryPack[]>([]);
  const [divisions, setDivisions] = useState<DivisionItem[]>([]);
  const [promotions, setPromotions] = useState<PromotionItem[]>([]);
  const [staffingProposals, setStaffingProposals] = useState<StaffingProposal[]>([]);
  const [crossDept, setCrossDept] = useState<CrossDeptRequest[]>([]);
  const [activityItems, setActivityItems] = useState<ActivityItem[]>([]);
  const [hqRoomCount, setHqRoomCount] = useState(0);
  const [workerLookupId, setWorkerLookupId] = useState("");
  const [workerCard, setWorkerCard] = useState<WorkerCard | null>(null);

  const scopes = settings.scopes;
  const api = useMemo(() => new ApiClient(settings), [settings]);

  const applyPairing = useCallback(async (ticket: string, baseUrl?: string) => {
    setPairing(true);
    setError(null);
    try {
      const origin = baseUrl || window.location.origin || settings.baseUrl || defaultApiBaseFromWindow();
      const data = await redeemPairing(origin, ticket);
      const next: Settings = {
        baseUrl: data.base_url || origin,
        token: data.token,
        access_level: data.access_level,
        label: data.label,
        scopes: data.scopes,
      };
      saveSettings(next);
      setSettings(next);
      clearPairingHash();
      if (data.tailscale_auth_key) {
        setError(
          "Paired. Auth key received — use the native companion (iOS or Android) to copy it into Tailscale "
          + "(Use an auth key), or paste it manually in the Tailscale app, then open the companion on the tailnet.",
        );
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setPairing(false);
    }
  }, [settings.baseUrl]);

  useEffect(() => {
    const ticket = pairingTicketFromHash();
    if (ticket) {
      applyPairing(ticket);
    }
  }, [applyPairing]);

  const refresh = useCallback(async () => {
    if (!settings.token) {
      setError(null);
      return;
    }
    setError(null);
    setOffline(false);
    try {
      const [d, p, dec, own, org, heads, local, score, objs, packs, divs, promos, staffing, xd, act, hq] =
        await Promise.all([
          api.dashboard(),
          api.projects(),
          api.decisions(),
          api.ownerInbox("open"),
          api.org(),
          api.headInbox(),
          api.localRepos().catch(() => null),
          api.scorecard().catch(() => null),
          api.objectives().catch(() => ({ items: [] as ObjectiveItem[] })),
          api.industryPacks().catch(() => ({ industry_packs: [] as IndustryPack[] })),
          api.divisions().catch(() => ({ divisions: [] as DivisionItem[] })),
          api.promotions("pending").catch(() => ({ items: [] as PromotionItem[] })),
          api.staffingProposals("pending").catch(() => ({ items: [] as StaffingProposal[] })),
          api.crossDepartmentRequests().catch(() => ({ items: [] as CrossDeptRequest[] })),
          api.activity().catch(() => ({ items: [] as ActivityItem[] })),
          api.headquarters().catch(() => ({ rooms: [] as Record<string, unknown>[] })),
        ]);
      setDashboard(d);
      setProjects(p.projects);
      setDecisions(dec.items);
      setInbox(own.items);
      setOrganization(org.departments);
      setHeadInbox(heads.items);
      setScorecardMetrics(score?.metrics ?? null);
      setObjectives(objs.items);
      setIndustryPacks(packs.industry_packs);
      setDivisions(divs.divisions);
      setPromotions(promos.items);
      setStaffingProposals(staffing.items);
      setCrossDept(xd.items);
      setActivityItems(act.items);
      setHqRoomCount((hq.rooms || []).length);
      if (local) {
        setLocalReposRoot(local.root);
        setLocalCandidates(local.candidates);
      }
    } catch (e) {
      setOffline(true);
      setError(e instanceof Error ? e.message : String(e));
    }
  }, [api, settings.token]);

  const loadDiagnostics = useCallback(async () => {
    if (!settings.token) return;
    setDiagBusy(true);
    const probes: { label: string; run: () => Promise<unknown> }[] = [
      { label: "health", run: () => api.health() },
      { label: "workers", run: () => api.workersStatus() },
      { label: "model", run: () => api.modelStatus() },
      { label: "github", run: () => api.githubStatus() },
      { label: "push", run: () => api.pushStatus() },
      { label: "chatdev", run: () => api.chatdevStatus() },
      { label: "feeds", run: () => api.feeds() },
      { label: "slos", run: () => api.slos() },
      { label: "local-repos", run: () => api.localRepos() },
    ];
    const settled = await Promise.all(
      probes.map(async (p) => {
        try {
          return { label: p.label, ok: true, data: await p.run() } as DiagBlock;
        } catch (e) {
          return { label: p.label, ok: false, error: e instanceof Error ? e.message : String(e) } as DiagBlock;
        }
      }),
    );
    setDiagBlocks(settled);
    setDiagBusy(false);
  }, [api, settings.token]);

  useEffect(() => {
    if (!settings.token) return;
    refresh();
    const id = setInterval(refresh, 15000);
    return () => clearInterval(id);
  }, [refresh, settings.token]);

  useEffect(() => {
    if (tab === "diagnostics" && settings.token) {
      loadDiagnostics();
    }
  }, [tab, settings.token, loadDiagnostics]);

  useEffect(() => {
    const manualOwnerToken = Boolean(settings.token) && !scopes?.length;
    if (!settings.token || (!canPause(scopes) && !manualOwnerToken)) {
      setPushStatus(
        settings.token
          ? "This pairing level cannot register push (needs company.pause). Re-pair as Admin / CEO mobile."
          : null,
      );
      return;
    }
    ensureWebPushRegistration(api)
      .then((msg) => setPushStatus(msg))
      .catch((e) => setPushStatus(e instanceof Error ? e.message : String(e)));
    api.pushSubscriptions()
      .then((r) => setPushSubscriptions(r.subscriptions.map((s) => ({ id: s.id, endpoint: s.endpoint }))))
      .catch(() => setPushSubscriptions([]));
  }, [api, settings.token, scopes]);

  useEffect(() => {
    if (!selectedProject || !settings.token) {
      setProjectDetail(null);
      return;
    }
    api.project(selectedProject).then(setProjectDetail).catch((e) => setError(String(e)));
  }, [api, selectedProject, settings.token]);

  async function decide(item: DecisionItem, decision: string) {
    const reason = decision === "approved" ? "Approved from mobile companion" : "Rejected from mobile companion";
    if (item.kind === "policy") await api.policyDecision(item.id, decision, reason);
    else if (item.kind === "consultant") await api.consultantDecision(item.id, decision, reason);
    else setError("Expansion decisions: use the CEO desk for now.");
    await refresh();
  }

  async function respond(req: OwnerRequest) {
    const response = window.prompt(`Response to: ${req.subject}`);
    if (!response) return;
    await api.respondOwner(req.id, response);
    await refresh();
  }

  async function escalate() {
    const departmentId = window.prompt("Department id", "engineering");
    const subject = window.prompt("Subject");
    const body = window.prompt("Message");
    if (!departmentId || !subject || !body) return;
    await api.escalateOwner(departmentId, "escalation", subject, body);
    await refresh();
  }

  function save(s: Settings) {
    saveSettings(s);
    setSettings(s);
  }

  const company = (dashboard?.company ?? {}) as Record<string, unknown>;
  const pad = (n: number) => String(n).padStart(2, "0");
  const accessBadge = settings.access_level === "read_only"
    ? "Read only"
    : settings.label || (settings.access_level ? settings.access_level : null);
  const canManageOrg = canManageOrganization(scopes);

  function departmentBudgetsFromLines(raw: string): Record<string, number> {
    return Object.fromEntries(
      raw.split(/\n/)
        .map((line) => {
          const [id, amount] = line.split("=");
          return [id?.trim(), Number(amount?.trim())] as const;
        })
        .filter(([id, amount]) => Boolean(id) && Number.isInteger(amount) && amount >= 0),
    );
  }

  if (!settings.token) {
    return (
      <div className="app" data-theme="cosmic-glass">
        <h1>FS-Corporation</h1>
        <section className="card">
          <p className="lede">Scan the pairing QR from the CEO desk to connect this device.</p>
          {pairing && <p className="muted">Redeeming pairing ticket…</p>}
          {error && <p className="error">{error}</p>}
          <label htmlFor="manual-ticket">Or paste pairing ticket (dev)</label>
          <input
            id="manual-ticket"
            type="text"
            value={manualTicket}
            onChange={(e) => setManualTicket(e.target.value)}
            placeholder="ticket from desk (not shown in QR)"
          />
          <label htmlFor="pair-base">API base URL</label>
          <input
            id="pair-base"
            type="text"
            value={settings.baseUrl}
            onChange={(e) => save({ ...settings, baseUrl: e.target.value })}
          />
          <div className="actions">
            <button
              className="primary"
              type="button"
              disabled={pairing || !manualTicket.trim()}
              onClick={() => applyPairing(manualTicket.trim(), settings.baseUrl)}
            >
              Pair device
            </button>
          </div>
        </section>
      </div>
    );
  }

  return (
    <div className="app" data-theme="cosmic-glass">
      <h1>FS-Corporation {accessBadge && <span className="tag tag-proposal">{accessBadge}</span>}</h1>
      {offline && <div className="offline">Cannot reach control service</div>}
      {error && <p className="error">{error}</p>}

      {tab === "dashboard" && (
        <section>
          <p className="lede">CEO companion — reads persisted state only.</p>
          <div className="metrics">
            <div className="card metric"><h2>Projects</h2><div className="value">{pad(projects.length)}</div></div>
            <div className="card metric"><h2>Decisions</h2><div className="value">{pad(decisions.length)}</div></div>
            <div className="card metric"><h2>Inbox</h2><div className="value">{pad(Number(dashboard?.owner_inbox_open ?? inbox.length))}</div></div>
          </div>
          <div className="card">
            <div>Policy v{String(company.policy_version ?? "?")}</div>
            <div>Paused: {String(company.paused ?? false)}</div>
            <div>Simulated spend: {String(company.simulated_spend_cents ?? 0)}¢</div>
            <div>Reserved: {String(company.reserved_cents ?? 0)}¢</div>
            <div>Open owner inbox: {String(dashboard?.owner_inbox_open ?? 0)}</div>
            <div>Pending decisions: {String((dashboard?.pending_decisions as unknown[])?.length ?? 0)}</div>
            <div className="actions">
              {canResume(scopes) && (
                <button className="primary" type="button" onClick={() => api.resume().then(refresh)}>Resume</button>
              )}
              {canPause(scopes) && (
                <button className="danger" type="button" onClick={() => api.pause().then(refresh)}>Pause</button>
              )}
              <button type="button" onClick={refresh}>Refresh</button>
            </div>
          </div>
          {(dashboard?.department_queues as { name: string; open_count: number }[] | undefined)?.map((d) => (
            <div key={d.name} className="card muted">{d.name}: {d.open_count} queued</div>
          ))}
        </section>
      )}

      {tab === "projects" && (
        <section>
          {!selectedProject ? (
            <>
              {projects.map((p) => (
                <div key={String(p.id)} className="card">
                  <strong>{String(p.id)}</strong>
                  <div className="muted">{String(p.brief)}</div>
                  <div className="muted">Blockers: {(p.blockers as string[])?.join(", ") || "none"}</div>
                  <div className="actions">
                    <button type="button" onClick={() => setSelectedProject(String(p.id))}>Details</button>
                  </div>
                </div>
              ))}
              <div className="card">
                <h2>Local candidates</h2>
                <p className="muted">
                  Folders under {localReposRoot || "local repos/"}. Tap Enroll to create a company project.
                </p>
                {localCandidates.map((c) => (
                  <div key={c.id} style={{ marginBottom: "0.75rem" }}>
                    <strong>{c.id}</strong>
                    <div className="muted">
                      {c.enrolled ? "enrolled" : "not enrolled"}
                      {c.has_git ? " · git" : ""}
                      {c.remote_url ? ` · ${c.remote_url}` : ""}
                    </div>
                    {canEnroll(scopes) && !c.enrolled && (
                      <div className="actions">
                        <button
                          className="primary"
                          type="button"
                          onClick={async () => {
                            try {
                              await api.enrollProject(c.id, c.remote_url || `Local repo ${c.path}`);
                              await refresh();
                            } catch (e) {
                              setError(String(e));
                            }
                          }}
                        >
                          Enroll
                        </button>
                      </div>
                    )}
                  </div>
                ))}
                {!localCandidates.length && (
                  <p className="muted">No local folders found (add directories under local repos/).</p>
                )}
              </div>
              {canEnroll(scopes) && (
                <div className="card">
                  <h2>Assign GitHub by address</h2>
                  <p className="muted">Paste upstream only. Creates same-owner {"{repo}"}-corp for writes.</p>
                  <label className="muted" htmlFor="gh-upstream">Upstream (owner/repo or github.com URL)</label>
                  <input
                    id="gh-upstream"
                    type="text"
                    value={ghUpstream}
                    placeholder="owner/repo"
                    onChange={(e) => {
                      const v = e.target.value;
                      setGhUpstream(v);
                      const m = v.trim().replace(/\.git\/?$/, "").match(/github\.com\/([^/\s]+)\/([^/\s]+)|([^/\s]+)\/([^/\s]+)/);
                      if (m && !ghProjectId) {
                        const name = (m[2] || m[4] || "").replace(/\.git$/, "");
                        if (name) setGhProjectId(name);
                      }
                    }}
                  />
                  <label className="muted" htmlFor="gh-project">Company project id</label>
                  <input
                    id="gh-project"
                    type="text"
                    value={ghProjectId}
                    placeholder="project-id"
                    onChange={(e) => setGhProjectId(e.target.value)}
                  />
                  <div className="actions">
                    <button
                      className="primary"
                      type="button"
                      disabled={ghBusy || !ghUpstream.trim() || !ghProjectId.trim()}
                      onClick={async () => {
                        setGhBusy(true);
                        setError(null);
                        setGhResult(null);
                        try {
                          const out = await api.assignGithub(ghProjectId.trim(), ghUpstream.trim()) as {
                            result?: {
                              upstream?: { full_name?: string; id?: string };
                              write_repo?: { full_name?: string; id?: string };
                              created_write_repo?: boolean;
                            };
                          };
                          const r = out.result || out;
                          setGhResult(
                            `Upstream ${(r as {upstream?:{full_name?:string}}).upstream?.full_name} → write ` +
                            `${(r as {write_repo?:{full_name?:string}}).write_repo?.full_name}` +
                            `${(r as {created_write_repo?:boolean}).created_write_repo ? " (created)" : " (existing)"}`,
                          );
                          await refresh();
                        } catch (e) {
                          setError(String(e));
                        } finally {
                          setGhBusy(false);
                        }
                      }}
                    >
                      Assign GitHub
                    </button>
                  </div>
                  {ghResult && <p className="muted">{ghResult}</p>}
                </div>
              )}
              {canEnroll(scopes) && (
                <div className="actions">
                  <button className="primary" type="button" onClick={async () => {
                    const id = window.prompt("Project id");
                    const brief = window.prompt("Brief");
                    if (id && brief) { await api.enrollProject(id, brief); await refresh(); }
                  }}>Enroll project</button>
                </div>
              )}
            </>
          ) : projectDetail && (
            <div className="card">
              <button type="button" onClick={() => setSelectedProject(null)}>← Back</button>
              <h2>{selectedProject}</h2>
              <p>{String(projectDetail.brief)}</p>
              <p className="muted">Departments: {(projectDetail.departments as string[])?.join(", ") || "none"}</p>
              {projectDetail.github != null && (
                <p className="muted">
                  GitHub upstream id {String((projectDetail.github as {upstream_repo_id?: string}).upstream_repo_id)}
                  {" · "}write id {String((projectDetail.github as {fork_repo_id?: string}).fork_repo_id)}
                </p>
              )}
              {canEnroll(scopes) && (
                <form onSubmit={async (event) => {
                  event.preventDefault();
                  const departmentBudgets = departmentBudgetsFromLines(dispatchBudgets);
                  if (!Object.keys(departmentBudgets).length) {
                    setError("Enter at least one valid department=budget line.");
                    return;
                  }
                  try {
                    await api.dispatchBrief(
                      selectedProject,
                      dispatchBrief.trim() || String(projectDetail.brief),
                      departmentBudgets,
                      dispatchCriteria.trim(),
                    );
                    setDispatchBrief("");
                    setDispatchCriteria("");
                    setDispatchBudgets("");
                    await refresh();
                    setSelectedProject(null);
                  } catch (e) {
                    setError(String(e));
                  }
                }}>
                  <h3>Dispatch to heads</h3>
                  <label htmlFor="dispatch-brief">Brief for heads</label>
                  <textarea id="dispatch-brief" value={dispatchBrief}
                    placeholder={String(projectDetail.brief)}
                    onChange={(e) => setDispatchBrief(e.target.value)} />
                  <label htmlFor="dispatch-criteria">Acceptance criteria</label>
                  <textarea id="dispatch-criteria" required value={dispatchCriteria}
                    onChange={(e) => setDispatchCriteria(e.target.value)} />
                  <label htmlFor="dispatch-budgets">Department budget (¢), one department=amount per line</label>
                  <textarea id="dispatch-budgets" required value={dispatchBudgets}
                    placeholder={"engineering=500\nproduct=300"}
                    onChange={(e) => setDispatchBudgets(e.target.value)} />
                  <div className="actions">
                    <button className="primary" type="submit">Dispatch to heads</button>
                  </div>
                </form>
              )}
            </div>
          )}
        </section>
      )}

      {tab === "organization" && (
        <section>
          <p className="lede">Catalog, persisted seat status, and roster. Vacant and dormant seats are not healthy workers.</p>
          {organization.map((department) => (
            <div key={department.id} className="card">
              <strong>{department.id} · {department.name}</strong>
              <div className="muted">
                Head seat: {department.seat.status} · {department.seat.principal_id || "vacant"}
              </div>
              <div className="muted">
                Roster: {department.assignments.length
                  ? department.assignments.map(
                    (a) => `${a.principal_id} (${a.position_id}; assignment ${a.id})`,
                  ).join(", ")
                  : "none"}
              </div>
            </div>
          ))}
          {!organization.length && <p className="muted">No organization catalog returned.</p>}
          {canManageOrg && (
            <>
              <form className="card" onSubmit={async (event) => {
                event.preventDefault();
                const form = event.currentTarget;
                const data = new FormData(form);
                try {
                  await api.createDepartment({
                    id: String(data.get("id") || "").trim(),
                    name: String(data.get("name") || "").trim(),
                    head_title: String(data.get("head_title") || "").trim(),
                    mission: String(data.get("mission") || "").trim(),
                    room_type: String(data.get("room_type") || "boardroom").trim(),
                    measures: [],
                    initially_active: data.get("initially_active") === "on",
                    default_model_profile: "mock-text",
                  });
                  form.reset();
                  await refresh();
                } catch (e) {
                  setError(String(e));
                }
              }}>
                <h2>Create department</h2>
                <label htmlFor="create-dept-id">Id</label>
                <input id="create-dept-id" name="id" required />
                <label htmlFor="create-dept-name">Name</label>
                <input id="create-dept-name" name="name" required />
                <label htmlFor="create-dept-head">Head title</label>
                <input id="create-dept-head" name="head_title" required />
                <label htmlFor="create-dept-mission">Mission</label>
                <input id="create-dept-mission" name="mission" required />
                <label htmlFor="create-dept-room">Room type</label>
                <input id="create-dept-room" name="room_type" defaultValue="boardroom" required />
                <label htmlFor="create-dept-active">
                  <input id="create-dept-active" name="initially_active" type="checkbox" /> Initially active
                </label>
                <div className="actions"><button className="primary" type="submit">Create department</button></div>
              </form>
              <form className="card" onSubmit={async (event) => {
                event.preventDefault();
                try {
                  await api.appointHead(appointHeadDepartment.trim(), appointHeadPrincipal.trim());
                  setAppointHeadDepartment("");
                  setAppointHeadPrincipal("");
                  await refresh();
                } catch (e) {
                  setError(String(e));
                }
              }}>
                <h2>Appoint department head</h2>
                <label htmlFor="appoint-head-department">Department id</label>
                <input id="appoint-head-department" required value={appointHeadDepartment}
                  onChange={(e) => setAppointHeadDepartment(e.target.value)} />
                <label htmlFor="appoint-head-principal">Principal id</label>
                <input id="appoint-head-principal" required value={appointHeadPrincipal}
                  onChange={(e) => setAppointHeadPrincipal(e.target.value)} />
                <div className="actions"><button className="primary" type="submit">Appoint head</button></div>
              </form>
              <form className="card" onSubmit={async (event) => {
                event.preventDefault();
                try {
                  await api.vacateHead(vacateHeadDepartment.trim());
                  setVacateHeadDepartment("");
                  await refresh();
                } catch (e) {
                  setError(String(e));
                }
              }}>
                <h2>Vacate department head</h2>
                <label htmlFor="vacate-head-department">Department id</label>
                <input id="vacate-head-department" required value={vacateHeadDepartment}
                  onChange={(e) => setVacateHeadDepartment(e.target.value)} />
                <div className="actions"><button className="danger" type="submit">Vacate head</button></div>
              </form>
              <form className="card" onSubmit={async (event) => {
                event.preventDefault();
                try {
                  await api.assignPosition(
                    positionId.trim(),
                    positionPrincipal.trim(),
                    positionReportsTo.trim() || undefined,
                  );
                  setPositionId("");
                  setPositionPrincipal("");
                  setPositionReportsTo("");
                  await refresh();
                } catch (e) {
                  setError(String(e));
                }
              }}>
                <h2>Assign position</h2>
                <label htmlFor="assign-position-id">Position id</label>
                <input id="assign-position-id" required value={positionId}
                  placeholder="engineering:Developer"
                  onChange={(e) => setPositionId(e.target.value)} />
                <label htmlFor="assign-position-principal">Principal id</label>
                <input id="assign-position-principal" required value={positionPrincipal}
                  onChange={(e) => setPositionPrincipal(e.target.value)} />
                <label htmlFor="assign-position-reports-to">Reports-to seat id (optional)</label>
                <input id="assign-position-reports-to" value={positionReportsTo}
                  placeholder="seat:engineering"
                  onChange={(e) => setPositionReportsTo(e.target.value)} />
                <div className="actions"><button className="primary" type="submit">Assign position</button></div>
              </form>
              <form className="card" onSubmit={async (event) => {
                event.preventDefault();
                try {
                  await api.releaseAssignment(releaseAssignmentId.trim());
                  setReleaseAssignmentId("");
                  await refresh();
                } catch (e) {
                  setError(String(e));
                }
              }}>
                <h2>Release assignment</h2>
                <label htmlFor="release-assignment-id">Assignment id</label>
                <input id="release-assignment-id" required value={releaseAssignmentId}
                  onChange={(e) => setReleaseAssignmentId(e.target.value)} />
                <div className="actions"><button className="danger" type="submit">Release assignment</button></div>
              </form>
              <form className="card" onSubmit={async (event) => {
                event.preventDefault();
                const form = event.currentTarget;
                const data = new FormData(form);
                try {
                  await api.createPosition(
                    String(data.get("department_id") || "").trim(),
                    String(data.get("title") || "").trim(),
                  );
                  form.reset();
                  await refresh();
                } catch (e) {
                  setError(String(e));
                }
              }}>
                <h2>Create position</h2>
                <label htmlFor="create-pos-dept">Department id</label>
                <input id="create-pos-dept" name="department_id" required />
                <label htmlFor="create-pos-title">Title</label>
                <input id="create-pos-title" name="title" required />
                <div className="actions"><button className="primary" type="submit">Create position</button></div>
              </form>
              <form className="card" onSubmit={async (event) => {
                event.preventDefault();
                const form = event.currentTarget;
                const data = new FormData(form);
                try {
                  const items = JSON.parse(String(data.get("items") || "[]"));
                  await api.reorderDepartments(items);
                  form.reset();
                  await refresh();
                } catch (e) {
                  setError(String(e));
                }
              }}>
                <h2>Reorder departments</h2>
                <label htmlFor="reorder-items">Items JSON</label>
                <textarea
                  id="reorder-items"
                  name="items"
                  required
                  placeholder='[{"id":"engineering","display_order":10}]'
                />
                <div className="actions"><button className="primary" type="submit">Reorder</button></div>
              </form>
              <form className="card" onSubmit={async (event) => {
                event.preventDefault();
                try {
                  await api.activateDepartment(activateProjectId.trim(), activateDepartmentId.trim());
                  setActivateProjectId("");
                  setActivateDepartmentId("");
                  await refresh();
                } catch (e) {
                  setError(String(e));
                }
              }}>
                <h2>Activate dormant department for project</h2>
                <label htmlFor="activate-project">Project id</label>
                <input id="activate-project" required value={activateProjectId}
                  onChange={(e) => setActivateProjectId(e.target.value)} />
                <label htmlFor="activate-department">Department id</label>
                <input id="activate-department" required value={activateDepartmentId}
                  onChange={(e) => setActivateDepartmentId(e.target.value)} />
                <div className="actions"><button className="primary" type="submit">Activate</button></div>
              </form>
            </>
          )}
          <form className="card" onSubmit={async (event) => {
            event.preventDefault();
            try {
              const card = await api.workerCard(workerLookupId.trim());
              setWorkerCard(card);
            } catch (e) {
              setWorkerCard(null);
              setError(String(e));
            }
          }}>
            <h2>Worker card</h2>
            <label htmlFor="worker-lookup-id">Employee id</label>
            <input id="worker-lookup-id" required value={workerLookupId}
              onChange={(e) => setWorkerLookupId(e.target.value)} />
            <div className="actions"><button className="primary" type="submit">Load card</button></div>
            {workerCard && (
              <div className="muted" style={{ marginTop: "0.75rem" }}>
                <strong>{workerCard.identity.display_name}</strong>
                <div>{workerCard.identity.headline || "No headline"}</div>
                <div>Position: {workerCard.identity.position_id}</div>
                <div>Sprite: {workerCard.sprite?.sprite_set || workerCard.sprite_placeholder.label}</div>
              </div>
            )}
          </form>
          <h2>Head inbox</h2>
          {headInbox.map((dispatch) => (
            <div key={dispatch.id} className="card">
              <strong>{dispatch.project_id} · {dispatch.department_id}</strong>
              <div className="muted">{dispatch.status} · budget {dispatch.budget_cents}¢</div>
              <p>{dispatch.brief}</p>
              <p className="muted">Acceptance: {dispatch.acceptance_criteria}</p>
              {canManageOrg && dispatch.status === "queued_for_head" && (
                <button type="button" onClick={() => setAssignDispatchId(dispatch.id)}>Assign</button>
              )}
            </div>
          ))}
          {!headInbox.length && <p className="muted">No open head dispatches.</p>}
          {canManageOrg && assignDispatchId && (
            <form className="card" onSubmit={async (event) => {
              event.preventDefault();
              try {
                await api.assignDispatch(
                  assignDispatchId,
                  assignAssignee.trim(),
                  assignAction.trim(),
                  Number(assignCost),
                );
                setAssignDispatchId("");
                setAssignAssignee("");
                setAssignAction("");
                setAssignCost("");
                await refresh();
              } catch (e) {
                setError(String(e));
              }
            }}>
              <h2>Assign dispatch</h2>
              <label htmlFor="assign-assignee">Assignee principal</label>
              <input id="assign-assignee" required value={assignAssignee}
                onChange={(e) => setAssignAssignee(e.target.value)} />
              <label htmlFor="assign-action">Action</label>
              <input id="assign-action" required value={assignAction}
                onChange={(e) => setAssignAction(e.target.value)} />
              <label htmlFor="assign-cost">Cost (¢)</label>
              <input id="assign-cost" required type="number" min="0" value={assignCost}
                onChange={(e) => setAssignCost(e.target.value)} />
              <div className="actions">
                <button className="primary" type="submit">Queue assignment</button>
                <button type="button" onClick={() => setAssignDispatchId("")}>Cancel</button>
              </div>
            </form>
          )}
        </section>
      )}

      {tab === "corporate" && (
        <section>
          <p className="lede">Scorecard, staffing, packs, divisions, and cross-department work from persisted state.</p>
          <div className="card">
            <h2>CEO scorecard</h2>
            <p className="muted">Measured from persisted operations — not simulated. HQ rooms: {hqRoomCount}</p>
            <pre style={{ whiteSpace: "pre-wrap", fontSize: "0.75rem" }}>
              {JSON.stringify(scorecardMetrics || {}, null, 2)}
            </pre>
            {canManageOrg && (
              <div className="actions">
                <button
                  type="button"
                  className="primary"
                  onClick={async () => {
                    try {
                      await api.createDefaultFloorplan();
                      await refresh();
                    } catch (e) {
                      setError(String(e));
                    }
                  }}
                >
                  Create default floorplan
                </button>
              </div>
            )}
          </div>
          <h2>Objectives</h2>
          {objectives.map((objective) => (
            <div key={objective.id} className="card">
              <strong>{objective.title}</strong>
              <div className="muted">{objective.status} · due {objective.due_at}</div>
              {canManageOrg && objective.status === "open" && (
                <div className="actions">
                  <button
                    type="button"
                    onClick={async () => {
                      try {
                        await api.closeObjective(objective.id);
                        await refresh();
                      } catch (e) {
                        setError(String(e));
                      }
                    }}
                  >
                    Close
                  </button>
                </div>
              )}
            </div>
          ))}
          {!objectives.length && <p className="muted">No objectives.</p>}
          {canManageOrg && (
            <form
              className="card"
              onSubmit={async (event) => {
                event.preventDefault();
                const form = event.currentTarget;
                const data = new FormData(form);
                try {
                  const dueLocal = String(data.get("due_at") || "");
                  const payload: Record<string, unknown> = {
                    title: String(data.get("title") || "").trim(),
                    due_at: dueLocal ? new Date(dueLocal).toISOString() : "",
                  };
                  const division = String(data.get("division_id") || "").trim();
                  if (division) payload.division_id = division;
                  const targetRaw = String(data.get("target") || "").trim();
                  if (targetRaw) payload.target = JSON.parse(targetRaw);
                  await api.createObjective(payload);
                  form.reset();
                  await refresh();
                } catch (e) {
                  setError(String(e));
                }
              }}
            >
              <h2>Create objective</h2>
              <label htmlFor="objective-title">Title</label>
              <input id="objective-title" name="title" required />
              <label htmlFor="objective-due">Due at</label>
              <input id="objective-due" name="due_at" type="datetime-local" required />
              <label htmlFor="objective-division">Division id (optional)</label>
              <input id="objective-division" name="division_id" />
              <label htmlFor="objective-target">Target JSON (optional)</label>
              <textarea id="objective-target" name="target" placeholder='{"accepted_artifacts": 5}' />
              <div className="actions"><button className="primary" type="submit">Create</button></div>
            </form>
          )}
          <h2>Industry packs</h2>
          {industryPacks.map((pack) => (
            <div key={pack.id} className="card muted">
              {pack.id} — {pack.industry} — minimal {pack.minimal_departments.length} / full {pack.full_departments.length}
            </div>
          ))}
          {!industryPacks.length && <p className="muted">No industry packs.</p>}
          <h2>Divisions</h2>
          {divisions.map((division) => (
            <div key={division.id} className="card">
              <strong>{division.name}</strong>
              <div className="muted">{division.industry_pack_id} · {division.mode} · {division.status}</div>
              {canManageOrg && division.status === "proposed" && (
                <div className="actions">
                  <button
                    type="button"
                    className="primary"
                    onClick={async () => {
                      try {
                        await api.activateDivision(division.id);
                        await refresh();
                      } catch (e) {
                        setError(String(e));
                      }
                    }}
                  >
                    Activate
                  </button>
                </div>
              )}
            </div>
          ))}
          {!divisions.length && <p className="muted">No divisions.</p>}
          {canManageOrg && (
            <form
              className="card"
              onSubmit={async (event) => {
                event.preventDefault();
                const form = event.currentTarget;
                const data = new FormData(form);
                try {
                  await api.proposeDivision(
                    String(data.get("pack_id") || "").trim(),
                    String(data.get("name") || "").trim(),
                    String(data.get("mode") || "minimal"),
                  );
                  form.reset();
                  await refresh();
                } catch (e) {
                  setError(String(e));
                }
              }}
            >
              <h2>Propose division</h2>
              <label htmlFor="division-pack">Industry pack id</label>
              <input id="division-pack" name="pack_id" required />
              <label htmlFor="division-name">Name</label>
              <input id="division-name" name="name" required />
              <label htmlFor="division-mode">Mode</label>
              <select id="division-mode" name="mode" defaultValue="minimal">
                <option value="minimal">Minimal</option>
                <option value="full">Full</option>
              </select>
              <div className="actions"><button className="primary" type="submit">Propose</button></div>
            </form>
          )}
          <h2>Pending promotions</h2>
          {promotions.map((promotion) => (
            <div key={promotion.id} className="card">
              <strong>{promotion.employee_id}</strong>
              <div className="muted">{promotion.from_level} → {promotion.to_level} · {promotion.status}</div>
              {canManageOrg && (
                <div className="actions">
                  <button
                    type="button"
                    className="approve"
                    onClick={async () => {
                      try {
                        await api.decidePromotion(promotion.id, "approved");
                        await refresh();
                      } catch (e) {
                        setError(String(e));
                      }
                    }}
                  >
                    Approve
                  </button>
                  <button
                    type="button"
                    className="danger"
                    onClick={async () => {
                      try {
                        await api.decidePromotion(promotion.id, "rejected");
                        await refresh();
                      } catch (e) {
                        setError(String(e));
                      }
                    }}
                  >
                    Reject
                  </button>
                </div>
              )}
            </div>
          ))}
          {!promotions.length && <p className="muted">No pending promotions.</p>}
          <h2>Staffing proposals</h2>
          {canManageOrg && (
            <div className="actions" style={{ marginBottom: "0.75rem" }}>
              <button
                type="button"
                className="primary"
                onClick={async () => {
                  try {
                    await api.scanStaffingGaps();
                    await refresh();
                  } catch (e) {
                    setError(String(e));
                  }
                }}
              >
                Scan staffing gaps
              </button>
            </div>
          )}
          {staffingProposals.map((proposal) => (
            <div key={proposal.id} className="card">
              <strong>{proposal.kind} · {proposal.position_id}</strong>
              <div className="muted">{proposal.cost_estimate_cents}¢ · {proposal.rationale}</div>
              {canManageOrg && (
                <div className="actions">
                  <button
                    type="button"
                    className="approve"
                    onClick={async () => {
                      try {
                        await api.decideStaffingProposal(proposal.id, "approved");
                        await refresh();
                      } catch (e) {
                        setError(String(e));
                      }
                    }}
                  >
                    Approve
                  </button>
                  <button
                    type="button"
                    className="danger"
                    onClick={async () => {
                      try {
                        await api.decideStaffingProposal(proposal.id, "rejected");
                        await refresh();
                      } catch (e) {
                        setError(String(e));
                      }
                    }}
                  >
                    Reject
                  </button>
                </div>
              )}
            </div>
          ))}
          {!staffingProposals.length && <p className="muted">No pending staffing proposals.</p>}
          <h2>Cross-department requests</h2>
          {crossDept.map((item) => (
            <div key={item.id} className="card">
              <strong>{item.subject}</strong>
              <div className="muted">
                {item.requesting_department_id} → {item.delivering_department_id} · {item.status}
              </div>
              {canManageOrg && item.status === "pending_acceptance" && (
                <div className="actions">
                  <button
                    type="button"
                    className="primary"
                    onClick={async () => {
                      try {
                        await api.acceptCrossDepartmentRequest(item.id);
                        await refresh();
                      } catch (e) {
                        setError(String(e));
                      }
                    }}
                  >
                    Accept
                  </button>
                </div>
              )}
            </div>
          ))}
          {!crossDept.length && <p className="muted">No cross-department requests.</p>}
          {canManageOrg && (
            <form
              className="card"
              onSubmit={async (event) => {
                event.preventDefault();
                const form = event.currentTarget;
                const data = new FormData(form);
                try {
                  const dueLocal = String(data.get("due_at") || "");
                  await api.createCrossDepartmentRequest({
                    project_id: String(data.get("project_id") || "").trim(),
                    requesting_department_id: String(data.get("requesting") || "").trim(),
                    delivering_department_id: String(data.get("delivering") || "").trim(),
                    subject: String(data.get("subject") || "").trim(),
                    brief: String(data.get("brief") || "").trim(),
                    acceptance_criteria: String(data.get("acceptance") || "").trim(),
                    budget_owner: String(data.get("budget_owner") || "").trim(),
                    budget_cents: Number(data.get("budget_cents") || 0),
                    due_at: dueLocal ? new Date(dueLocal).toISOString() : "",
                    escalation_path: String(data.get("escalation") || "owner").trim(),
                  });
                  form.reset();
                  await refresh();
                } catch (e) {
                  setError(String(e));
                }
              }}
            >
              <h2>Create cross-department request</h2>
              <label htmlFor="xd-project">Project id</label>
              <input id="xd-project" name="project_id" required />
              <label htmlFor="xd-requesting">Requesting department</label>
              <input id="xd-requesting" name="requesting" required />
              <label htmlFor="xd-delivering">Delivering department</label>
              <input id="xd-delivering" name="delivering" required />
              <label htmlFor="xd-subject">Subject</label>
              <input id="xd-subject" name="subject" required />
              <label htmlFor="xd-brief">Brief</label>
              <textarea id="xd-brief" name="brief" required />
              <label htmlFor="xd-acceptance">Acceptance criteria</label>
              <textarea id="xd-acceptance" name="acceptance" required />
              <label htmlFor="xd-budget-owner">Budget owner</label>
              <input id="xd-budget-owner" name="budget_owner" required />
              <label htmlFor="xd-budget">Budget cents</label>
              <input id="xd-budget" name="budget_cents" type="number" min="0" required />
              <label htmlFor="xd-due">Due at</label>
              <input id="xd-due" name="due_at" type="datetime-local" required />
              <label htmlFor="xd-escalation">Escalation path</label>
              <input id="xd-escalation" name="escalation" defaultValue="owner" required />
              <div className="actions"><button className="primary" type="submit">Create request</button></div>
            </form>
          )}
          <h2>Open activity</h2>
          {activityItems.map((item) => (
            <div key={item.id} className="card muted">
              {item.kind} · {item.status}{item.room_id ? ` · room ${item.room_id}` : ""}
            </div>
          ))}
          {!activityItems.length && <p className="muted">No open activity sessions.</p>}
        </section>
      )}

      {tab === "decisions" && (
        <section>
          {decisions.map((item) => (
            <div key={`${item.kind}-${item.id}`} className="card">
              <div className={item.kind === "consultant" ? "tag tag-proposal" : "tag tag-warning"}>{item.kind}</div>
              <strong>{item.title}</strong>
              <p className="muted">{item.summary}</p>
              {canApprove(scopes) && (item.kind === "policy" || item.kind === "consultant") && (
                <div className="actions">
                  <button className="approve" type="button" onClick={() => decide(item, "approved")}>Approve</button>
                  <button className="danger" type="button" onClick={() => decide(item, "rejected")}>Reject</button>
                </div>
              )}
            </div>
          ))}
          {!decisions.length && <p className="muted">No pending decisions.</p>}
        </section>
      )}

      {tab === "inbox" && (
        <section>
          {canEscalate(scopes) && (
            <div className="actions" style={{ marginBottom: "0.75rem" }}>
              <button className="primary" type="button" onClick={escalate}>New escalation</button>
            </div>
          )}
          {inbox.map((req) => (
            <div key={req.id} className="card">
              <div className="muted">{req.kind} · {req.department_id}</div>
              <strong>{req.subject}</strong>
              <p>{req.body}</p>
              {canRespondInbox(scopes) && (
                <div className="actions">
                  <button className="primary" type="button" onClick={() => respond(req)}>Respond</button>
                </div>
              )}
            </div>
          ))}
          {!inbox.length && <p className="muted">No open owner requests.</p>}
        </section>
      )}

      {tab === "diagnostics" && (
        <section>
          <div className="actions" style={{ marginBottom: "0.75rem" }}>
            <button type="button" className="primary" disabled={diagBusy} onClick={loadDiagnostics}>
              {diagBusy ? "Refreshing…" : "Refresh diagnostics"}
            </button>
          </div>
          <p className="muted">Live probes only. Unavailable endpoints show an error — nothing is invented.</p>
          {diagBlocks.map((b) => (
            <div key={b.label} className="card">
              <strong>{b.label}</strong>
              {b.ok ? (
                <pre style={{ whiteSpace: "pre-wrap", fontSize: "0.75rem" }}>
                  {JSON.stringify(b.data, null, 2)}
                </pre>
              ) : (
                <p className="error">{b.error}</p>
              )}
            </div>
          ))}
          {!diagBlocks.length && <p className="muted">No diagnostics loaded yet.</p>}
        </section>
      )}

      {tab === "settings" && (
        <section className="card">
          <label htmlFor="baseUrl">API base URL</label>
          <input id="baseUrl" type="text" value={settings.baseUrl}
            onChange={(e) => save({ ...settings, baseUrl: e.target.value })} />
          <label htmlFor="token">Bearer token</label>
          <input id="token" type="password" value={settings.token}
            onChange={(e) => save({ ...settings, token: e.target.value })} />
          {settings.scopes?.length ? (
            <p className="muted">Scopes: {settings.scopes.join(", ")}</p>
          ) : null}
          <p className="muted">Pair a new device from the CEO desk QR at /desk, or clear token below and scan again.</p>
          {pushStatus ? <p className="muted">{pushStatus}</p> : (
            <p className="muted">Push status unknown — tap Enable push.</p>
          )}
          {pushSubscriptions.length ? (
            <p className="muted">{pushSubscriptions.length} active push subscription(s) registered.</p>
          ) : (
            <p className="muted">No push subscription yet. On iPhone you must open the home-screen app icon, not a Safari tab.</p>
          )}
          <div className="actions">
            <button type="button" onClick={refresh}>Test connection</button>
            <button
              type="button"
              onClick={async () => {
                try {
                  const msg = await ensureWebPushRegistration(api);
                  setPushStatus(msg);
                  const r = await api.pushSubscriptions();
                  setPushSubscriptions(r.subscriptions.map((s) => ({ id: s.id, endpoint: s.endpoint })));
                } catch (e) {
                  setPushStatus(e instanceof Error ? e.message : String(e));
                }
              }}
            >
              Enable push
            </button>
            {pushSubscriptions.length ? (
              <button
                type="button"
                className="primary"
                onClick={async () => {
                  try {
                    const body = await api.pushNotify(`Companion test ${new Date().toLocaleTimeString()}`);
                    const deliveries = body.result?.deliveries || body.deliveries || [];
                    if (!deliveries.length) {
                      setPushStatus("Test push returned no deliveries.");
                      return;
                    }
                    const statuses = [...new Set(deliveries.map((d) => d.status))];
                    if (statuses.includes("applied")) {
                      setPushStatus(`Test push applied (${deliveries.length} delivery). Check OS notification.`);
                    } else if (statuses.every((s) => s === "failed")) {
                      setPushStatus(`Test push failed: ${statuses.join(", ")}. Server could not deliver.`);
                    } else {
                      setPushStatus(`Test push statuses: ${statuses.join(", ")}.`);
                    }
                  } catch (e) {
                    setPushStatus(e instanceof Error ? e.message : String(e));
                  }
                }}
              >
                Send test push
              </button>
            ) : null}
            <button type="button" onClick={() => save({ baseUrl: settings.baseUrl, token: "" })}>Clear token</button>
          </div>
        </section>
      )}

      <nav className="tabs" aria-label="Primary">
        {([
          ["dashboard", "Home"],
          ["projects", "Projects"],
          ["organization", "Org"],
          ["corporate", "Corporate"],
          ["decisions", "Decisions"],
          ["inbox", "Inbox"],
          ["diagnostics", "Diagnostics"],
          ["settings", "Settings"],
        ] as [Tab, string][]).map(([t, label]) => (
          <button key={t} type="button" className={tab === t ? "active" : ""} onClick={() => setTab(t)}>
            {label}
          </button>
        ))}
      </nav>
    </div>
  );
}

function defaultApiBaseFromWindow(): string {
  if (typeof window !== "undefined" && window.location.origin && window.location.origin !== "null") {
    return window.location.origin;
  }
  return "http://127.0.0.1:8000";
}
