import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
const root = join(import.meta.dirname, "..");
// Over-limit client files awaiting their milestone split. This list may only shrink.
const allowlist = new Set([
  "components/overview.tsx",
  "components/research.tsx",
]);
const sources = (dir: string): string[] =>
  readdirSync(join(root, dir), { withFileTypes: true }).flatMap((entry) =>
    entry.isDirectory()
      ? sources(join(dir, entry.name))
      : /\.tsx?$/.test(entry.name)
        ? [join(dir, entry.name)]
        : [],
  );
const files = ["app", "components", "lib"].flatMap(sources);
const text = (file: string) => readFileSync(join(root, file), "utf8");
const isClient = (file: string) => /^\s*["']use client["']/.test(text(file));
const lines = (file: string) => text(file).trimEnd().split("\n").length;
describe("server/client boundaries", () => {
  it("keeps pages and layouts as Server Components", () => {
    const routes = files.filter((f) => /^app\/.*(page|layout)\.tsx$/.test(f));
    expect(routes.length).toBeGreaterThan(0);
    expect(routes.filter(isClient)).toEqual([]);
  });
  it("keeps client files at or under 160 lines", () => {
    const over = files
      .filter((f) => isClient(f) && !allowlist.has(f) && lines(f) > 160)
      .map((f) => `${f}: ${lines(f)}`);
    expect(over).toEqual([]);
  });
  it("allowlists only files that still exceed the limit", () => {
    for (const file of allowlist) {
      expect(files).toContain(file);
      expect(lines(file)).toBeGreaterThan(160);
    }
  });
  it("starts every lib/server module with the server-only import", () => {
    const server = files.filter((f) => f.startsWith("lib/server/"));
    expect(server.length).toBeGreaterThan(0);
    for (const file of server)
      expect(text(file).trimStart().split("\n")[0], file).toBe(
        'import "server-only";',
      );
  });
});
