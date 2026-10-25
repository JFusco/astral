# Application health and its independent health engine

The health engine is separate from telemetry and trading. Telemetry supplies
observations; health applies explicit freshness and availability rules, retains
state transitions and exposes its own heartbeat. Nothing in this engine can
place orders, clear risk gates, promote strategies or launch model calls.

Health is a child page in ASTRAL, using the same logo, sidebar, header and main
navigation as Overview and Accounting. Only the assessment engine/process is
independent; the health UI is not a separate application or brand.
Open **App health** in the main navigation or the **System Heartbeat** card, or visit
`http://127.0.0.1:3000/health`. The health universe shows every discovered
dependency as a node. Click a node or its keyboard-accessible dependency button
to inspect its state, scope and observation time. Drag/zoom the map; filter to
dependencies needing attention. The central pulse and heartbeat trace follow
completed assessments. Eight types share one three-dimensional star field. Topic hues and glows
identify types; small status lights and outlines retain the same health colors.
Connected Systems uses expandable sections by type, retaining expansion state
across health refreshes. The dependency inspector organizes the inventory by type; there are no
separate application-level topic pages. The type selector filters the map and inspector together. Shooting stars, breathing glows and neuron trails circling the shared disk
are labeled ambient motion. The heartbeat trace and expanding wave reflect real
assessments. Reduced-motion preferences stop ambient animation.
Status text in Systems by type uses green for healthy, lavender for unknown,
red/coral for down/degraded issues, slate for inactive and cyan for checking.
Text labels remain present alongside the colors.

The scene uses the same Three.js 0.186.1 WebGL renderer and additive radial
sprite approach as the local Brain viewer, with irregular dust/nebulae rather
than rigid spiral arms. Shooting stars use soft, tapered textured ribbons and
luminous heads; a fixed pool of four neurons has varied tilted paths that cross the front and back of the disk,
with depth-dependent brightness and perspective size. Each neuron has a smooth,
textured ribbon that follows its recent 3D path and fades toward the tail, using
the same light-trail texture as shooting stars. Stars have deterministic varied
sizes, gentle independent drift and asynchronous decorative pulses. The complete field rotates continuously at a slow rate;
reduced-motion preferences keep it still. Three.js is pinned to 0.186.1 in the npm workspace and bundled locally with its
MIT license. `frontend/graphics/health-galaxy.js` owns the renderer; no CDN, Brain
data or Brain service is connected. The
force-layout wrapper from Brain is unnecessary for these fixed health nodes.
If WebGL is unavailable, the categorized health inspector remains usable.

## Three separate responsibilities

| Component | Responsibility | Storage |
| --- | --- | --- |
| Existing application/collector telemetry | Worker observations, source fetches, quote/account timestamps, model execution receipts | Existing trading and intelligence ledgers |
| `backend/health_engine.py` | Assess observations, freshness, local failures and recovery | Separate `runtime/astral-health.sqlite` |
| `backend/health_app.py` and `frontend/components/health.tsx` | Read-only cached API and live 3D health universe | No browser trading state or credentials |

Run one independent health process from the project root:

```sh
.venv/bin/python -m uvicorn backend.health_app:app --host 127.0.0.1 --port 8769 --workers 1 --timeout-graceful-shutdown 5 --no-access-log
```

It owns `runtime/health.lock`. It does not load `.env`, open either existing
ledger, import the broker/strategy engines, or use account/model credentials.
For local development, all three Python services and the Next.js frontend run on this Mac. No login daemon, external alert delivery
or cloud deployment is installed. A sleeping/offline Mac creates a visible gap.

## What is checked

- Application and collector: bounded GETs to their new `/api/health-inputs`
  endpoints. These are small, allowlisted read-only observations, not full
  portfolio/replay scans. They exclude balances, orders, prompts, keys and tokens.
- Paper readback: recent account/order snapshot plus current connection state;
  not a broker write or an execution/fee-reconciliation acceptance test.
- Quotes: source and arrival timestamps for all eight instruments. Closed ETF
  sessions are explicitly inactive; missing crypto observations are degraded.
- Every reported worker, including quote/reconciliation, research, replay,
  liquidity, event context, fees and news. Disabled strategy/shadow/exit workers
  remain inactive. Ledger health uses the latest durable-event timestamp rather
  than its startup-only worker label. Learning is dataset recording, not an
  active trained policy.
- Every public source returned by the collector, using its existing cadence and
  freshness contract. Alpaca published status reuses its existing retained
  snapshot; the health engine does not duplicate Alpaca requests.
- QuantConnect's official status page and OpenAI's official component-status
  JSON. Only these two fixed public status requests are added. Responses have
  size/time limits, strict validation and bounded backoff, including Retry-After.
- Research model: whether it is enabled and the status/time of its last recorded
  call. A disabled model is inactive, not failed. An enabled model with no recent
  call is unknown. No free/paid canary call or quota/authentication probe occurs.
- Local disk capacity and successful writes to the separate health ledger.
  Capacity warns below 5 GiB and is critical below 1 GiB; these are operational
  health thresholds and cannot alter strategy risk limits.

Docker daemon health, actual LEAN execution and QuantConnect checkout/entitlement
are **not verified**. They have explicit unknown/inactive nodes. Finding an
executable alone does not establish runtime health. Published component status
does not establish this account's/model's availability. QuantConnect's aggregate
page does not separately certify checkout. Unknown data never becomes healthy
because another component is green. This is the currently instrumented inventory,
not a claim that every possible operating-system or third-party capability has
an active probe.

## Cadence, heartbeat and changes

Local assessments run every 10 seconds after the preceding bounded cycle.
Public provider reports run independently every 120 seconds, avoiding a slow
status page stalling local checks. Their freshness limit is 360 seconds; the
provider's own last-change timestamp remains distinct from local revalidation.
The browser reads cached health every five seconds and never triggers paid or
authenticated probes. UI color changes immediately on a failed health request.
A server heartbeat older than 30 seconds invalidates retained green states and
shows nodes as unknown. Browser liveness also expires if fresh responses stop.

Changes and recovery are deduplicated in the health ledger and visible in the
universe. An unchanged error does not create repeated transition events. These
are local health events; external notifications are off. Published reports and
raw content hashes retain their own provenance. Health persistence/assessment
failure prevents the engine from presenting cached results as a current success.

Provider release-note/deprecation and pricing-change surveillance remains a
separate roadmap item. This implementation does not auto-upgrade dependencies,
enroll services, send support messages, change subscriptions or bypass any gate.

Official public sources: [QuantConnect](https://status.quantconnect.com/),
[OpenAI](https://status.openai.com/api/v2/summary.json),
[Alpaca](https://status.alpaca.markets/).
