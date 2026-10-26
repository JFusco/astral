"use client";
import { useMotionSettings } from "../../motion";
export function SettingsView() {
  const { mode, setMode, reduced } = useMotionSettings();
  return (
    <>
      <label className="block text-caption">
        Universe motion
        <select
          className="mt-2 w-full rounded-lg border border-line bg-surface-raised px-4 py-3 text-ink"
          value={mode}
          onChange={(e) => setMode(e.target.value as typeof mode)}
        >
          <option value="cinematic">Cinematic</option>
          <option value="calm">Calm</option>
          <option value="reduced">Reduced</option>
        </select>
      </label>
      <p>
        {reduced
          ? "Reduced motion is active."
          : "Motion follows this browser setting and the operating system preference."}
      </p>
      <p>
        Display settings affect this browser only. Python continues recording
        and managing orders independently.
      </p>
    </>
  );
}
