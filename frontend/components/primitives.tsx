import type { ReactNode } from "react";
import { ui } from "@/lib/ui";
export function Heading({
  title,
  subtitle,
  action,
}: {
  title: string;
  subtitle: string;
  action?: ReactNode;
}) {
  return (
    <div className={ui.heading}>
      <div>
        <p className={ui.eyebrow}>APPLICATION / {title.toUpperCase()}</p>
        <h1 className={ui.title}>{title}</h1>
        <p className={ui.subtitle}>{subtitle}</p>
      </div>
      {action}
    </div>
  );
}
export function Card({
  label,
  value,
  note,
  tone = "",
}: {
  label: string;
  value: ReactNode;
  note: ReactNode;
  tone?: string;
}) {
  return (
    <div className={ui.card}>
      <span className={ui.label}>{label}</span>
      <strong className={`${ui.value} ${tone}`}>{value}</strong>
      <div className={ui.note}>{note}</div>
    </div>
  );
}
export function Panel({
  title,
  subtitle,
  action,
  children,
  className = "",
}: {
  title: string;
  subtitle?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`${ui.panel} ${className}`}>
      <div className={ui.panelHeading}>
        <div>
          <h2 className={ui.sectionTitle}>{title}</h2>
          {subtitle ? (
            <p className="text-caption text-muted">{subtitle}</p>
          ) : null}
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}
export function Empty({ children }: { children: ReactNode }) {
  return (
    <p className="px-5 py-6 text-caption leading-relaxed text-muted">
      {children}
    </p>
  );
}
export const label = (value: string) => value.replaceAll("_", " ");
export const display = (value: unknown): string =>
  value === null || value === undefined
    ? "Unknown"
    : typeof value === "object"
      ? JSON.stringify(value)
      : String(value);
export const money = (value: unknown): string =>
  value === null ||
  value === undefined ||
  (typeof value === "string" && value.trim() === "") ||
  !Number.isFinite(Number(value))
    ? "—"
    : new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
        maximumFractionDigits: 2,
      }).format(Number(value));
export const quantity = (value: unknown) =>
  value === null || value === undefined
    ? "—"
    : new Intl.NumberFormat("en-US", { maximumFractionDigits: 9 }).format(
        Number(value),
      );
export const utc = (value: unknown) =>
  typeof value === "string" && Number.isFinite(Date.parse(value))
    ? new Date(value).toISOString().slice(11, 19) + " UTC"
    : "Unknown";
export function Counts({ values }: { values: Record<string, unknown> }) {
  return (
    <dl className={ui.counts}>
      {Object.entries(values).map(([key, value]) => (
        <div key={key}>
          <dt>{label(key)}</dt>
          <dd>{display(value)}</dd>
        </div>
      ))}
    </dl>
  );
}
export function Evidence({ value }: { value: unknown }) {
  if (value === null || value === undefined)
    return <p className="text-caption text-muted">No retained evidence.</p>;
  if (Array.isArray(value))
    return value.length ? (
      <div className="space-y-3">
        {value.map((item, i) => (
          <div key={i} className="border-b border-line py-3 last:border-0">
            <Evidence value={item} />
          </div>
        ))}
      </div>
    ) : (
      <p>No records.</p>
    );
  if (typeof value === "object")
    return (
      <dl className="space-y-3 text-caption text-muted">
        {Object.entries(value).map(([key, item]) => (
          <div key={key}>
            <dt className="mb-1 text-ink">{label(key)}</dt>
            <dd className="pl-3 break-words">
              {item && typeof item === "object" ? (
                <Evidence value={item} />
              ) : (
                display(item)
              )}
            </dd>
          </div>
        ))}
      </dl>
    );
  return <span className="break-words">{display(value)}</span>;
}
export function SourceLink({
  url,
  children = "Read the source ↗",
}: {
  url: unknown;
  children?: ReactNode;
}) {
  if (typeof url !== "string" || !/^https:\/\//i.test(url)) return null;
  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className="text-cyan underline-offset-4 hover:underline"
    >
      {children}
    </a>
  );
}
