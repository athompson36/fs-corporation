import { useState, type FormEvent, type ReactNode } from "react";
import type { ApiClient, DispatchOptions } from "./api/client";
import { ModeSwitch, type PanelMode } from "./ModeSwitch";
import { canEnroll } from "./scopes";

export type LocalCandidate = {
  id: string;
  path: string;
  has_git: boolean;
  remote_url: string | null;
  enrolled: boolean;
};

type FormStatus = { ok: boolean; text: string };
type DispatchSelection = Record<string, { checked: boolean; budget: number }>;

export type ProjectsPanelProps = {
  api: ApiClient;
  scopes: string[] | undefined;
  projects: Record<string, unknown>[];
  selectedProject: string | null;
  setSelectedProject: React.Dispatch<React.SetStateAction<string | null>>;
  projectDetail: Record<string, unknown> | null;
  localCandidates: LocalCandidate[];
  localReposRoot: string | null;
  ghUpstream: string;
  setGhUpstream: React.Dispatch<React.SetStateAction<string>>;
  ghProjectId: string;
  setGhProjectId: React.Dispatch<React.SetStateAction<string>>;
  ghBusy: boolean;
  setGhBusy: React.Dispatch<React.SetStateAction<boolean>>;
  ghResult: string | null;
  setGhResult: React.Dispatch<React.SetStateAction<string | null>>;
  enrollProjectId: string;
  setEnrollProjectId: React.Dispatch<React.SetStateAction<string>>;
  enrollBrief: string;
  setEnrollBrief: React.Dispatch<React.SetStateAction<string>>;
  dispatchBrief: string;
  setDispatchBrief: React.Dispatch<React.SetStateAction<string>>;
  dispatchCriteria: string;
  setDispatchCriteria: React.Dispatch<React.SetStateAction<string>>;
  dispatchBudgets: string;
  setDispatchBudgets: React.Dispatch<React.SetStateAction<string>>;
  dispatchOptions: DispatchOptions | null;
  setDispatchOptions: React.Dispatch<React.SetStateAction<DispatchOptions | null>>;
  dispatchBriefTemplate: string;
  setDispatchBriefTemplate: React.Dispatch<React.SetStateAction<string>>;
  dispatchCriteriaTemplate: string;
  setDispatchCriteriaTemplate: React.Dispatch<React.SetStateAction<string>>;
  dispatchDeptSelection: DispatchSelection;
  setDispatchDeptSelection: React.Dispatch<React.SetStateAction<DispatchSelection>>;
  dispatchRecommendSource: string | null;
  setDispatchRecommendSource: React.Dispatch<React.SetStateAction<string | null>>;
  setFormStatus: React.Dispatch<React.SetStateAction<Record<string, FormStatus>>>;
  runAction: (
    key: string,
    success: string,
    action: () => Promise<unknown>,
  ) => Promise<boolean>;
  status: (key: string) => ReactNode;
  scopeNotice: (action: string, scope: string) => ReactNode;
};

