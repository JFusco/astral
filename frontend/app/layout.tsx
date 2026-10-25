import type { Metadata } from "next";
import type { ReactNode } from "react";
import "../styles/app.css";
import { Provider } from "@/components/provider";
import { Navigation, ConnectionControls } from "@/components/shell";
import { AnimationProvider } from "@/components/motion";
export const metadata: Metadata = {
  title: { default: "ASTRAL / Trading command", template: "ASTRAL / %s" },
  description:
    "Local paper trading, accounting, offline learning and service health.",
  robots: { index: false, follow: false },
};
export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className="bg-app text-ink">
      <body className="min-w-80 bg-app font-sans text-body text-ink antialiased scheme-dark">
        <AnimationProvider>
          <Provider>
            <div className="ml-rail-compact min-w-0 md:ml-rail">
              <header className="flex min-h-header flex-wrap items-center gap-x-4 gap-y-3 border-b border-line bg-app px-4 py-4 md:px-8 lg:flex-nowrap">
                <Navigation />
                <ConnectionControls />
              </header>
              <main
                id="main"
                tabIndex={-1}
                className="mx-auto w-full max-w-page px-4 py-6 outline-none md:px-8 md:py-8"
              >
                {children}
              </main>
            </div>
          </Provider>
        </AnimationProvider>
      </body>
    </html>
  );
}
