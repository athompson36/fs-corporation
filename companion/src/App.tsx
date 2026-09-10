import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import {
  ApiClient,
  ActivityItem,
  CompanySetting,
  CrossDeptRequest,
  DecisionItem,
  DispatchOptions,
  DivisionItem,
  HeadDispatch,
  IndustryPack,
  ObjectiveItem,
  OrgDepartment,
  OwnerRequest,
  PromotionItem,
  SecretStatus,
  SessionInfo,
  SettingValue,
  StaffingProposal,
  WorkerCard,
  loadSettings,
  redeemPairing,
  saveSettings,
  type Settings,
} from "./api/client";
import { ensureWebPushRegistration } from "./push";
import { normalizeSettingDraft, settingDraftDiffers } from "./settingsDraft";
import { FinancePanel } from "./FinancePanel";
import { HomePanel } from "./HomePanel";
import { WorkersPanel } from "./WorkersPanel";
import {
  canApprove,
  canEnroll,
  canEscalate,
  canPause,
  canManageOrganization,
  canRespondInbox,
} from "./scopes";

type Tab =
  | "dashboard"
  | "projects"
  | "organization"
  | "corporate"
  | "workers"
  | "decisions"
  | "inbox"
  | "diagnostics"
  | "finance"
  | "settings";

/** Primary bar labels. `work`/`people`/`money` are group sentinels for the bar only. */
const PRIMARY_TABS: [string, string][] = [
  ["dashboard", "Home"],
  ["work", "Work"],
  ["people", "People"],
  ["money", "Money"],
];

const primaryLabel = Object.fromEntries(PRIMARY_TABS) as Record<string, string>;

const WORK_TABS: [Tab, string][] = [
  ["projects", "Projects"],
  ["corporate", "Corporate"],
  ["workers", "Workers"],
];

const MORE_TABS: [Tab, string][] = [
  ["decisions", "Decisions"],
  ["inbox", "Inbox"],
  ["diagnostics", "Diagnostics"],
  ["settings", "Settings"],
];

