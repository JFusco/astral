import { LoadingPanel } from "@/components/motion";
export default function Loading() {
  return (
    <div className="space-y-6">
      <LoadingPanel label="Opening ASTRAL" cards />
      <LoadingPanel label="Loading screen" />
    </div>
  );
}
