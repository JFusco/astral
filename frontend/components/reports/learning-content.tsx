import type { Learning } from "@/lib/contracts";
import { ui } from "@/lib/ui";
import { Reveal } from "../motion";
import { LearningSummary } from "./learning-summary";
import { LearningOutcomes } from "./learning-outcomes";
import { LearningModel } from "./learning-model";
import { LearningInventory } from "./learning-inventory";
import { LearningUsage } from "./learning-usage";
import { LearningProtected } from "./learning-protected";
import { LearningBoundaries } from "./learning-boundaries";
export function LearningContent({ r }: { r: Learning }) {
  return (
    <Reveal>
      <LearningSummary r={r} />
      <div className={ui.columns}>
        <LearningOutcomes r={r} />
        <LearningModel r={r} />
        <LearningInventory r={r} />
        <LearningUsage r={r} />
      </div>
      <LearningProtected r={r} />
      <LearningBoundaries r={r} />
    </Reveal>
  );
}