type FormStatus = { ok: boolean; text: string };

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
  const [dispatchOptions, setDispatchOptions] = useState<DispatchOptions | null>(null);
  const [dispatchBriefTemplate, setDispatchBriefTemplate] = useState("");
  const [dispatchCriteriaTemplate, setDispatchCriteriaTemplate] = useState("");
  const [dispatchDeptSelection, setDispatchDeptSelection] = useState<
    Record<string, { checked: boolean; budget: number }>
  >({});
  const [dispatchRecommendSource, setDispatchRecommendSource] = useState<string | null>(null);
  const [ownerResponseDrafts, setOwnerResponseDrafts] = useState<Record<string, string>>({});
  const [escalateDepartment, setEscalateDepartment] = useState("engineering");
  const [escalateSubject, setEscalateSubject] = useState("");
  const [escalateBody, setEscalateBody] = useState("");
  const [enrollProjectId, setEnrollProjectId] = useState("");
  const [enrollBrief, setEnrollBrief] = useState("");
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
  const [session, setSession] = useState<SessionInfo | null>(null);
  const [companySettings, setCompanySettings] = useState<CompanySetting[]>([]);
  const [settingsDraft, setSettingsDraft] = useState<Record<string, SettingValue>>({});
  const [secretStatuses, setSecretStatuses] = useState<SecretStatus[]>([]);
  const [companySettingsBusy, setCompanySettingsBusy] = useState(false);
  const [feedSources, setFeedSources] = useState<Record<string, unknown>[]>([]);
  const [feedApproveId, setFeedApproveId] = useState("");
  const [feedApproveUrl, setFeedApproveUrl] = useState("https://");
  const [modelProfiles, setModelProfiles] = useState<Record<string, unknown>[]>([]);
  const [lastWorkTab, setLastWorkTab] = useState<Tab>("projects");
  const [lastMoreTab, setLastMoreTab] = useState<Tab>("decisions");
  const [formStatus, setFormStatus] = useState<Record<string, FormStatus>>({});
  const [backendVersion, setBackendVersion] = useState<string | null>(null);

  const scopes = settings.scopes;
  const api = useMemo(() => new ApiClient(settings), [settings]);
  const settingsRef = useRef(settings);
  settingsRef.current = settings;
  const sessionSyncedFor = useRef<string | null>(null);

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
      try {
        const health = await api.health();
        setBackendVersion(health.version ?? null);
      } catch {
        setBackendVersion(null);
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

  const loadCompanySettings = useCallback(async () => {
    if (!settings.token) return;
    setCompanySettingsBusy(true);
    try {
      const [catalog, secrets, feedsBody, profilesBody] = await Promise.all([
        api.companySettings(),
        api.secretsStatus(),
        api.feeds().catch(() => ({ feeds: [] as Record<string, unknown>[] })),
        api.modelProfiles().catch(() => ({ profiles: [] as Record<string, unknown>[] })),
      ]);
      setCompanySettings(catalog.items);
      setSettingsDraft(Object.fromEntries(catalog.items.map((item) => [item.key, item.value])));
      setSecretStatuses(secrets.secrets);
      setFeedSources(feedsBody.feeds || []);
      setModelProfiles(profilesBody.profiles || []);
    } catch (e) {
      setCompanySettings([]);
      setSecretStatuses([]);
      setSettingsDraft({});
      setFeedSources([]);
      setModelProfiles([]);
      setFormStatus((prev) => ({
        ...prev,
        settingsLoad: { ok: false, text: e instanceof Error ? e.message : String(e) },
      }));
    } finally {
      setCompanySettingsBusy(false);
    }
  }, [api, settings.token]);

  // Scopes come from the server, never from whatever a shell wrote into storage.
  // The native WebView injects a session without them, which would otherwise
  // hide every control behind canManage* checks.
  useEffect(() => {
    const token = settings.token;
    if (!token || sessionSyncedFor.current === token) return;
    let cancelled = false;
    api.session()
      .then((info) => {
        if (cancelled) return;
        sessionSyncedFor.current = token;
        setSession(info);
        const current = settingsRef.current;
        const next: Settings = {
          ...current,
          access_level: info.access_level || current.access_level,
          scopes: info.scopes,
        };
        saveSettings(next);
        setSettings(next);
      })
      .catch(() => {
        // Older host without /api/v1/session: keep whatever scopes we have.
      });
    return () => {
      cancelled = true;
    };
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
    if (tab === "settings" && settings.token) {
      loadCompanySettings();
    }
  }, [tab, settings.token, loadCompanySettings]);

  useEffect(() => {
    if (MORE_TABS.some(([t]) => t === tab)) setLastMoreTab(tab);
    if (WORK_TABS.some(([t]) => t === tab)) setLastWorkTab(tab);
  }, [tab]);

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
      setDispatchOptions(null);
      setDispatchDeptSelection({});
      setDispatchRecommendSource(null);
      return;
    }
    api.project(selectedProject).then(setProjectDetail).catch((e) => setError(String(e)));
    if (!canEnroll(scopes)) return;
    api.dispatchOptions(selectedProject)
      .then((opts) => {
        setDispatchOptions(opts);
        setDispatchBrief((prev) => prev || opts.brief_default || "");
        const next: Record<string, { checked: boolean; budget: number }> = {};
        for (const dept of opts.departments) {
          next[dept.id] = { checked: false, budget: 0 };
        }
        setDispatchDeptSelection(next);
      })
      .catch((e) => setError(String(e)));
  }, [api, selectedProject, settings.token, scopes]);

  /** Run a write and report the outcome next to the control that triggered it. */
  const runAction = useCallback(
    async (key: string, success: string, action: () => Promise<unknown>): Promise<boolean> => {
      setFormStatus((prev) => ({ ...prev, [key]: { ok: true, text: "Working…" } }));
      try {
        await action();
        setFormStatus((prev) => ({ ...prev, [key]: { ok: true, text: success } }));
        await refresh();
        return true;
      } catch (e) {
        setFormStatus((prev) => ({
          ...prev,
          [key]: { ok: false, text: e instanceof Error ? e.message : String(e) },
        }));
        return false;
      }
    },
    [refresh],
  );

  function status(key: string) {
    const s = formStatus[key];
    if (!s) return null;
    return <p className={s.ok ? "muted form-status" : "error form-status"}>{s.text}</p>;
  }

  function scopeNotice(what: string, scope = "organization.write") {
    return (
      <p className="muted notice">
        This pairing cannot {what}: it needs the {scope} scope. Re-pair as Admin / CEO mobile
        from the CEO desk.
      </p>
    );
  }

  async function decide(item: DecisionItem, decision: string) {
    const reason = decision === "approved" ? "Approved from mobile companion" : "Rejected from mobile companion";
    if (item.kind !== "policy" && item.kind !== "consultant") {
      setFormStatus((prev) => ({
        ...prev,
        [`decision-${item.id}`]: { ok: false, text: "Expansion decisions: use the CEO desk for now." },
      }));
      return;
    }
    await runAction(`decision-${item.id}`, `Marked ${decision}.`, () =>
      item.kind === "policy"
        ? api.policyDecision(item.id, decision, reason)
        : api.consultantDecision(item.id, decision, reason));
  }

  async function respond(req: OwnerRequest) {
    const response = (ownerResponseDrafts[req.id] || "").trim();
    if (!response) {
      setFormStatus((prev) => ({
        ...prev,
        [`respond-${req.id}`]: { ok: false, text: "Enter a response before submitting." },
      }));
      return;
    }
    const ok = await runAction(`respond-${req.id}`, "Response recorded.", () =>
      api.respondOwner(req.id, response));
    if (ok) {
      setOwnerResponseDrafts((prev) => {
        const next = { ...prev };
        delete next[req.id];
        return next;
      });
    }
  }

  async function escalate(event: FormEvent) {
    event.preventDefault();
    const departmentId = escalateDepartment.trim();
    const subject = escalateSubject.trim();
    const body = escalateBody.trim();
    if (!departmentId || !subject || !body) {
      setFormStatus((prev) => ({
        ...prev,
        escalate: { ok: false, text: "Department, subject, and message are required." },
      }));
      return;
    }
    const ok = await runAction("escalate", "Escalation sent.", () =>
      api.escalateOwner(departmentId, "escalation", subject, body));
    if (ok) {
      setEscalateSubject("");
      setEscalateBody("");
    }
  }

  function save(s: Settings) {
    saveSettings(s);
    setSettings(s);
  }

  async function saveRuntimeSettings(event: FormEvent) {
    event.preventDefault();
    const updates = Object.fromEntries(
      companySettings
        .filter((item) => item.editable && settingDraftDiffers(settingsDraft[item.key], item.value, item.type))
        .map((item) => [item.key, normalizeSettingDraft(settingsDraft[item.key] ?? item.value, item.type)]),
    );
    if (!Object.keys(updates).length) {
      setFormStatus((prev) => ({
        ...prev,
        settingsSave: { ok: true, text: "No runtime changes to save." },
      }));
      return;
    }
    await runAction("settingsSave", "Runtime settings saved.", async () => {
      await api.patchCompanySettings(updates);
      await loadCompanySettings();
    });
  }

  async function resetRuntimeSettings(keys?: string[]) {
    await runAction(
      "settingsReset",
      keys ? "Runtime setting reset." : "All runtime overlays reset.",
      async () => {
        await api.resetCompanySettings(keys, !keys);
        await loadCompanySettings();
      },
    );
  }

  async function approveFeedSource(event: FormEvent) {
    event.preventDefault();
    if (!canEnroll(scopes)) return;
    const id = feedApproveId.trim();
    const url = feedApproveUrl.trim();
    if (!id || !url) return;
    await runAction("feedApprove", `Feed ${id} approved.`, async () => {
      await api.approveFeed(id, url);
      setFeedApproveId("");
      setFeedApproveUrl("https://");
      await loadCompanySettings();
    });
  }

  async function feedAction(
    key: string,
    message: string,
    run: () => Promise<unknown>,
  ) {
    await runAction(key, message, async () => {
      await run();
      await loadCompanySettings();
    });
  }

  const company = (dashboard?.company ?? {}) as Record<string, unknown>;
  const accessBadge = settings.access_level === "read_only"
    ? "Read only"
    : settings.label || (settings.access_level ? settings.access_level : null);
  const canManageOrg = canManageOrganization(scopes);
  const canEditSettings = canPause(scopes);
  const canApproveFeeds = canEnroll(scopes);
  const canOperateFeeds = canPause(scopes);
  const isWorkTab = WORK_TABS.some(([t]) => t === tab);
  const isMoreTab = MORE_TABS.some(([t]) => t === tab);
  const moreCount = decisions.length + inbox.length;

  function departmentBudgetsFromSelection(): Record<string, number> {
    return Object.fromEntries(
      Object.entries(dispatchDeptSelection)
        .filter(([, row]) => row.checked && Number.isInteger(row.budget) && row.budget >= 0)
        .map(([id, row]) => [id, row.budget]),
    );
  }

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

  const dispatchBlockedByDormant = Object.entries(dispatchDeptSelection).some(([id, row]) => {
    if (!row.checked) return false;
    const dept = dispatchOptions?.departments.find((item) => item.id === id);
    return Boolean(dept && !dept.dispatchable);
  });

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
      {tab !== "dashboard" && (
        <h1>FS-Corporation {accessBadge && <span className="tag tag-proposal">{accessBadge}</span>}</h1>
      )}
      {offline && <div className="offline">Cannot reach control service</div>}
      {error && <p className="error">{error}</p>}

      {isWorkTab && (
        <div className="segmented" role="tablist" aria-label="Work sections">
          {WORK_TABS.map(([t, label]) => (
            <button
              key={t}
              type="button"
              role="tab"
              aria-selected={tab === t}
              className={tab === t ? "active" : ""}
              onClick={() => setTab(t)}
            >
              {label}
            </button>
          ))}
        </div>
      )}

      {isMoreTab && (
        <div className="segmented" role="tablist" aria-label="More sections">
          {MORE_TABS.map(([t, label]) => (
            <button
              key={t}
              type="button"
              role="tab"
              aria-selected={tab === t}
              className={tab === t ? "active" : ""}
              onClick={() => setTab(t)}
            >
              {label}
            </button>
          ))}
        </div>
      )}

      {tab === "dashboard" && (
        // HomePanel owns the "Needs you" queue and the only Home page title.
        <HomePanel
          scopes={scopes}
          decisions={decisions}
          inbox={inbox}
          company={company}
          dashboard={dashboard}
          ownerResponseDrafts={ownerResponseDrafts}
          setOwnerResponseDrafts={setOwnerResponseDrafts}
          onDecide={decide}
          onRespond={respond}
          onPause={() => { void api.pause().then(refresh); }}
          onResume={() => { void api.resume().then(refresh); }}
          onRefresh={refresh}
          onOpenDecisions={() => setTab("decisions")}
          onOpenInbox={() => setTab("inbox")}
          status={status}
          scopeNotice={scopeNotice}
          accessBadge={accessBadge}
        />
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
                          onClick={() => runAction(`enroll-${c.id}`, "Project enrolled.", () =>
                            api.enrollProject(c.id, c.remote_url || `Local repo ${c.path}`))}
                        >
                          Enroll
                        </button>
                      </div>
                    )}
                    {status(`enroll-${c.id}`)}
                  </div>
                ))}
                {!localCandidates.length && (
                  <p className="muted">No local folders found (add directories under local repos/).</p>
                )}
                {!canEnroll(scopes) && scopeNotice("enroll projects", "project.enroll")}
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
                        setGhResult(null);
                        await runAction("github-assign", "GitHub assigned.", async () => {
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
                        });
                        setGhBusy(false);
                      }}
                    >
                      Assign GitHub
                    </button>
                  </div>
                  {status("github-assign")}
                  {ghResult && <p className="muted">{ghResult}</p>}
                </div>
              )}
              {canEnroll(scopes) && (
                <form className="card" onSubmit={async (event) => {
                  event.preventDefault();
                  const id = enrollProjectId.trim();
                  const brief = enrollBrief.trim();
                  if (!id || !brief) {
                    setFormStatus((prev) => ({
                      ...prev,
                      "enroll-manual": { ok: false, text: "Project id and brief are required." },
                    }));
                    return;
                  }
                  const ok = await runAction("enroll-manual", "Project enrolled.", () =>
                    api.enrollProject(id, brief));
                  if (ok) {
                    setEnrollProjectId("");
                    setEnrollBrief("");
                  }
                }}>
                  <h3>Enroll project</h3>
                  <label htmlFor="enroll-project-id">Project id</label>
                  <input
                    id="enroll-project-id"
                    type="text"
                    required
                    value={enrollProjectId}
                    onChange={(e) => setEnrollProjectId(e.target.value)}
                  />
                  <label htmlFor="enroll-project-brief">Brief</label>
                  <textarea
                    id="enroll-project-brief"
                    required
                    value={enrollBrief}
                    onChange={(e) => setEnrollBrief(e.target.value)}
                  />
                  <div className="actions">
                    <button className="primary" type="submit">Enroll project</button>
                  </div>
                  {status("enroll-manual")}
                </form>
              )}
            </>
          ) : projectDetail && (
            <div className="card">
              <div className="actions">
                <button type="button" onClick={() => setSelectedProject(null)}>← Back</button>
              </div>
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
                  const fromSelection = departmentBudgetsFromSelection();
                  const departmentBudgets = Object.keys(fromSelection).length
                    ? fromSelection
                    : departmentBudgetsFromLines(dispatchBudgets);
                  if (!Object.keys(departmentBudgets).length) {
                    setFormStatus((prev) => ({
                      ...prev,
                      dispatch: { ok: false, text: "Select at least one department with a budget." },
                    }));
                    return;
                  }
                  if (dispatchBlockedByDormant) {
                    setFormStatus((prev) => ({
                      ...prev,
                      dispatch: { ok: false, text: "Activate dormant departments before dispatch." },
                    }));
                    return;
                  }
                  const ok = await runAction("dispatch", "Dispatched to heads.", () =>
                    api.dispatchBrief(
                      selectedProject,
                      dispatchBrief.trim() || String(projectDetail.brief),
                      departmentBudgets,
                      dispatchCriteria.trim(),
                    ));
                  if (!ok) return;
                  setDispatchBrief("");
                  setDispatchCriteria("");
                  setDispatchBudgets("");
                  setDispatchBriefTemplate("");
                  setDispatchCriteriaTemplate("");
                  setDispatchRecommendSource(null);
                  setSelectedProject(null);
                }}>
                  <h3>Dispatch to heads</h3>
                  <div className="actions">
                    <button
                      type="button"
                      onClick={async () => {
                        const ok = await runAction(
                          "dispatch-recommend",
                          "Recommendation applied.",
                          async () => {
                            const wrapped = await api.dispatchRecommend(selectedProject, true);
                            const body = wrapped.result ?? wrapped;
                            setDispatchBrief(body.brief || "");
                            setDispatchCriteria(body.acceptance_criteria || "");
                            setDispatchRecommendSource(
                              `${body.source}${body.notes?.length ? ` (${body.notes.join(", ")})` : ""}`,
                            );
                            setDispatchDeptSelection((prev) => {
                              const next = { ...prev };
                              for (const id of Object.keys(next)) {
                                next[id] = { ...next[id], checked: false };
                              }
                              for (const dept of body.departments || []) {
                                next[dept.id] = {
                                  checked: Boolean(dept.recommended),
                                  budget: dept.budget_cents,
                                };
                              }
                              return next;
                            });
                            const lines = (body.departments || [])
                              .filter((d) => d.recommended)
                              .map((d) => `${d.id}=${d.budget_cents}`);
                            setDispatchBudgets(lines.join("\n"));
                          },
                        );
                        if (ok) {
                          /* status line from runAction */
                        }
                      }}
                    >
                      Recommend for this project
                    </button>
                  </div>
                  {status("dispatch-recommend")}
                  {dispatchRecommendSource && (
                    <p className="muted">Recommendation source: {dispatchRecommendSource}</p>
                  )}
                  <label htmlFor="dispatch-brief-template">Brief template</label>
                  <select
                    id="dispatch-brief-template"
                    value={dispatchBriefTemplate}
                    onChange={(e) => {
                      const id = e.target.value;
                      setDispatchBriefTemplate(id);
                      const template = dispatchOptions?.fields.brief.templates.find((t) => t.id === id);
                      if (template) setDispatchBrief(template.body);
                    }}
                  >
                    <option value="">Custom / free text</option>
                    {(dispatchOptions?.fields.brief.templates || []).map((template) => (
                      <option key={template.id} value={template.id}>{template.label}</option>
                    ))}
                  </select>
                  <label htmlFor="dispatch-brief">Brief for heads</label>
                  <textarea id="dispatch-brief" value={dispatchBrief}
                    placeholder={String(projectDetail.brief)}
                    onChange={(e) => setDispatchBrief(e.target.value)} />
                  <label htmlFor="dispatch-criteria-template">Acceptance criteria template</label>
                  <select
                    id="dispatch-criteria-template"
                    value={dispatchCriteriaTemplate}
                    onChange={(e) => {
                      const id = e.target.value;
                      setDispatchCriteriaTemplate(id);
                      const template = dispatchOptions?.fields.acceptance_criteria.templates
                        .find((t) => t.id === id);
                      if (template) setDispatchCriteria(template.body);
                    }}
                  >
                    <option value="">Custom / free text</option>
                    {(dispatchOptions?.fields.acceptance_criteria.templates || []).map((template) => (
                      <option key={template.id} value={template.id}>{template.label}</option>
                    ))}
                  </select>
                  <label htmlFor="dispatch-criteria">Acceptance criteria</label>
                  <textarea id="dispatch-criteria" required value={dispatchCriteria}
                    onChange={(e) => setDispatchCriteria(e.target.value)} />
                  <div className="dispatch-dept-list">
                    {(dispatchOptions?.departments || []).map((dept) => {
                      const row = dispatchDeptSelection[dept.id] || { checked: false, budget: 0 };
                      const maxCents = dispatchOptions?.fields.department_budgets.max_cents ?? 0;
                      const presets = (dispatchOptions?.fields.department_budgets.presets_cents || [])
                        .filter((preset) => preset <= maxCents);
                      return (
                        <div key={dept.id} className="dispatch-dept-row">
                          <label htmlFor={`dispatch-dept-${dept.id}`}>
                            <input
                              id={`dispatch-dept-${dept.id}`}
                              type="checkbox"
                              checked={row.checked}
                              onChange={(e) => setDispatchDeptSelection((prev) => ({
                                ...prev,
                                [dept.id]: { ...row, checked: e.target.checked },
                              }))}
                            />
                            {" "}{dept.name}
                            <span className={dept.dispatchable ? "badge-active" : "badge-dormant"}>
                              {dept.status}{dept.dispatchable ? "" : " — Activate first"}
                            </span>
                          </label>
                          <input
                            type="number"
                            min={0}
                            max={maxCents}
                            value={row.budget}
                            aria-label={`${dept.name} budget cents`}
                            onChange={(e) => {
                              const budget = Number(e.target.value);
                              setDispatchDeptSelection((prev) => ({
                                ...prev,
                                [dept.id]: {
                                  checked: true,
                                  budget: Number.isFinite(budget) ? Math.max(0, Math.min(maxCents, Math.trunc(budget))) : 0,
                                },
                              }));
                            }}
                          />
                          <div className="chip-row">
                            {presets.map((preset) => (
                              <button
                                key={preset}
                                type="button"
                                className="chip"
                                onClick={() => setDispatchDeptSelection((prev) => ({
                                  ...prev,
                                  [dept.id]: { checked: true, budget: preset },
                                }))}
                              >
                                {preset}
                              </button>
                            ))}
                          </div>
                          {!dept.dispatchable && row.checked && (
                            <button
                              type="button"
                              onClick={() => runAction(
                                `activate-${dept.id}`,
                                "Department activated.",
                                () => api.activateDepartment(selectedProject, dept.id),
                              ).then((ok) => {
                                if (ok) {
                                  return api.dispatchOptions(selectedProject).then(setDispatchOptions);
                                }
                                return undefined;
                              })}
                            >
                              Activate {dept.id}
                            </button>
                          )}
                          {status(`activate-${dept.id}`)}
                        </div>
                      );
                    })}
                  </div>
                  <label htmlFor="dispatch-budgets">Department budget (¢), advanced fallback</label>
                  <textarea id="dispatch-budgets" value={dispatchBudgets}
                    placeholder={"engineering=500\nproduct=300"}
                    onChange={(e) => setDispatchBudgets(e.target.value)} />
                  <details>
                    <summary>Valid values</summary>
                    <pre className="muted">
                      {dispatchOptions
                        ? [
                          `max_cents=${dispatchOptions.fields.department_budgets.max_cents}`,
                          `presets_cents=${JSON.stringify(dispatchOptions.fields.department_budgets.presets_cents)}`,
                          `departments=${dispatchOptions.departments.map(
                            (d) => `${d.id}:${d.status}${d.dispatchable ? ":ok" : ":dormant"}`,
                          ).join(", ")}`,
                        ].join("\n")
                        : "Loading options…"}
                    </pre>
                  </details>
                  <div className="actions">
                    <button className="primary" type="submit" disabled={dispatchBlockedByDormant}>
                      Dispatch to heads
                    </button>
                  </div>
                  {dispatchBlockedByDormant && (
                    <p className="error">Activate dormant departments before dispatch.</p>
                  )}
                  {status("dispatch")}
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
          {!canManageOrg && scopeNotice("edit the organization")}
          {canManageOrg && (
            <>
              <form className="card" onSubmit={async (event) => {
                event.preventDefault();
                const form = event.currentTarget;
                const data = new FormData(form);
                const ok = await runAction("create-dept", "Department created.", () =>
                  api.createDepartment({
                    id: String(data.get("id") || "").trim(),
                    name: String(data.get("name") || "").trim(),
                    head_title: String(data.get("head_title") || "").trim(),
                    mission: String(data.get("mission") || "").trim(),
                    room_type: String(data.get("room_type") || "boardroom").trim(),
                    measures: [],
                    initially_active: data.get("initially_active") === "on",
                    default_model_profile: "mock-text",
                  }));
                if (ok) form.reset();
              }}>
                <h2>Create department</h2>
                <label htmlFor="create-dept-id">Id</label>
                <input id="create-dept-id" name="id" type="text" required />
                <label htmlFor="create-dept-name">Name</label>
                <input id="create-dept-name" name="name" type="text" required />
                <label htmlFor="create-dept-head">Head title</label>
                <input id="create-dept-head" name="head_title" type="text" required />
                <label htmlFor="create-dept-mission">Mission</label>
                <input id="create-dept-mission" name="mission" type="text" required />
                <label htmlFor="create-dept-room">Room type</label>
                <input id="create-dept-room" name="room_type" type="text" defaultValue="boardroom" required />
                <label className="check" htmlFor="create-dept-active">
                  <input id="create-dept-active" name="initially_active" type="checkbox" /> Initially active
                </label>
                <div className="actions"><button className="primary" type="submit">Create department</button></div>
                {status("create-dept")}
              </form>
              <form className="card" onSubmit={async (event) => {
                event.preventDefault();
                const ok = await runAction("appoint-head", "Head appointed.", () =>
                  api.appointHead(appointHeadDepartment.trim(), appointHeadPrincipal.trim()));
                if (!ok) return;
                setAppointHeadDepartment("");
                setAppointHeadPrincipal("");
              }}>
                <h2>Appoint department head</h2>
                <label htmlFor="appoint-head-department">Department id</label>
                <input id="appoint-head-department" type="text" required value={appointHeadDepartment}
                  onChange={(e) => setAppointHeadDepartment(e.target.value)} />
                <label htmlFor="appoint-head-principal">Principal id</label>
                <input id="appoint-head-principal" type="text" required value={appointHeadPrincipal}
                  onChange={(e) => setAppointHeadPrincipal(e.target.value)} />
                <div className="actions"><button className="primary" type="submit">Appoint head</button></div>
                {status("appoint-head")}
              </form>
              <form className="card" onSubmit={async (event) => {
                event.preventDefault();
                const ok = await runAction("vacate-head", "Head vacated.", () =>
                  api.vacateHead(vacateHeadDepartment.trim()));
                if (ok) setVacateHeadDepartment("");
              }}>
                <h2>Vacate department head</h2>
                <label htmlFor="vacate-head-department">Department id</label>
                <input id="vacate-head-department" type="text" required value={vacateHeadDepartment}
                  onChange={(e) => setVacateHeadDepartment(e.target.value)} />
                <div className="actions"><button className="danger" type="submit">Vacate head</button></div>
                {status("vacate-head")}
              </form>
              <form className="card" onSubmit={async (event) => {
                event.preventDefault();
                const ok = await runAction("assign-position", "Position assigned.", () =>
                  api.assignPosition(
                    positionId.trim(),
                    positionPrincipal.trim(),
                    positionReportsTo.trim() || undefined,
                  ));
                if (!ok) return;
                setPositionId("");
                setPositionPrincipal("");
                setPositionReportsTo("");
              }}>
                <h2>Assign position</h2>
                <label htmlFor="assign-position-id">Position id</label>
                <input id="assign-position-id" type="text" required value={positionId}
                  placeholder="engineering:Developer"
                  onChange={(e) => setPositionId(e.target.value)} />
                <label htmlFor="assign-position-principal">Principal id</label>
                <input id="assign-position-principal" type="text" required value={positionPrincipal}
                  onChange={(e) => setPositionPrincipal(e.target.value)} />
                <label htmlFor="assign-position-reports-to">Reports-to seat id (optional)</label>
                <input id="assign-position-reports-to" type="text" value={positionReportsTo}
                  placeholder="seat:engineering"
                  onChange={(e) => setPositionReportsTo(e.target.value)} />
                <div className="actions"><button className="primary" type="submit">Assign position</button></div>
                {status("assign-position")}
              </form>
              <form className="card" onSubmit={async (event) => {
                event.preventDefault();
                const ok = await runAction("release-assignment", "Assignment released.", () =>
                  api.releaseAssignment(releaseAssignmentId.trim()));
                if (ok) setReleaseAssignmentId("");
              }}>
                <h2>Release assignment</h2>
                <label htmlFor="release-assignment-id">Assignment id</label>
                <input id="release-assignment-id" type="text" required value={releaseAssignmentId}
                  onChange={(e) => setReleaseAssignmentId(e.target.value)} />
                <div className="actions"><button className="danger" type="submit">Release assignment</button></div>
                {status("release-assignment")}
              </form>
              <form className="card" onSubmit={async (event) => {
                event.preventDefault();
                const form = event.currentTarget;
                const data = new FormData(form);
                const ok = await runAction("create-position", "Position created.", () =>
                  api.createPosition(
                    String(data.get("department_id") || "").trim(),
                    String(data.get("title") || "").trim(),
                  ));
                if (ok) form.reset();
              }}>
                <h2>Create position</h2>
                <label htmlFor="create-pos-dept">Department id</label>
                <input id="create-pos-dept" name="department_id" type="text" required />
                <label htmlFor="create-pos-title">Title</label>
                <input id="create-pos-title" name="title" type="text" required />
                <div className="actions"><button className="primary" type="submit">Create position</button></div>
                {status("create-position")}
              </form>
              <form className="card" onSubmit={async (event) => {
                event.preventDefault();
                const form = event.currentTarget;
                const data = new FormData(form);
                let items: { id: string; display_order: number }[];
                try {
                  items = JSON.parse(String(data.get("items") || "[]"));
                } catch {
                  setFormStatus((prev) => ({
                    ...prev,
                    "reorder-departments": { ok: false, text: "Items must be valid JSON." },
                  }));
                  return;
                }
                const ok = await runAction("reorder-departments", "Departments reordered.", () =>
                  api.reorderDepartments(items));
                if (ok) form.reset();
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
                {status("reorder-departments")}
              </form>
              <form className="card" onSubmit={async (event) => {
                event.preventDefault();
                const ok = await runAction("activate-department", "Department activated.", () =>
                  api.activateDepartment(activateProjectId.trim(), activateDepartmentId.trim()));
                if (!ok) return;
                setActivateProjectId("");
                setActivateDepartmentId("");
              }}>
                <h2>Activate dormant department for project</h2>
                <label htmlFor="activate-project">Project id</label>
                <input id="activate-project" type="text" required value={activateProjectId}
                  onChange={(e) => setActivateProjectId(e.target.value)} />
                <label htmlFor="activate-department">Department id</label>
                <input id="activate-department" type="text" required value={activateDepartmentId}
                  onChange={(e) => setActivateDepartmentId(e.target.value)} />
                <div className="actions"><button className="primary" type="submit">Activate</button></div>
                {status("activate-department")}
              </form>
            </>
          )}
          <form className="card" onSubmit={async (event) => {
            event.preventDefault();
            await runAction("worker-card", "Card loaded.", async () => {
              try {
                setWorkerCard(await api.workerCard(workerLookupId.trim()));
              } catch (e) {
                setWorkerCard(null);
                throw e;
              }
            });
          }}>
            <h2>Worker card</h2>
            <label htmlFor="worker-lookup-id">Employee id</label>
            <input id="worker-lookup-id" type="text" required value={workerLookupId}
              onChange={(e) => setWorkerLookupId(e.target.value)} />
            <div className="actions"><button className="primary" type="submit">Load card</button></div>
            {status("worker-card")}
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
                <div className="actions">
                  <button type="button" onClick={() => setAssignDispatchId(dispatch.id)}>Assign</button>
                </div>
              )}
            </div>
          ))}
          {!headInbox.length && <p className="muted">No open head dispatches.</p>}
          {canManageOrg && assignDispatchId && (
            <form className="card" onSubmit={async (event) => {
              event.preventDefault();
              const ok = await runAction("assign-dispatch", "Assignment queued.", () =>
                api.assignDispatch(
                  assignDispatchId,
                  assignAssignee.trim(),
                  assignAction.trim(),
                  Number(assignCost),
                ));
              if (!ok) return;
              setAssignDispatchId("");
              setAssignAssignee("");
              setAssignAction("");
              setAssignCost("");
            }}>
              <h2>Assign dispatch</h2>
              <label htmlFor="assign-assignee">Assignee principal</label>
              <input id="assign-assignee" type="text" required value={assignAssignee}
                onChange={(e) => setAssignAssignee(e.target.value)} />
              <label htmlFor="assign-action">Action</label>
              <input id="assign-action" type="text" required value={assignAction}
                onChange={(e) => setAssignAction(e.target.value)} />
              <label htmlFor="assign-cost">Cost (¢)</label>
              <input id="assign-cost" required type="number" inputMode="numeric" min="0" value={assignCost}
                onChange={(e) => setAssignCost(e.target.value)} />
              <div className="actions">
                <button className="primary" type="submit">Queue assignment</button>
                <button type="button" onClick={() => setAssignDispatchId("")}>Cancel</button>
              </div>
              {status("assign-dispatch")}
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
                  onClick={() => runAction("default-floorplan", "Default floorplan created.", () =>
                    api.createDefaultFloorplan())}
                >
                  Create default floorplan
                </button>
              </div>
            )}
            {status("default-floorplan")}
            {!canManageOrg && scopeNotice("change headquarters or corporate records")}
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
                    onClick={() => runAction(`objective-${objective.id}`, "Objective closed.", () =>
                      api.closeObjective(objective.id))}
                  >
                    Close
                  </button>
                </div>
              )}
              {status(`objective-${objective.id}`)}
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
                const dueLocal = String(data.get("due_at") || "");
                const payload: Record<string, unknown> = {
                  title: String(data.get("title") || "").trim(),
                  due_at: dueLocal ? new Date(dueLocal).toISOString() : "",
                };
                const division = String(data.get("division_id") || "").trim();
                if (division) payload.division_id = division;
                const targetRaw = String(data.get("target") || "").trim();
                if (targetRaw) {
                  try {
                    payload.target = JSON.parse(targetRaw);
                  } catch {
                    setFormStatus((prev) => ({
                      ...prev,
                      "create-objective": { ok: false, text: "Target must be valid JSON." },
                    }));
                    return;
                  }
                }
                const ok = await runAction("create-objective", "Objective created.", () =>
                  api.createObjective(payload));
                if (ok) form.reset();
              }}
            >
              <h2>Create objective</h2>
              <label htmlFor="objective-title">Title</label>
              <input id="objective-title" name="title" type="text" required />
              <label htmlFor="objective-due">Due at</label>
              <input id="objective-due" name="due_at" type="datetime-local" required />
              <label htmlFor="objective-division">Division id (optional)</label>
              <input id="objective-division" name="division_id" type="text" />
              <label htmlFor="objective-target">Target JSON (optional)</label>
              <textarea id="objective-target" name="target" placeholder='{"accepted_artifacts": 5}' />
              <div className="actions"><button className="primary" type="submit">Create</button></div>
              {status("create-objective")}
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
                    onClick={() => runAction(`division-${division.id}`, "Division activated.", () =>
                      api.activateDivision(division.id))}
                  >
                    Activate
                  </button>
                </div>
              )}
              {status(`division-${division.id}`)}
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
                const ok = await runAction("propose-division", "Division proposed.", () =>
                  api.proposeDivision(
                    String(data.get("pack_id") || "").trim(),
                    String(data.get("name") || "").trim(),
                    String(data.get("mode") || "minimal"),
                  ));
                if (ok) form.reset();
              }}
            >
              <h2>Propose division</h2>
              <label htmlFor="division-pack">Industry pack id</label>
              <input id="division-pack" name="pack_id" type="text" required />
              <label htmlFor="division-name">Name</label>
              <input id="division-name" name="name" type="text" required />
              <label htmlFor="division-mode">Mode</label>
              <select id="division-mode" name="mode" defaultValue="minimal">
                <option value="minimal">Minimal</option>
                <option value="full">Full</option>
              </select>
              <div className="actions"><button className="primary" type="submit">Propose</button></div>
              {status("propose-division")}
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
                    onClick={() => runAction(`promotion-${promotion.id}`, "Promotion approved.", () =>
                      api.decidePromotion(promotion.id, "approved"))}
                  >
                    Approve
                  </button>
                  <button
                    type="button"
                    className="danger"
                    onClick={() => runAction(`promotion-${promotion.id}`, "Promotion rejected.", () =>
                      api.decidePromotion(promotion.id, "rejected"))}
                  >
                    Reject
                  </button>
                </div>
              )}
              {status(`promotion-${promotion.id}`)}
            </div>
          ))}
          {!promotions.length && <p className="muted">No pending promotions.</p>}
          <h2>Staffing proposals</h2>
          {canManageOrg && (
            <>
              <div className="actions" style={{ marginBottom: "0.75rem" }}>
                <button
                  type="button"
                  className="primary"
                  onClick={() => runAction("staffing-scan", "Scan complete.", () => api.scanStaffingGaps())}
                >
                  Scan staffing gaps
                </button>
              </div>
              {status("staffing-scan")}
            </>
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
                    onClick={() => runAction(`staffing-${proposal.id}`, "Proposal approved.", () =>
                      api.decideStaffingProposal(proposal.id, "approved"))}
                  >
                    Approve
                  </button>
                  <button
                    type="button"
                    className="danger"
                    onClick={() => runAction(`staffing-${proposal.id}`, "Proposal rejected.", () =>
                      api.decideStaffingProposal(proposal.id, "rejected"))}
                  >
                    Reject
                  </button>
                </div>
              )}
              {status(`staffing-${proposal.id}`)}
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
                    onClick={() => runAction(`cross-dept-${item.id}`, "Request accepted.", () =>
                      api.acceptCrossDepartmentRequest(item.id))}
                  >
                    Accept
                  </button>
                </div>
              )}
              {status(`cross-dept-${item.id}`)}
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
                const dueLocal = String(data.get("due_at") || "");
                const ok = await runAction("create-cross-dept", "Request created.", () =>
                  api.createCrossDepartmentRequest({
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
                  }));
                if (ok) form.reset();
              }}
            >
              <h2>Create cross-department request</h2>
              <label htmlFor="xd-project">Project id</label>
              <input id="xd-project" name="project_id" type="text" required />
              <label htmlFor="xd-requesting">Requesting department</label>
              <input id="xd-requesting" name="requesting" type="text" required />
              <label htmlFor="xd-delivering">Delivering department</label>
              <input id="xd-delivering" name="delivering" type="text" required />
              <label htmlFor="xd-subject">Subject</label>
              <input id="xd-subject" name="subject" type="text" required />
              <label htmlFor="xd-brief">Brief</label>
              <textarea id="xd-brief" name="brief" required />
              <label htmlFor="xd-acceptance">Acceptance criteria</label>
              <textarea id="xd-acceptance" name="acceptance" required />
              <label htmlFor="xd-budget-owner">Budget owner</label>
              <input id="xd-budget-owner" name="budget_owner" type="text" required />
              <label htmlFor="xd-budget">Budget cents</label>
              <input id="xd-budget" name="budget_cents" type="number" inputMode="numeric" min="0" required />
              <label htmlFor="xd-due">Due at</label>
              <input id="xd-due" name="due_at" type="datetime-local" required />
              <label htmlFor="xd-escalation">Escalation path</label>
              <input id="xd-escalation" name="escalation" type="text" defaultValue="owner" required />
              <div className="actions"><button className="primary" type="submit">Create request</button></div>
              {status("create-cross-dept")}
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

      {tab === "workers" && (
        <WorkersPanel
          api={api}
          hasToken={Boolean(settings.token)}
          canPause={canPause(scopes)}
          scopeNotice={scopeNotice}
          runAction={async (key, okMessage, run) => {
            await runAction(key, okMessage, run);
          }}
          status={status}
        />
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
              {status(`decision-${item.id}`)}
            </div>
          ))}
          {!decisions.length && <p className="muted">No pending decisions.</p>}
          {decisions.length > 0 && !canApprove(scopes)
            && scopeNotice("decide proposals", "policy.approve")}
        </section>
      )}

      {tab === "inbox" && (
        <section>
          {canEscalate(scopes) && (
            <form className="card" onSubmit={escalate}>
              <h3>New escalation</h3>
              <label htmlFor="escalate-department">Department id</label>
              <input
                id="escalate-department"
                type="text"
                required
                value={escalateDepartment}
                onChange={(e) => setEscalateDepartment(e.target.value)}
              />
              <label htmlFor="escalate-subject">Subject</label>
              <input
                id="escalate-subject"
                type="text"
                required
                value={escalateSubject}
                onChange={(e) => setEscalateSubject(e.target.value)}
              />
              <label htmlFor="escalate-body">Message</label>
              <textarea
                id="escalate-body"
                required
                value={escalateBody}
                onChange={(e) => setEscalateBody(e.target.value)}
              />
              <div className="actions">
                <button className="primary" type="submit">Send escalation</button>
              </div>
              {status("escalate")}
            </form>
          )}
          {inbox.map((req) => (
            <div key={req.id} className="card">
              <div className="muted">{req.kind} · {req.department_id}</div>
              <strong>{req.subject}</strong>
              <p>{req.body}</p>
              {canRespondInbox(scopes) && (
                <form onSubmit={(event) => {
                  event.preventDefault();
                  void respond(req);
                }}>
                  <label htmlFor={`owner-response-${req.id}`}>Response</label>
                  <textarea
                    id={`owner-response-${req.id}`}
                    required
                    value={ownerResponseDrafts[req.id] || ""}
                    onChange={(e) => setOwnerResponseDrafts((prev) => ({
                      ...prev,
                      [req.id]: e.target.value,
                    }))}
                  />
                  <div className="actions">
                    <button className="primary" type="submit">Respond</button>
                  </div>
                </form>
              )}
              {status(`respond-${req.id}`)}
            </div>
          ))}
          {!inbox.length && <p className="muted">No open owner requests.</p>}
          {inbox.length > 0 && !canRespondInbox(scopes)
            && scopeNotice("respond to owner requests", "company.pause")}
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

      {tab === "finance" && (
        <FinancePanel
          api={api}
          hasToken={Boolean(settings.token)}
          canPause={canPause(scopes)}
          scopeNotice={scopeNotice}
          runAction={async (key, okMessage, run) => {
            await runAction(key, okMessage, run);
          }}
          status={status}
        />
      )}

      {tab === "settings" && (
        <section>
          <div className="card">
            <h2>Connection</h2>
            <label htmlFor="baseUrl">API base URL</label>
            <input id="baseUrl" type="text" value={settings.baseUrl}
              onChange={(e) => save({ ...settings, baseUrl: e.target.value })} />
            <label htmlFor="token">Bearer token</label>
            <input id="token" type="password" value={settings.token}
              onChange={(e) => save({ ...settings, token: e.target.value })} />
            {session ? (
              <p className="muted">
                Signed in as {session.principal_id}
                {session.access_level ? ` (${session.access_level})` : ""} · scopes:{" "}
                {session.scopes.length ? session.scopes.join(", ") : "none"}
              </p>
            ) : (
              <p className="muted">Session scopes not confirmed by the server yet.</p>
            )}
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
              <button
                type="button"
                onClick={() => {
                  sessionSyncedFor.current = null;
                  setSession(null);
                  save({ baseUrl: settings.baseUrl, token: "" });
                }}
              >
                Clear token
              </button>
            </div>
          </div>

          <form className="card" onSubmit={saveRuntimeSettings}>
            <h2>Runtime</h2>
            {companySettingsBusy && !companySettings.length && <p className="muted">Loading settings…</p>}
            {companySettings.filter((item) => item.editable).map((item) => (
              <div key={item.key} style={{ marginBottom: "1rem" }}>
                <label htmlFor={`runtime-${item.key}`}>{item.key}</label>
                <p className="muted">{item.description}</p>
                {item.type === "bool" ? (
                  <select
                    id={`runtime-${item.key}`}
                    value={String(settingsDraft[item.key] ?? item.value)}
                    disabled={!canEditSettings}
                    onChange={(e) => setSettingsDraft((prev) => ({
                      ...prev,
                      [item.key]: e.target.value === "true",
                    }))}
                  >
                    <option value="true">Enabled</option>
                    <option value="false">Disabled</option>
                  </select>
                ) : item.type === "enum" ? (
                  <select
                    id={`runtime-${item.key}`}
                    value={String(settingsDraft[item.key] ?? item.value)}
                    disabled={!canEditSettings}
                    onChange={(e) => setSettingsDraft((prev) => ({ ...prev, [item.key]: e.target.value }))}
                  >
                    {(item.enum_values || []).map((value) => (
                      <option key={value} value={value}>{value}</option>
                    ))}
                  </select>
                ) : (
                  <input
                    id={`runtime-${item.key}`}
                    type={item.type === "int" || item.type === "float" ? "number" : "text"}
                    step={item.type === "int" ? 1 : item.type === "float" ? "any" : undefined}
                    min={item.min}
                    max={item.max}
                    value={String(settingsDraft[item.key] ?? item.value)}
                    disabled={!canEditSettings}
                    onChange={(e) => setSettingsDraft((prev) => ({
                      ...prev,
                      [item.key]: e.target.value,
                    }))}
                  />
                )}
                <div className="actions">
                  <span className="tag tag-proposal">Source: {item.source}</span>
                  {canEditSettings && item.source === "overlay" && (
                    <button type="button" onClick={() => resetRuntimeSettings([item.key])}>Reset</button>
                  )}
                </div>
                {item.restart_required && item.source === "overlay" && (
                  <p className="muted">Takes effect after API restart</p>
                )}
              </div>
            ))}
            {canEditSettings ? (
              <div className="actions">
                <button className="primary" type="submit">Save runtime changes</button>
                <button type="button" onClick={() => resetRuntimeSettings()}>Reset all overlays</button>
              </div>
            ) : scopeNotice("edit runtime settings", "company.pause")}
            {status("settingsSave")}
            {status("settingsReset")}
            {status("settingsLoad")}
          </form>

          <div className="card">
            <h2>Feeds</h2>
            <p className="muted">
              Approved HTTPS market feeds only. Watchlist templates stay non-live.
              Poll requires status approved.
            </p>
            {feedSources.length === 0 && !companySettingsBusy && (
              <p className="muted">No feed sources enrolled.</p>
            )}
            {feedSources.map((feed) => {
              const id = String(feed.id || "");
              const statusValue = String(feed.status || "");
              return (
                <div key={id} style={{ marginBottom: "0.85rem" }}>
                  <strong>{id}</strong>
                  <div className="muted">{String(feed.url || "")}</div>
                  <div className="actions">
                    <span className="tag tag-proposal">{statusValue}</span>
                    {canOperateFeeds && statusValue === "approved" && (
                      <>
                        <button
                          type="button"
                          onClick={() => feedAction(`feed-poll-${id}`, `Polled ${id}.`, () => api.pollFeed(id))}
                        >
                          Poll
                        </button>
                        <button
                          type="button"
                          onClick={() => feedAction(`feed-pause-${id}`, `Paused ${id}.`, () => api.pauseFeed(id))}
                        >
                          Pause
                        </button>
                      </>
                    )}
                    {canOperateFeeds && statusValue !== "revoked" && (
                      <button
                        type="button"
                        onClick={() => feedAction(`feed-revoke-${id}`, `Revoked ${id}.`, () => api.revokeFeed(id))}
                      >
                        Revoke
                      </button>
                    )}
                  </div>
                  {status(`feed-poll-${id}`)}
                  {status(`feed-pause-${id}`)}
                  {status(`feed-revoke-${id}`)}
                </div>
              );
            })}
            {canApproveFeeds ? (
              <form onSubmit={approveFeedSource}>
                <label htmlFor="feed-approve-id">Source id</label>
                <input
                  id="feed-approve-id"
                  value={feedApproveId}
                  onChange={(e) => setFeedApproveId(e.target.value)}
                  required
                />
                <label htmlFor="feed-approve-url">HTTPS URL</label>
                <input
                  id="feed-approve-url"
                  type="url"
                  value={feedApproveUrl}
                  onChange={(e) => setFeedApproveUrl(e.target.value)}
                  required
                />
                <div className="actions">
                  <button className="primary" type="submit">Approve / re-approve</button>
                </div>
                {status("feedApprove")}
              </form>
            ) : (
              scopeNotice("approve feeds", "project.enroll")
            )}
            {!canOperateFeeds && feedSources.length > 0
              && scopeNotice("pause, revoke, or poll feeds", "company.pause")}
          </div>

          <div className="card">
            <h2>Models</h2>
            <p className="muted">
              Global billed rate uses FS_CORP_MODEL_CENTS_PER_1K_TOKENS (edit under Runtime).
              Profile list is read-only; profile cents override the global rate when set.
            </p>
            {modelProfiles.length === 0 && !companySettingsBusy && (
              <p className="muted">No model profiles loaded.</p>
            )}
            {modelProfiles.map((profile) => {
              const id = String(profile.id || "");
              const body = typeof profile.body === "string"
                ? (() => { try { return JSON.parse(profile.body as string); } catch { return {}; } })()
                : (profile.body as Record<string, unknown> | undefined) || {};
              const cents = body.cents_per_1k_tokens ?? profile.cents_per_1k_tokens;
              return (
                <div key={id} style={{ marginBottom: "0.65rem" }}>
                  <strong>{id}</strong>
                  <div className="muted">
                    enabled: {String(profile.enabled ?? body.enabled ?? "—")}
                    {cents != null ? ` · cents/1k: ${String(cents)}` : " · cents/1k: (global)"}
                  </div>
                </div>
              );
            })}
          </div>

          <div className="card">
            <h2>Host (read-only)</h2>
            {companySettings.filter((item) => !item.editable).map((item) => (
              <div key={item.key} style={{ marginBottom: "0.75rem" }}>
                <strong>{item.key}</strong>
                <div>{String(item.value || "Not configured")}</div>
                <div className="muted">{item.description} · source: {item.source}</div>
              </div>
            ))}
          </div>

          <div className="card">
            <h2>Secrets</h2>
            <p className="muted">Configuration only from secrets-status; secret values are never shown.</p>
            {secretStatuses.map((secret) => (
              <div key={secret.name} style={{ marginBottom: "0.5rem" }}>
                <strong>{secret.name}</strong>
                {" "}
                <span className={secret.configured ? "badge-active" : "badge-dormant"}>
                  {secret.configured ? "configured" : "missing"}
                </span>
              </div>
            ))}
            {!secretStatuses.length && !companySettingsBusy && (
              <p className="muted">No secret status returned.</p>
            )}
          </div>
        </section>
      )}

      <p className="app-version muted" aria-live="polite">
        {backendVersion ? `v${backendVersion}` : ""}
      </p>
      <nav className="tabs" aria-label="Primary">
        <button type="button" className={tab === "dashboard" ? "active" : ""} onClick={() => setTab("dashboard")}>
          {primaryLabel.dashboard}
          {moreCount > 0 && <span className="tab-badge">{moreCount}</span>}
        </button>
        <button
          type="button"
          className={isWorkTab ? "active" : ""}
          onClick={() => setTab(lastWorkTab)}
        >
          {primaryLabel.work}
        </button>
        <button
          type="button"
          className={tab === "organization" ? "active" : ""}
          onClick={() => setTab("organization")}
        >
          {primaryLabel.people}
        </button>
        <button
          type="button"
          className={tab === "finance" ? "active" : ""}
          onClick={() => setTab("finance")}
        >
          {primaryLabel.money}
        </button>
        <button
          type="button"
          className={isMoreTab ? "active" : ""}
          onClick={() => setTab(lastMoreTab)}
        >
          More
        </button>
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
