import { useState, type Dispatch, type ReactNode, type SetStateAction } from "react";
import type { ApiClient, HeadDispatch, OrgDepartment, WorkerCard } from "./api/client";
import { ModeSwitch, type PanelMode } from "./ModeSwitch";

type FormStatus = { ok: boolean; text: string };

type OrgPanelProps = {
  api: ApiClient;
  organization: OrgDepartment[];
  headInbox: HeadDispatch[];
  canManage: boolean;
  activateProjectId: string;
  setActivateProjectId: Dispatch<SetStateAction<string>>;
  activateDepartmentId: string;
  setActivateDepartmentId: Dispatch<SetStateAction<string>>;
  appointHeadDepartment: string;
  setAppointHeadDepartment: Dispatch<SetStateAction<string>>;
  appointHeadPrincipal: string;
  setAppointHeadPrincipal: Dispatch<SetStateAction<string>>;
  vacateHeadDepartment: string;
  setVacateHeadDepartment: Dispatch<SetStateAction<string>>;
  positionId: string;
  setPositionId: Dispatch<SetStateAction<string>>;
  positionPrincipal: string;
  setPositionPrincipal: Dispatch<SetStateAction<string>>;
  positionReportsTo: string;
  setPositionReportsTo: Dispatch<SetStateAction<string>>;
  releaseAssignmentId: string;
  setReleaseAssignmentId: Dispatch<SetStateAction<string>>;
  assignDispatchId: string;
  setAssignDispatchId: Dispatch<SetStateAction<string>>;
  assignAssignee: string;
  setAssignAssignee: Dispatch<SetStateAction<string>>;
  assignAction: string;
  setAssignAction: Dispatch<SetStateAction<string>>;
  assignCost: string;
  setAssignCost: Dispatch<SetStateAction<string>>;
  workerLookupId: string;
  setWorkerLookupId: Dispatch<SetStateAction<string>>;
  workerCard: WorkerCard | null;
  setWorkerCard: Dispatch<SetStateAction<WorkerCard | null>>;
  setFormStatus: Dispatch<SetStateAction<Record<string, FormStatus>>>;
  runAction: (
    key: string,
    success: string,
    action: () => Promise<unknown>,
  ) => Promise<boolean>;
  status: (key: string) => ReactNode;
  scopeNotice: (what: string, scope?: string) => ReactNode;
};

