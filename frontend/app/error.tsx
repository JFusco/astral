"use client";
import { ui } from "@/lib/ui";
export default function ErrorPage({ reset }: { reset: () => void }) {
  return (
    <section role="alert" className={ui.notice}>
      <h1 className={ui.sectionTitle}>This screen could not load</h1>
      <p className="my-4">
        The application services continue independently. Try loading this screen
        again.
      </p>
      <button className={ui.button} onClick={reset}>
        Try again
      </button>
    </section>
  );
}