export function ProjectsPanel(props: ProjectsPanelProps) {
  const {
    api, scopes, projects, selectedProject, setSelectedProject, projectDetail,
    localCandidates, localReposRoot,
    ghUpstream, setGhUpstream, ghProjectId, setGhProjectId,
    ghBusy, setGhBusy, ghResult, setGhResult,
    enrollProjectId, setEnrollProjectId, enrollBrief, setEnrollBrief,
    dispatchBrief, setDispatchBrief, dispatchCriteria, setDispatchCriteria,
    dispatchBudgets, setDispatchBudgets, dispatchOptions, setDispatchOptions,
    dispatchBriefTemplate, setDispatchBriefTemplate,
    dispatchCriteriaTemplate, setDispatchCriteriaTemplate,
    dispatchDeptSelection, setDispatchDeptSelection,
    dispatchRecommendSource, setDispatchRecommendSource,
    setFormStatus, runAction, status, scopeNotice,
  } = props;
  const [mode, setMode] = useState<PanelMode>("browse");

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

  return (
    <section>
      <ModeSwitch mode={mode} onChange={setMode} label="Projects mode" />
      {mode === "browse" ? (
        /* Browse: project list and detail entry points. */
        <div className="project-browse-split">
          <div className="project-browse-list">
            <div className="section-head">
              <h2>Projects</h2>
            </div>
            {!projects.length && (
              <p className="panel-empty">No projects enrolled yet.</p>
            )}
            {projects.map((project) => {
              const id = String(project.id);
              const active = selectedProject === id;
              return (
                <button
                  key={id}
                  type="button"
                  className={active ? "list-row active" : "list-row"}
                  aria-pressed={active}
                  onClick={() => setSelectedProject(id)}
                >
                  <strong>{id}</strong>
                  <div className="muted">{String(project.brief)}</div>
                  <div className="muted">
                    Blockers: {(project.blockers as string[])?.join(", ") || "none"}
                  </div>
                </button>
              );
            })}
          </div>
          <div className="project-browse-detail">
            {!selectedProject && (
              <div className="card">
                <p className="panel-empty">Select a project</p>
              </div>
            )}
            {selectedProject && !projectDetail && (
              <div className="card">
                <p className="muted">Loading…</p>
              </div>
            )}
            {selectedProject && projectDetail && (
          <div className="card">
            <div className="detail-toolbar">
              <h2>{selectedProject}</h2>
              <button type="button" onClick={() => setSelectedProject(null)}>
                Clear selection
              </button>
            </div>
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
                      await runAction(
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
                                budget: Number.isFinite(budget)
                                  ? Math.max(0, Math.min(maxCents, Math.trunc(budget)))
                                  : 0,
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
          </div>
        </div>
      ) : (
        /* Manage: enrollment and repository assignment. */
        <>
          <div className="card">
            <div className="section-head">
              <h2>Local candidates</h2>
            </div>
            <p className="muted">
              Folders under {localReposRoot || "local repos/"}. Tap Enroll to create a company project.
            </p>
            {localCandidates.map((candidate) => (
              <div key={candidate.id} style={{ marginBottom: "0.75rem" }}>
                <strong>{candidate.id}</strong>
                <div className="muted">
                  {candidate.enrolled ? "enrolled" : "not enrolled"}
                  {candidate.has_git ? " · git" : ""}
                  {candidate.remote_url ? ` · ${candidate.remote_url}` : ""}
                </div>
                {canEnroll(scopes) && !candidate.enrolled && (
                  <div className="actions">
                    <button
                      className="primary"
                      type="button"
                      onClick={() => runAction(`enroll-${candidate.id}`, "Project enrolled.", () =>
                        api.enrollProject(
                          candidate.id,
                          candidate.remote_url || `Local repo ${candidate.path}`,
                        ))}
                    >
                      Enroll
                    </button>
                  </div>
                )}
                {status(`enroll-${candidate.id}`)}
              </div>
            ))}
            {!localCandidates.length && (
              <p className="panel-empty">No local folders found (add directories under local repos/).</p>
            )}
            {!canEnroll(scopes) && scopeNotice("enroll projects", "project.enroll")}
          </div>
          {canEnroll(scopes) && (
            <div className="card">
              <div className="section-head">
                <h2>Assign GitHub by address</h2>
              </div>
              <p className="muted">Paste upstream only. Creates same-owner {"{repo}"}-corp for writes.</p>
              <label className="muted" htmlFor="gh-upstream">Upstream (owner/repo or github.com URL)</label>
              <input
                id="gh-upstream"
                type="text"
                value={ghUpstream}
                placeholder="owner/repo"
                onChange={(e) => {
                  const value = e.target.value;
                  setGhUpstream(value);
                  const match = value.trim().replace(/\.git\/?$/, "")
                    .match(/github\.com\/([^/\s]+)\/([^/\s]+)|([^/\s]+)\/([^/\s]+)/);
                  if (match && !ghProjectId) {
                    const name = (match[2] || match[4] || "").replace(/\.git$/, "");
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
                      const result = out.result || out;
                      setGhResult(
                        `Upstream ${(result as {upstream?:{full_name?:string}}).upstream?.full_name} → write ` +
                        `${(result as {write_repo?:{full_name?:string}}).write_repo?.full_name}` +
                        `${(result as {created_write_repo?:boolean}).created_write_repo
                          ? " (created)"
                          : " (existing)"}`,
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
            <form className="card" onSubmit={async (event: FormEvent) => {
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
      )}
    </section>
  );
}
