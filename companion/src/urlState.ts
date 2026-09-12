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

export type CompanionUrlState = {
  tab: CompanionTab;
  project: string | null;
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
  return { tab, project };
}

/** Build canonical search string with leading `?`; always includes `tab`; adds `project` only on Projects with a selection. */
export function serializeCompanionSearch(state: CompanionUrlState): string {
  const params = new URLSearchParams();
  const tab = state.tab;
  const project =
    tab === "projects" && state.project ? state.project : null;
  params.set("tab", tab);
  if (project) params.set("project", project);
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}
