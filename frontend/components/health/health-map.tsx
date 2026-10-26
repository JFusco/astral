"use client";
import { useEffect, useRef, useState } from "react";
import { statusClass, statusDot, topicNames } from "@/lib/assets";
import { ui } from "@/lib/ui";
import { Panel } from "../ui/panel";
import { useMotionSettings } from "../motion";
import { useHealthView } from "./health-view-state";
export function HealthMap() {
  const {
    state,
    live,
    nodes,
    scoped,
    selected,
    setSelected,
    issuesOnly,
    setIssuesOnly,
    topic,
  } = useHealthView();
  const { reduced } = useMotionSettings();
  const [rendererStatus, setRendererStatus] = useState("Loading 3D view…");
  const canvas = useRef<HTMLCanvasElement>(null);
  const galaxy = useRef<{ reset: () => void; dispose: () => void } | null>(
    null,
  );
  const pulse = useRef(0);
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
    // setSelected is a stable useState setter from context, so the galaxy is still created once.
  }, [setSelected]);
  return (
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
        Slow galaxy rotation, shooting stars and circling neurons are ambient
        motion. Heartbeat and check waves follow completed assessments.
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
  );
}
