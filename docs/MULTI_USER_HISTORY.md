# Landline — Multi-User Transport History

This document is the durable history of Landline's multi-user transport work. It supplements `docs/CURRENT.md`, which should remain concise.

The source code and live branch state remain authoritative. This history records why the current branches exist, what was attempted, what has been runtime-tested, and what remains unproven.

## Starting point — proven one-to-one baseline

The stable macOS `main` baseline uses protocol v1 (`landline-iroh-audio/1`) with one remote Iroh session at a time.

Before multi-user work began, the following were already proven:

- Mac ↔ Mac two-way PTT/audio;
- Mac ↔ Mac operation across separate networks, including a phone hotspot case;
- macOS ↔ NixOS one-to-one interoperability;
- persistent Iroh endpoint identity;
- local profile/avatar exchange over the Hello payload;
- no-peer PTT behavior on macOS.

The product UI already reserved seven remote dial positions, but the transport supported only one connected remote peer.

## Add User became the entry point for group work

The approved V22 Add User interaction was implemented on `feature/macos-add-user` before group transport work.

That branch connected a pasted Iroh endpoint ID from the selected empty dial slot and preserved the selected slot for the connected peer. It provided the UI path required to test more than one remote participant.

## 2026-09-08 — protocol v2 / direct mesh branch

Multi-user transport work moved to `feature/macos-multi-user`, stacked on the Add User work so the earlier two-person checkpoint remained available.

The branch deliberately changed the macOS ALPN from:

`landline-iroh-audio/1`

to:

`landline-iroh-audio/2`

Protocol v2 keeps the existing frame header, Hello/profile payload, PTT/audio packet layout and ping/pong encoding, and adds message kind `7` (`membership`).

The intended topology is a full direct peer mesh rather than a permanent host:

- each remote peer owns an independent `PeerSession` and bidirectional QUIC stream;
- manually adding a peer should not intentionally disconnect existing peers;
- membership frames share known endpoint IDs;
- newly discovered peer pairs use a deterministic endpoint-ID rule to decide which side initiates the mesh edge;
- duplicate simultaneous connections are resolved deterministically so both Macs keep the same physical session;
- local PTT begin/audio/end frames are broadcast to every connected direct peer;
- one failed peer session is intended not to collapse the other sessions;
- product capacity remains one local participant plus seven remotes.

Because the ALPN changed, the current v2 macOS branch is intentionally not compatible with the current v1 NixOS client. NixOS parity is deferred until macOS group behavior is runtime-proven.

## Group speaker arbitration

The v2 branch also introduced distributed one-speaker-at-a-time arbitration.

- A client does not begin local PTT when it already knows a remote speaker owns the floor.
- If two users start PTT before either sees the other's `pttBegin`, the lexicographically lower endpoint ID wins.
- A losing local sender stops local capture/talking state and broadcasts `pttEnd`.
- Receivers play audio only from the currently selected speaker session and ignore competing audio packets.

This avoids a central floor server, but it still requires real multi-machine runtime validation.

## 2026-09-08 to 2026-09-10 — compile/build validation and UI integration

The v2 transport completed repeated Apple Silicon arm64 Release builds on GitHub's macOS runners while group transport, duplicate-session handling, Add User UI and UI-polish changes were combined.

A packaged test build was produced on 2026-09-10 from application source at commit:

`0e0372d75c904c4780dd314418165cf1e0a7476f`

The branch later removed the temporary packaging workflow without changing application source; the resulting `feature/macos-multi-user` head was:

`71d9f57222d24d1c558287c91d9a3afd4b49b8f9`

At that stage the implementation was compile/package validated but had not yet passed a three-or-more-Mac runtime test.

## First three-Mac runtime test — failure discovered

The first test across three macOS machines exposed the main blocking defect:

1. the tester added user A;
2. A appeared on the dial;
3. the tester then added user B;
4. A disappeared / was dropped when B joined;
5. as a result, a real three-way audio test could not proceed.

