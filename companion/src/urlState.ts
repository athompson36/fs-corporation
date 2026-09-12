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
  "finance",
]);

const CLUSTERS = new Set<CorporateClusterId>([
  "strategy",
  "structure",
  "people",
  "coordination",
]);

const MANAGE_GROUPS: Record<string, ReadonlySet<string>> = {
  organization: new Set(["catalog", "seats", "positions", "lookup"]),
  corporate: new Set(["goals", "structure", "coordination", "ops"]),
  projects: new Set(["enroll", "github"]),
  workers: new Set(["hosts", "token"]),
  finance: new Set(["invoice", "adjustment", "period"]),
};

const MANAGE_DEFAULT: Record<string, string> = {
  organization: "catalog",
  corporate: "goals",
  projects: "enroll",
  workers: "hosts",
  finance: "invoice",
};

/** @deprecated Use MANAGE_GROUPS */
const GROUPS = MANAGE_GROUPS;

/** @deprecated Use MANAGE_DEFAULT */
const DEFAULT_GROUP = MANAGE_DEFAULT;

const FINANCE_BROWSE_GROUPS = new Set([
  "overview",
  "invoices",
  "adjustments",
  "periods",
]);
const FINANCE_BROWSE_DEFAULT = "overview";

export function allowedGroups(
  tab: CompanionTab,
  mode: PanelMode,
): ReadonlySet<string> | null {
  if (tab === "finance") {
    return mode === "manage" ? MANAGE_GROUPS.finance : FINANCE_BROWSE_GROUPS;
  }
  if (mode !== "manage") return null;
  return MANAGE_GROUPS[tab] ?? null;
}

export function defaultGroupFor(
  tab: CompanionTab,
  mode: PanelMode,
): string | null {
  if (tab === "finance") {
    return mode === "manage" ? MANAGE_DEFAULT.finance : FINANCE_BROWSE_DEFAULT;
  }
  if (mode !== "manage") return null;
  return MANAGE_DEFAULT[tab] ?? null;
}

/** @deprecated Prefer defaultGroupFor(tab, "manage") */
export function defaultManageGroup(tab: CompanionTab): string | null {
  return defaultGroupFor(tab, "manage");
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
  if (capable) {
    const allowed = allowedGroups(tab, mode);
    const fallback = defaultGroupFor(tab, mode);
    if (allowed && fallback) {
      group = allowed.has(rawGroup) ? rawGroup : fallback;
    }
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

  if (capable) {
    const allowed = allowedGroups(tab, mode);
    const fallback = defaultGroupFor(tab, mode);
    if (allowed && fallback) {
      const group =
        state.group && allowed.has(state.group) ? state.group : fallback;
      if (group !== fallback) params.set("group", group);
    }
  }

  const qs = params.toString();
  return qs ? `?${qs}` : "";
}
