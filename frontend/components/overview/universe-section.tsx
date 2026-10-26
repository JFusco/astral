"use client";
import { MarketUniverse } from "../market-universe";
import { AssetBar } from "./asset-bar";
import { useSelection } from "./selection";
/** Connects the selection context to MarketUniverse, whose logic is unchanged. */
export function UniverseSection() {
  const { selected, setSelected } = useSelection();
  return (
    <MarketUniverse selected={selected} onSelect={setSelected}>
      <AssetBar />
    </MarketUniverse>
  );
}
