"use client";
import { createContext, useContext, useState, type ReactNode } from "react";
import { healthIsLive } from "@/lib/connection";
import { useDashboard } from "../provider";
import { inTopic, reportedNodes, shown } from "./health-view";
type View = {
  selected: string;
  setSelected: (id: string) => void;
  issuesOnly: boolean;
  setIssuesOnly: (value: boolean) => void;
  topic: string;
  setTopic: (topic: string) => void;
};
const Context = createContext<View | null>(null);
/** Selection, topic and issue filter shared by the Health map, details and summary. */
export function HealthViewState({ children }: { children: ReactNode }) {
  const [selected, setSelected] = useState("application");
  const [issuesOnly, setIssuesOnly] = useState(false);
  const [topic, setTopic] = useState("all");
  return (
    <Context.Provider
      value={{
        selected,
        setSelected,
        issuesOnly,
        setIssuesOnly,
        topic,
        setTopic,
      }}
    >
      {children}
    </Context.Provider>
  );
}
export function useHealthView() {
  const view = useContext(Context);
  if (!view) throw new Error("Health view state missing");
  const { snapshot } = useDashboard();
  const state = snapshot.health,
    live = healthIsLive(snapshot);
  const nodes = reportedNodes(state, live);
  const scoped = inTopic(nodes, view.topic);
  const visible = shown(scoped, view.issuesOnly);
  return { ...view, snapshot, state, live, nodes, scoped, visible };
}
