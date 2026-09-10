import { useCallback, useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import type { ApiClient } from "./api/client";
import { formatUsd } from "./financeMoney";

type SubTab = "overview" | "invoices" | "adjustments" | "periods";

const SUB_TABS: [SubTab, string][] = [
  ["overview", "Overview"],
  ["invoices", "Invoices"],
  ["adjustments", "Adjustments"],
  ["periods", "Periods"],
];

type FinancePanelProps = {
  api: ApiClient;
  hasToken: boolean;
  canPause: boolean;
  scopeNotice: (action: string, scope: string) => ReactNode;
  runAction: (
    key: string,
    okMessage: string,
    run: () => Promise<void>,
  ) => Promise<void>;
  status: (key: string) => ReactNode;
};

type FinanceSummary = {
  billed_cost_gross_cents: number;
  billed_adjustment_cents: number;
  billed_cost_cents: number;
  revenue_cents: number;
  open_budget_period: Record<string, unknown> | null;
};

type BilledCost = Record<string, unknown> & {
  id: string;
  amount_cents: number;
  remaining_creditable_cents: number;
  provider: string;
};

function toDatetimeLocalValue(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function fromDatetimeLocalValue(local: string): string {
  const d = new Date(local);
  if (Number.isNaN(d.getTime())) throw new Error("Invalid datetime");
  return d.toISOString();
}

function cents(value: unknown): number {
  return typeof value === "number" ? value : Number(value);
}

export function FinancePanel(props: FinancePanelProps) {
  const { api, hasToken, canPause, scopeNotice, runAction, status } = props;
  const [subTab, setSubTab] = useState<SubTab>("overview");
  const [summary, setSummary] = useState<FinanceSummary | null>(null);
  const [invoices, setInvoices] = useState<Record<string, unknown>[]>([]);
  const [adjustments, setAdjustments] = useState<Record<string, unknown>[]>([]);
  const [periods, setPeriods] = useState<Record<string, unknown>[]>([]);
  const [billedCosts, setBilledCosts] = useState<BilledCost[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [expandedInvoice, setExpandedInvoice] = useState<Record<string, unknown> | null>(null);
  const [expandedInvoiceId, setExpandedInvoiceId] = useState("");
  const [invoiceStart, setInvoiceStart] = useState("");
  const [invoiceEnd, setInvoiceEnd] = useState("");
  const [adjustmentKind, setAdjustmentKind] = useState<"void" | "partial_credit">("partial_credit");
  const [selectedBilledCostId, setSelectedBilledCostId] = useState("");
  const [adjustmentAmount, setAdjustmentAmount] = useState("");
  const [adjustmentReason, setAdjustmentReason] = useState("");
  const [periodStart, setPeriodStart] = useState("");
  const [periodEnd, setPeriodEnd] = useState("");
  const [periodLimit, setPeriodLimit] = useState("500000");
  const periodStartRef = useRef<HTMLInputElement>(null);
  const expandedInvoiceIdRef = useRef("");

  const loadAll = useCallback(async (isCancelled: () => boolean = () => false) => {
    if (!hasToken) return;
    try {
      const [summaryBody, invoiceBody, adjustmentBody, periodBody, billedCostBody] =
        await Promise.all([
          api.financeSummary(),
          api.financeInvoices(),
          api.financeAdjustments(),
          api.financeBudgetPeriods(),
          api.financeBilledCosts(),
        ]);
      if (isCancelled()) return;
      const costs = billedCostBody.billed_costs as BilledCost[];
      setSummary(summaryBody);
      setInvoices(invoiceBody.invoices || []);
      setAdjustments(adjustmentBody.adjustments || []);
      setPeriods(periodBody.periods || []);
      setBilledCosts(costs);
      setSelectedBilledCostId((current) =>
        costs.some((item) => item.id === current) ? current : costs[0]?.id || "");
      setLoadError(null);
    } catch (error) {
      if (isCancelled()) return;
      setSummary(null);
      setInvoices([]);
      setAdjustments([]);
      setPeriods([]);
      setBilledCosts([]);
      setSelectedBilledCostId("");
      setLoadError(error instanceof Error ? error.message : String(error));
    }
  }, [api, hasToken]);

  useEffect(() => {
    let cancelled = false;
    void loadAll(() => cancelled);
    return () => {
      cancelled = true;
    };
  }, [loadAll]);

  const selectedBilledCost = billedCosts.find((item) => item.id === selectedBilledCostId);

  async function toggleInvoice(invoiceId: string) {
    if (expandedInvoiceId === invoiceId) {
      expandedInvoiceIdRef.current = "";
      setExpandedInvoiceId("");
      setExpandedInvoice(null);
      return;
    }
    expandedInvoiceIdRef.current = invoiceId;
    setExpandedInvoiceId(invoiceId);
    setExpandedInvoice(null);
    try {
      const detail = await api.financeInvoice(invoiceId);
      if (expandedInvoiceIdRef.current !== invoiceId) return;
      setExpandedInvoice(detail);
    } catch (error) {
      if (expandedInvoiceIdRef.current !== invoiceId) return;
      setExpandedInvoice({
        error: error instanceof Error ? error.message : String(error),
      });
    }
  }

  function setCalendarMonth() {
    const now = new Date();
    const start = new Date(now.getFullYear(), now.getMonth(), 1, 0, 0);
    const end = new Date(now.getFullYear(), now.getMonth() + 1, 1, 0, 0);
    setInvoiceStart(toDatetimeLocalValue(start.toISOString()));
    setInvoiceEnd(toDatetimeLocalValue(end.toISOString()));
  }

  async function createInvoice(event: FormEvent) {
    event.preventDefault();
    await runAction("financeInvoice", "Invoice created.", async () => {
      if (!invoiceStart || !invoiceEnd) throw new Error("Invoice start and end are required.");
      await api.createFinanceInvoice(
        fromDatetimeLocalValue(invoiceStart),
        fromDatetimeLocalValue(invoiceEnd),
      );
      setInvoiceStart("");
      setInvoiceEnd("");
      await loadAll();
    });
  }

  async function postAdjustment(event: FormEvent) {
    event.preventDefault();
    await runAction("financeAdjustment", "Adjustment recorded.", async () => {
      if (!selectedBilledCost) throw new Error("Select a creditable billed cost.");
      const payload: Record<string, unknown> = {
        kind: adjustmentKind,
        billed_cost_id: selectedBilledCost.id,
        reason: adjustmentReason.trim(),
      };
      if (!adjustmentReason.trim()) throw new Error("Reason is required.");
      if (adjustmentKind === "partial_credit") {
        const amount = Number(adjustmentAmount);
        if (!Number.isFinite(amount) || amount <= 0) {
          throw new Error("Partial credit must be greater than zero.");
        }
        if (amount > selectedBilledCost.remaining_creditable_cents) {
          throw new Error("Partial credit exceeds the remaining creditable amount.");
        }
        payload.amount_cents = amount;
      }
      await api.postFinanceAdjustment(payload);
      setAdjustmentAmount("");
      setAdjustmentReason("");
      await loadAll();
    });
  }

  async function closePeriod(period: Record<string, unknown>) {
    if (!window.confirm("Close this budget period? Snapshot will be frozen.")) return;
    await runAction(
      `finance-close-${String(period.id)}`,
      "Period closed.",
      async () => {
        await api.closeFinanceBudgetPeriod(String(period.id));
        setPeriodStart(toDatetimeLocalValue(String(period.period_end)));
        setSubTab("periods");
        window.setTimeout(() => periodStartRef.current?.focus(), 0);
        await loadAll();
      },
    );
  }

  function setNextThirtyDays() {
    const start = new Date();
    const end = new Date(start);
    end.setDate(end.getDate() + 30);
    setPeriodStart(toDatetimeLocalValue(start.toISOString()));
    setPeriodEnd(toDatetimeLocalValue(end.toISOString()));
  }

  async function setBudgetPeriod(event: FormEvent) {
    event.preventDefault();
    await runAction("financePeriod", "Budget period set.", async () => {
      if (!periodStart || !periodEnd) throw new Error("Period start and end are required.");
      const limit = Number(periodLimit);
      if (!Number.isInteger(limit) || limit < 0) {
        throw new Error("Limit must be a non-negative integer number of cents.");
      }
      await api.setFinanceBudgetPeriod({
        scope: "company",
        period_start: fromDatetimeLocalValue(periodStart),
        period_end: fromDatetimeLocalValue(periodEnd),
        limit_cents: limit,
      });
      setPeriodStart("");
      setPeriodEnd("");
      await loadAll();
    });
  }

  const invoiceLines =
    expandedInvoice && typeof expandedInvoice.body === "object" && expandedInvoice.body
      ? ((expandedInvoice.body as Record<string, unknown>).lines as Record<string, unknown>[] | undefined) || []
      : [];

  return (
    <section>
      <p className="lede">
        Overview and lists are read from persisted finance state. Create invoice, adjustment,
        and period actions stay on their tabs — not a second Browse/Manage layer.
      </p>
      <div className="segmented" role="tablist" aria-label="Finance sections">
        {SUB_TABS.map(([t, label]) => (
          <button
            key={t}
            type="button"
            role="tab"
            aria-selected={subTab === t}
            className={subTab === t ? "active" : ""}
            onClick={() => setSubTab(t)}
          >
            {label}
          </button>
        ))}
      </div>

      {loadError && <p className="error">Finance data could not be loaded: {loadError}</p>}

      {subTab === "overview" && (
        <div className="card">
          <h2>Overview</h2>
          <p className="muted">API amounts are cents; display is USD.</p>
          {summary ? (
            <>
              <div>Gross billed: {formatUsd(summary.billed_cost_gross_cents)}</div>
              <div>Adjustments: {formatUsd(summary.billed_adjustment_cents)}</div>
              <div>Net billed: {formatUsd(summary.billed_cost_cents)}</div>
              <div>Revenue: {formatUsd(summary.revenue_cents)}</div>
              {summary.open_budget_period ? (
                <p className="muted">
                  Open period: {String(summary.open_budget_period.period_start)} →{" "}
                  {String(summary.open_budget_period.period_end)} · limit{" "}
                  {formatUsd(cents(summary.open_budget_period.limit_cents))}
                </p>
              ) : <p className="muted">No open budget period.</p>}
            </>
          ) : <p className="muted">No finance summary loaded.</p>}
        </div>
      )}

      {subTab === "invoices" && (
        <>
          <div className="card">
            <h2>Invoices</h2>
            {invoices.map((invoice) => {
              const id = String(invoice.id);
              return (
                <div key={id} style={{ marginBottom: "0.65rem" }}>
                  <button type="button" onClick={() => void toggleInvoice(id)}>
                    {id.slice(0, 8)}… · {formatUsd(cents(invoice.total_cents))}
                  </button>
                  <div className="muted">
                    {String(invoice.period_start)} → {String(invoice.period_end)} ·{" "}
                    {String(invoice.line_count)} lines
                  </div>
                  {expandedInvoiceId === id && Boolean(expandedInvoice?.error) && (
                    <p className="error">{String(expandedInvoice?.error)}</p>
                  )}
                  {expandedInvoiceId === id && invoiceLines.map((line, index) => (
                    <div className="muted" key={`${String(line.billed_cost_id)}-${index}`}>
                      {String(line.provider)} · {formatUsd(cents(line.amount_cents))} ·{" "}
                      {String(line.billed_cost_id)}
                    </div>
                  ))}
                </div>
              );
            })}
            {!invoices.length && <p className="muted">No invoices yet.</p>}
          </div>
          {canPause ? (
            <form className="card" onSubmit={createInvoice}>
              <h2>Create invoice</h2>
              <label htmlFor="finance-invoice-start">Period start</label>
              <input id="finance-invoice-start" type="datetime-local" value={invoiceStart}
                onChange={(event) => setInvoiceStart(event.target.value)} required />
              <label htmlFor="finance-invoice-end">Period end</label>
              <input id="finance-invoice-end" type="datetime-local" value={invoiceEnd}
                onChange={(event) => setInvoiceEnd(event.target.value)} required />
              <div className="actions">
                <button type="button" onClick={setCalendarMonth}>This calendar month</button>
                <button className="primary" type="submit">Create invoice</button>
              </div>
              {status("financeInvoice")}
            </form>
          ) : scopeNotice("create invoices", "company.pause")}
        </>
      )}

      {subTab === "adjustments" && (
        <>
          <div className="card">
            <h2>Adjustments</h2>
            {adjustments.map((adjustment) => (
              <div key={String(adjustment.id)} style={{ marginBottom: "0.55rem" }}>
                <strong>{String(adjustment.kind)}</strong>
                <div className="muted">
                  {String(adjustment.billed_cost_id)} · {formatUsd(cents(adjustment.amount_cents))} ·{" "}
                  {String(adjustment.reason)}
                </div>
              </div>
            ))}
            {!adjustments.length && <p className="muted">No adjustments yet.</p>}
          </div>
          {canPause ? (
            <form className="card" onSubmit={postAdjustment}>
              <h2>Post adjustment</h2>
              <label htmlFor="finance-adjustment-kind">Kind</label>
              <select id="finance-adjustment-kind" value={adjustmentKind}
                onChange={(event) => setAdjustmentKind(event.target.value as "void" | "partial_credit")}>
                <option value="partial_credit">partial_credit</option>
                <option value="void">void</option>
              </select>
              <label htmlFor="finance-billed-cost">Creditable billed cost</label>
              <select id="finance-billed-cost" value={selectedBilledCostId}
                onChange={(event) => setSelectedBilledCostId(event.target.value)}
                disabled={billedCosts.length === 0} required>
                {billedCosts.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.provider} · {formatUsd(item.amount_cents)} · remaining{" "}
                    {formatUsd(item.remaining_creditable_cents)}
                  </option>
                ))}
              </select>
              {selectedBilledCost && (
                <p className="muted">
                  Remaining creditable: {formatUsd(selectedBilledCost.remaining_creditable_cents)}
                </p>
              )}
              {billedCosts.length === 0 && <p className="muted">No creditable lines.</p>}
              {adjustmentKind === "partial_credit" && (
                <>
                  <label htmlFor="finance-adjustment-amount">Amount cents</label>
                  <input id="finance-adjustment-amount" type="number" min={1} step={1}
                    max={selectedBilledCost?.remaining_creditable_cents}
                    value={adjustmentAmount}
                    onChange={(event) => setAdjustmentAmount(event.target.value)} required />
                </>
              )}
              <label htmlFor="finance-adjustment-reason">Reason</label>
              <input id="finance-adjustment-reason" value={adjustmentReason}
                onChange={(event) => setAdjustmentReason(event.target.value)} required />
              <div className="actions">
                <button className="primary" type="submit" disabled={billedCosts.length === 0}>
                  Post adjustment
                </button>
              </div>
              {status("financeAdjustment")}
            </form>
          ) : scopeNotice("post adjustments", "company.pause")}
        </>
      )}

      {subTab === "periods" && (
        <>
          <div className="card">
            <h2>Periods</h2>
            {periods.map((period) => (
              <div key={String(period.id)} style={{ marginBottom: "0.65rem" }}>
                <strong>{String(period.scope)}</strong>
                <div className="muted">
                  {String(period.period_start)} → {String(period.period_end)} · limit{" "}
                  {formatUsd(cents(period.limit_cents))} · {period.closed ? "closed" : "open"}
                </div>
                {canPause && !period.closed && (
                  <button type="button" onClick={() => void closePeriod(period)}>Close period</button>
                )}
                {status(`finance-close-${String(period.id)}`)}
              </div>
            ))}
            {!periods.length && <p className="muted">No budget periods.</p>}
          </div>
          {canPause ? (
            <form className="card" onSubmit={setBudgetPeriod}>
              <h2>Set budget period</h2>
              <label htmlFor="finance-period-start">Start</label>
              <input ref={periodStartRef} id="finance-period-start" type="datetime-local"
                value={periodStart} onChange={(event) => setPeriodStart(event.target.value)} required />
              <label htmlFor="finance-period-end">End</label>
              <input id="finance-period-end" type="datetime-local" value={periodEnd}
                onChange={(event) => setPeriodEnd(event.target.value)} required />
              <label htmlFor="finance-period-limit">Limit cents</label>
              <input id="finance-period-limit" type="number" min={0} step={1} value={periodLimit}
                onChange={(event) => setPeriodLimit(event.target.value)} required />
              <div className="actions">
                <button type="button" onClick={setNextThirtyDays}>Next 30 days</button>
                <button className="primary" type="submit">Set period</button>
              </div>
              {status("financePeriod")}
            </form>
          ) : scopeNotice("set budget periods", "company.pause")}
        </>
      )}
    </section>
  );
}
