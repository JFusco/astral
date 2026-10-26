import type { ReactNode } from "react";
import { ui } from "@/lib/ui";
export function Panel({
  title,
  subtitle,
  action,
  children,
  className = "",
}: {
  title: string;
  subtitle?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`${ui.panel} ${className}`}>
      <div className={ui.panelHeading}>
        <div>
          <h2 className={ui.sectionTitle}>{title}</h2>
          {subtitle ? (
            <p className="text-caption text-muted">{subtitle}</p>
          ) : null}
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}
