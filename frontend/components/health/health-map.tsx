"use client";
import { assets, statusClass, statusDot, topicNames } from "@/lib/assets";
import { ui } from "@/lib/ui";
import { OrbitalUniverse, type OrbitItem } from "../orbital-universe";
import { useHealthView } from "./health-view-state";
import { attention } from "./health-view";
export function HealthMap() {
  const { live, scoped, visible, selected, setSelected, issuesOnly, setIssuesOnly, topic, setTopic } = useHealthView();
  const topicLabels: Record<string, string> = { core: "Application", execution: "Broker", market: "Markets", workers: "Engines", sources: "Intelligence", providers: "Providers", models: "Models", local: "Runtime" };
  const entries = topic === "all" ? Object.entries(topicNames).flatMap(([id, name]) => {
    const members = visible.filter((node) => node.group === id);
    return members.length ? [{ id, name, label: topicLabels[id], detail: `${members.length} ${members.length === 1 ? "system" : "systems"}${members.some((n) => attention.includes(n.status)) ? " · needs attention" : ""}`, tone: "text-cyan" }] : [];
  }) : visible.map((node) => ({ ...node, label: node.name, detail: node.status, tone: statusClass[node.status] }));
  const items: OrbitItem[] = entries.map((entry, i) => ({
    ...assets[i % assets.length], symbol: entry.id, name: entry.name,
    label: entry.label, detail: entry.detail, tone: entry.tone,
    phase: (i / Math.max(entries.length, 1)) * Math.PI * 2,
  }));
  return (
    <OrbitalUniverse title="Health universe" subtitle={`${scoped.length} dependencies · ${live ? "Health engine live" : "Health engine unavailable"}`}
      items={items} selected={topic === "all" ? "" : selected}
      onSelect={topic === "all" ? setTopic : setSelected} core="APPLICATION CORE" observation={live ? "OBSERVING" : "HEARTBEAT NOT CURRENT"}>
      <div className="flex flex-wrap items-center gap-3 border-t border-line p-5">
        <button className={ui.button} aria-pressed={!issuesOnly} onClick={() => setIssuesOnly(false)}>All nodes</button>
        <button className={ui.button} aria-pressed={issuesOnly} onClick={() => setIssuesOnly(true)}>Needs attention</button>
        {topic !== "all" ? <button className={ui.button} onClick={() => setTopic("all")}>All topics</button> : null}
        <p className="text-caption text-muted">{topic === "all" ? "Select a topic to explore its systems." : `${topicNames[topic]} · select a system for its last check.`}</p>
        {!items.length ? <p role="status" className="text-caption text-muted">{live ? "No systems match these filters." : "Waiting for current health data. No healthy state is assumed."}</p> : null}
      </div>
      <div className="flex flex-wrap items-center gap-4 border-t border-line p-5 text-xxs text-muted">
        {Object.keys(statusClass).map((status) => <span key={status} className="flex items-center gap-2"><i className={`size-1.5 rounded-full ${statusDot[status as keyof typeof statusDot]}`} />{status}</span>)}
      </div>
    </OrbitalUniverse>
  );
}
