import { ui } from "@/lib/ui";
import { display, label } from "@/lib/format";
export function Counts({ values }: { values: Record<string, unknown> }) {
  return (
    <dl className={ui.counts}>
      {Object.entries(values).map(([key, value]) => (
        <div key={key}>
          <dt>{label(key)}</dt>
          <dd>{display(value)}</dd>
        </div>
      ))}
    </dl>
  );
}
