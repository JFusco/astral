"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import type { z } from "zod";
import {
  accountingSchema,
  learningSchema,
  type Accounting,
  type Learning,
} from "@/lib/contracts";
import { api, errorMessage } from "@/lib/api";
import { ui } from "@/lib/ui";
import { Heading, Card, Panel, Counts, label } from "./primitives";
import { LoadingPanel, Reveal } from "./motion";

function useReport<T>(path: string, schema: z.ZodType<T>) {
  const [data, setData] = useState<T | null>(null);
  const [pending, setPending] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const active = useRef<AbortController | null>(null);
  const load = useCallback(
    async (controller: AbortController) => {
      try {
        const report = await api(path, schema, {
          signal: controller.signal,
          timeout: 5000,
        });
        if (!controller.signal.aborted) setData(report);
      } catch (e) {
        if (!controller.signal.aborted) setError(errorMessage(e));
      } finally {
        if (!controller.signal.aborted) {
          active.current = null;
          setPending(false);
        }
      }
    },
    [path, schema],
  );
  const refresh = () => {
    if (active.current) return;
    const controller = new AbortController();
    active.current = controller;
    setPending(true);
    setError(null);
    void load(controller);
  };
  // load updates React state only after the awaited request settles; cleanup aborts late responses.
  useEffect(() => {
    const controller = new AbortController();
    active.current = controller;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load(controller);
    return () => {
      active.current?.abort();
      active.current = null;
    };
  }, [load]);
  return { data, pending, error, refresh };
}
const amounts = (value: Record<string, string | number> | null) =>
  value && Object.keys(value).length
    ? Object.entries(value)
        .map(([currency, value]) => `${currency} ${value}`)
        .join(" · ")
    : "Unknown";
