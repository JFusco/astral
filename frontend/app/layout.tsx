import type { Metadata } from "next";
import { Suspense, type ReactNode } from "react";
import "../styles/app.css";
import { Provider } from "@/components/provider";
import { AppFrame } from "@/components/shell/app-frame";
import { AnimationProvider } from "@/components/motion";
import { loadSeed } from "@/lib/server/seed";
export const metadata: Metadata = {
  title: { default: "ASTRAL / Trading command", template: "ASTRAL / %s" },
  description:
    "Local paper trading, accounting, offline learning and service health.",
  robots: { index: false, follow: false },
  icons: { icon: "/astral-mark.svg" },
};
export const dynamic = "force-dynamic";
export default function RootLayout({ children }: { children: ReactNode }) {
  // Not awaited: the static frame streams first; the seeded frame follows within the read timeout.
  const seed = loadSeed();
  return (
    <html lang="en" className="bg-app text-ink">
      <body className="min-w-80 bg-app font-sans text-body text-ink antialiased scheme-dark">
        <AnimationProvider>
          <Suspense fallback={<AppFrame unseeded />}>
            <Provider seed={seed}>
              <AppFrame>{children}</AppFrame>
            </Provider>
          </Suspense>
        </AnimationProvider>
      </body>
    </html>
  );
}
