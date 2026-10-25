# ASTRAL trading command prototype

Private static interface prototype for the paper-first trading architecture in `../../reports/Paper trading bot architecture.md`.

Run locally with `python3 -m http.server 4173 --directory dist`, then open `http://localhost:4173`.

This is a browser simulation. Prices, news, telemetry and fills are synthetic; no broker, model or news API is connected. There are no real orders, real API charges, backend workers, historical strategy tests or durable trading records. The prototype pauses price updates in a hidden tab and resets on reload. A 24/7 production service must run separately from the UI.

The interface contains a perspective-projected 3D canvas universe, selectable assets, simulated trade events and accounting, entry halt, pause/resume, news filters/details, portfolio chart periods, system/source/strategy panels, and saved motion settings. Buys bloom as nebulas; sells create expanding supernova rings. Reduced motion removes orbital movement and bursts.

`dist/core.js` owns synthetic portfolio accounting and simple illustrative risk limits. `dist/app.js` owns UI events and rendering. `dist/styles.css` owns the responsive layout. Google Fonts is the only external display dependency; system fonts provide a fallback.

The diagram, sources, proposed backend, current provider limits, estimates, learning loop and acceptance gates are in the research blueprint. No simulator behavior should be treated as live execution evidence.
