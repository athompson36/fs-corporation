import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ApiClient,
  DecisionItem,
  OwnerRequest,
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
  canRespondInbox,
  canResume,
} from "./scopes";

type Tab = "dashboard" | "projects" | "decisions" | "inbox" | "diagnostics" | "settings";

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
      const [d, p, dec, own, local] = await Promise.all([
        api.dashboard(),
        api.projects(),
        api.decisions(),
        api.ownerInbox("open"),
        api.localRepos().catch(() => null),
      ]);
      setDashboard(d);
      setProjects(p.projects);
      setDecisions(dec.items);
      setInbox(own.items);
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
                <div className="actions">
                  <button className="primary" type="button" onClick={async () => {
                    const depts = window.prompt("Departments (comma-separated)", "engineering,product");
                    const brief = window.prompt("Brief for heads", String(projectDetail.brief));
                    const criteria = window.prompt("Acceptance criteria", "Deliverable reviewed");
                    if (!depts || !brief || !criteria) return;
                    const departmentBudgets = Object.fromEntries(
                      depts.split(",").map((s) => [s.trim(), 500]).filter(([id]) => id),
                    );
                    await api.dispatchBrief(selectedProject, brief, departmentBudgets, criteria);
                    await refresh();
                    setSelectedProject(null);
                  }}>Dispatch to heads</button>
                </div>
              )}
            </div>
          )}
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
