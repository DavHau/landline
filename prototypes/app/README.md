# Canonical Landline Web Prototype

This directory contains the current full browser prototype used to validate Landline UI flows before they are implemented in the native clients.

## Current version

**LANDLINE browser prototype V22** remains the canonical baseline in `index.html`.

V22 is based on the established V21 browser prototype and adds the approved **Add Users** flow while retaining the existing profile, PTT, status, volume, VU and avatar interactions.

Open `index.html` directly in a modern browser for the V22 baseline.

A focused **Dial Groups / Create a dial** prototype is now available in `group-creation.html`. It is based on the current group-creation Figma section and is the active executable reference for the new dial-group navigation/creation work while that flow is being reviewed.

The latest approved review artifact is **Landline V23.13** (browser-ready ZIP handoff). Its source has not yet been merged into this directory, so `index.html` remains V22 and `group-creation.html` is older than the accepted review flow. Continue design review from V23.13 rather than regressing to the older focused page. Accepted V23.13 interaction details include: app → sheet slides up; sheet → sheet swaps content in place; top-left back controls are 32 × 32 with 10 px radius and `#F3F3F3` hover background without scaling; and Saori’s Landline uses the supplied account/group SVG icons at 32 × 32 with 105% icon hover scale.

The current **V23.14 review build** is pending approval. Relative to V23.13, `Edit profile` and `Dial groups` now use top-left arrows back to `Saori’s Landline` instead of close buttons; back-arrow backgrounds are transparent at rest and `#F3F3F3` on hover; and the supplied Saori’s Landline menu icons use a 110% hover scale.

The current **V23.15 review build** adds Figma-matched member states for the group dials: Work people shows Fiona, Stuart and Matt; Family chat shows Yumie and Michiyo. The back-arrow hover is explicitly a solid `#F3F3F3` at 100% opacity, while the default state remains transparent. V23.15 preserves the established app → sheet slide-up and sheet → sheet in-place content-swap behavior.

## V22 Add Users flow

- Hover any empty dial slot to reveal the 56 px add-user state and the `Add someone to Landline` status message.
- Click an empty slot to open the Add / Invite sheet.
- The **Add someone** section accepts a Landline ID.
- Press Return after entering an ID to populate the selected slot with a prototype contact and close the sheet.
- The **Invite someone** section shows the local user's six-word Landline ID.
- **Copy Landline ID** copies that ID, briefly shows `Copied`, then closes the sheet.

## Dial Groups / Create a dial flow

Open `group-creation.html` directly in a modern browser.

The current prototype implements the two interactions defined in the Figma `Create group` section:

1. Click the top **Group title** to open the dial-title dropdown. Select **Saori, Matt** to switch the title and dial state to the Saori/Matt group.
2. Click the top-right **Dial groups** icon to open the **Dial groups** bottom sheet. Select **Create a dial** to transition to the **Create a dial** sheet.

The group list also includes the Figma placeholder groups **Work people** and **Family chat**. The create sheet includes the Landline-ID input, disabled/enabled `Add to Landline` state, `Cancel`, and `Next`; the prototype intentionally stops at this first create-dial step until the subsequent group-profile flow is explicitly taken into scope.

The group-creation prototype is intentionally self-contained so the proven V22 Add Users behavior in `index.html` is not regressed while the new navigation model is reviewed. Once the group flow is approved, integrate the accepted interaction into the full canonical app prototype rather than maintaining two divergent implementations.

`README.txt` is retained as the source notes supplied with V22, and `ASSET-SOURCES.txt` records prototype asset provenance.

## Structure

The prototype is deliberately lightweight and self-contained:

- `index.html` — canonical V22 markup, prototype state and interaction logic
- `styles.css` — V22 layout and visual styling
- `group-creation.html` — focused Dial Groups / Create a dial interaction prototype
- `assets/` — local SVG and PNG assets
- `README.txt` — supplied version notes
- `ASSET-SOURCES.txt` — asset-source notes

No package manager, build step, framework, CDN or external runtime dependency is required.

## Feature handoff

For new Landline UI work:

1. design/idea is explored and validated in the web prototype;
2. approved behavior is recorded here when it is not obvious from the interaction itself;
3. implement the approved behavior in `LandlineMac/`;
4. runtime-test it on macOS;
5. implement corresponding Linux/NixOS parity work;
6. validate cross-platform behavior where applicable.

The **Add Users** flow established this prototype → macOS → NixOS handoff workflow. The Dial Groups / Create a dial prototype now follows the same process.
