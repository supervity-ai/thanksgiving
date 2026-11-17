# Supervity Thanksgiving 2026 — Final

Responsive Thanksgiving campaign page for Webflow, based on the latest `teest-supervity` illustration palette. The illustration accents use blue, green, and gold while the existing headline and button palette stays warm and unchanged.

## Project layout

- `webflow/` — authored page fragments and head code.
- `webflow-embeds/` — generated, minified Webflow snippets in paste order. Each file is below Webflow's 50,000-character Embed limit.
- `assets/` — illustration assets plus hosted CSS and JavaScript.
- `preview/index.html` — locally assembled page with a stand-in navbar.
- `scripts/build_webflow.py` — regenerates bundles and the preview.
- `scripts/thanksgiving.base.css` — complete authored stylesheet, including all keyframes. The build derives the final hosted CSS and the two Webflow style embeds from this source.

## Build and preview

From the project root:

```sh
python3 scripts/build_webflow.py
python3 -m http.server 8000
```

Open `http://localhost:8000/preview/` to preview. Build requires Node/npm so `npx` can run `esbuild` and `html-minifier-terser`.

The generated `webflow-embeds/` files are in paste order:

1. `01-head.html` — page head.
2. `02-styles-a.html`, `03-styles-b.html` — styles.
3. `04-content-a.html`, `05-content-b.html`, `06-content-c.html` — page content.
4. `07-scripts.html` — page scripts.

Use the real Webflow navbar; the optional mock navbar and promo bar are hidden. The real `.w-nav` is layered above campaign sections (`z-index: 10001`); all campaign dialogs/popups are layered above it (`z-index: 999999`), with the Section 05 dimmer just below its card (`999998`). The campaign hero has responsive top spacing (12rem, with 13rem in the 992–1199px range). The Section 05 downstairs floor is explicitly kept full-size so the complete two-floor office/lobby scene can render.

## Asset hosting

`webflow/00-page-head-code.html` is configured to load assets from the intended public GitHub/jsDelivr location:

`https://cdn.jsdelivr.net/gh/vishaltestin/supervity-thanks-giving-final@main/assets/`

That URL will only serve files after this project is published to that public repository. For local preview, the build swaps the base URL to local `assets/` paths.

## Palette and scope

The updated illustration colors are included; headline, button, and text colors are retained. The real site navbar remains visible; optional campaign mock chrome is hidden. No Webflow publish is performed by this project build.
