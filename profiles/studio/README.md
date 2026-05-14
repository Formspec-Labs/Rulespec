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

Studio has filed an L2 + D3 conformance disclosure against this profile at
`../../conformance/partners/policy-studio.yaml`. The matching report lives in
the partner submodule at `policy-studio/conformance-reports/L2-report.json`.
Overlay-emission (`wos-studio-compiler::rkaf_overlay`) and the overlay-grounded
lint tier (`wos-studio-lint::overlay_grounded`) have landed; the SNAP
byte-identical gate passes against the rebaselined `snap-baseline/`.

The L3 (Constraint) gate is intentionally deferred: `rkaf-validate` is JSON
Schema only, and L3 per `spec/rkaf-conformance.md` additionally requires SHACL +
Pattern-C cross-property invariants. The path to close is documented in
the partner YAML's `provisional.l3_path` block.

The disclosure carries other explicit provisional notes — warrant chain is
provisional until Stage-8 wires `SourceAuthority` records; per-assertion
`AccessScope` classification (HIPAA-PHI / GDPR-PII) defaults to
`rkaf:organizationVisible` pending Stage-8 source-classification surfacing.
These provisional gaps are disclosed in both the partner YAML and the
conformance report.