function ReportFrame({
  title,
  subtitle,
  pending,
  error,
  asOf,
  mode,
  refresh,
  children,
}: {
  title: string;
  subtitle: string;
  pending: boolean;
  error: string | null;
  asOf?: string;
  mode?: string;
  refresh: () => void;
  children: React.ReactNode;
}) {
  return (
    <>
      <Heading
        title={title}
        subtitle={subtitle}
        action={
          <button className={ui.button} onClick={refresh} disabled={pending}>
            {pending ? "Reading report…" : "Refresh report"}
          </button>
        }
      />
      <div
        role="status"
        aria-busy={pending}
        className={`${ui.notice} ${error ? "unavailable" : ""}`}
      >
        {error
          ? `${error}. ${asOf ? "Displayed figures are retained from the previous response." : "No saved figures are assumed."}`
          : asOf
            ? `Saved ${asOf} · ${mode} records. Refresh reads the saved snapshot; it does not start an evaluation.`
            : "Reading the latest saved report. Refresh does not start an evaluation."}
      </div>
      {pending && !asOf ? (
        <LoadingPanel
          label={`Reading saved ${title.toLowerCase()} report`}
          cards
        />
      ) : null}
      {children}
      <footer className={ui.footer}>
        <span>{title.toUpperCase()} / SAVED LOCAL REPORT</span>
        <span>
          {asOf ? `Report cutoff ${asOf}` : "Waiting for a saved report"}
        </span>
      </footer>
    </>
  );
}
function AccountingContent({ r }: { r: Accounting }) {
  const c = r.operating_costs;
  return (
    <Reveal>
      <section className={ui.summaryGrid} aria-label="Accounting summary">
        <Card
          label="PERSONAL MONTHLY BUDGET"
          value={amounts(c.monthly_astral_personal_budget_by_currency)}
          note="Known subscription inputs; coverage may be incomplete"
          tone="text-accent"
        />
        <Card
          label="RECORDED ACTUAL CHARGES"
          value={amounts(c.actual_total_by_currency)}
          note="Confirmed records; budgets are not invoices"
        />
        <Card
          label="NET TRADING P&L"
          value={
            r.money_results.realized_net_pnl_usd === null
              ? "Unknown"
              : `USD ${r.money_results.realized_net_pnl_usd}`
          }
          note="Requires reconciled fees, basis and cash flows"
        />
        <Card
          label="CUSTODY RECONCILIATION"
          value={
            r.custody.status === "needs_review"
              ? "Needs review"
              : "Quantities matched"
          }
          note={`${r.fill_rows} retained fill rows · fee coverage unverified`}
          tone={r.custody.status === "needs_review" ? "text-status-down" : ""}
        />
      </section>
      <div className={ui.columns}>
        <Panel title="Unresolved records">
          <div className={`${ui.panelBody} overflow-x-auto`}>
            {Object.keys(r.issues).length ? (
              <Counts values={r.issues} />
            ) : (
              <p>
                No quantity issues in this saved snapshot. Net results still
                require complete evidence.
              </p>
            )}
            {r.custody.differences.length ? (
              <table className={ui.table}>
                <thead>
                  <tr>
                    {[
                      "ASSET",
                      "RECORDED NET QTY",
                      "BROKER QTY",
                      "UNEXPLAINED QTY",
                    ].map((v) => (
                      <th key={v}>{v}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {r.custody.differences.map((d) => (
                    <tr key={d.symbol}>
                      <td>{d.symbol}</td>
                      <td>{d.recorded_net_quantity}</td>
                      <td>{d.broker_quantity}</td>
                      <td>{d.unexplained_quantity}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p>No comparable custody differences recorded.</p>
            )}
          </div>
        </Panel>
        <Panel title="Operating costs">
          <div className={ui.panelBody}>
            <p>
              Personal ASTRAL monthly budget:{" "}
              {amounts(c.monthly_astral_personal_budget_by_currency)}
            </p>
            <p>
              Subscription coverage:{" "}
              {c.monthly_budget_complete
                ? "User-asserted complete"
                : "Incomplete / unverified plans remain"}
            </p>
            <p>
              Recorded confirmed charge subtotal:{" "}
              {amounts(c.recorded_confirmed_charges_by_currency)}
            </p>
            <p>Estimated charges: {amounts(c.estimated_charges_by_currency)}</p>
            <p>
              Budgets, bills and included allocations are separate. Missing
              records do not mean zero spending. Employer-funded subscriptions
              can have a $0 personal budget.
            </p>
          </div>
        </Panel>
      </div>
      <Panel
        title="Gross matches by book"
        subtitle="Before fees · retained source records"
      >
        <div className={`${ui.panelBody} overflow-x-auto`}>
          <p>
            {label(r.gross_fifo_diagnostics.status)}.{" "}
            {r.gross_fifo_diagnostics.basis}
          </p>
          {r.gross_fifo_diagnostics.by_book.length ? (
            <table className={ui.table}>
              <thead>
                <tr>
                  <th>ASSET</th>
                  <th>BOOK</th>
                  <th>GROSS REALIZED USD</th>
                </tr>
              </thead>
              <tbody>
                {r.gross_fifo_diagnostics.by_book.map((b, i) => (
                  <tr key={i}>
                    <td>{b.symbol}</td>
                    <td>{b.book}</td>
                    <td>{b.gross_realized_usd}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p>No gross lot matches recorded.</p>
          )}
        </div>
      </Panel>
      <div className="mt-6 space-y-4 border-t border-line py-6 text-body text-muted">
        <h2 className={ui.sectionTitle}>Evaluation boundaries</h2>
        <p>{r.money_results.reason}</p>
        <p>
          Source CSVs and gross lot matches are preparation records, not
          certified tax lots or a filing. Subscription funding notes do not
          create payment or reimbursement transactions.
        </p>
        <p>
          This page displays an on-demand saved snapshot. Refresh does not run
          an evaluation, change a ledger, call a model or enable trading.
        </p>
      </div>
    </Reveal>
  );
}
function LearningContent({ r }: { r: Learning }) {
  const data = r.data_and_outcomes,
    model = r.model_research;
  return (
    <Reveal>
      <section className={ui.summaryGrid} aria-label="Learning summary">
        <Card
          label="OUTCOME READINESS"
          value={label(data.status)}
          note="Reconciled financial labels are required"
          tone="text-status-unknown"
        />
        <Card
          label="RESOLVED NET P&L LABELS"
          value={data.resolved_net_pnl_labels}
          note="Approvals and fills are not profit labels"
        />
        <Card
          label="MODEL CONTRACTS CHECKED"
          value={
            (model.contract_checks.contract_passed ?? 0) +
            (model.contract_checks.contract_failed ?? 0)
          }
          note="Existing receipts only; no new model calls"
        />
        <Card
          label="MODEL USEFULNESS"
          value={label(model.usefulness.status)}
          note="Requires comparable, reconciled outcome pairs"
          tone="text-status-unknown"
        />
      </section>
      <div className={ui.columns}>
        <Panel title="Data and outcomes">
          <div className={ui.panelBody}>
            <p>{data.reason}</p>
            <Counts values={data.decision_categories} />
            <p>
              Training rows: {data.training_rows}. Research packets inspected:{" "}
              {data.research_packets_inspected}.
            </p>
          </div>
        </Panel>
        <Panel title="Model research quality">
          <div className={ui.panelBody}>
            <h3 className={ui.sectionTitle}>Receipt categories</h3>
            <Counts values={model.receipt_categories} />
            <h3 className={ui.sectionTitle}>Contract and timing checks</h3>
            <Counts values={model.contract_checks} />
            <p>{model.usefulness.reason}</p>
          </div>
        </Panel>
        <Panel title="Evidence inventory" subtitle="Counts at the saved cutoff">
          <div className={`${ui.panelBody} overflow-x-auto`}>
            <table className={ui.table}>
              <thead>
                <tr>
                  {[
                    "SOURCE",
                    "AVAILABLE",
                    "PROTECTED",
                    "AFTER CUTOFF",
                    "INVALID TIME",
                  ].map((v) => (
                    <th key={v}>{v}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {Object.entries(r.inventory).map(([name, v]) => (
                  <tr key={name}>
                    <td>{label(name)}</td>
                    {(
                      [
                        "available",
                        "protected_window",
                        "after_cutoff",
                        "invalid_timestamp",
                      ] as const
                    ).map((key) => (
                      <td key={key}>{v[key] ?? "—"}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
        <Panel title="Recorded usage and costs">
          <div className={ui.panelBody}>
            <Counts values={model.recorded_usage} />
            <p>
              Attributable model cost:{" "}
              {model.costs.total_actual_usd === null
                ? "unknown"
                : `${model.costs.total_actual_usd} USD`}
              .
            </p>
            <p>
              Unknown-cost receipts: {model.costs.unknown_cost_receipts}.{" "}
              {model.costs.scope}.
            </p>
            <p>
              Platform subscriptions and employer reimbursements belong to
              Accounting.
            </p>
          </div>
        </Panel>
      </div>
      <Panel title="Protected evidence" subtitle="Reserved forward windows">
        <div className={ui.panelBody}>
          {r.protected_windows.map((w) => (
            <div
              key={w.id}
              className="space-y-2 border-b border-line pb-4 last:border-0"
            >
              <h3 className={ui.sectionTitle}>{w.id}</h3>
              <p>
                {w.starts_at} → {w.ends_at}
              </p>
              <p>{w.policy}</p>
            </div>
          ))}
        </div>
      </Panel>
      <div className="mt-6 space-y-4 border-t border-line py-6 text-body text-muted">
        <h2 className={ui.sectionTitle}>Evaluation boundaries</h2>
        <p>
          This saved offline audit cannot train, promote a strategy, change risk
          limits, call a model or place a trade.
        </p>
        <p>
          Protected outcome bodies and raw model prompts are not exposed here. A
          contract pass checks consistency with supplied evidence; it does not
          establish narrative truth or predictive skill.
        </p>
        {Object.keys(r.issues).length ? <Counts values={r.issues} /> : null}
      </div>
    </Reveal>
  );
}
export function AccountingReport() {
  const report = useReport("/api/accounting/report", accountingSchema);
  return (
    <ReportFrame
      title="Accounting"
      subtitle="Recorded costs, gross trade records and unresolved money evidence."
      {...report}
      refresh={() => void report.refresh()}
      asOf={report.data?.as_of}
      mode={report.data?.source_mode}
    >
      {report.data ? (
        <AccountingContent r={report.data} />
      ) : !report.pending ? (
        <p className={ui.panelBody}>
          No verified accounting report is available. Net results remain
          unknown.
        </p>
      ) : null}
    </ReportFrame>
  );
}
export function LearningReport() {
  const report = useReport("/api/learning/report", learningSchema);
  return (
    <ReportFrame
      title="Learning"
      subtitle="Offline evidence readiness and checks of recorded model research."
      {...report}
      refresh={() => void report.refresh()}
      asOf={report.data?.as_of}
      mode={report.data?.source_mode}
    >
      {report.data ? (
        <LearningContent r={report.data} />
      ) : !report.pending ? (
        <p className={ui.panelBody}>
          No verified learning report is available. Outcome readiness remains
          unknown.
        </p>
      ) : null}
    </ReportFrame>
  );
}
