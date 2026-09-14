import { useCallback, useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import type { ApiClient } from "./api/client";
import { formatUsd } from "./financeMoney";
import { ManageClusters } from "./ManageClusters";
import { ModeSwitch, type PanelMode } from "./ModeSwitch";

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
  mode: PanelMode;
  onModeChange: (mode: PanelMode) => void;
  manageGroup: string;
  onManageGroupChange: (id: string) => void;
};

type FinanceSummary = {
  billed_cost_gross_cents: number;
  billed_adjustment_cents: number;
  billed_cost_cents: number;
  revenue_cents: number;
  open_budget_period: Record<string, unknown> | null;
  provider_invoice_variance_cents?: number;
  pricing?: { model_cents_per_1k_configured: boolean; hint: string };
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
  const {
    api, hasToken, canPause, scopeNotice, runAction, status,
    mode, onModeChange, manageGroup, onManageGroupChange,
  } = props;
  const [summary, setSummary] = useState<FinanceSummary | null>(null);
  const [invoices, setInvoices] = useState<Record<string, unknown>[]>([]);
  const [providerInvoices, setProviderInvoices] = useState<Record<string, unknown>[]>([]);
  const [adjustments, setAdjustments] = useState<Record<string, unknown>[]>([]);
  const [periods, setPeriods] = useState<Record<string, unknown>[]>([]);
  const [billedCosts, setBilledCosts] = useState<BilledCost[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [expandedInvoice, setExpandedInvoice] = useState<Record<string, unknown> | null>(null);
  const [expandedInvoiceId, setExpandedInvoiceId] = useState("");
  const [expandedProviderInvoice, setExpandedProviderInvoice] = useState<Record<string, unknown> | null>(null);
  const [expandedProviderInvoiceId, setExpandedProviderInvoiceId] = useState("");
  const [invoiceStart, setInvoiceStart] = useState("");
  const [invoiceEnd, setInvoiceEnd] = useState("");
  const [providerName, setProviderName] = useState("");
  const [providerExternalId, setProviderExternalId] = useState("");
  const [providerTotalCents, setProviderTotalCents] = useState("");
  const [providerIssuedAt, setProviderIssuedAt] = useState("");
  const [providerNote, setProviderNote] = useState("");
  const [selectedProviderInvoiceId, setSelectedProviderInvoiceId] = useState("");
  const [providerAllocateBilledCostId, setProviderAllocateBilledCostId] = useState("");
  const [providerAllocatedCents, setProviderAllocatedCents] = useState("");
  const [voidProviderInvoiceId, setVoidProviderInvoiceId] = useState("");
  const [adjustmentKind, setAdjustmentKind] = useState<"void" | "partial_credit">("partial_credit");
  const [selectedBilledCostId, setSelectedBilledCostId] = useState("");
  const [adjustmentAmount, setAdjustmentAmount] = useState("");
  const [adjustmentReason, setAdjustmentReason] = useState("");
  const [periodStart, setPeriodStart] = useState("");
  const [periodEnd, setPeriodEnd] = useState("");
  const [periodLimit, setPeriodLimit] = useState("500000");
  const expandedInvoiceIdRef = useRef("");
  const expandedProviderInvoiceIdRef = useRef("");

  const loadAll = useCallback(async (isCancelled: () => boolean = () => false) => {
    if (!hasToken) return;
    try {
      const [summaryBody, invoiceBody, providerInvoiceBody, adjustmentBody, periodBody, billedCostBody] =
        await Promise.all([
          api.financeSummary(),
          api.financeInvoices(),
          api.listProviderInvoices(),
          api.financeAdjustments(),
          api.financeBudgetPeriods(),
          api.financeBilledCosts(),
        ]);
      if (isCancelled()) return;
      const costs = billedCostBody.billed_costs as BilledCost[];
      const providerList = providerInvoiceBody.provider_invoices || [];
      setSummary(summaryBody);
      setInvoices(invoiceBody.invoices || []);
      setProviderInvoices(providerList);
      setAdjustments(adjustmentBody.adjustments || []);
      setPeriods(periodBody.periods || []);
      setBilledCosts(costs);
      setSelectedBilledCostId((current) =>
        costs.some((item) => item.id === current) ? current : costs[0]?.id || "");
      const openProvider = providerList.filter((item) => item.status === "open");
      setSelectedProviderInvoiceId((current) =>
        openProvider.some((item) => String(item.id) === current)
          ? current
          : String(openProvider[0]?.id || ""));
      setProviderAllocateBilledCostId((current) =>
        costs.some((item) => item.id === current) ? current : costs[0]?.id || "");
      setVoidProviderInvoiceId((current) =>
        openProvider.some((item) => String(item.id) === current)
          ? current
          : String(openProvider[0]?.id || ""));
      setLoadError(null);
    } catch (error) {
      if (isCancelled()) return;
      setSummary(null);
      setInvoices([]);
      setProviderInvoices([]);
      setAdjustments([]);
      setPeriods([]);
      setBilledCosts([]);
      setSelectedBilledCostId("");
      setSelectedProviderInvoiceId("");
      setProviderAllocateBilledCostId("");
      setVoidProviderInvoiceId("");
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

  async function toggleProviderInvoice(invoiceId: string) {
    if (expandedProviderInvoiceId === invoiceId) {
      expandedProviderInvoiceIdRef.current = "";
      setExpandedProviderInvoiceId("");
      setExpandedProviderInvoice(null);
      return;
    }
    expandedProviderInvoiceIdRef.current = invoiceId;
    setExpandedProviderInvoiceId(invoiceId);
    setExpandedProviderInvoice(null);
    try {
      const detail = await api.getProviderInvoice(invoiceId);
      if (expandedProviderInvoiceIdRef.current !== invoiceId) return;
      setExpandedProviderInvoice(detail);
    } catch (error) {
      if (expandedProviderInvoiceIdRef.current !== invoiceId) return;
      setExpandedProviderInvoice({
        error: error instanceof Error ? error.message : String(error),
      });
    }
  }

  async function createProviderInvoice(event: FormEvent) {
    event.preventDefault();
    await runAction("financeProviderInvoice", "Provider invoice created.", async () => {
      if (!providerName.trim()) throw new Error("Provider is required.");
      if (!providerExternalId.trim()) throw new Error("External id is required.");
      const total = Number(providerTotalCents);
      if (!Number.isFinite(total) || total < 0) {
        throw new Error("Total cents must be a non-negative number.");
      }
      if (!providerIssuedAt) throw new Error("Issued at is required.");
      const payload: Record<string, unknown> = {
        provider: providerName.trim(),
        external_id: providerExternalId.trim(),
        total_cents: total,
        issued_at: fromDatetimeLocalValue(providerIssuedAt),
      };
      if (providerNote.trim()) payload.note = providerNote.trim();
      await api.createProviderInvoice(payload);
      setProviderName("");
      setProviderExternalId("");
      setProviderTotalCents("");
      setProviderIssuedAt("");
      setProviderNote("");
      await loadAll();
    });
  }

  async function allocateProviderInvoice(event: FormEvent) {
    event.preventDefault();
    await runAction("financeProviderAllocate", "Allocation recorded.", async () => {
      if (!selectedProviderInvoiceId) throw new Error("Select a provider invoice.");
      if (!providerAllocateBilledCostId) throw new Error("Select a billed cost.");
      const allocated = Number(providerAllocatedCents);
      if (!Number.isFinite(allocated) || allocated < 0) {
        throw new Error("Allocated cents must be a non-negative number.");
      }
      await api.allocateProviderInvoice(selectedProviderInvoiceId, {
        billed_cost_id: providerAllocateBilledCostId,
        allocated_cents: allocated,
      });
      setProviderAllocatedCents("");
      await loadAll();
    });
  }

  async function voidProviderInvoice(invoiceId: string, externalId: string) {
    if (!window.confirm(`Void provider invoice ${externalId || invoiceId}?`)) return;
    await runAction(
      `finance-provider-void-${invoiceId}`,
      "Provider invoice voided.",
      async () => {
        await api.voidProviderInvoice(invoiceId);
        await loadAll();
      },
    );
  }

  async function voidProviderInvoiceFromManage(event: FormEvent) {
    event.preventDefault();
    if (!voidProviderInvoiceId) throw new Error("Select a provider invoice.");
    const selected = openProviderInvoices.find(
      (item) => String(item.id) === voidProviderInvoiceId,
    );
    await voidProviderInvoice(
      voidProviderInvoiceId,
      selected ? String(selected.external_id) : voidProviderInvoiceId,
    );
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
        await loadAll();
      },
    );
  }

  async function openNextPeriod(period: Record<string, unknown>) {
    await runAction(
      `finance-open-next-${String(period.id)}`,
      "Next period opened.",
      async () => {
        await api.openFinanceBudgetPeriodNext(String(period.id));
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

  const providerAllocations =
    expandedProviderInvoice && Array.isArray(expandedProviderInvoice.allocations)
      ? (expandedProviderInvoice.allocations as Record<string, unknown>[])
      : [];

  const openProviderInvoices = providerInvoices.filter((item) => item.status === "open");

  return (
    <section>
      <p className="lede">
        Persisted finance totals and lists in Browse; create invoice, adjustment, and
        period actions in Manage.
      </p>
      <ModeSwitch mode={mode} onChange={onModeChange} label="Finance mode" />
      {loadError && <p className="error">Finance data could not be loaded: {loadError}</p>}

      {mode === "browse" && (
        <ManageClusters
          ariaLabel="Finance browse groups"
          activeGroupId={manageGroup}
          onActiveGroupIdChange={onManageGroupChange}
          defaultGroupId="overview"
          groups={[
            {
              id: "overview",
              label: "Overview",
              content: (
                <div className="card">
                  <p className="muted">API amounts are cents; display is USD.</p>
                  {summary ? (
                    <>
                      <div>Gross billed: {formatUsd(summary.billed_cost_gross_cents)}</div>
                      <div>Adjustments: {formatUsd(summary.billed_adjustment_cents)}</div>
                      <div>Net billed: {formatUsd(summary.billed_cost_cents)}</div>
                      <div>Revenue: {formatUsd(summary.revenue_cents)}</div>
                      {summary.provider_invoice_variance_cents != null && (
                        <div>
                          Provider invoice variance:{" "}
                          {formatUsd(summary.provider_invoice_variance_cents)}
                        </div>
                      )}
                      {summary.open_budget_period ? (
                        <p className="muted">
                          Open period: {String(summary.open_budget_period.period_start)} →{" "}
                          {String(summary.open_budget_period.period_end)} · limit{" "}
                          {formatUsd(cents(summary.open_budget_period.limit_cents))}
                        </p>
                      ) : <p className="muted">No open budget period.</p>}
                      {summary.pricing && !summary.pricing.model_cents_per_1k_configured && (
                        <p className="muted">{summary.pricing.hint}</p>
                      )}
                    </>
                  ) : <p className="panel-empty">No finance summary loaded.</p>}
                </div>
              ),
            },
            {
              id: "invoices",
              label: "Invoices",
              content: (
                <div className="card">
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
                  {!invoices.length && <p className="panel-empty">No invoices yet.</p>}
                </div>
              ),
            },
            {
              id: "provider-invoices",
              label: "Provider invoices",
              content: (
                <div className="card">
                  {providerInvoices.map((invoice) => {
                    const id = String(invoice.id);
                    return (
                      <div key={id} style={{ marginBottom: "0.65rem" }}>
                        <button type="button" onClick={() => void toggleProviderInvoice(id)}>
                          {String(invoice.provider)} · {String(invoice.external_id)} ·{" "}
                          {formatUsd(cents(invoice.total_cents))}
                        </button>
                        <div className="muted">
                          {String(invoice.status)} · allocated{" "}
                          {formatUsd(cents(invoice.allocated_cents))} · unallocated{" "}
                          {formatUsd(cents(invoice.unallocated_cents))} · variance{" "}
                          {formatUsd(cents(invoice.variance_cents))}
                        </div>
                        {expandedProviderInvoiceId === id && Boolean(expandedProviderInvoice?.error) && (
                          <p className="error">{String(expandedProviderInvoice?.error)}</p>
                        )}
                        {expandedProviderInvoiceId === id && providerAllocations.map((line, index) => (
                          <div className="muted" key={`${String(line.billed_cost_id)}-${index}`}>
                            {String(line.billed_cost_id)} · est{" "}
                            {formatUsd(cents(line.estimated_cents))} · alloc{" "}
                            {formatUsd(cents(line.allocated_cents))} · variance{" "}
                            {formatUsd(cents(line.variance_cents))}
                          </div>
                        ))}
                        {canPause && invoice.status === "open" && (
                          <button type="button" onClick={() => void voidProviderInvoice(id, String(invoice.external_id))}>
                            Void
                          </button>
                        )}
                        {status(`finance-provider-void-${id}`)}
                      </div>
                    );
                  })}
                  {!providerInvoices.length && (
                    <p className="panel-empty">No provider invoices yet.</p>
                  )}
                </div>
              ),
            },
            {
              id: "adjustments",
              label: "Adjustments",
              content: (
                <div className="card">
                  {adjustments.map((adjustment) => (
                    <div key={String(adjustment.id)} style={{ marginBottom: "0.55rem" }}>
                      <strong>{String(adjustment.kind)}</strong>
                      <div className="muted">
                        {String(adjustment.billed_cost_id)} · {formatUsd(cents(adjustment.amount_cents))} ·{" "}
                        {String(adjustment.reason)}
                      </div>
                    </div>
                  ))}
                  {!adjustments.length && <p className="panel-empty">No adjustments yet.</p>}
                </div>
              ),
            },
            {
              id: "periods",
              label: "Periods",
              content: (
                <div className="card">
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
                      {canPause && !!period.closed && (
                        <button type="button" onClick={() => void openNextPeriod(period)}>Open next period</button>
                      )}
                      {status(`finance-close-${String(period.id)}`)}
                      {status(`finance-open-next-${String(period.id)}`)}
                    </div>
                  ))}
                  {!periods.length && <p className="panel-empty">No budget periods.</p>}
                </div>
              ),
            },
          ]}
        />
      )}

      {mode === "manage" && (
        <ManageClusters
          ariaLabel="Finance manage groups"
          activeGroupId={manageGroup}
          onActiveGroupIdChange={onManageGroupChange}
          defaultGroupId="invoice"
          groups={[
            {
              id: "invoice",
              label: "Invoice",
              content: canPause ? (
                <form className="card" onSubmit={createInvoice}>
                  <div className="section-head">
                    <h2>Create invoice</h2>
                  </div>
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
              ) : scopeNotice("create invoices", "company.pause"),
            },
            {
              id: "adjustment",
              label: "Adjustment",
              content: canPause ? (
                <form className="card" onSubmit={postAdjustment}>
                  <div className="section-head">
                    <h2>Post adjustment</h2>
                  </div>
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
                  {billedCosts.length === 0 && <p className="panel-empty">No creditable lines.</p>}
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
              ) : scopeNotice("post adjustments", "company.pause"),
            },
            {
              id: "provider",
              label: "Provider",
              content: canPause ? (
                <>
                  <form className="card" onSubmit={createProviderInvoice}>
                    <div className="section-head">
                      <h2>Provider invoice</h2>
                    </div>
                    <label htmlFor="finance-provider-name">Provider</label>
                    <input id="finance-provider-name" value={providerName}
                      onChange={(event) => setProviderName(event.target.value)} required />
                    <label htmlFor="finance-provider-external-id">External id</label>
                    <input id="finance-provider-external-id" value={providerExternalId}
                      onChange={(event) => setProviderExternalId(event.target.value)} required />
                    <label htmlFor="finance-provider-total">Total cents</label>
                    <input id="finance-provider-total" type="number" min={0} step={1}
                      value={providerTotalCents}
                      onChange={(event) => setProviderTotalCents(event.target.value)} required />
                    <label htmlFor="finance-provider-issued">Issued at</label>
                    <input id="finance-provider-issued" type="datetime-local" value={providerIssuedAt}
                      onChange={(event) => setProviderIssuedAt(event.target.value)} required />
                    <label htmlFor="finance-provider-note">Note (optional)</label>
                    <input id="finance-provider-note" value={providerNote}
                      onChange={(event) => setProviderNote(event.target.value)} />
                    <div className="actions">
                      <button className="primary" type="submit">Create provider invoice</button>
                    </div>
                    {status("financeProviderInvoice")}
                  </form>
                  <form className="card" onSubmit={allocateProviderInvoice}>
                    <div className="section-head">
                      <h2>Allocate provider invoice</h2>
                    </div>
                    <label htmlFor="finance-provider-invoice-select">Provider invoice</label>
                    <select id="finance-provider-invoice-select" value={selectedProviderInvoiceId}
                      onChange={(event) => setSelectedProviderInvoiceId(event.target.value)}
                      disabled={openProviderInvoices.length === 0} required>
                      {openProviderInvoices.map((item) => (
                        <option key={String(item.id)} value={String(item.id)}>
                          {String(item.provider)} · {String(item.external_id)} · unallocated{" "}
                          {formatUsd(cents(item.unallocated_cents))}
                        </option>
                      ))}
                    </select>
                    {openProviderInvoices.length === 0 && (
                      <p className="panel-empty">No open provider invoices.</p>
                    )}
                    <label htmlFor="finance-provider-billed-cost">Billed cost</label>
                    <select id="finance-provider-billed-cost" value={providerAllocateBilledCostId}
                      onChange={(event) => setProviderAllocateBilledCostId(event.target.value)}
                      disabled={billedCosts.length === 0} required>
                      {billedCosts.map((item) => (
                        <option key={item.id} value={item.id}>
                          {item.provider} · {formatUsd(item.amount_cents)} · {item.id}
                        </option>
                      ))}
                    </select>
                    {billedCosts.length === 0 && (
                      <p className="panel-empty">No billed costs.</p>
                    )}
                    <label htmlFor="finance-provider-allocated">Allocated cents</label>
                    <input id="finance-provider-allocated" type="number" min={0} step={1}
                      value={providerAllocatedCents}
                      onChange={(event) => setProviderAllocatedCents(event.target.value)} required />
                    <div className="actions">
                      <button className="primary" type="submit"
                        disabled={openProviderInvoices.length === 0 || billedCosts.length === 0}>
                        Allocate
                      </button>
                    </div>
                    {status("financeProviderAllocate")}
                  </form>
                  <form className="card" onSubmit={(event) => void voidProviderInvoiceFromManage(event)}>
                    <div className="section-head">
                      <h2>Void provider invoice</h2>
                    </div>
                    <label htmlFor="finance-provider-void-select">Provider invoice</label>
                    <select id="finance-provider-void-select" value={voidProviderInvoiceId}
                      onChange={(event) => setVoidProviderInvoiceId(event.target.value)}
                      disabled={openProviderInvoices.length === 0} required>
                      {openProviderInvoices.map((item) => (
                        <option key={String(item.id)} value={String(item.id)}>
                          {String(item.provider)} · {String(item.external_id)}
                        </option>
                      ))}
                    </select>
                    {openProviderInvoices.length === 0 && (
                      <p className="panel-empty">No open provider invoices.</p>
                    )}
                    <div className="actions">
                      <button type="submit" disabled={openProviderInvoices.length === 0}>
                        Void
                      </button>
                    </div>
                    {voidProviderInvoiceId && status(`finance-provider-void-${voidProviderInvoiceId}`)}
                  </form>
                </>
              ) : scopeNotice("manage provider invoices", "company.pause"),
            },
            {
              id: "period",
              label: "Period",
              content: canPause ? (
                <form className="card" onSubmit={setBudgetPeriod}>
                  <div className="section-head">
                    <h2>Set budget period</h2>
                  </div>
                  <label htmlFor="finance-period-start">Start</label>
                  <input id="finance-period-start" type="datetime-local"
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
              ) : scopeNotice("set budget periods", "company.pause"),
            },
          ]}
        />
      )}
    </section>
  );
}