A second defect was discovered at the same time:

- a user without a custom avatar appeared as a blank grey dial circle instead of using the default toy/Buddha avatar.

This test changed the status of v2 from “awaiting 3+ client validation” to “3-client validation attempted and failed before three-way audio could be meaningfully tested.”

## Root causes addressed in the repair branch

The repair was isolated on:

`feature/macos-multi-user-fix`

This branch was created from `feature/macos-multi-user` so the previous test branch remained intact for comparison.

### Participant/session retention repair

The original v2 code treated a failed peer session too much like a participant leaving the Landline. During mesh convergence, a transient stream/session failure could immediately clear that participant's dial slot. In practice this could make A appear to be replaced by B while a new peer was being added.

The repair changes that model:

- desired group membership is tracked separately from the currently healthy QUIC session;
- a failed direct session no longer immediately removes the participant from the dial;
- failed peers are retried with bounded reconnect attempts/backoff;
- the participant remains in the same dial slot while reconnect is attempted;
- only after repeated reconnect failure plus a grace period is the participant removed;
- reconnect/removal tasks are cancelled when the peer successfully reconnects;
- a full local disconnect still clears the entire desired group and pending retry state.

This is intended to make mesh convergence/session repair resilient enough that adding B does not evict A.

### Default avatar repair

The Swift UI already expected a named image called `ToyBuddha`, but that image was not actually bundled in the macOS target. `NSImage(named: "ToyBuddha")` therefore returned no image and the dial fell back to a blank grey circle.

The repair adds the canonical web-prototype toy-face image to the macOS asset catalog as `ToyBuddha`, so both local and remote users whose Hello profile declares `avatarKind = "default"` can render the intended fallback image without transmitting duplicate image bytes.

## 2026-09-14 — repair build validated

The repair completed an Apple Silicon Release compile, explicit asset-catalog verification, ad-hoc signing and ZIP package verification.

Validated repair source commit:

`3756e1ef863592ac7cf6064f9c723aca507e844a`

Branch:

`feature/macos-multi-user-fix`

The corresponding test artifact was named:

`LandlineMac-MultiUser-Fix-Test-2026-09-14`

Important distinction: this proves the repaired source compiles/packages correctly. It does **not** yet prove that the A → add B → retain A behavior works on real Macs.

## Current validation state

As of the latest recorded work:

- protocol v1 one-to-one remains the proven stable/cross-platform baseline;
- protocol v2 direct-mesh macOS transport is implemented on the feature branches;
- the first three-Mac v2 test failed because the first participant was dropped when the second was added;
- the participant-retention/session-reconnect repair is implemented and build-validated on `feature/macos-multi-user-fix`;
- the default `ToyBuddha` fallback is implemented and build-validated on the same repair branch;
- the repaired branch still requires a repeat three-Mac runtime test before multi-user transport can be called working;
- Linux/NixOS should remain on v1 until macOS v2 is sufficiently runtime-proven.

## Next runtime test

Use the repaired macOS build on all three machines and test in this order:

1. Mac A adds Mac B and B remains visible/connected.
2. Mac A adds Mac C and B remains present while C occupies another slot.
3. Confirm all three Macs converge on the same three participants.
4. Confirm a no-custom-avatar participant shows `ToyBuddha`, not a grey blank.
5. Test A → B+C PTT/audio.
6. Test B → A+C PTT/audio.
7. Test C → A+B PTT/audio.
8. Quit or disconnect one peer and confirm the remaining pair stays connected.
9. Reconnect that peer and confirm its dial identity/slot recovers cleanly.
10. Exercise near-simultaneous PTT and verify the group converges to one speaker without mixed playback.
11. Repeat across separate networks where practical.

If this passes, the repair should be folded back into the active macOS multi-user line and the continuity/protocol documents updated from “experimental/failing” to the new proven state. Only then should Linux/NixOS protocol-v2 parity become the next transport step.
