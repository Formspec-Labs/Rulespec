# Rulespec Studio Profile

This directory publishes the WOS Studio (Authoring) schema profile under the
Rulespec namespace.

The current cutover is intentionally conservative:

- `schema-source/` is the canonical Studio profile payload inside Rulespec.
- `schemas-derived/` is generated from `schema-source/` by `derive.sh`.
- `policy-studio/schemas-derived` points at `schemas-derived/`.
- `policy-studio/schemas/` is frozen historical input from before the
  Rulespec cutover.

The top-level schema set contains the 18 current Studio authoring schemas. The
`api/` subdirectory carries the six frontend API schemas because the Studio
schema tests load them into the same Draft 2020-12 registry.

This is a source-control cutover first: Studio consumes a Rulespec-owned schema
surface and the SNAP compiler output is pinned by a byte-identical gate. A later
projector upgrade can replace the identity derivation in `derive.sh` with a
richer Formspec/CUE projection as long as the derived schemas and SNAP gate stay
stable.

This profile publication is not a Studio L3 conformance declaration. Studio
still needs the Rulespec overlay-emission and overlay-grounded lint work before
it can honestly file the L3 partner disclosure.
