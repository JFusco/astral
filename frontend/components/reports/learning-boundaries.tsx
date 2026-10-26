import type { Learning } from "@/lib/contracts";
import { ui } from "@/lib/ui";
import { Counts } from "../primitives";
export function LearningBoundaries({ r }: { r: Learning }) {
  return (
    <div className="mt-6 space-y-4 border-t border-line py-6 text-body text-muted">
      <h2 className={ui.sectionTitle}>Evaluation boundaries</h2>
      <p>
        This saved offline audit cannot train, promote a strategy, change risk
        limits, call a model or place a trade.
      </p>
      <p>
        Protected outcome bodies and raw model prompts are not exposed here. A
        contract pass checks consistency with supplied evidence; it does not
        establish narrative truth or predictive skill.
      </p>
      {Object.keys(r.issues).length ? <Counts values={r.issues} /> : null}
    </div>
  );
}
