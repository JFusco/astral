import type { ReactNode } from "react";
export function Empty({ children }: { children: ReactNode }) {
  return (
    <p className="px-5 py-6 text-caption leading-relaxed text-muted">
      {children}
    </p>
  );
}