export function OrgPanel(props: OrgPanelProps) {
  const {
    api, organization, headInbox, canManage,
    activateProjectId, setActivateProjectId, activateDepartmentId, setActivateDepartmentId,
    appointHeadDepartment, setAppointHeadDepartment, appointHeadPrincipal, setAppointHeadPrincipal,
    vacateHeadDepartment, setVacateHeadDepartment,
    positionId, setPositionId, positionPrincipal, setPositionPrincipal,
    positionReportsTo, setPositionReportsTo, releaseAssignmentId, setReleaseAssignmentId,
    assignDispatchId, setAssignDispatchId, assignAssignee, setAssignAssignee,
    assignAction, setAssignAction, assignCost, setAssignCost,
    workerLookupId, setWorkerLookupId, workerCard, setWorkerCard,
    setFormStatus, runAction, status, scopeNotice,
  } = props;
  const [mode, setMode] = useState<PanelMode>("browse");

  return (
    <section>
      <p className="lede">Catalog, persisted seat status, and roster. Vacant and dormant seats are not healthy workers.</p>
      <ModeSwitch mode={mode} onChange={setMode} label="Organization mode" />
      {!canManage && scopeNotice("edit the organization")}

      {mode === "browse" && (
        <>
          {organization.map((department) => (
            <div key={department.id} className="card">
              <strong>{department.id} · {department.name}</strong>
              <div className="muted">
                Head seat: {department.seat.status} · {department.seat.principal_id || "vacant"}
              </div>
              <div className="muted">
                Roster: {department.assignments.length
                  ? department.assignments.map(
                    (assignment) =>
                      `${assignment.principal_id} (${assignment.position_id}; assignment ${assignment.id})`,
                  ).join(", ")
                  : "none"}
              </div>
            </div>
          ))}
          {!organization.length && <p className="panel-empty">No organization catalog returned.</p>}

          <div className="section-head">
            <h2>Head inbox</h2>
          </div>
          {headInbox.map((dispatch) => (
            <div key={dispatch.id} className="card">
              <strong>{dispatch.project_id} · {dispatch.department_id}</strong>
              <div className="muted">{dispatch.status} · budget {dispatch.budget_cents}¢</div>
              <p>{dispatch.brief}</p>
              <p className="muted">Acceptance: {dispatch.acceptance_criteria}</p>
              {canManage && dispatch.status === "queued_for_head" && (
                <div className="actions">
                  <button type="button" onClick={() => setAssignDispatchId(dispatch.id)}>Assign</button>
                </div>
              )}
              {canManage && assignDispatchId === dispatch.id && (
                <form onSubmit={async (event) => {
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
                  <label htmlFor={`assign-assignee-${dispatch.id}`}>Assignee principal</label>
                  <input
                    id={`assign-assignee-${dispatch.id}`}
                    type="text"
                    required
                    value={assignAssignee}
                    onChange={(event) => setAssignAssignee(event.target.value)}
                  />
                  <label htmlFor={`assign-action-${dispatch.id}`}>Action</label>
                  <input
                    id={`assign-action-${dispatch.id}`}
                    type="text"
                    required
                    value={assignAction}
                    onChange={(event) => setAssignAction(event.target.value)}
                  />
                  <label htmlFor={`assign-cost-${dispatch.id}`}>Cost (¢)</label>
                  <input
                    id={`assign-cost-${dispatch.id}`}
                    required
                    type="number"
                    inputMode="numeric"
                    min="0"
                    value={assignCost}
                    onChange={(event) => setAssignCost(event.target.value)}
                  />
                  <div className="actions">
                    <button className="primary" type="submit">Queue assignment</button>
                    <button type="button" onClick={() => setAssignDispatchId("")}>Cancel</button>
                  </div>
                  {status("assign-dispatch")}
                </form>
              )}
            </div>
          ))}
          {!headInbox.length && <p className="panel-empty">No open head dispatches.</p>}
        </>
      )}

      {mode === "manage" && (
        <>
          {canManage && (
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
            <input
              id="appoint-head-department"
              type="text"
              required
              value={appointHeadDepartment}
              onChange={(event) => setAppointHeadDepartment(event.target.value)}
            />
            <label htmlFor="appoint-head-principal">Principal id</label>
            <input
              id="appoint-head-principal"
              type="text"
              required
              value={appointHeadPrincipal}
              onChange={(event) => setAppointHeadPrincipal(event.target.value)}
            />
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
            <input
              id="vacate-head-department"
              type="text"
              required
              value={vacateHeadDepartment}
              onChange={(event) => setVacateHeadDepartment(event.target.value)}
            />
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
            <input
              id="assign-position-id"
              type="text"
              required
              value={positionId}
              placeholder="engineering:Developer"
              onChange={(event) => setPositionId(event.target.value)}
            />
            <label htmlFor="assign-position-principal">Principal id</label>
            <input
              id="assign-position-principal"
              type="text"
              required
              value={positionPrincipal}
              onChange={(event) => setPositionPrincipal(event.target.value)}
            />
            <label htmlFor="assign-position-reports-to">Reports-to seat id (optional)</label>
            <input
              id="assign-position-reports-to"
              type="text"
              value={positionReportsTo}
              placeholder="seat:engineering"
              onChange={(event) => setPositionReportsTo(event.target.value)}
            />
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
            <input
              id="release-assignment-id"
              type="text"
              required
              value={releaseAssignmentId}
              onChange={(event) => setReleaseAssignmentId(event.target.value)}
            />
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
              setFormStatus((previous) => ({
                ...previous,
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
            <input
              id="activate-project"
              type="text"
              required
              value={activateProjectId}
              onChange={(event) => setActivateProjectId(event.target.value)}
            />
            <label htmlFor="activate-department">Department id</label>
            <input
              id="activate-department"
              type="text"
              required
              value={activateDepartmentId}
              onChange={(event) => setActivateDepartmentId(event.target.value)}
            />
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
              } catch (error) {
                setWorkerCard(null);
                throw error;
              }
            });
          }}>
            <h2>Worker card</h2>
            <label htmlFor="worker-lookup-id">Employee id</label>
            <input
              id="worker-lookup-id"
              type="text"
              required
              value={workerLookupId}
              onChange={(event) => setWorkerLookupId(event.target.value)}
            />
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
        </>
      )}
    </section>
  );
}
