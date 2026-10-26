"use client";
import { useState, useTransition, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { ui } from "@/lib/ui";
import { Heading } from "../ui/heading";
import { LoadingPanel } from "../motion";

type Shown = { children: ReactNode; asOf: string; mode?: string };
export function ReportFrame({
  title,
  subtitle,
  asOf,
  mode,
  error,
  empty,
  children,
}: {
  title: string;
  subtitle: string;
  asOf?: string;
  mode?: string;
  error: string | null;
  empty: string;
  children?: ReactNode;
}) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  // Previous-props pattern: keep the last report that carried data, so a failed refresh retains it.
  const [retained, setRetained] = useState<Shown | null>(
    asOf ? { children, asOf, mode } : null,
  );
  if (
    asOf &&
    (retained?.asOf !== asOf ||
      retained.mode !== mode ||
      retained.children !== children)
  )
    setRetained({ children, asOf, mode });
  const shown = asOf ? { children, asOf, mode } : error ? retained : null;
  // A refresh in flight clears the previous error, as the browser read did.
  const failure = pending ? null : error;
  const refresh = () => startTransition(() => router.refresh());
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
        className={`${ui.notice} ${failure ? "unavailable" : ""}`}
      >
        {failure
          ? `${failure}. ${shown ? "Displayed figures are retained from the previous response." : "No saved figures are assumed."}`
          : shown
            ? `Saved ${shown.asOf} · ${shown.mode} records. Refresh reads the saved snapshot; it does not start an evaluation.`
            : "Reading the latest saved report. Refresh does not start an evaluation."}
      </div>
      {pending && !shown ? (
        <LoadingPanel
          label={`Reading saved ${title.toLowerCase()} report`}
          cards
        />
      ) : null}
      {shown ? (
        shown.children
      ) : !pending ? (
        <p className={ui.panelBody}>{empty}</p>
      ) : null}
      <footer className={ui.footer}>
        <span>{title.toUpperCase()} / SAVED LOCAL REPORT</span>
        <span>
          {shown ? `Report cutoff ${shown.asOf}` : "Waiting for a saved report"}
        </span>
      </footer>
    </>
  );
}
