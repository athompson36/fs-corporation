import {
  type Dispatch,
  type FormEvent,
  type ReactNode,
  type SetStateAction,
} from "react";
import { useWideViewport } from "./useWideViewport";
import type {
  ActivityItem,
  ApiClient,
  CrossDeptRequest,
  DivisionItem,
  IndustryPack,
  ObjectiveItem,
  PromotionItem,
  StaffingProposal,
} from "./api/client";
import { ManageClusters } from "./ManageClusters";
import { ModeSwitch, type PanelMode } from "./ModeSwitch";
import type { CorporateClusterId } from "./urlState";

type FormStatus = { ok: boolean; text: string };

const CORPORATE_CLUSTERS: { id: CorporateClusterId; label: string }[] = [
  { id: "strategy", label: "Strategy" },
  { id: "structure", label: "Structure" },
  { id: "people", label: "People" },
  { id: "coordination", label: "Coordination" },
];

type CorporatePanelProps = {
  api: ApiClient;
  scorecard: Record<string, unknown> | null;
  objectives: ObjectiveItem[];
  packs: IndustryPack[];
  divisions: DivisionItem[];
  promotions: PromotionItem[];
  staffing: StaffingProposal[];
  crossDept: CrossDeptRequest[];
  activity: ActivityItem[];
  hqRoomCount: number;
  canManage: boolean;
  runAction: (
    key: string,
    success: string,
    action: () => Promise<unknown>,
  ) => Promise<boolean>;
  setFormStatus: Dispatch<SetStateAction<Record<string, FormStatus>>>;
  status: (key: string) => ReactNode;
  scopeNotice: (what: string, scope?: string) => ReactNode;
  mode: PanelMode;
  onModeChange: (mode: PanelMode) => void;
  cluster: CorporateClusterId;
  onClusterChange: (id: CorporateClusterId) => void;
  manageGroup: string;
  onManageGroupChange: (id: string) => void;
};

