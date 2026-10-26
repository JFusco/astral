import type { ReactNode } from "react";
import { Heading } from "../ui/heading";
import { ResearchLab } from "../research/research-lab";
import { ModeBadge } from "./mode-badge";
import { ConnectionBanner } from "./connection-banner";
import { PortfolioCards } from "./portfolio-cards";
import { SelectionState } from "./selection";
import { UniverseSection } from "./universe-section";
import { PositionsPanel } from "./positions-panel";
import { EquityChart } from "./equity-chart";
import { ExecutionStream } from "./execution-stream";
import { IntelligenceFeed } from "./intelligence-feed";
import { OverviewFooter } from "./overview-footer";
import { ViewDialog } from "./view-dialog";
import { SettingsView } from "./views/settings-view";
import { StrategiesView } from "./views/strategies-view";
import { IntelligenceView } from "./views/intelligence-view";
import { SystemView } from "./views/system-view";
const views: Record<string, () => ReactNode> = {
  settings: () => <SettingsView />,
  strategies: () => <StrategiesView />,
  intelligence: () => <IntelligenceView />,
  system: () => <SystemView />,
};
/** Server composition; each live region is its own client component. */
export function OverviewPage({ view }: { view: string | null }) {
  const content = view && Object.hasOwn(views, view) ? views[view] : undefined;
  return (
    <>
      <Heading
        title="Market overview"
        subtitle="Paper account, positions and retained research evidence."
        action={<ModeBadge />}
      />
      <ConnectionBanner />
      <PortfolioCards />
      <SelectionState>
        <div className="mb-6 grid grid-cols-1 gap-6 xl:grid-cols-3">
          <UniverseSection />
          <PositionsPanel />
        </div>
      </SelectionState>
      <div className="mb-6 grid grid-cols-1 gap-6 lg:grid-cols-2 xl:grid-cols-3">
        <EquityChart />
        <ExecutionStream />
        <IntelligenceFeed />
      </div>
      <ResearchLab />
      <OverviewFooter />
      {view && content ? (
        <ViewDialog view={view}>{content()}</ViewDialog>
      ) : null}
    </>
  );
}
