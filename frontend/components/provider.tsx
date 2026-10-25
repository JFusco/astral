"use client";
import {
  createContext,
  useContext,
  useEffect,
  useState,
  useSyncExternalStore,
  type ReactNode,
} from "react";
import { Connection, serverSnapshot, type Snapshot } from "@/lib/connection";
const Context = createContext<{
  connection: Connection;
  snapshot: Snapshot;
} | null>(null);
export function Provider({ children }: { children: ReactNode }) {
  const [connection] = useState(() => new Connection());
  const snapshot = useSyncExternalStore(
    connection.subscribe,
    connection.getSnapshot,
    serverSnapshot,
  );
  useEffect(() => connection.start(), [connection]);
  return (
    <Context.Provider value={{ connection, snapshot }}>
      {children}
    </Context.Provider>
  );
}
export function useDashboard() {
  const value = useContext(Context);
  if (!value) throw new Error("Dashboard provider missing");
  return value;
}
