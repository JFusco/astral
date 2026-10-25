"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { z } from "zod";
import { useDashboard } from "./provider";
import { api, errorMessage } from "@/lib/api";
import { ui } from "@/lib/ui";
const pages = [
  ["/", "Overview", "⌂"],
  ["/health", "App health", "♡"],
  ["/accounting", "Accounting", "▤"],
  ["/learning", "Learning", "✧"],
];
const rail =
  "grid size-10 shrink-0 cursor-pointer place-items-center rounded-lg border border-transparent text-xl text-muted no-underline transition-colors hover:bg-surface-raised hover:text-ink focus-visible:outline-2 focus-visible:outline-cyan aria-[current=page]:border-accent/20 aria-[current=page]:bg-accent/10 aria-[current=page]:text-accent";
function RailLink({
  href,
  title,
  icon,
}: {
  href: string;
  title: string;
  icon: string;
}) {
  const path = usePathname();
  return (
    <Link
      href={href}
      className={rail}
      aria-label={title}
      title={title}
      aria-current={path === href ? "page" : undefined}
    >
      {icon}
    </Link>
  );
}
export function Navigation() {
  const path = usePathname();
  return (
    <>
      <a
        className="sr-only z-50 rounded bg-surface p-3 text-cyan focus:not-sr-only focus:fixed focus:left-20 focus:top-2"
        href="#main"
      >
        Skip to content
      </a>
      <aside
        className="fixed inset-y-0 left-0 z-40 flex w-rail-compact flex-col items-center gap-3 overflow-y-auto border-r border-line bg-app py-4 md:w-rail"
        aria-label="Workspace navigation"
      >
        <Link
          href="/"
          className="relative mb-4 grid size-10 shrink-0 place-items-center rounded-full border border-cyan/25 font-display text-3xl text-ink"
          aria-label="Astral overview"
        >
          A
          <span className="absolute top-0 right-0 size-1 rounded-full bg-accent" />
        </Link>
        <RailLink href="/" title="Overview" icon="⌂" />
        {[
          ["strategies", "Strategy allocations", "⌁"],
          ["intelligence", "Intelligence sources", "◉"],
          ["system", "System telemetry", "⌘"],
        ].map(([id, title, icon]) => (
          <RailLink key={id} href={`/?view=${id}`} title={title} icon={icon} />
        ))}
        {pages.slice(1).map(([href, title, icon]) => (
          <RailLink key={href} href={href} title={title} icon={icon} />
        ))}
        <div className="flex-1" />
        <RailLink href="/?view=settings" title="Display settings" icon="⚙" />
        <div
          className="grid size-8 shrink-0 place-items-center rounded-full border border-line bg-surface-raised text-xxs text-muted"
          title="Private workspace"
        >
          JF
        </div>
      </aside>
      <div className="flex h-8 shrink-0 items-center gap-4 font-display text-lg font-semibold tracking-widest">
        ASTRAL
        <span className="hidden border-l border-line pl-4 font-sans text-xxs text-muted 2xl:block">
          TRADING COMMAND
        </span>
      </div>
      <nav
        className="order-3 flex w-full flex-wrap gap-1 lg:order-none lg:w-auto lg:flex-1"
        aria-label="Main navigation"
      >
        {pages.map(([href, title]) => (
          <Link
            key={href}
            href={href}
            aria-current={path === href ? "page" : undefined}
            className="rounded-lg border border-transparent px-1 py-2 text-caption font-medium text-muted hover:bg-surface-raised hover:text-ink focus-visible:outline-2 focus-visible:outline-cyan aria-[current=page]:border-accent/20 aria-[current=page]:bg-accent/5 aria-[current=page]:text-accent sm:px-2 lg:px-3"
          >
            {title}
          </Link>
        ))}
      </nav>
    </>
  );
}
export function ConnectionControls() {
  const { snapshot, connection } = useDashboard();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const state = snapshot.state;
  async function halt() {
    if (pending || !state || !snapshot.connected) return;
    setPending(true);
    setError("");
    try {
      await api("/api/halt", z.object({ halted: z.boolean() }), {
        body: { halted: !state.halted },
      });
      await connection.refresh();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setPending(false);
    }
  }
  return (
    <div className="ml-auto flex flex-wrap items-center gap-3 text-caption text-muted">
      <span
        role="status"
        className={
          snapshot.connected ? "text-status-healthy" : "text-status-unknown"
        }
      >
        {snapshot.connected
          ? state?.mode === "simulator"
            ? "SIMULATOR / SERVER STREAM"
            : state?.connected
              ? "ALPACA / PAPER STREAM"
              : "ALPACA / NOT CONNECTED"
          : state
            ? "BACKEND DISCONNECTED"
            : snapshot.error
              ? "SERVICE UNAVAILABLE"
              : "CONNECTING TO SERVICE"}
      </span>
      <span className="hidden font-display xl:block">
        {snapshot.now
          ? new Date(snapshot.now).toISOString().slice(11, 19) + " UTC"
          : "— UTC"}
      </span>
      <button
        onClick={halt}
        disabled={!snapshot.connected || pending}
        className={`${ui.button} text-status-degraded`}
      >
        {pending
          ? "Saving…"
          : state?.halted
            ? "◇ Resume entries"
            : "◈ Halt entries"}
      </button>
      {error ? (
        <span role="alert" className="w-full max-w-lg text-status-down">
          {error}
        </span>
      ) : null}
    </div>
  );
}
