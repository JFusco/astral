import type { ReactNode } from "react";
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
