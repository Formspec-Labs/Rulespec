# Rulespec Batch 3 Validation Report

Status: **Batch 3 complete — clean validation**
Bridge contract: `rkaf-bridge/1.0`
Baseline: Rulespec v0.1-rc1 + Batch 2 (both accepted)

## Executive summary

Batch 3 adds seven lifecycle packet and revalidation shapes to the Core (Batch 1+1.1) and ConceptRegistry (Batch 2) shape sets. After one iteration cycle of evidence-driven patching (2 fixture additions), all four fixtures validate cleanly against the combined three-batch shape set.

| Run | Total violations | Local Op | Mapping | Statutory | Registry Failure |
|---|---|---|---|---|---|
| Initial Batch 3 | 2 | 1 | 0 | 1 | 0 |
| After 2 fixture patches | **0** | **0** | **0** | **0** | **0** |

```
Rulespec CI validation gate — mode: batch3
  Rulespec Core + ConceptRegistry + Lifecycle (Batch 3)
============================================================

[1/3] Environment check
  pyshacl 0.31.0 OK
  shapes:  shapes/rkaf-shapes-core-v0.1.ttl
  shapes:  shapes/rkaf-shapes-conceptregistry-v0.1.ttl
  shapes:  shapes/rkaf-shapes-lifecycle-v0.1.ttl

[2/3] Per-fixture validation
  [PASS] local-operational-v0.2: 0 violations, 350 triples
  [PASS] mapping-v0.1: 0 violations, 319 triples
  [PASS] statutory-authority-v0.1: 0 violations, 294 triples
  [PASS] registry-failure-conflict-v0.1: 0 violations, 223 triples

[3/3] Summary
  Mode:       batch3 (Core + ConceptRegistry + Lifecycle)
  Triples:    1,186
  Violations: 0
  Result:     PASS
```

## 1. Batch 3 shape additions

Seven shapes added in `rkaf-shapes-lifecycle-v0.1.ttl`, anchored on Rulespec Core v0.1 §4:

| Shape | Spec section | Targets |
|---|---|---|
| `AmendmentPacketShape` | §4.4 | `rkaf:AmendmentPacket` |
| `RescissionPacketShape` | §4.4 | `rkaf:RescissionPacket` |
| `SupersessionPacketShape` | §4.4 | `rkaf:SupersessionPacket` |
| `MaterialRevisionPacketShape` | §4.4 | `rkaf:MaterialRevisionPacket` |
| `RevalidationEventShape` | §4.8 | `rkaf:RevalidationEvent` |
| `RevalidationClosureEventShape` | §4.8 | `rkaf:RevalidationClosureEvent` |
| `PointInTimeExceptionShape` | §4.6, §4.7 | `rkaf:PointInTimeException` |

All four packet shapes share the same minimum structural requirements (`emittedBy`, `effectiveDate`, `bridgeContractVersion`, `cascadeAlgorithm`) per the spec. Two shapes use SHACL Advanced conditional logic:

- **`RevalidationClosureEventShape`:** if `closureDecision = revalidatedWithSuccessor`, must reference at least one successor (`successorAssertion` singular OR `successorAssertions` plural for split cases).
- **`PointInTimeExceptionShape`:** `evaluationAnchor` accepts either the closed v0.1 enum OR a declared extension URI (per Rulespec Core §4.7 extension governance pattern).

## 2. What Batch 3 deliberately does NOT enforce

**Cascade closure correctness.** SHACL validates packet *structure*: required fields, correct types, enum membership, conditional requirements. It does NOT validate that:

- `affectedAssertions` actually contains the correct transitive closure under `CascadeClosureV1`
- `affectedWorkProducts` reflects the inverse-edge traversal from the source assertion
- `affectedAdoptions` includes all `LocalAdoption.targetAssertion` inverse edges
- `requiredRevalidationActions` enumerates all consumer-affecting transitions

Those are **runtime conformance tests**, asserted by fixture-specific expected output. They will be added as a separate test layer in a future batch; SHACL is the wrong tool for transitive closure correctness.

This is the explicit boundary Mike called out in the Batch 3 review:

> "SHACL can validate that a packet has emittedBy, effectiveDate, bridgeContractVersion, cascadeAlgorithm, requiredRevalidationActions, affectedAssertions / affectedWorkProducts / affectedAdoptions. But it cannot prove that CascadeClosureV1 actually computed the correct transitive closure. That should remain a runtime conformance test, not a structural shape."

Batch 3 honors that boundary.

## 3. Classification of initial violations

| Cluster | Count | Category | Root cause |
|---|---|---|---|
| `PointInTimeException` missing `retainsAssertion` | 2 | Fixture bug | Inline PIT blocks in `RevalidationEvent.retainedPointInTimeException` were abbreviated |

Zero shape over-strictness. Zero core ambiguities. Zero missing vocabulary. Zero intended-failure mismatches.