export function CorporatePanel(props: CorporatePanelProps) {
  const {
    api, scorecard, objectives, packs, divisions, promotions, staffing, crossDept,
    activity, hqRoomCount, canManage, runAction, setFormStatus, status, scopeNotice,
    mode, onModeChange, cluster, onClusterChange, manageGroup, onManageGroupChange,
  } = props;
  const wide = useWideViewport();

  async function createObjective(event: FormEvent<HTMLFormElement>) {
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
  }

  async function proposeDivision(event: FormEvent<HTMLFormElement>) {
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
  }

  async function createCrossDept(event: FormEvent<HTMLFormElement>) {
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
  }

  return (
    <section>
      <p className="lede">Scorecard, staffing, packs, divisions, and cross-department work from persisted state.</p>
      <ModeSwitch mode={mode} onChange={onModeChange} label="Corporate mode" />
      {!canManage && scopeNotice("change headquarters or corporate records")}

      {mode === "browse" && (
        <>
          {!wide && (
            <div className="segmented corporate-cluster-tabs" role="tablist" aria-label="Corporate clusters">
              {CORPORATE_CLUSTERS.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  role="tab"
                  aria-selected={cluster === item.id}
                  className={cluster === item.id ? "active" : ""}
                  onClick={() => onClusterChange(item.id)}
                >
                  {item.label}
                </button>
              ))}
            </div>
          )}

          {(wide || cluster === "strategy") && (
            <div className="corporate-cluster" data-cluster="strategy">
              <div className="cluster-head">
                <h2>Strategy</h2>
              </div>
              <div className="card">
                <h2>CEO scorecard</h2>
                <p className="muted">Measured from persisted operations — not simulated. HQ rooms: {hqRoomCount}</p>
                <pre style={{ whiteSpace: "pre-wrap", fontSize: "0.75rem" }}>
                  {JSON.stringify(scorecard || {}, null, 2)}
                </pre>
              </div>

              <div className="section-head">
                <h2>Objectives</h2>
              </div>
              {objectives.map((objective) => (
                <div key={objective.id} className="card">
                  <strong>{objective.title}</strong>
                  <div className="muted">{objective.status} · due {objective.due_at}</div>
                  {canManage && objective.status === "open" && (
                    <div className="actions">
                      <button type="button" onClick={() =>
                        runAction(`objective-${objective.id}`, "Objective closed.", () =>
                          api.closeObjective(objective.id))}>Close</button>
                    </div>
                  )}
                  {status(`objective-${objective.id}`)}
                </div>
              ))}
              {!objectives.length && <p className="panel-empty">No objectives.</p>}
            </div>
          )}

          {(wide || cluster === "structure") && (
            <div className="corporate-cluster" data-cluster="structure">
              <div className="cluster-head">
                <h2>Structure</h2>
              </div>
              <div className="section-head">
                <h2>Industry packs</h2>
              </div>
              {packs.map((pack) => (
                <div key={pack.id} className="card muted">
                  {pack.id} — {pack.industry} — minimal {pack.minimal_departments.length} / full {pack.full_departments.length}
                </div>
              ))}
              {!packs.length && <p className="panel-empty">No industry packs.</p>}

              <div className="section-head">
                <h2>Divisions</h2>
              </div>
              {divisions.map((division) => (
                <div key={division.id} className="card">
                  <strong>{division.name}</strong>
                  <div className="muted">{division.industry_pack_id} · {division.mode} · {division.status}</div>
                  {canManage && (
                    <div className="actions">
                      {division.status === "proposed" && (
                        <button type="button" className="primary" onClick={() =>
                          runAction(`division-${division.id}`, "Division activated.", () =>
                            api.activateDivision(division.id))}>Activate</button>
                      )}
                    </div>
                  )}
                  {status(`division-${division.id}`)}
                </div>
              ))}
              {!divisions.length && <p className="panel-empty">No divisions.</p>}
            </div>
          )}

          {(wide || cluster === "people") && (
            <div className="corporate-cluster" data-cluster="people">
              <div className="cluster-head">
                <h2>People</h2>
              </div>
              <div className="section-head">
                <h2>Pending promotions</h2>
              </div>
              {promotions.map((promotion) => (
                <div key={promotion.id} className="card">
                  <strong>{promotion.employee_id}</strong>
                  <div className="muted">{promotion.from_level} → {promotion.to_level} · {promotion.status}</div>
                  {canManage && (
                    <div className="actions">
                      <button type="button" className="approve" onClick={() =>
                        runAction(`promotion-${promotion.id}`, "Promotion approved.", () =>
                          api.decidePromotion(promotion.id, "approved"))}>Approve</button>
                      <button type="button" className="danger" onClick={() =>
                        runAction(`promotion-${promotion.id}`, "Promotion rejected.", () =>
                          api.decidePromotion(promotion.id, "rejected"))}>Reject</button>
                    </div>
                  )}
                  {status(`promotion-${promotion.id}`)}
                </div>
              ))}
              {!promotions.length && <p className="panel-empty">No pending promotions.</p>}

              <div className="section-head">
                <h2>Staffing proposals</h2>
              </div>
              {staffing.map((proposal) => (
                <div key={proposal.id} className="card">
                  <strong>{proposal.kind} · {proposal.position_id}</strong>
                  <div className="muted">{proposal.cost_estimate_cents}¢ · {proposal.rationale}</div>
                  {canManage && (
                    <div className="actions">
                      <button type="button" className="approve" onClick={() =>
                        runAction(`staffing-${proposal.id}`, "Proposal approved.", () =>
                          api.decideStaffingProposal(proposal.id, "approved"))}>Approve</button>
                      <button type="button" className="danger" onClick={() =>
                        runAction(`staffing-${proposal.id}`, "Proposal rejected.", () =>
                          api.decideStaffingProposal(proposal.id, "rejected"))}>Reject</button>
                    </div>
                  )}
                  {status(`staffing-${proposal.id}`)}
                </div>
              ))}
              {!staffing.length && <p className="panel-empty">No pending staffing proposals.</p>}
            </div>
          )}

          {(wide || cluster === "coordination") && (
            <div className="corporate-cluster" data-cluster="coordination">
              <div className="cluster-head">
                <h2>Coordination</h2>
              </div>
              <div className="section-head">
                <h2>Cross-department requests</h2>
              </div>
              {crossDept.map((item) => (
                <div key={item.id} className="card">
                  <strong>{item.subject}</strong>
                  <div className="muted">
                    {item.requesting_department_id} → {item.delivering_department_id} · {item.status}
                  </div>
                  {canManage && item.status === "pending_acceptance" && (
                    <div className="actions">
                      <button type="button" className="primary" onClick={() =>
                        runAction(`cross-dept-${item.id}`, "Request accepted.", () =>
                          api.acceptCrossDepartmentRequest(item.id))}>Accept</button>
                    </div>
                  )}
                  {status(`cross-dept-${item.id}`)}
                </div>
              ))}
              {!crossDept.length && <p className="panel-empty">No cross-department requests.</p>}

              <div className="section-head">
                <h2>Open activity</h2>
              </div>
              {activity.map((item) => (
                <div key={item.id} className="card muted">
                  {item.kind} · {item.status}{item.room_id ? ` · room ${item.room_id}` : ""}
                </div>
              ))}
              {!activity.length && <p className="panel-empty">No open activity sessions.</p>}
            </div>
          )}
        </>
      )}

      {mode === "manage" && canManage && (
        <ManageClusters
          ariaLabel="Corporate manage groups"
          defaultGroupId="goals"
          activeGroupId={manageGroup}
          onActiveGroupIdChange={onManageGroupChange}
          groups={[
            {
              id: "goals",
              label: "Goals",
              content: (
                <>
                  <div className="section-head">
                    <h2>Create objective</h2>
                  </div>
                  <form className="card" onSubmit={createObjective}>
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
                </>
              ),
            },
            {
              id: "structure",
              label: "Structure",
              content: (
                <>
                  <div className="section-head">
                    <h2>Propose division</h2>
                  </div>
                  <form className="card" onSubmit={proposeDivision}>
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
                </>
              ),
            },
            {
              id: "coordination",
              label: "Coordination",
              content: (
                <>
                  <div className="section-head">
                    <h2>Create cross-department request</h2>
                  </div>
                  <form className="card" onSubmit={createCrossDept}>
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
                </>
              ),
            },
            {
              id: "ops",
              label: "Ops",
              content: (
                <>
                  <div className="section-head">
                    <h2>Corporate operations</h2>
                  </div>
                  <div className="card">
                    <div className="actions">
                      <button id="default-floorplan-btn" type="button" className="primary" onClick={() =>
                        runAction("default-floorplan", "Default floorplan created.", () =>
                          api.createDefaultFloorplan())}>Create default floorplan</button>
                      <button id="staffing-scan-btn" type="button" className="primary" onClick={() =>
                        runAction("staffing-scan", "Scan complete.", () =>
                          api.scanStaffingGaps())}>Scan staffing gaps</button>
                    </div>
                    {status("default-floorplan")}
                    {status("staffing-scan")}
                  </div>
                </>
              ),
            },
          ]}
        />
      )}
    </section>
  );
}
