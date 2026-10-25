import { cp } from "node:fs/promises";
const frontend = new URL("../frontend/", import.meta.url);
await cp(
  new URL(".next/static/", frontend),
  new URL(".next/standalone/frontend/.next/static/", frontend),
  { recursive: true },
);
await cp(
  new URL("public/", frontend),
  new URL(".next/standalone/frontend/public/", frontend),
  { recursive: true },
);
