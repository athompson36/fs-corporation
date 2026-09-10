import type { FormEvent } from "react";
import type { DecisionItem, OwnerRequest } from "./api/client";
import { canApprove, canPause, canRespondInbox, canResume } from "./scopes";

type StatusFn = (key: string) => React.ReactNode;
type ScopeNoticeFn = (action: string, scope: string) => React.ReactNode;

export type HomePanelProps = {
  scopes: string[] | undefined;
  decisions: DecisionItem[];
  inbox: OwnerRequest[];
  company: Record<string, unknown>;
  dashboard: Record<string, unknown> | null;
  ownerResponseDrafts: Record<string, string>;
  setOwnerResponseDrafts: React.Dispatch<React.SetStateAction<Record<string, string>>>;
  onDecide: (item: DecisionItem, decision: "approved" | "rejected") => void;
  onRespond: (req: OwnerRequest) => void;
  onPause: () => void;
  onResume: () => void;
  onRefresh: () => void;
  onOpenDecisions: () => void;
  onOpenInbox: () => void;
  status: StatusFn;
  scopeNotice: ScopeNoticeFn;
  accessBadge: string | null;
};

export function HomePanel(props: HomePanelProps) {
  const {
    scopes, decisions, inbox, company, dashboard,
    ownerResponseDrafts, setOwnerResponseDrafts,
    onDecide, onRespond, onPause, onResume, onRefresh,
    onOpenDecisions, onOpenInbox, status, scopeNotice, accessBadge,
  } = props;

  return (
    <section className="home-panel">
      <h1 className="brand-title">
        FS-Corporation{" "}
        {accessBadge && <span className="tag tag-proposal">{accessBadge}</span>}
      </h1>
      <p className="lede">Needs-you queue from persisted decisions and inbox — nothing invented.</p>

      <div className="card">
        <div className="section-head">
          <h2>Needs you</h2>
          <div className="chip-row">
            <button type="button" className="chip" onClick={onOpenDecisions}>View all decisions</button>
            <button type="button" className="chip" onClick={onOpenInbox}>View all inbox</button>
          </div>
        </div>

        {decisions.map((item) => (
          <div key={`d-${item.kind}-${item.id}`} className="card nested-card">
            <div className={item.kind === "consultant" ? "tag tag-proposal" : "tag tag-warning"}>{item.kind}</div>
            <strong>{item.title}</strong>
            <p className="muted">{item.summary}</p>
            {canApprove(scopes) && (item.kind === "policy" || item.kind === "consultant") && (
              <div className="actions">
                <button className="approve" type="button" onClick={() => onDecide(item, "approved")}>Approve</button>
                <button className="danger" type="button" onClick={() => onDecide(item, "rejected")}>Reject</button>
              </div>
            )}
            {status(`decision-${item.id}`)}
          </div>
        ))}

        {inbox.map((req) => (
          <div key={`i-${req.id}`} className="card nested-card">
            <div className="muted">{req.kind} · {req.department_id}</div>
            <strong>{req.subject}</strong>
            <p>{req.body}</p>
            {canRespondInbox(scopes) && (
              <form
                onSubmit={(event: FormEvent) => {
                  event.preventDefault();
                  onRespond(req);
                }}
              >
                <label htmlFor={`home-owner-response-${req.id}`}>Response</label>
                <textarea
                  id={`home-owner-response-${req.id}`}
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

        {!decisions.length && !inbox.length && (
          <p className="muted">Nothing needs you right now.</p>
        )}
        {decisions.length > 0 && !canApprove(scopes) && scopeNotice("decide proposals", "policy.approve")}
        {inbox.length > 0 && !canRespondInbox(scopes)
          && scopeNotice("respond to owner requests", "company.pause")}
      </div>

      <div className="card">
        <h2>Status</h2>
        <div>Policy v{String(company.policy_version ?? "?")}</div>
        <div>Paused: {String(company.paused ?? false)}</div>
        <div>Simulated spend: {String(company.simulated_spend_cents ?? 0)}¢</div>
        <div>Reserved: {String(company.reserved_cents ?? 0)}¢</div>
        <div>Open owner inbox: {String(dashboard?.owner_inbox_open ?? inbox.length)}</div>
        <div>Pending decisions: {String(decisions.length)}</div>
        <div className="actions">
          {canResume(scopes) && (
            <button className="primary" type="button" onClick={onResume}>Resume</button>
          )}
          {canPause(scopes) && (
            <button className="danger" type="button" onClick={onPause}>Pause</button>
          )}
          <button type="button" onClick={onRefresh}>Refresh</button>
        </div>
      </div>
    </section>
  );
}
