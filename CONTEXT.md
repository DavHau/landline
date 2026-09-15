# Landline — Context Loader

This file defines the standard context-loading workflow for ChatGPT conversations about Landline.

## Shortcut

When the user's entire message is `Load project context`, load the current Landline project context from this repository before continuing.

Do not ask the user to restate project history that is already recorded here.

## Load order

1. Read `docs/CURRENT.md` first. Treat it as the concise continuity record and the primary statement of the current next step.
2. Read `README.md`.
3. Read the durable project documents:
   - `docs/PRODUCT.md`
   - `docs/ARCHITECTURE.md`
   - `docs/DESIGN.md`
   - `docs/DEVELOPMENT.md`
   - `docs/PROTOCOL.md`
4. If the task concerns multi-user/group transport, protocol v2, participant retention/reconnect, or the three-Mac test work, also read `docs/MULTI_USER_HISTORY.md` before changing transport code.
5. If the task concerns a UI flow or interaction that has been prototyped, inspect `prototypes/README.md` and the relevant source under `prototypes/app/` before changing native code. Use `prototypes/experiments/` only when an isolated experiment is directly relevant.
6. Inspect the current `main` source relevant to the next task.
7. If the task concerns Linux/NixOS or cross-platform interoperability, inspect the current `linux-nix` branch as well.
8. Check recent commits, branch heads and relevant CI state when necessary to understand changes made after the documentation was last updated.
9. If a current Figma frame is material to the task, use the Figma design as the visual source of truth rather than inferring intent from an older implementation screenshot.

## Current branch meaning

- `main` — current stable macOS working baseline plus canonical project continuity documentation and canonical web prototypes.
- `feature/macos-multi-user` — protocol-v2/direct-mesh macOS group work before the latest runtime repair.
- `feature/macos-multi-user-fix` — current macOS group repair branch; see `docs/CURRENT.md` and `docs/MULTI_USER_HISTORY.md` for validation status.
- `linux-nix` — active native Linux/NixOS port.

Do not assume one branch supersedes the others: `main` remains the proven stable baseline while feature branches may contain compile-validated but not yet runtime-proven work. Platform implementations are expected to remain deliberately versioned/wire-compatible when cross-platform parity is undertaken.

The preferred product-development sequence for new UI work is web prototype → macOS implementation/runtime validation → Linux/NixOS parity. This does not mean the browser prototype is a production Landline client; it is the executable interaction reference used before native implementation.

## Ground rules

- GitHub is the source of truth for implementation files.
- `docs/CURRENT.md` is the short continuity record, not a substitute for inspecting source when implementation details matter.
- `docs/MULTI_USER_HISTORY.md` is the durable chronology for group transport work; use it to avoid reconstructing that history from chat memory.
- Figma is the source of truth for intended visual design where a current design exists.
- For an approved new UI flow, the canonical browser implementation under `prototypes/app/` is the executable interaction reference to inspect before changing native clients.
- An isolated prototype under `prototypes/experiments/` does not become canonical behavior until its accepted result is integrated into `prototypes/app/` or otherwise recorded as an approved decision.
- `docs/PROTOCOL.md` records the cross-platform compatibility contract, but actual macOS/Linux source and relevant protocol-v2 feature branches must be checked before changing the wire format.
- Update `docs/CURRENT.md` when a meaningful milestone, technical decision, known issue, working baseline or next step changes.
- Update `docs/MULTI_USER_HISTORY.md` when a meaningful multi-user implementation/test milestone, failure, repair or validation result changes.
- Update the durable documents when their underlying product/design/architecture/development/protocol decisions change.
- Do not rely on chat memory as the primary project record. Chat/project history may supplement the repository but should not override newer repository evidence.
- Do not invent missing project history or prototype source. If the repository documentation/source does not support something, say so.
- Do not modify files merely because `Load project context` was invoked. Context loading is read-only unless the user also asks for a change.
- Do not reintroduce ZIP-file handoffs as the normal source workflow; work from the repository unless there is a specific diagnostic reason not to.

## Response after loading

Reply concisely with:

- confirmation that Landline context is loaded;
- the current web-prototype state when relevant;
- the current macOS stable baseline and any active feature/repair branch relevant to the task;
- the current Linux/NixOS implementation state when relevant;
- the current next step recorded in `docs/CURRENT.md`;
- any important mismatch between the documentation, branch heads, CI state or current source.

After that, continue normally with the user's request.
