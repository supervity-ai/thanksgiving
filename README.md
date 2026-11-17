# Supervity Thanksgiving — production build

This repo is the production asset source for the Thanksgiving 2026 Webflow page. The campaign uses a unique `.svtg-thx26` root namespace so its authored styles are isolated from Webflow and other site classes.

## Mobile updates

- Tom stays visible in the mobile hero, with tighter headline spacing and no automatic page jump when the game starts.
- The game hit area allows normal vertical page scrolling on touch screens.
- The “Less Busywork” section is hidden on phones only.
- Mobile gifts show two large, closed gift boxes; tapping one opens its offer after Tom’s scene transition.
- The gift-floor artwork runs edge-to-edge on mobile, with a larger Tom character.
- The card maker exposes only To, From, “Surprise me,” and the download action. Each page visit starts with a randomized card background, message, lettering, and illustration combination.
- Paragraph color and button/SVG sizing are explicitly set to prevent Webflow color inheritance and clipping.

## Build and preview

```sh
python3 scripts/build_webflow.py
python3 -m http.server 8000
```

Open `/preview/` on the local server. The build requires Node/npm for `esbuild` and `html-minifier-terser`. Generated `webflow-embeds/` snippets are in paste order; each is below Webflow’s 50,000-character limit.

## Production asset path

The Webflow head code and SVG fallback references use the assets in this repo:

`https://cdn.jsdelivr.net/gh/supervity-ai/thanksgiving@main/assets/`

The build refreshes the hosted `assets/thanksgiving.css` and `assets/thanksgiving.js`, Webflow embeds, and local preview from the authored files under `webflow/` and `scripts/`.
