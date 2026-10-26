import type { Health, HealthNode } from "@/lib/contracts";
export const attention = ["degraded", "down", "unknown"];
/** Without a current heartbeat, retained node states are reported as unknown. */
export const reportedNodes = (
  state: Health | null,
  live: boolean,
): HealthNode[] =>
  (state?.nodes ?? []).map((node) =>
    live
      ? node
      : {
          ...node,
          status: "unknown",
          detail:
            "Health engine unavailable or heartbeat missed. Retained observation only.",
        },
  );
export const inTopic = (nodes: HealthNode[], topic: string) =>
  nodes.filter((node) => topic === "all" || node.group === topic);
export const shown = (nodes: HealthNode[], issuesOnly: boolean) =>
  nodes.filter((node) => !issuesOnly || attention.includes(node.status));
