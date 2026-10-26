"use client";
import {
  createContext,
  use,
  useContext,
  useEffect,
  useState,
  useSyncExternalStore,
  type ReactNode,
} from "react";
import { Connection, type Seed, type Snapshot } from "@/lib/connection";
const Context = createContext<{
  connection: Connection;
  snapshot: Snapshot;
} | null>(null);
export function Provider({
  seed,
  children,
}: {
  seed: Promise<Seed>;
  children: ReactNode;
}) {
  const initial = use(seed);
  // Created once; seeds from later layout renders (router.refresh) are ignored.
  const [connection] = useState(() => new Connection(initial));
  const snapshot = useSyncExternalStore(
    connection.subscribe,
    connection.getSnapshot,
    connection.getInitialSnapshot,
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
