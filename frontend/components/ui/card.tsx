import type { ReactNode } from "react";
import { ui } from "@/lib/ui";
export function Card({
  label,
  value,
  note,
  tone = "",
}: {
  label: string;
  value: ReactNode;
  note: ReactNode;
  tone?: string;
}) {
  return (
    <div className={ui.card}>
      <span className={ui.label}>{label}</span>
      <strong className={`${ui.value} ${tone}`}>{value}</strong>
      <div className={ui.note}>{note}</div>
    </div>
  );
}
