export const amounts = (value: Record<string, string | number> | null) =>
  value && Object.keys(value).length
    ? Object.entries(value)
        .map(([currency, value]) => `${currency} ${value}`)
        .join(" · ")
    : "Unknown";
