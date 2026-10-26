import type { ReactNode } from "react";
import { ui } from "@/lib/ui";
export function Heading({
  title,
  subtitle,
  action,
}: {
  title: string;
  subtitle: string;
  action?: ReactNode;
}) {
  return (
    <div className={ui.heading}>
      <div>
        <p className={ui.eyebrow}>APPLICATION / {title.toUpperCase()}</p>
        <h1 className={ui.title}>{title}</h1>
        <p className={ui.subtitle}>{subtitle}</p>
      </div>
      {action}
    </div>
  );
}
