# ASTRAL UI foundation

Overview, App health, Accounting and Learning are pages in one local application.
They share the navigation and logo in `dist/app-shell.js`. Accounting and Learning
share the report layout, heading, summary cards and panels in `dist/ui.js`.
App health uses those same spacing and typography recipes alongside its map.

## Build

```sh
npm ci --ignore-scripts
npm run build
```

Tailwind CSS and its CLI are pinned to **4.3.3**. `npm run dev:css` watches UI
changes. The Python service serves the committed `dist/app.css`; it does not
compile CSS or contact a CDN at runtime. Fontsource packages supply locally
copied DM Sans Variable and Space Grotesk Variable fonts, including their licenses.

## Ownership

| Source | Owns |
| --- | --- |
| `styles/app.css` | Single Tailwind entry, explicit HTML/JS scan paths, font-face setup |
| `styles/tokens/colors.css` | Semantic surfaces/text, status and topic colors |
| `styles/tokens/typography.css` | Font families and text sizes/line heights |
| `styles/tokens/layout.css` | Four-pixel spacing scale, shared frame dimensions and panel radius |
| `../dist/ui.js` | Complete utility-class recipes and reusable report rendering helpers |
| `../dist/app-shell.js` | Shared navigation, frame and active-page state |
| `../dist/report-pages.js` | Shared, data-free Learning/Accounting page definitions |
| `../scripts/render-ui-shell.mjs` | Initial HTML frame and report placeholders, using the same pure helpers as the browser |
| `../dist/*.html`, `../dist/*.js` | Component presentation through Tailwind utilities |

## Navigation and first paint

The build pre-renders the shared shell on every page and the report layout on
Learning/Accounting. Edit report definitions/helpers rather than the generated
report sections in HTML. The renderer is idempotent. Font and module preload
hints are emitted in each page's head; the fonts are local assets.

`dist/boot.js` starts before body parsing. A Tailwind attribute variant briefly
cloaks the frame until page initialization and font readiness settle. A delayed
loading message avoids flashing a spinner for fast navigation. A three-second
fallback keeps navigation usable and hides uninitialized main content if startup
fails; a later successful initialization can recover. With JavaScript disabled,
the cloak is never activated and the styled static frame remains visible.

Same-origin navigation documents are prefetched during idle time unless Save-Data
is enabled. Hover, keyboard focus and touch warm the destination's page module.
These are browser hints, not a guarantee of zero network latency. Prefetching
does not read reports, run evaluations, contact providers or enable workers.
No Next.js migration is included; the pure shell/report rendering keeps that a
separate future framework choice.

Author utility classes in markup or shared rendering helpers. Keep complete class
names in source so Tailwind can detect them; use explicit maps for status/topic
variants. Do not add page-specific stylesheets, component CSS selectors, `@apply`
wrappers or alternate font/spacing scales. Keep shared containers at `max-w-page`,
`px-4 md:px-8`, `py-6 md:py-8`; headings use `text-title`, panel headings
`text-section`, body copy `text-body`, labels `text-xxs`, supporting copy
`text-caption`, cards `p-5`, and section gaps `gap-6`/`mb-6`.

Runtime geometry is distinct from static presentation: canvas/WebGL drawing,
projected orbit label coordinates and measured portfolio exposure widths still
come from data. The health renderer reads its palette from the theme variables;
its HTML status labels use utility maps. Financial records and engine authority
must not be embedded in generated CSS or static previews.

Learning's `GET /api/learning/report` and Accounting's
`GET /api/accounting/report` serve verified saved snapshots for the current
application ledger and mode. Refresh reads cached files only. Learning exposes
counts, limitations and protected-window metadata, without protected outcome
bodies, receipt bodies, raw model prompts, new training, model calls or promotion.

## References used

Applied Brain's [responsibility-based token guidance](https://github.com/JFusco/brain/blob/eaa45472a1bb493bdcbd07657f123e5d957dcfab/knowledge/tailwind/responsibility-based-tokens.md)
from snapshot `eaa45472a1bb493bdcbd07657f123e5d957dcfab`, plus Tailwind's official
[theme](https://tailwindcss.com/docs/theme),
[customization](https://tailwindcss.com/docs/adding-custom-styles) and
[CLI](https://tailwindcss.com/docs/installation/tailwind-cli) documentation.
No conflict with ASTRAL's paper-only or frozen-experiment boundaries was found.
