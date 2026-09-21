LANDLINE browser prototype V23.17 — Create Group flow

V23.16 is the current cumulative browser prototype on the web-prototype branch.

CORE TRANSITION RULE
- App → sheet: the first sheet slides up from the bottom.
- Sheet → sheet: the sheet container stays in place and the content swaps directly. No new bottom-up entrance animation is replayed.

V23.16 CHANGES
- Edit profile and Dial groups use top-left back arrows to return to Saori's Landline.
- Back-arrow controls are 32 x 32 with 10px radius.
- Back-arrow default background is transparent.
- Back-arrow hover background is solid #F3F3F3 at 100% opacity, with no scaling.
- Saori's Landline uses supplied account-square and group-add SVG icons with 110% icon-only hover scaling.
- Work people dial shows Fiona in pos-2, Stuart in pos-3, and Matt in pos-4.
- Family chat dial shows Yumie in pos-2 and Michiyo in pos-3.
- Fiona, Stuart, Yumie, and Michiyo dial avatars are refreshed from exact Figma crops at 4× resolution.
- Add someone and Create a dial group now share the current existing-member list: Matt, Fiona, Yumie, Michiyo, Stuart.
- Existing-member avatars now use local Figma-derived assets.

RETAINED BEHAVIOR
- 320 x 672 Landline shell and dial geometry.
- PTT, status, volume, VU, Profile and avatar interactions.
- Share your Landline ID and Add someone flows.
- Group-title dropdown and Dial Groups button.
- Create Group member selection, Landline ID entry, group profile, Saori/Matt group detail and edit.
- #323232 / 90% sheet backdrop.
- Corrected selected-circle tick alignment.

DESIGN REFERENCE
https://www.figma.com/design/cbBv0kCV29fX8h2QXbZNDk/SpacesOS-2026?node-id=4193-1036

Open index.html directly in a modern browser. No build step is required.


V23.17 main-sheet / dial-group-page refinements
- Saori’s Landline is now the 320 × 240 main sheet from Figma node 4221:1243.
- Choosing Edit profile or Groups expands the existing sheet surface from 240px to 584px; returning with the back arrow collapses it to 240px without replaying the app-to-sheet slide.
- Dial groups -> Work people now opens the Figma Dial group page Work people (node 4256:56204).
- Dial groups -> Family chat now opens the Figma Dial group page Family chat (node 4256:56231).
- Work people detail shows Fiona, Matt, Saori, and Stuart; Family chat detail shows Saori, Yumie, and Michiyo.
- Start dial on each detail page switches to the corresponding accepted dial state; Edit group profile reuses the existing profile-edit flow and returns to the originating group page.
