"use client";
import { useEffect, useId, useRef, type ReactNode } from "react";
import * as m from "motion/react-m";
import { ui } from "@/lib/ui";
import { useMotionSettings } from "./motion";
export function Dialog({
  title,
  eyebrow,
  children,
  onClose,
}: {
  title: string;
  eyebrow: string;
  children: ReactNode;
  onClose: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const id = useId();
  const { reduced } = useMotionSettings();
  useEffect(() => {
    const el = ref.current;
    el?.showModal();
    return () => el?.close();
  }, []);
  return (
    <dialog
      ref={ref}
      aria-labelledby={id}
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      onClick={(event) => {
        if (event.target === ref.current) {
          const r = ref.current.getBoundingClientRect();
          if (
            event.clientX < r.left ||
            event.clientX > r.right ||
            event.clientY < r.top ||
            event.clientY > r.bottom
          )
            onClose();
        }
      }}
      className="fixed inset-0 m-auto max-h-[85dvh] w-[min(44rem,calc(100%-2rem))] overflow-y-auto rounded-panel border border-line bg-surface p-0 text-ink backdrop:bg-app/80"
    >
      <m.div
        initial={{ opacity: reduced ? 1 : 0, y: reduced ? 0 : 8 }}
        animate={{ opacity: 1, y: 0 }}
        className="p-5 md:p-7"
      >
        <div className="mb-5 flex items-start justify-between gap-4">
          <div>
            <p className={ui.eyebrow}>{eyebrow}</p>
            <h2 id={id} className="font-display text-xl text-ink">
              {title}
            </h2>
          </div>
          <button
            className={ui.button}
            onClick={onClose}
            aria-label="Close dialog"
          >
            ×
          </button>
        </div>
        <div className="space-y-4 text-body leading-relaxed text-muted">
          {children}
        </div>
      </m.div>
    </dialog>
  );
}
