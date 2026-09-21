# Canonical Landline Web Prototype

This directory contains Landline's current full browser prototype used to validate UI flows before native implementation.

## Current version

**LANDLINE browser prototype V23.16** is the current canonical browser prototype on the `chore/web-prototype-workflow` branch.

Open `index.html` directly in a modern browser. No package manager or build step is required.

V23.16 evolves the V22 baseline cumulatively. It preserves the established 320 × 672 Landline shell, Profile, PTT, status, volume, VU, avatar, Add User, Share ID, and existing dial behavior while adding the reviewed Dial Groups / Create Group flows.

## Sheet transition convention

This is an established Landline interaction rule:

- **App → sheet:** the first sheet slides up from the bottom.
- **Sheet → sheet:** keep the sheet container in place and replace the content directly. Do not replay the bottom-up entrance animation.

## V23.16 group behavior

- Top group dropdown: Home dial / Saori, Matt / Work people / Family chat.
- Dial Groups button opens Saori's Landline.
- Saori's Landline provides Edit profile and Groups.
- Edit profile and Dial groups use a top-left back arrow to return to Saori's Landline.
- Back arrow: 32 × 32, 10 px radius, transparent by default, solid `#F3F3F3` at 100% opacity on hover, no hover scaling.
- Saori's Landline account/group icons use the supplied SVG artwork with 110% icon-only hover scale.
- Work people dial shows Saori + Fiona + Stuart + Matt, using refreshed 4× Figma avatar exports for Fiona and Stuart.
- Family chat dial shows Saori + Yumie + Michiyo, using refreshed 4× Figma avatar exports for Yumie and Michiyo.
- Add someone and Create a dial group use the current Figma existing-member list: Matt, Fiona, Yumie, Michiyo, Stuart, with local avatar assets.
- Create Group includes existing-member selection, Landline ID entry, group profile creation, and the existing Saori/Matt group detail/edit flow.
- Member selection circles use the corrected centered tick treatment.
- Bottom-sheet backdrop remains `#323232` at 90% opacity.

## Design reference

Figma Create Group section:

https://www.figma.com/design/cbBv0kCV29fX8h2QXbZNDk/SpacesOS-2026?node-id=4193-1036

Relevant current frames include:

- `4252:1422` — Work dial page
- `4252:1521` — Family chat dial page
- `4221:1243` — Saori's Landline
- `4227:1422` — Edit profile
- `4184:1129` — Dial groups
- `4227:1361` — Create a dial group
- `4242:1336` — Enter a Landline ID for group creation
- `4183:1565` — Create dial group profile
- `4183:1457` — Saori & Matt group page
- `4242:1349` — Dial group profile edit
- `4242:1289` — Selected circle states

## Structure

- `index.html` — complete prototype markup
- `styles.css` — visual styling and geometry
- `app.js` — interaction/state logic
- `assets/` — local prototype assets
- `README.txt` — review notes
- `ASSET-SOURCES.txt` — asset provenance

## Working convention

GitHub is the durable shared source of truth for web prototype work. Browser-ready ZIP files may still be produced as convenient review artifacts, but they are supplemental; accepted prototype work should be committed here so the whole team can access it.
