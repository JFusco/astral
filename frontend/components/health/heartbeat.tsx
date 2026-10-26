"use client";
import { useEffect, useRef } from "react";
export function Heartbeat({
  sequence,
  live,
  reduced,
}: {
  sequence: number;
  live: boolean;
  reduced: boolean;
}) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const lastPulse = useRef(0);
  useEffect(() => {
    if (live) lastPulse.current = performance.now();
  }, [sequence, live]);
  useEffect(() => {
    const el = canvas.current,
      ctx = el?.getContext("2d");
    if (!el || !ctx) return;
    let frame = 0;
    let disposed = false;
    function draw(now: number) {
      if (disposed) return;
      const { width, height } = el!.getBoundingClientRect();
      const d = Math.min(devicePixelRatio || 1, 2);
      if (
        el!.width !== Math.round(width * d) ||
        el!.height !== Math.round(height * d)
      ) {
        el!.width = Math.round(width * d);
        el!.height = Math.round(height * d);
      }
      ctx!.setTransform(d, 0, 0, d, 0, 0);
      ctx!.clearRect(0, 0, width, height);
      ctx!.strokeStyle = getComputedStyle(el!).getPropertyValue(
        live ? "--color-status-checking" : "--color-status-unknown",
      );
      ctx!.lineWidth = 1.5;
      ctx!.beginPath();
      const elapsed = now - lastPulse.current;
      for (let x = 0; x < width; x++) {
        const center = live && !reduced && elapsed < 2500 ? elapsed / 2200 : 2,
          offset = x / width - center;
        let y = height * 0.55;
        if (Math.abs(offset) < 0.09)
          y +=
            Math.exp((-offset * offset) / 0.0006) *
            Math.sin(offset * 120) *
            height *
            0.42;
        if (x) ctx!.lineTo(x, y);
        else ctx!.moveTo(x, y);
      }
      ctx!.stroke();
      frame = requestAnimationFrame(draw);
    }
    frame = requestAnimationFrame(draw);
    return () => {
      disposed = true;
      cancelAnimationFrame(frame);
    };
  }, [live, reduced]);
  return (
    <canvas
      ref={canvas}
      className="my-2 h-10 w-full"
      aria-label={
        live
          ? "Heartbeat follows completed health checks"
          : "No current health heartbeat"
      }
    />
  );
}
