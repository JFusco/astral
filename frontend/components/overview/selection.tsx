"use client";
import { createContext, useContext, useState, type ReactNode } from "react";
import { OrderDialog } from "../order";
type Selection = {
  selected: string;
  setSelected: (symbol: string) => void;
  setOrder: (side: "buy" | "sell" | null) => void;
};
const Context = createContext<Selection | null>(null);
/** The selected symbol and pending order side, shared by the universe, asset bar and positions. */
export function SelectionState({ children }: { children: ReactNode }) {
  const [selected, setSelected] = useState("BTC");
  const [order, setOrder] = useState<"buy" | "sell" | null>(null);
  return (
    <Context.Provider value={{ selected, setSelected, setOrder }}>
      {children}
      {order ? (
        <OrderDialog
          symbol={selected}
          side={order}
          onClose={() => setOrder(null)}
        />
      ) : null}
    </Context.Provider>
  );
}
export function useSelection() {
  const selection = useContext(Context);
  if (!selection) throw new Error("Selection state missing");
  return selection;
}
