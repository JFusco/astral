import { LoadingPanel } from "../motion";
export function OpeningPanels() {
  return (
    <div className="space-y-6">
      <LoadingPanel label="Opening ASTRAL" cards />
      <LoadingPanel label="Loading screen" />
    </div>
  );
}
