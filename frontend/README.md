# ASTRAL Next.js frontend

The sole UI is a Next.js 16.4.3 App Router application with React 19.3.1,
strict TypeScript, Tailwind 4.3.3 and Motion 14.6.0. Python owns every engine,
ledger, risk decision, provider connection and order submission. Effect is deferred.

## Run

From the repository root, use Node 22+ (verified with Node 24):

```sh
npm ci --ignore-scripts
npm run dev
```

Open http://127.0.0.1:3000. The backend API stays on 8766, intelligence on 8768,
and health on 8769. Start those processes separately using the root README.
The frontend does not restart workers or change broker flags. For production,
run `npm run build` then `npm start`; the build prepares standalone assets.
Webpack is explicit because Turbopack worker-port binding failed in this environment.

Server-only upstream configuration is documented in `.env.example`. Do not copy
broker credentials here. The root Python `.env` is independent of this workspace.

## Ownership

- `app/`: shared server-rendered frame, routes, loading/error states and API handlers.
- `components/`: React shell, controls, reports, research evidence and graphics wrappers.
- `lib/connection.ts`: one persistent SSE/polling owner, replay cursor and fill deduplication.
- `lib/contracts.ts`: runtime validation and inferred TypeScript contracts.
- `lib/relay.ts` and `lib/upstream.ts`: exact API allowlist, local host/origin checks,
  uncached forwarding and streaming cancellation. Native Node HTTP preserves the
  validated browser Host and Origin; Node Fetch replaces Host with the upstream host.
- `graphics/`: retained Canvas and Three.js drawing algorithms. These imperative
  JavaScript modules have cleanup ownership; strict TypeScript owns the React/API layer.
- `styles/app.css`: the only CSS entry, local Fontsource assets and explicit source scans.
- `styles/tokens/`: existing semantic colors, typography and four-pixel layout scale.

Preserve complete Tailwind class names and shared utility recipes. Avoid alternate
spacing/font scales, page stylesheets and component CSS wrappers. Runtime geometry
stays in the renderer. Three.js remains pinned to 0.186.1, with its package MIT license;
fonts retain their package licenses. There are no runtime CDN requests.

Motion is the standard UI animation library. `LazyMotion`/`m`, `MotionConfig` and
`useReducedMotion` power loading feedback, connection notices and dialogs. System
reduced motion takes precedence over the browser's cinematic/calm setting; reduced
mode also stops infinite opacity pulses. No loading indicator claims that missing
account data is zero or that a saved report is live. The shell remains visible.

All browser API calls share the frontend origin. API paths/methods are explicit;
requests cannot choose upstream URLs. State and report responses use no-store.
Mutation requests are never automatically retried. An uncertain order retains its
intent and blocks new submission across navigation until explicit reconciliation
finds a definite saved order state. Python independently enforces every risk guard.

## Verify

```sh
npm run lint
npm run typecheck
npm test
npm run build
npm run test:e2e
```

Browser tests require installed Chrome (Playwright's `chrome` channel) and the root
Python `.venv` with development dependencies. They own ports 18730/18766 and a
fresh temporary simulator ledger, with orders enabled only in that simulator.
They do not connect to the operator's paper service, health providers or collector.
Health/report fixtures used by browser tests are explicitly test data. Test reports,
traces and screenshots stay ignored under `frontend/test-results/`.

Docker builds the standalone frontend separately and publishes only loopback port
3000. Python services keep independent process lifecycles and a persistent private
volume. No legacy HTML routes, static export, hosted preview or browser-only demo
are maintained. Existing external preview retirement is outside this local checkout.

## References

Brain snapshot `eaa45472a1bb493bdcbd07657f123e5d957dcfab`: release-matched docs and
async route parameters. Next.js APIs were checked in installed `next/dist/docs/`.
Brain retrieval worked; its local activity recording was unavailable.

- [Motion installation and App Router](https://motion.dev/docs/react-installation)
- [Motion accessibility](https://motion.dev/docs/react-accessibility)
- [Motion AnimatePresence](https://motion.dev/docs/react-animate-presence)
- [Motion bundle size](https://motion.dev/docs/react-reduce-bundle-size)
- [Next.js Server and Client Components](https://nextjs.org/docs/app/getting-started/server-and-client-components)
- [Next.js backend forwarding](https://nextjs.org/docs/app/guides/backend-for-frontend#proxying-to-a-backend)
