"use client";
import { useEffect, useRef, useState } from "react";
import { useDashboard } from "./provider";
import { useMotionSettings, LoadingPanel } from "./motion";
import { Card, Heading, Panel, Empty, utc } from "./primitives";
import { healthIsLive } from "@/lib/connection";
import { statusClass, statusDot, topicNames } from "@/lib/assets";
import type { HealthNode } from "@/lib/contracts";
import { ui } from "@/lib/ui";

function Heartbeat({
  sequence,
  live,
  reduced,
}: {
  sequence: number;
  live: boolean;
  reduced: boolean;
}) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const lastPulse = useRef(0);
  useEffect(() => {
    if (live) lastPulse.current = performance.now();
  }, [sequence, live]);
  useEffect(() => {
    const el = canvas.current,
      ctx = el?.getContext("2d");
    if (!el || !ctx) return;
    let frame = 0;
    let disposed = false;
    function draw(now: number) {
      if (disposed) return;
      const { width, height } = el!.getBoundingClientRect();
      const d = Math.min(devicePixelRatio || 1, 2);
      if (
        el!.width !== Math.round(width * d) ||
        el!.height !== Math.round(height * d)
      ) {
        el!.width = Math.round(width * d);
        el!.height = Math.round(height * d);
      }
      ctx!.setTransform(d, 0, 0, d, 0, 0);
      ctx!.clearRect(0, 0, width, height);
      ctx!.strokeStyle = getComputedStyle(el!).getPropertyValue(
        live ? "--color-status-checking" : "--color-status-unknown",
      );
      ctx!.lineWidth = 1.5;
      ctx!.beginPath();
      const elapsed = now - lastPulse.current;
      for (let x = 0; x < width; x++) {
        const center = live && !reduced && elapsed < 2500 ? elapsed / 2200 : 2,
          offset = x / width - center;
        let y = height * 0.55;
        if (Math.abs(offset) < 0.09)
          y +=
            Math.exp((-offset * offset) / 0.0006) *
            Math.sin(offset * 120) *
            height *
            0.42;
        if (x) ctx!.lineTo(x, y);
        else ctx!.moveTo(x, y);
      }
      ctx!.stroke();
      frame = requestAnimationFrame(draw);
    }
    frame = requestAnimationFrame(draw);
    return () => {
      disposed = true;
      cancelAnimationFrame(frame);
    };
  }, [live, reduced]);
  return (
    <canvas
      ref={canvas}
      className="my-2 h-10 w-full"
      aria-label={
        live
          ? "Heartbeat follows completed health checks"
          : "No current health heartbeat"
      }
    />
  );
}
export function HealthPage() {
  const { snapshot } = useDashboard();
  const { reduced } = useMotionSettings();
  const state = snapshot.health,
    live = healthIsLive(snapshot);
  const [selected, setSelected] = useState("application");
  const [issuesOnly, setIssuesOnly] = useState(false);
  const [topic, setTopic] = useState("all");
  const [rendererStatus, setRendererStatus] = useState("Loading 3D view…");
  const canvas = useRef<HTMLCanvasElement>(null);
  const galaxy = useRef<{ reset: () => void; dispose: () => void } | null>(
    null,
  );
  const pulse = useRef(0);
  const nodes: HealthNode[] = (state?.nodes ?? []).map((node) =>
    live
      ? node
      : {
          ...node,
          status: "unknown",
          detail:
            "Health engine unavailable or heartbeat missed. Retained observation only.",
        },
  );
  const view = { topic, issuesOnly, selected };
  const current = useRef({ nodes, view, live, reduced });
  useEffect(() => {
    current.current = { nodes, view, live, reduced };
  });
  useEffect(() => {
    if (live) pulse.current = performance.now();
  }, [state?.sequence, live]);
  useEffect(() => {
    let disposed = false;
    void import("@/graphics/health-galaxy")
      .then(({ createHealthGalaxy }) => {
        if (disposed || !canvas.current) return;
        const theme = getComputedStyle(canvas.current);
        const token = (name: string) =>
          theme.getPropertyValue("--color-" + name).trim();
        const topics = Object.fromEntries(
          Object.entries(topicNames).map(([id, name]) => [
            id,
            { name, color: token("topic-" + id) },
          ]),
        );
        const colors = Object.fromEntries(
          Object.keys(statusClass).map((name) => [
            name,
            token("status-" + name),
          ]),
        );
        try {
          galaxy.current = createHealthGalaxy(canvas.current, {
            topics,
            colors,
            getNodes: () => current.current.nodes,
            getView: () => current.current.view,
            isLive: () => current.current.live,
            getPulse: () => pulse.current,
            isReduced: () => current.current.reduced,
            onSelect: (id: string) => setSelected(id),
            onRendererStatus: setRendererStatus,
          });
          setRendererStatus("");
        } catch {
          setRendererStatus("3D view unavailable · use Systems by Type");
        }
      })
      .catch(() => {
        if (!disposed)
          setRendererStatus("3D view unavailable · use Systems by Type");
      });
    return () => {
      disposed = true;
      galaxy.current?.dispose();
      galaxy.current = null;
    };
  }, []);
  const scoped = nodes.filter(
    (node) => topic === "all" || node.group === topic,
  );
  const visible = scoped.filter(
    (node) =>
      !issuesOnly || ["degraded", "down", "unknown"].includes(node.status),
  );
  const inspected = nodes.find((node) => node.id === selected);
  const count = (statuses: string[]) =>
    state
      ? scoped.filter((node) => statuses.includes(node.status)).length
      : "—";
  return (
    <>
      <Heading
        title="App health"
        subtitle="Live checks for the application, data, workers and connected services."
        action={
          <p className="text-caption text-muted">
            Assessments every 10 seconds
          </p>
        }
      />
      {!state && snapshot.healthLoading ? (
        <LoadingPanel label="Connecting to health engine" cards />
      ) : (
        <section className={ui.summaryGrid} aria-label="Health summary">
          <Card
            label="HEALTHY"
            value={count(["healthy"])}
            tone="text-status-healthy"
            note="Recent checks passed"
          />
          <Card
            label="NEEDS ATTENTION"
            value={count(["degraded", "down", "unknown"])}
            tone="text-status-degraded"
            note="Degraded, down or unknown"
          />
          <Card
            label="INACTIVE"
            value={count(["inactive"])}
            tone="text-status-inactive"
            note="Explicitly disabled or deferred"
          />
          <div className={ui.card}>
            <span className={ui.label}>ENGINE HEARTBEAT</span>
            <Heartbeat
              sequence={state?.sequence ?? 0}
              live={live}
              reduced={reduced}
            />
            <span className={ui.note}>
              {state
                ? `${live ? "Completed" : "Last recorded"} ${utc(state.checked_at)}`
                : "Waiting for a real check"}
            </span>
          </div>
        </section>
      )}
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <Panel
          className="xl:col-span-2"
          title={topic === "all" ? "Service map" : topicNames[topic]}
          subtitle={`${scoped.length} dependencies · ${live ? "Health engine live" : "Health engine unavailable"}`}
          action={
            <div className="flex gap-2">
              <button
                className={ui.button}
                aria-pressed={!issuesOnly}
                onClick={() => setIssuesOnly(false)}
              >
                All nodes
              </button>
              <button
                className={ui.button}
                aria-pressed={issuesOnly}
                onClick={() => setIssuesOnly(true)}
              >
                Needs attention
              </button>
            </div>
          }
        >
          <div className="relative h-galaxy touch-none bg-app">
            <canvas
              className="size-full cursor-grab active:cursor-grabbing"
              ref={canvas}
              aria-label="Interactive three-dimensional dependency map. Use the dependency buttons alongside it for keyboard access."
            />
            <span className="pointer-events-none absolute top-5 left-5 text-xxs text-muted">
              {live
                ? `CHECK ${String(state?.sequence).padStart(4, "0")} / ${state?.duration_ms} MS`
                : "HEARTBEAT NOT CURRENT"}
            </span>
            {rendererStatus ? (
              <p
                role="status"
                className="pointer-events-none absolute bottom-10 left-5 text-caption text-muted"
              >
                {rendererStatus}
              </p>
            ) : null}
            <span className="pointer-events-none absolute right-5 bottom-4 text-xxs text-faint">
              DRAG TO ROTATE · SCROLL TO ZOOM
            </span>
          </div>
          <p className="px-5 py-3 text-caption text-muted">
            Slow galaxy rotation, shooting stars and circling neurons are
            ambient motion. Heartbeat and check waves follow completed
            assessments.
          </p>
          <div className="flex flex-wrap items-center gap-4 border-t border-line p-5 text-xxs text-muted">
            {Object.keys(statusClass).map((status) => (
              <span key={status} className="flex items-center gap-2">
                <i
                  className={`size-1.5 rounded-full ${statusDot[status as keyof typeof statusDot]}`}
                />
                {status}
              </span>
            ))}
            <button
              className="ml-auto text-cyan"
              onClick={() => galaxy.current?.reset()}
            >
              Reset orbit ↻
            </button>
          </div>
        </Panel>
        <Panel
          title="System details"
          subtitle="Select a system to see its last check"
        >
          <div className="min-h-52 space-y-3 border-b border-line p-5">
            {inspected ? (
              <>
                <span
                  className={`text-caption uppercase ${statusClass[inspected.status]}`}
                >
                  {inspected.status}
                </span>
                <h3 className="font-display text-xl">{inspected.name}</h3>
                <p className="text-caption text-muted">{inspected.detail}</p>
                <p className="text-xxs text-faint">
                  {inspected.checked_at ?? "No retained check"}
                </p>
              </>
            ) : (
              <Empty>
                Waiting for the health engine. No healthy state is assumed.
              </Empty>
            )}
          </div>
          <div className="flex items-center justify-between gap-3 px-5 pt-4 text-xxs text-muted">
            <span>SYSTEMS BY TYPE · {visible.length}</span>
            <label>
              Topic{" "}
              <select
                className="max-w-36 rounded border border-line bg-app p-2"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
              >
                <option value="all">All topics</option>
                {Object.entries(topicNames).map(([id, name]) => (
                  <option key={id} value={id}>
                    {name}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div
            className="max-h-96 overflow-y-auto p-3"
            aria-label="Dependencies"
          >
            {Object.entries(topicNames).map(([group, name]) => {
              const members = visible.filter((node) => node.group === group);
              return members.length ? (
                <details
                  key={group}
                  className="my-2 rounded-lg border border-line bg-app"
                  open={
                    group === "core" ||
                    members.some((node) => node.id === selected) ||
                    undefined
                  }
                >
                  <summary className="cursor-pointer px-3 py-3 text-caption text-ink">
                    {name} · {members.length}
                  </summary>
                  {members.map((node) => (
                    <button
                      key={node.id}
                      aria-pressed={selected === node.id}
                      onClick={() => setSelected(node.id)}
                      className={`flex w-full items-center justify-between gap-3 px-3 py-3 text-left text-caption hover:bg-surface-raised ${selected === node.id ? "bg-surface-raised" : ""}`}
                    >
                      <span>{node.name}</span>
                      <span className={statusClass[node.status]}>
                        {node.status}
                      </span>
                    </button>
                  ))}
                </details>
              ) : null;
            })}
          </div>
        </Panel>
      </div>
      <div className={`${ui.columns} mt-6`}>
        <Panel title="Recent status changes">
          <div className={ui.panelBody}>
            {state?.changes.length ? (
              state.changes.slice(0, 4).map((change, i) => (
                <div
                  key={i}
                  className="flex justify-between gap-3 text-caption"
                >
                  <span>
                    {nodes.find((n) => n.id === change.payload.id)?.name ??
                      change.payload.id}
                    : {change.payload.previous ?? "unknown"} →{" "}
                    {change.payload.status ?? "unknown"}
                  </span>
                  <span>{utc(change.at)}</span>
                </div>
              ))
            ) : (
              <p>No health checks received.</p>
            )}
          </div>
        </Panel>
        <Panel title="Check coverage">
          <div className={ui.panelBody}>
            <p>
              Application · broker readback · quotes · workers · public feeds ·
              model state · provider reports
            </p>
            <p>
              Checks every 10s. Provider reports every 120s. A missed heartbeat
              becomes unknown. No test trades, paid model calls, automatic
              upgrades or risk changes.
            </p>
            <p>
              Published provider status does not prove account access, payment
              processing or model availability.
            </p>
          </div>
        </Panel>
      </div>
      <footer className={ui.footer}>
        <span>Health checks do not enable trading</span>
        <span>
          {state
            ? `Last checked ${state.checked_at}`
            : "Waiting for health data"}
        </span>
      </footer>
    </>
  );
}