The same pattern continues: shapes catch real defects, fixtures need mechanical alignment.

### Detail

Both fixtures (local-operational v0.2 and statutory-authority v0.1) have a `rkaf:retainedPointInTimeException` field on their post-cascade RevalidationEvent. The packet-inline PIT exceptions (in `AmendmentPacket.pointInTimeExceptions[]` and `RescissionPacket.pointInTimeExceptions[]`) correctly carry `retainsAssertion`. The RevalidationEvent-inline PIT blocks were written more compactly and omitted `retainsAssertion`.

Per Rulespec Core §4.6, every PointInTimeException must be self-describing with `retainsAssertion`/`retainsWorkProduct`. The shape correctly enforces this. The fixtures needed the field added.

## 4. Patches applied

### 4.1 Local Operational Fixture v0.2

Patched `RevalidationEvent` for `req-002-postamend`. Inline PIT exception now carries `rkaf:retainsAssertion: req-002` matching the RevalidationEvent's `targetAssertion`.

### 4.2 Statutory Authority Fixture v0.1

Patched `RevalidationEvent` for `wos-verify-identity-postrescission`. Inline PIT exception now carries `rkaf:retainsAssertion: caa-42-identity-req-001` matching the RevalidationEvent's `targetAssertion`.

## 5. Coverage matrix

The seven Batch 3 shapes target types that appear across the fixtures:

| Shape | Local Op | Mapping | Statutory | Registry Failure |
|---|:---:|:---:|:---:|:---:|
| AmendmentPacketShape | ✓ (1) | — | — | — |
| RescissionPacketShape | — | — | ✓ (1) | — |
| SupersessionPacketShape | — | — | — | — (gap) |
| MaterialRevisionPacketShape | — | — | — | — (gap) |
| RevalidationEventShape | ✓ (1) | ✓ (1) | ✓ (1) | — |
| RevalidationClosureEventShape | ✓ (1) | ✓ (1) | — | — |
| PointInTimeExceptionShape | ✓ (2) | — | ✓ (2) | — |

## 6. Coverage gaps flagged

Per the editorial discipline (no fixture force-fits to satisfy coverage):

- **`SupersessionPacketShape`** — no fixture target. Shape is correct but unbound. A future fixture that exercises full-document supersession (e.g., a regulation being replaced by a successor regulation) will naturally exercise it.

- **`MaterialRevisionPacketShape`** — no fixture target. Shape is correct but unbound. Material revisions are distinct from amendments and supersessions per Rulespec Core; no current fixture instantiates this packet type because the existing rescission and amendment paths cover the operational scenarios that matter for v0.1 conformance.

Both gaps follow the same accepted pattern as `ConceptMintingAuthorityShape` from Batch 2: keep the shape as a written-down constraint; do not force-fit fixtures to satisfy coverage vanity. The shapes will activate when any future fixture or production data instantiates the relevant packet type.

## 7. Triple count drift

| Fixture | Pre-Batch-3 | Post-Batch-3 | Delta | Cause |
|---|---:|---:|---:|---|
| local-operational-v0.2 | 349 | 350 | +1 | Added `retainsAssertion` to inline PIT |
| mapping-v0.1 | 319 | 319 | 0 | — |
| statutory-authority-v0.1 | 293 | 294 | +1 | Added `retainsAssertion` to inline PIT |
| registry-failure-conflict-v0.1 | 223 | 223 | 0 | — |
| **Total** | **1,184** | **1,186** | **+2** | — |

Both new triples are mechanical fixture patches: each PIT block gains one `retainsAssertion` edge.

## 8. Batch 3 deliverables

| Path | SHA-256 |
|---|---|
| `shapes/rkaf-shapes-lifecycle-v0.1.ttl` | `97363100b7e66a21700a42f7f983f853608e80a2895d9d004672bec14995515c` |
| `fixtures/context.jsonld` (v0.2, unchanged) | `e29452da358440595b3104ede35b6db37c31b1bf70bbc52b16801adac8930f96` |
| `fixtures/local-operational-v0.2.jsonld` (Batch 3 patched) | `9bd30054a1f110bcf39e2a6cb295a153d6f65116ce5d344558bedbdef13ba845` |
| `fixtures/statutory-authority-v0.1.jsonld` (Batch 3 patched) | `d556e85b5589aa23ae0028255e18d23880e0d1df2aeb945c37f6bd9b25285cb8` |
| `fixtures/mapping-v0.1.jsonld` (unchanged from Batch 2) | `573ab5b12d4e52e6a684c072d2408bda8b513a8a64acdf82f1dfb9920fe7529f` |
| `fixtures/registry-failure-conflict-v0.1.jsonld` (unchanged from Batch 2) | `e672540093d0e1891e12c41ce794221f74eb1d3aac78858223f6e63a2ff29f23` |
| `ci_validate.py` (multi-mode: core, batch2, batch3) | `4410223a0b75c60257dde7429c4bca1cc2bd8bbb5d7e84dec0acdff8445a6934` |

