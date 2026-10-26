"use client";
import { useDashboard } from "../provider";
/** Server-captured `now` on first render, then the connection's one-second tick. */
export function Clock() {
  const { snapshot } = useDashboard();
  return (
    <span className="hidden font-display xl:block">
      {snapshot.now
        ? new Date(snapshot.now).toISOString().slice(11, 19) + " UTC"
        : "— UTC"}
    </span>
  );
}
