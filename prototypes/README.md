# Landline Web Prototypes

This directory is the canonical repository home for Landline's browser-based interaction prototypes.

## Role in the product workflow

For new UI flows, the normal implementation sequence is:

1. design/idea in Figma or discussion;
2. implement and test the interaction in the web prototype;
3. agree the behavior and visual treatment;
4. implement the approved flow in the macOS app;
5. runtime-test the macOS implementation;
6. bring the Linux/NixOS app to behavioral and visual parity;
7. run cross-platform validation when networking or shared state is involved.

The web prototype is a design-validation implementation, not a production web version of Landline.

## Structure

- `app/` — the canonical full Landline web prototype.
- `experiments/` — focused experiments for isolated interaction/visual questions.

## Prototype principles

- Prefer plain HTML, CSS and JavaScript while sufficient.
- Do not add a framework/build system merely for convenience.
- Use supplied Figma/exported artwork where available rather than approximating distinctive assets.
- Keep the canonical prototype runnable with minimal setup.
- Record important accepted interaction decisions in the prototype README and durable project docs.
- Do not treat an experiment as canonical until its result has been accepted and integrated into `app/`.

## Source and delivery

**GitHub is the durable shared source of truth for prototype work.** When a prototype iteration is accepted or handed off for review, update the relevant source under `prototypes/app/` on this web-prototype branch so the team can access the same implementation.

A browser-ready `.zip` may also be produced for convenient local review. ZIPs are supplemental review artifacts, not a substitute for keeping the repository source current.

## Source of truth

Current Figma frames are the primary source of truth for visual intent. The canonical web prototype is the executable interaction reference for an approved flow before native implementation.
