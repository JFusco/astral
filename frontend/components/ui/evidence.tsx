import { display, label } from "@/lib/format";
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
