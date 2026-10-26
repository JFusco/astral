"use client";
import { statusClass, topicNames } from "@/lib/assets";
import { Panel } from "../ui/panel";
import { Empty } from "../ui/empty";
import { useHealthView } from "./health-view-state";
export function HealthDetails() {
  const { nodes, visible, selected, setSelected, topic, setTopic } =
    useHealthView();
  const inspected = nodes.find((node) => node.id === selected);
  return (
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
      <div className="max-h-96 overflow-y-auto p-3" aria-label="Dependencies">
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
  );
}
