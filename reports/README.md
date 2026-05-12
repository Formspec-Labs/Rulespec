# PKAF Validation Reports

This directory archives the per-batch validation reports produced during PKAF development. Each report documents one iteration of the shape-batch method: shapes added, fixtures validated, violations classified, patches applied, final clean state.

## Reading order

For the full provenance story, read in order:

1. **`v0.1-rc1-manifest.md`** — Initial release candidate. Establishes the spec, core shapes, four fixtures, and the multi-pass validation arc (251 → 14 → 0 violations across 1,183 triples).

2. **`batch1-shapes.md`** — Batch 1 shape design notes. Documents the initial design of `TrustZoneEligibilityShape`, `RelationshipAssertionShape`, evidence/attestation/adoption/authority shapes.

3. **`batch1.1-patches.md`** — Batch 1.1 shape patches. Eight patches addressing issues found in Batch 1 validation: trust zone matrix corrections, evidence-role refinements, applicability requirements, attestation decision extension URIs, scope extensions, adoption-scope string-or-IRI handling, authority-chain-hop predicate restriction, bridge-result remediation requirement.

4. **`batch2-validation-report.md`** — ConceptRegistry shapes. Adds 11 shapes covering registered concepts, local concepts, mappings, applicability, resolution, lifecycle, conflicts, consumer registration. Arc: 7 → 0 violations.

5. **`batch3-validation-report.md`** — Lifecycle packet shapes. Adds 7 shapes covering all four lifecycle packet types, revalidation events, point-in-time exceptions. Arc: 2 → 0 violations. Explicitly preserves the cascade-correctness-is-runtime boundary.

6. **`batch4-validation-report.md`** — Generated artifact justification shapes + the pySHACL discovery. Adds 5 consumer-overlay shapes. Discovers that `sh:if`/`sh:then` patterns don't evaluate reliably in pySHACL 0.31.0; rewrites 8 conditional shapes across all prior batches using Pattern C; surfaces and patches 6 latent fixture defects. Arc: 0 → 6 → 0 violations.

7. **`v0.1.1-release-manifest.md`** — The combined v0.1.1 release manifest. Final SHA-256 hashes, conformance signature (1,206 triples, 0 violations), full per-shape coverage matrix with 4 accepted coverage gaps, synthetic defect coverage table, runtime conformance test layer outline.

## What the reports preserve

These reports are kept in the repo (rather than treated as ephemeral notes) because they preserve:

- **Decision provenance.** When an external reviewer asks "why does AuthorityChainHopShape forbid `implements`?", the answer is in `batch1.1-patches.md` patch 7.

- **Iteration discipline as documentation.** The shape-batch method described in `CONTRIBUTING.md` is grounded in these concrete examples.

- **The pySHACL discovery.** Batch 4 is the most consequential report — it documents how a real validation gate found and fixed problems the v0.1-rc1 freeze had been carrying. The report serves as a worked example of what synthetic defect testing accomplishes.

- **Accepted coverage gaps.** Each gap is justified in the report that first noted it. The justifications stay accessible to anyone considering whether to "force-fit" a fixture to satisfy coverage.

## Format conventions

Each batch report follows the same structure:

1. **Executive summary** — Status, baseline, key statistics
2. **Shape additions** — What was added, with spec section anchors
3. **What the batch does NOT enforce** — The structural-vs-behavioral boundary
4. **Classification of initial violations** — Each violation tagged with category and root cause
5. **Patches applied** — Each patch addresses a specific classified violation
6. **Coverage matrix** — Per-shape fixture coverage
7. **Coverage gaps flagged** — With justification
8. **Triple count drift** — Before/after
9. **Deliverables with hashes** — SHA-256 for reproducibility
10. **What the batch establishes** — Functional invariants now structurally enforced
11. **What remains as future work** — Deferred items per editorial discipline
12. **Reproducibility** — Commands to re-run validation

New batch reports should follow the same format.
