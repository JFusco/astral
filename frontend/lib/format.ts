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
export const basisPoints = (value: unknown): string =>
  (typeof value !== "number" && typeof value !== "string") ||
  (typeof value === "string" && value.trim() === "") ||
  !Number.isFinite(Number(value))
    ? "Unknown"
    : new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 }).format(
        Number(value),
      );
export const utc = (value: unknown) =>
  typeof value === "string" && Number.isFinite(Date.parse(value))
    ? new Date(value).toISOString().slice(11, 19) + " UTC"
    : "Unknown";