## 9. What Batch 3 establishes

Beyond v0.1-rc1 + Batch 2, the combined three-batch shape set now structurally enforces:

1. **Lifecycle packet completeness.** All four lifecycle packet types (Amendment, Rescission, Supersession, MaterialRevision) require `emittedBy`, `effectiveDate`, `bridgeContractVersion`, and `cascadeAlgorithm`. Without these four fields, a packet cannot be ingested by a bridge consumer.

2. **Bridge contract version pattern.** All packets must match the `rkaf-bridge/X.Y` version pattern; consumers refuse packets with mismatched or absent versions.

3. **RevalidationEvent must target something.** Every RevalidationEvent must reference at least one of `targetAssertion` or `targetWorkProduct`; an "untargeted" RevalidationEvent is structurally invalid.

4. **Revalidation closure must reference the open event.** `RevalidationClosureEvent.closesRevalidationEvent` is mandatory; closures cannot float independently of the event they close.

5. **Successor-on-revalidation pairing.** When a closure decision is `revalidatedWithSuccessor`, the closure event must reference at least one successor (singular or plural plural list); the spec's "successor" guarantee is now machine-enforced.

6. **PointInTimeException self-description.** Every PIT exception declares `evaluationAnchor` (closed enum or extension URI) AND at least one of `retainsAssertion` or `retainsWorkProduct`. A bare PIT exception with only a scope description and anchor is structurally invalid.

7. **Cascade algorithm declaration.** Every packet declares its `cascadeAlgorithm` (typically `rkaf:CascadeClosureV1`). Consumers refuse packets emitted by unrecognized algorithms. Structurally validated; algorithm output correctness remains a runtime test.

## 10. Conformance level — combined three-batch package

Combined Core + Batch 2 + Batch 3 shapes structurally enforce:

- **Rulespec Core v0.1 — structurally enforced.** All assertion, attestation, adoption, authority, evidence, and lifecycle structures from Rulespec Core §1-§5 have shape coverage.
- **ConceptRegistry-Core (v0.1.2 §10) — structurally enforced.**
- **ConceptRegistry-Lifecycle (v0.1.2 §10) — structurally enforced for packet structure** (Amendment, Rescission, ConceptLifecyclePacket from Batch 2 + Supersession/MaterialRevision shape stubs from Batch 3). Runtime cache TTL and cascade correctness remain bridge-implementation conformance.
- **ConceptRegistry-Federated (v0.1.2 §10) — partial.** Mapping conflicts with severity-conditional artifact binding (Batch 2). Cross-org sync semantics remain out of scope per v0.1 plan.

The package is now structurally complete for v0.2 release tagging once external review concludes.

## 11. What remains as future work

Per editorial discipline, deferred:

- **Batch 4 — Generated artifact justification shapes.** `GeneratedWorkProductJustificationShape`, `FormspecFieldJustificationShape`, `WOSStepJustificationShape`, full `BridgeValidationResultShape` enhancements. These validate the consumer-side justification packet structure.
- **Runtime conformance tests.** Cascade closure correctness, reducer output correctness, registry TTL behavior. These need a test layer beyond SHACL — likely fixture-specific expected-output JSON files that consumers diff against their actual output.
- **`JustificationChainHopShape`.** Allows `implements` as a hop predicate (distinct from `AuthorityChainHopShape` from Batch 1.1 patch 7 which forbids it). Needed when generated-artifact justification shapes are drafted.
- **SHACL-Core compatibility profile.** Currently the package requires SHACL Advanced Features. A core-compatible profile splits conditional shapes into multiple class-targeted shapes — substantial work, deferred unless implementer demand emerges.

## 12. Reproducibility

```bash
# Multi-mode CI gate — three conformance modes
python3 ci_validate.py --mode core      # v0.1-rc1: Core shapes only,         1,183 triples
python3 ci_validate.py --mode batch2    # Core + ConceptRegistry,             1,184 triples
python3 ci_validate.py --mode batch3    # Core + ConceptRegistry + Lifecycle, 1,186 triples (default)
```

Each mode is independently runnable. The `--mode core` invocation validates the v0.1-rc1 baseline; `--mode batch3` is the current default and reflects the full three-batch shape set against the current fixture state.

## Sign-off

Batch 3 lifecycle packet shapes are complete. The model continues to hold: all seven shapes validate cleanly across all four fixtures after evidence-driven patches. No new vocabulary added. No spec changes. The cascade-correctness boundary is honored — SHACL validates packet structure only; transitive closure correctness remains a runtime test.

This is the third proof point that Rulespec's discipline works. The pattern is now thoroughly established: write shapes anchored on spec sections, validate against fixtures, classify violations into the standard rubric, patch evidence-driven (always fixtures or context, never speculative spec additions), converge to clean validation.

Three batches, three iteration arcs, zero spec drift.
