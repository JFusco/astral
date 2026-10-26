"use client";
import { useSyncExternalStore, type ReactNode } from "react";
import { LazyMotion, MotionConfig, domAnimation } from "motion/react";
import * as m from "motion/react-m";
import { ui } from "@/lib/ui";
type Mode = "cinematic" | "calm" | "reduced";
let browserFallback: Mode = "cinematic";
function readMode(): Mode {
  try {
    const value = localStorage.getItem("astral-motion");
    return value === "reduced" || value === "calm" || value === "cinematic"
      ? value
      : browserFallback;
  } catch {
    return browserFallback;
  }
}
function subscribeMode(listener: () => void) {
  window.addEventListener("storage", listener);
  window.addEventListener("astral-motion-change", listener);
  return () => {
    window.removeEventListener("storage", listener);
    window.removeEventListener("astral-motion-change", listener);
  };
}
const initialMode = (): Mode => "cinematic";
// The OS preference is a browser read too: the server snapshot keeps hydration deterministic.
const reducedQuery = "(prefers-reduced-motion: reduce)";
function subscribeSystem(listener: () => void) {
  const query = window.matchMedia(reducedQuery);
  query.addEventListener("change", listener);
  return () => query.removeEventListener("change", listener);
}
const readSystem = () => window.matchMedia(reducedQuery).matches;
const initialSystem = () => false;
function setMode(value: Mode) {
  browserFallback = value;
  try {
    localStorage.setItem("astral-motion", value);
  } catch {}
  window.dispatchEvent(new Event("astral-motion-change"));
}
/**
 * Read per consumer, not through context: each component hydrates with the
 * server snapshot even when its Suspense boundary streams in after the
 * browser preference has been applied above it.
 */
export function useMotionSettings() {
  const mode = useSyncExternalStore(subscribeMode, readMode, initialMode);
  const systemReduced = useSyncExternalStore(
    subscribeSystem,
    readSystem,
    initialSystem,
  );
  return { mode, reduced: systemReduced || mode === "reduced", setMode };
}
export function AnimationProvider({ children }: { children: ReactNode }) {
  const { reduced } = useMotionSettings();
  return (
    <MotionConfig
      reducedMotion={reduced ? "always" : "user"}
      transition={{ duration: reduced ? 0 : 0.18 }}
    >
      <LazyMotion features={domAnimation} strict>
        {children}
      </LazyMotion>
    </MotionConfig>
  );
}
export function Reveal({ children }: { children: ReactNode }) {
  const { reduced } = useMotionSettings();
  return (
    <m.div
      initial={false}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: reduced ? 0 : 0.18 }}
    >
      {children}
    </m.div>
  );
}
export function LoadingPanel({
  label = "Loading saved records",
  cards = false,
}: {
  label?: string;
  cards?: boolean;
}) {
  const { reduced } = useMotionSettings();
  return (
    <div
      role="status"
      aria-busy="true"
      aria-label={label}
      className="space-y-4"
    >
      <span className="text-caption text-muted">{label}…</span>
      <m.div
        aria-hidden="true"
        animate={reduced ? { opacity: 1 } : { opacity: [0.45, 0.85, 0.45] }}
        transition={
          reduced
            ? { duration: 0 }
            : { duration: 1.7, repeat: Infinity, ease: "easeInOut" }
        }
        className={cards ? ui.summaryGrid : "space-y-4"}
      >
        {Array.from({ length: cards ? 4 : 3 }, (_, i) => (
          <div key={i} className={cards ? ui.card : "h-4 rounded bg-line/60"}>
            {cards ? (
              <>
                <div className="mb-5 h-2 w-24 rounded bg-line" />
                <div className="mb-3 h-8 w-28 rounded bg-line" />
                <div className="h-2 w-40 max-w-full rounded bg-line" />
              </>
            ) : null}
          </div>
        ))}
      </m.div>
    </div>
  );
}
