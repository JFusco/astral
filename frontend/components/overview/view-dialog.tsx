"use client";
import { useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { Dialog } from "../dialog";
/** Route-driven dialog: closing returns to "/"; the view content arrives as children. */
export function ViewDialog({
  view,
  children,
}: {
  view: string;
  children: ReactNode;
}) {
  const router = useRouter();
  const titles: Record<string, string> = {
    settings: "Display settings",
    strategies: "Deterministic rules. Measured risk.",
    intelligence: "Connected intelligence. Explicit coverage.",
    system: "System telemetry",
  };
  return (
    <Dialog
      title={titles[view] ?? "Application details"}
      eyebrow={
        view === "settings"
          ? "BROWSER DISPLAY SETTINGS"
          : "RETAINED STATE / SERVER AUTHORITY"
      }
      onClose={() => router.replace("/", { scroll: false })}
    >
      {children}
    </Dialog>
  );
}
