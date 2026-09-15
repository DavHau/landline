# Landline — Current State

This is the concise continuity record for active Landline work. Update it whenever a meaningful milestone, technical decision, known issue, working baseline or next step changes.

Last consolidated: 2026-09-15.

## Repository / branch roles

Repository: `mattatgit/landline`

- `main` — canonical stable macOS SwiftUI/AppKit + Iroh v1 baseline, canonical V22 browser prototype and continuity docs.
- `feature/macos-add-user` — native macOS Add User work based on the approved V22 flow.
- `feature/macos-multi-user` — macOS protocol-v2/direct-mesh group transport before the latest runtime repair.
- `feature/macos-multi-user-fix` — current macOS group repair branch; retains participants across transient session failure and restores the default ToyBuddha avatar.
- `linux-nix` — active native Rust/NixOS port; currently protocol v1/one-to-one.

GitHub is the durable source of truth. Do not return to ZIP-based source handoffs as the normal development workflow.

For the detailed chronology of the group transport work, read `docs/MULTI_USER_HISTORY.md`.

## Prototype-first product workflow

Landline uses this sequence for new UI flows:

1. explore/design in Figma or discussion;
2. implement and test the interaction in the browser prototype;
3. agree the behavior and visual treatment;
4. implement the approved flow in macOS;
5. runtime-test macOS;
6. bring Linux/NixOS to behavioral/visual parity;
7. run cross-platform validation where networking/shared state is involved.

Repository locations:

- `prototypes/app/` — canonical full Landline browser prototype;
- `prototypes/experiments/` — isolated interaction/visual experiments.

The browser prototype is a design-validation implementation, not a production web client.

### Canonical browser prototype

Landline V22 is committed under `prototypes/app/` and remains the executable interaction reference for the approved Add User flow. It includes empty-slot hover, Add/Invite sheet, Landline-ID entry, copy-ID feedback, Profile, PTT, status, volume, VU and avatar interactions.

## Stable macOS baseline — `main`

The stable macOS implementation on `main` is the integrated SwiftUI/AppKit + Iroh baseline historically called Landline Iroh Spike V10.

Established behavior includes:

- fixed 320 × 672 custom window with native glass/backdrop treatment;
- local user fixed at 12 o'clock and seven remote dial positions;
- persisted local Profile name/avatar;
- press-and-hold PTT, status panel, volume and VU meter;
- persistent Iroh endpoint identity;
- protocol v1 (`landline-iroh-audio/1`) one-to-one Iroh transport;
- Iroh direct/relay selection managed by Iroh;
- Iroh diagnostics in macOS Settings;
- older `RelayClient` retained only as fallback/reference.

### Proven v1 networking

- Mac ↔ Mac two-way audio is proven.
- Mac ↔ Mac cross-network audio worked with one laptop on a phone hotspot and the other on a separate network.
- macOS ↔ NixOS connection by endpoint ID and two-way PTT/audio worked on 2026-09-03.

Protocol v1 remains the proven stable/cross-platform baseline while protocol-v2 group work is validated.

Known audio issue: occasional brief crackling can occur around PTT start; most audio is otherwise clear. Investigate capture/playback/buffering/device-format boundaries before changing the PCM packet format.

## Native Add User — `feature/macos-add-user`

The approved V22 Add User flow has been implemented natively in Swift.

Behavior includes:

- empty dial positions expose the Add User hover/plus treatment;
- status bar changes to `Add someone to Landline` while hovering an empty position;
- clicking an empty position opens the Add/Invite bottom sheet;
- entering a real Iroh endpoint ID and pressing Return uses the Iroh connection path;
- the connected peer is assigned to the dial position selected by the user;
- the user's local endpoint ID can be copied from the sheet;
- existing Profile/PTT behavior is preserved.

This work became the UI entry point for the macOS multi-user transport experiments.

## macOS multi-user transport — protocol v2

The group implementation lives on `feature/macos-multi-user` and the latest repair lives on `feature/macos-multi-user-fix`.

Protocol v2 uses:

`landline-iroh-audio/2`

It deliberately adds group semantics while keeping the proven v1 frame layout, Hello/profile payload, PCM audio packet format and ping/pong encoding. Message kind `7` carries membership endpoint IDs.

The topology is a full direct peer mesh:

- each remote endpoint has an independent `PeerSession` / QUIC stream;
- membership frames share known endpoint IDs;
- automatically discovered mesh edges use a deterministic endpoint-ID initiation rule;
- duplicate simultaneous peer connections are resolved deterministically;
- local PTT begin/audio/end is broadcast to every connected direct peer;
- product capacity remains local user + seven remotes;
- group speaker arbitration uses a deterministic endpoint-ID tie-break rather than a central floor server.

The current NixOS client remains protocol v1 and is intentionally not wire-compatible with the v2 macOS branch yet.

### First three-Mac test — blocking failure found

A first runtime test across three macOS machines was attempted before three-way audio could be meaningfully exercised.

Observed sequence:

1. add user A;
2. A appears;
3. add user B;
4. A is dropped/replaced as B joins.

This meant the build could not maintain three participants simultaneously, so the core three-way PTT/audio behavior was not yet testable.

The same test also exposed a profile-display defect: a participant without a custom avatar appeared as a blank grey dial circle instead of the default toy/Buddha avatar.

### Latest repair — `feature/macos-multi-user-fix`

