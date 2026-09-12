import type { PanelMode } from "./ModeSwitch";

export type CompanionTab =
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

const VALID_TABS = new Set<CompanionTab>([
  "dashboard",
  "projects",
  "organization",
  "corporate",
  "workers",
  "decisions",
  "inbox",
  "diagnostics",
  "finance",
  "settings",
]);

export type CorporateClusterId =
  | "strategy"
  | "structure"
  | "people"
  | "coordination";

export const MODE_CAPABLE_TABS = new Set<CompanionTab>([
  "projects",
  "organization",
  "corporate",
  "workers",
]);

const CLUSTERS = new Set<CorporateClusterId>([
  "strategy",
  "structure",
  "people",
  "coordination",
]);

const GROUPS: Record<string, ReadonlySet<string>> = {
  organization: new Set(["catalog", "seats", "positions", "lookup"]),
  corporate: new Set(["goals", "structure", "coordination", "ops"]),
  projects: new Set(["enroll", "github"]),
  workers: new Set(["hosts", "token"]),
};

const DEFAULT_GROUP: Record<string, string> = {
  organization: "catalog",
  corporate: "goals",
  projects: "enroll",
  workers: "hosts",
};

export function defaultManageGroup(tab: CompanionTab): string | null {
  return DEFAULT_GROUP[tab] ?? null;
}

export type CompanionUrlState = {
  tab: CompanionTab;
  project: string | null;
  mode: PanelMode;
  cluster: CorporateClusterId;
  group: string | null;
};

function isCompanionTab(value: string): value is CompanionTab {
  return VALID_TABS.has(value as CompanionTab);
}

/** Parse `window.location.search` (with or without leading `?`). */
export function parseCompanionSearch(search: string): CompanionUrlState {
  const params = new URLSearchParams(
    search.startsWith("?") ? search.slice(1) : search,
  );
  const rawTab = (params.get("tab") || "").trim();
  const rawProject = (params.get("project") || "").trim();
  const project = rawProject || null;
  let tab: CompanionTab = isCompanionTab(rawTab) ? rawTab : "dashboard";
  if (project) tab = "projects";

  const capable = MODE_CAPABLE_TABS.has(tab);
  const rawMode = (params.get("mode") || "").trim();
  let mode: PanelMode = rawMode === "manage" ? "manage" : "browse";
  if (!capable) mode = "browse";

  const rawCluster = (params.get("cluster") || "").trim();
  let cluster: CorporateClusterId = CLUSTERS.has(rawCluster as CorporateClusterId)
    ? (rawCluster as CorporateClusterId)
    : "strategy";
  if (tab !== "corporate" || mode !== "browse") cluster = "strategy";

  const rawGroup = (params.get("group") || "").trim();
  let group: string | null = null;
  if (capable && mode === "manage") {
    const allowed = GROUPS[tab];
    const fallback = DEFAULT_GROUP[tab];
    group = allowed?.has(rawGroup) ? rawGroup : fallback;
  }

  return { tab, project, mode, cluster, group };
}

/** Build canonical search string with leading `?`; always includes `tab`; adds `project` only on Projects with a selection. */
export function serializeCompanionSearch(state: CompanionUrlState): string {
  const params = new URLSearchParams();
  const tab = state.tab;
  const project = tab === "projects" && state.project ? state.project : null;
  params.set("tab", tab);
  if (project) params.set("project", project);

  const capable = MODE_CAPABLE_TABS.has(tab);
  const mode: PanelMode = capable && state.mode === "manage" ? "manage" : "browse";
  if (capable && mode === "manage") params.set("mode", "manage");

  if (tab === "corporate" && mode === "browse") {
    const cluster = CLUSTERS.has(state.cluster) ? state.cluster : "strategy";
    if (cluster !== "strategy") params.set("cluster", cluster);
  }

  if (capable && mode === "manage") {
    const fallback = DEFAULT_GROUP[tab];
    const allowed = GROUPS[tab];
    const group =
      state.group && allowed?.has(state.group) ? state.group : fallback;
    if (group && group !== fallback) params.set("group", group);
  }

  const qs = params.toString();
  return qs ? `?${qs}` : "";
}
