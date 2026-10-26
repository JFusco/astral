import type { ReactNode } from "react";
import { ui } from "@/lib/ui";
import { Navigation } from "./navigation";
import { ConnectionStatus } from "./connection-status";
import { Clock } from "./clock";
import { HaltButton } from "./halt-button";
import { OpeningPanels } from "./opening-panels";
/**
 * Header, navigation and main landmark. `unseeded` is the provider-independent
 * frame shown while the server seed streams: static status, disabled halt.
 */
export function AppFrame({
  unseeded = false,
  children,
}: {
  unseeded?: boolean;
  children?: ReactNode;
}) {
  return (
    <div className="ml-rail-compact min-w-0 md:ml-rail">
      <header className="flex min-h-header flex-wrap items-center gap-x-4 gap-y-3 border-b border-line bg-app px-4 py-4 md:px-8 lg:flex-nowrap">
        <Navigation />
        <div className="ml-auto flex flex-wrap items-center gap-3 text-caption text-muted">
          {unseeded ? (
            <>
              <span role="status" className="text-status-unknown">
                CONNECTING TO SERVICE
              </span>
              <span className="hidden font-display xl:block">— UTC</span>
              <button disabled className={`${ui.button} text-status-degraded`}>
                ◈ Halt entries
              </button>
            </>
          ) : (
            <>
              <ConnectionStatus />
              <Clock />
              <HaltButton />
            </>
          )}
        </div>
      </header>
      <main
        id="main"
        tabIndex={-1}
        className="mx-auto w-full max-w-page px-4 py-6 outline-none md:px-8 md:py-8"
      >
        {unseeded ? <OpeningPanels /> : children}
      </main>
    </div>
  );
}
