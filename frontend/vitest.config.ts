import { defineConfig } from "vitest/config";
export default defineConfig({
  resolve: {
    // Next aliases this inside its own compilers; mirror that with its installed empty module.
    alias: { "server-only": "next/dist/compiled/server-only/empty" },
  },
  test: {
    include: ["tests/**/*.test.ts"],
    environment: "node",
    restoreMocks: true,
  },
});