The repair branch changes participant/session handling so transient direct-session failures do not immediately evict a participant from the dial.

Current repair behavior:

- desired group membership is tracked separately from a currently healthy session;
- failed peer sessions no longer immediately clear the participant slot;
- direct-session reconnect is retried with bounded backoff;
- a participant remains in the same dial slot while reconnect is attempted;
- only repeated reconnect failure plus a grace period removes the participant;
- successful reconnect cancels pending removal/retry state;
- a full local disconnect still clears the entire group and retry state.

The default-avatar defect was also repaired by adding the canonical prototype toy-face image to the macOS asset catalog as the named `ToyBuddha` image expected by the Swift UI.

Validated repair source commit:

`3756e1ef863592ac7cf6064f9c723aca507e844a`

The repair completed Apple Silicon arm64 Release compile, asset verification, ad-hoc signing and ZIP package verification. This is build validation only; the repaired participant-retention behavior still requires a repeat real three-Mac runtime test.

Detailed history and the exact validation sequence are in `docs/MULTI_USER_HISTORY.md`.

## Linux/NixOS baseline — `linux-nix`

The native Linux client lives under `LandlineNix/` and uses Rust 1.91, Iroh 1.0.2, eframe/egui, CPAL and Rodio.

Current Linux behavior includes:

- same 320 × 672 layout basis and custom window controls;
- shared Landline title/profile/PTT artwork;
- embedded Inter + Inter Tight;
- persistent Iroh endpoint identity;
- protocol v1 one-to-one PTT/audio;
- local profile name/avatar persistence;
- Profile sheet and image selection/drop;
- avatar exchange through the v1 Hello/profile payload;
- Nix flake and locked dependency set.

The current `linux-nix` CI baseline is green at the last recorded branch head and real macOS ↔ NixOS v1 audio is proven.

Do not attempt a v2 Mac ↔ v1 Nix connection and interpret failure as a regression: the ALPN difference is intentional. NixOS should move to Add User + v2 group semantics only after macOS group behavior is runtime-proven.

## macOS regressions / outstanding checks

### Traffic-light drift repair

The replacement traffic-light architecture completed Apple Silicon Release compile/package/signature validation on 2026-09-07. Longer real-Mac validation remains pending for placement, hover/inactive appearance, close/minimize/green-button behavior, fixed-size behavior, appearance/sleep/display stability and long-running drift recurrence.

### No-peer PTT

Fixed and runtime-confirmed 2026-09-04. Endpoint-online users can hold PTT with zero peers; capture/VU/talking state remain active while network sends simply have no destinations.

### First microphone permission path

The Swift 6 permission crash is fixed in source using:

`await AVCaptureDevice.requestAccess(for: .audio)`

A first-permission real-Mac re-test after resetting microphone permission remains pending.

### Packaging

The current macOS distributable target is Apple Silicon arm64, macOS 15+. Pinned `iroh-ffi` 1.1.0 does not provide the required x86_64 macOS slice. Do not label current builds Universal.

Ad-hoc signing is appropriate for test builds, not release notarization.

## UI conventions to preserve

- local user stays at 12 o'clock;
- PTT is press-and-hold;
- no-peer PTT remains allowed while the endpoint is online;
- suppress remote speaking indicators while local user is talking;
- speaking badge uses four centered animated bars in a 24 × 24 green circle;
- status text uses Medium weight;
- muted PTT hover may say `Click to talk` but must not swap the muted icon to active;
- Profile button hover scales the whole 24 px control;
- Profile opens Profile; networking settings belong in Settings/app menu;
- preserve established sheet geometry/hierarchy first;
- macOS traffic lights use caller-owned native standard buttons at the established Figma centres;
- for Add User behavior, use `prototypes/app/` V22 plus current Figma as the executable/visual reference.

## Design reference

Primary Figma prototype reference:

`https://www.figma.com/proto/cbBv0kCV29fX8h2QXbZNDk/SpacesOS-2026?node-id=3911-102362&p=f&viewport=-1105%2C1488%2C0.5&t=zjZbXgJbbsOfVRT9-1&scaling=min-zoom&content-scaling=fixed&starting-point-node-id=3911%3A102362&page-id=3889%3A130618`

When implementation and visual intent disagree, inspect the relevant Figma frame and current canonical browser prototype before inventing a new treatment.

## Current next step

Repeat the macOS three-machine group test using the validated `feature/macos-multi-user-fix` build before merging or porting protocol v2.

Test in this order:

1. A adds B; confirm B remains present/connected.
2. A adds C; confirm B remains while C appears in another slot.
3. Confirm all three Macs converge on the same three participants.
4. Confirm a no-custom-avatar participant displays `ToyBuddha` rather than a blank grey circle.
5. Test A → B+C PTT/audio.
6. Test B → A+C PTT/audio.
7. Test C → A+B PTT/audio.
8. Disconnect/quit one peer and confirm the remaining pair survives.
9. Reconnect that peer and confirm participant/slot recovery.
10. Exercise near-simultaneous PTT and verify deterministic single-speaker convergence.
11. Repeat across separate networks where practical.

If this passes, fold the repair into the active macOS multi-user line, update the continuity/protocol status to the proven result, and only then move Linux/NixOS toward protocol-v2 parity.

The traffic-light longevity and first-microphone-permission regression checks remain outstanding and should not be lost while group work continues.
