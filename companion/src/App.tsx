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
import { CorporatePanel } from "./CorporatePanel";
import { FinancePanel } from "./FinancePanel";
import { HomePanel } from "./HomePanel";
import { OrgPanel } from "./OrgPanel";
import { ProjectsPanel, type LocalCandidate } from "./ProjectsPanel";
import { WorkersPanel } from "./WorkersPanel";
import {
  canApprove,
  canEnroll,
  canEscalate,
  canPause,
  canManageOrganization,
  canRespondInbox,
} from "./scopes";
import type { PanelMode } from "./ModeSwitch";
import {
  defaultGroupFor,
  MODE_CAPABLE_TABS,
  parseCompanionSearch,
  serializeCompanionSearch,
  stateAfterModeChange,
  stateAfterTabChange,
  type CompanionTab,
  type CorporateClusterId,
} from "./urlState";

type Tab = CompanionTab;

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

const initialUrl =
  typeof window !== "undefined"
    ? parseCompanionSearch(window.location.search)
    : parseCompanionSearch("");

export default function App() {
  const [settings, setSettings] = useState<Settings>(loadSettings);
  const [tab, setTab] = useState<Tab>(initialUrl.tab);
  const [panelMode, setPanelMode] = useState<PanelMode>(initialUrl.mode);
  const [corporateCluster, setCorporateCluster] = useState<CorporateClusterId>(initialUrl.cluster);
  const [manageGroup, setManageGroup] = useState<string>(
    initialUrl.group
      ?? defaultGroupFor(initialUrl.tab, initialUrl.mode)
      ?? "catalog",
  );
  const [error, setError] = useState<string | null>(null);
  const [offline, setOffline] = useState(false);
  const [pairing, setPairing] = useState(false);
  const [manualTicket, setManualTicket] = useState("");
  const [dashboard, setDashboard] = useState<Record<string, unknown> | null>(null);
  const [projects, setProjects] = useState<Record<string, unknown>[]>([]);
  const [projectsLoaded, setProjectsLoaded] = useState(false);
  const [decisions, setDecisions] = useState<DecisionItem[]>([]);
  const [inbox, setInbox] = useState<OwnerRequest[]>([]);
  const [organization, setOrganization] = useState<OrgDepartment[]>([]);
  const [headInbox, setHeadInbox] = useState<HeadDispatch[]>([]);
  const [selectedProject, setSelectedProject] = useState<string | null>(initialUrl.project);
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
  const canManageOrg = canManageOrganization(scopes);
  const api = useMemo(() => new ApiClient(settings), [settings]);
  const settingsRef = useRef(settings);
  settingsRef.current = settings;
  const sessionSyncedFor = useRef<string | null>(null);
  const tabRef = useRef(tab);
  const modeRef = useRef(panelMode);

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

  useEffect(() => {
    if (tab === "organization" && !canManageOrg && panelMode === "manage" && manageGroup !== "lookup") {
      setManageGroup("lookup");
    }
  }, [tab, canManageOrg, panelMode, manageGroup]);

  useEffect(() => {
    if (tab === "corporate" && !canManageOrg && panelMode === "manage") {
      setPanelMode("browse");
    }
  }, [tab, canManageOrg, panelMode]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    let mode = panelMode;
    let group =
      tab === "finance" || panelMode === "manage" ? manageGroup : null;
    if (tab === "corporate" && !canManageOrg && mode === "manage") {
      mode = "browse";
      group = null;
    }
    if (tab === "organization" && !canManageOrg && mode === "manage") {
      group = "lookup";
    }
    const next = serializeCompanionSearch({
      tab,
      project: tab === "projects" ? selectedProject : null,
      mode,
      cluster: corporateCluster,
      group,
    });
    const url = window.location.pathname + next + window.location.hash;
    const current = window.location.pathname + window.location.search + window.location.hash;
    if (url !== current) {
      window.history.replaceState(null, "", url);
    }
  }, [tab, selectedProject, panelMode, corporateCluster, manageGroup, canManageOrg]);

  useEffect(() => {
    if (tab !== "projects" && selectedProject !== null) {
      setSelectedProject(null);
    }
  }, [tab, selectedProject]);

  useEffect(() => {
    if (!projectsLoaded || !selectedProject) return;
    const known = projects.some((p) => String(p.id) === selectedProject);
    if (!known) setSelectedProject(null);
  }, [projects, projectsLoaded, selectedProject]);

  useEffect(() => {
    if (!MODE_CAPABLE_TABS.has(tab as CompanionTab)) {
      if (panelMode !== "browse") setPanelMode("browse");
    }
  }, [tab, panelMode]);

  useEffect(() => {
    function onPopState() {
      const parsed = parseCompanionSearch(window.location.search);
      tabRef.current = parsed.tab;
      setTab(parsed.tab);
      setSelectedProject(parsed.project);
      modeRef.current = parsed.mode;
      setPanelMode(parsed.mode);
      setCorporateCluster(parsed.cluster);
      setManageGroup(
        parsed.group ?? defaultGroupFor(parsed.tab, parsed.mode) ?? "catalog",
      );
    }
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

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
      setProjectsLoaded(true);
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

  const selectTab = useCallback((next: Tab) => {
    const canonical = stateAfterTabChange(
      {
        tab: tab as CompanionTab,
        project: selectedProject,
        mode: panelMode,
        cluster: corporateCluster,
        group: manageGroup,
      },
      next as CompanionTab,
    );
    tabRef.current = canonical.tab;
    modeRef.current = canonical.mode;
    setTab(canonical.tab);
    setPanelMode(canonical.mode);
    setCorporateCluster(canonical.cluster);
    setManageGroup(canonical.group ?? "catalog");
    if (canonical.project === null) setSelectedProject(null);
    else setSelectedProject(canonical.project);
  }, [tab, selectedProject, panelMode, corporateCluster, manageGroup]);

  const handlePanelModeChange = useCallback(
    (mode: PanelMode) => {
      if (tab === "corporate" && !canManageOrg && mode === "manage") {
        setPanelMode("browse");
        modeRef.current = "browse";
        return;
      }
      const canonical = stateAfterModeChange(
        {
          tab: tab as CompanionTab,
          project: selectedProject,
          mode: panelMode,
          cluster: corporateCluster,
          group: manageGroup,
        },
        mode,
      );
      modeRef.current = canonical.mode;
      setPanelMode(canonical.mode);
      setCorporateCluster(canonical.cluster);
      setManageGroup(canonical.group ?? "catalog");
    },
    [tab, canManageOrg, selectedProject, panelMode, corporateCluster, manageGroup],
  );

  const handleManageGroupChange = useCallback(
    (id: string) => {
      if (tab === "organization" && !canManageOrg && panelMode === "manage" && id !== "lookup") {
        return;
      }
      setManageGroup(id);
    },
    [tab, canManageOrg, panelMode],
  );

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
  const canEditSettings = canPause(scopes);
  const canApproveFeeds = canEnroll(scopes);
  const canOperateFeeds = canPause(scopes);
  const isWorkTab = WORK_TABS.some(([t]) => t === tab);
  const isMoreTab = MORE_TABS.some(([t]) => t === tab);
  const moreCount = decisions.length + inbox.length;

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
              onClick={() => selectTab(t)}
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
              onClick={() => selectTab(t)}
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
          onOpenDecisions={() => selectTab("decisions")}
          onOpenInbox={() => selectTab("inbox")}
          status={status}
          scopeNotice={scopeNotice}
          accessBadge={accessBadge}
        />
      )}

      {tab === "projects" && (
        <ProjectsPanel
          api={api}
          scopes={scopes}
          projects={projects}
          selectedProject={selectedProject}
          setSelectedProject={setSelectedProject}
          projectDetail={projectDetail}
          localCandidates={localCandidates}
          localReposRoot={localReposRoot}
          ghUpstream={ghUpstream}
          setGhUpstream={setGhUpstream}
          ghProjectId={ghProjectId}
          setGhProjectId={setGhProjectId}
          ghBusy={ghBusy}
          setGhBusy={setGhBusy}
          ghResult={ghResult}
          setGhResult={setGhResult}
          enrollProjectId={enrollProjectId}
          setEnrollProjectId={setEnrollProjectId}
          enrollBrief={enrollBrief}
          setEnrollBrief={setEnrollBrief}
          dispatchBrief={dispatchBrief}
          setDispatchBrief={setDispatchBrief}
          dispatchCriteria={dispatchCriteria}
          setDispatchCriteria={setDispatchCriteria}
          dispatchBudgets={dispatchBudgets}
          setDispatchBudgets={setDispatchBudgets}
          dispatchOptions={dispatchOptions}
          setDispatchOptions={setDispatchOptions}
          dispatchBriefTemplate={dispatchBriefTemplate}
          setDispatchBriefTemplate={setDispatchBriefTemplate}
          dispatchCriteriaTemplate={dispatchCriteriaTemplate}
          setDispatchCriteriaTemplate={setDispatchCriteriaTemplate}
          dispatchDeptSelection={dispatchDeptSelection}
          setDispatchDeptSelection={setDispatchDeptSelection}
          dispatchRecommendSource={dispatchRecommendSource}
          setDispatchRecommendSource={setDispatchRecommendSource}
          setFormStatus={setFormStatus}
          runAction={runAction}
          status={status}
          scopeNotice={scopeNotice}
          mode={panelMode}
          onModeChange={setPanelMode}
          manageGroup={manageGroup}
          onManageGroupChange={setManageGroup}
        />
      )}

      {tab === "organization" && (
        <OrgPanel
          api={api}
          organization={organization}
          headInbox={headInbox}
          canManage={canManageOrg}
          activateProjectId={activateProjectId}
          setActivateProjectId={setActivateProjectId}
          activateDepartmentId={activateDepartmentId}
          setActivateDepartmentId={setActivateDepartmentId}
          appointHeadDepartment={appointHeadDepartment}
          setAppointHeadDepartment={setAppointHeadDepartment}
          appointHeadPrincipal={appointHeadPrincipal}
          setAppointHeadPrincipal={setAppointHeadPrincipal}
          vacateHeadDepartment={vacateHeadDepartment}
          setVacateHeadDepartment={setVacateHeadDepartment}
          positionId={positionId}
          setPositionId={setPositionId}
          positionPrincipal={positionPrincipal}
          setPositionPrincipal={setPositionPrincipal}
          positionReportsTo={positionReportsTo}
          setPositionReportsTo={setPositionReportsTo}
          releaseAssignmentId={releaseAssignmentId}
          setReleaseAssignmentId={setReleaseAssignmentId}
          assignDispatchId={assignDispatchId}
          setAssignDispatchId={setAssignDispatchId}
          assignAssignee={assignAssignee}
          setAssignAssignee={setAssignAssignee}
          assignAction={assignAction}
          setAssignAction={setAssignAction}
          assignCost={assignCost}
          setAssignCost={setAssignCost}
          workerLookupId={workerLookupId}
          setWorkerLookupId={setWorkerLookupId}
          workerCard={workerCard}
          setWorkerCard={setWorkerCard}
          setFormStatus={setFormStatus}
          runAction={runAction}
          status={status}
          scopeNotice={scopeNotice}
          mode={panelMode}
          onModeChange={handlePanelModeChange}
          manageGroup={manageGroup}
          onManageGroupChange={handleManageGroupChange}
        />
      )}

      {tab === "corporate" && (
        <CorporatePanel
          api={api}
          scorecard={scorecardMetrics}
          objectives={objectives}
          packs={industryPacks}
          divisions={divisions}
          promotions={promotions}
          staffing={staffingProposals}
          crossDept={crossDept}
          activity={activityItems}
          hqRoomCount={hqRoomCount}
          canManage={canManageOrg}
          runAction={runAction}
          setFormStatus={setFormStatus}
          status={status}
          scopeNotice={scopeNotice}
          mode={panelMode}
          onModeChange={handlePanelModeChange}
          cluster={corporateCluster}
          onClusterChange={setCorporateCluster}
          manageGroup={manageGroup}
          onManageGroupChange={setManageGroup}
        />
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
          mode={panelMode}
          onModeChange={setPanelMode}
          manageGroup={manageGroup}
          onManageGroupChange={setManageGroup}
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
          mode={panelMode}
          onModeChange={handlePanelModeChange}
          manageGroup={manageGroup}
          onManageGroupChange={setManageGroup}
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
        <button type="button" className={tab === "dashboard" ? "active" : ""} onClick={() => selectTab("dashboard")}>
          {primaryLabel.dashboard}
          {moreCount > 0 && <span className="tab-badge">{moreCount}</span>}
        </button>
        <button
          type="button"
          className={isWorkTab ? "active" : ""}
          onClick={() => selectTab(lastWorkTab)}
        >
          {primaryLabel.work}
        </button>
        <button
          type="button"
          className={tab === "organization" ? "active" : ""}
          onClick={() => selectTab("organization")}
        >
          {primaryLabel.people}
        </button>
        <button
          type="button"
          className={tab === "finance" ? "active" : ""}
          onClick={() => selectTab("finance")}
        >
          {primaryLabel.money}
        </button>
        <button
          type="button"
          className={isMoreTab ? "active" : ""}
          onClick={() => selectTab(lastMoreTab)}
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
