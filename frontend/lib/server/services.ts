import "server-only";
export type Service = "application" | "health" | "intelligence";
const originDefaults = {
  application: "http://127.0.0.1:8766",
  health: "http://127.0.0.1:8769",
  intelligence: "http://127.0.0.1:8768",
};
const originVariables = {
  application: "ASTRAL_API_ORIGIN",
  health: "ASTRAL_HEALTH_ORIGIN",
  intelligence: "ASTRAL_INTELLIGENCE_ORIGIN",
};

/** Forwarded headers are intentionally ignored. Only configured local browser origins are trusted. */
export function allowedHost(host: string | null): host is string {
  const allowed = (
    process.env.ASTRAL_UI_ORIGINS ??
    "http://127.0.0.1:3000,http://localhost:3000"
  )
    .split(",")
    .map((s) => s.trim());
  return !!host && allowed.includes(`http://${host}`);
}

/** Resolved per call so environment changes apply; null for an unusable configuration. */
export function serviceUrl(service: Service, path: string): URL | null {
  const upstream = new URL(
    process.env[originVariables[service]] ?? originDefaults[service],
  );
  if (upstream.protocol !== "http:" || upstream.username || upstream.password)
    return null;
  upstream.pathname = `/api/${path}`;
  return upstream;
}
