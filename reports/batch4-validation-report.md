# Rulespec Batch 4 Validation Report

Status: **Batch 4 complete — clean validation, plus discovery and fix of v0.1-era SHACL evaluation bug**
Bridge contract: `rkaf-bridge/1.0`
Baseline: Rulespec v0.1-rc1 + Batch 2 + Batch 3 (all accepted)

## Executive summary

Batch 4 added five generated-artifact and bridge-justification shapes, and in the process **discovered that pyshacl 0.31.0 does not correctly evaluate `sh:if`/`sh:then` patterns**. Eight conditional shapes across Batches 1.1, 2, 3, and 4 — including some that were part of the v0.1-rc1 freeze — never actually fired in production validation. All eight have been rewritten using Pattern C (`sh:or` + `sh:not`), which pyshacl evaluates correctly. The rewrite surfaced six latent fixture defects that were hidden for the entire v0.1-rc1 era, and those are now patched.

| Run | Total violations | Total triples |
|---|---:|---:|
| Batch 4 initial (with new shapes, broken sh:if/sh:then still in effect) | 0 | 1,186 |
| After Pattern C rewrite of 8 conditional shapes | 6 | 1,186 |
| After 6 fixture defect patches | **0** | **1,206** |

```
Rulespec CI validation gate — mode: batch4
  Rulespec Core + ConceptRegistry + Lifecycle + Justification (Batch 4)
============================================================
  shapes:  rkaf-shapes-core-v0.1.ttl
  shapes:  rkaf-shapes-conceptregistry-v0.1.ttl
  shapes:  rkaf-shapes-lifecycle-v0.1.ttl
  shapes:  rkaf-shapes-justification-v0.1.ttl

  [PASS] local-operational-v0.2: 0 violations, 355 triples
  [PASS] mapping-v0.1: 0 violations, 320 triples
  [PASS] statutory-authority-v0.1: 0 violations, 307 triples
  [PASS] registry-failure-conflict-v0.1: 0 violations, 224 triples
                                       ──────────────────────
                                       0 violations, 1,206 triples
```

## 1. Batch 4 shape additions

Five shapes added in `rkaf-shapes-justification-v0.1.ttl`:

| Shape | Spec section | Targets |
|---|---|---|
| `GeneratedWorkProductJustificationShape` | Rulespec Core §6.1 | `rkaf:GeneratedWorkProduct` |
| `FormspecFieldJustificationShape` | Rulespec Core §6 | `formspec:Field` (conditional on overlay) |
| `WOSStepJustificationShape` | Rulespec Core §6 | `wos:WorkflowStep` (conditional on overlay) |
| `FullBridgeValidationResultShape` | Rulespec Core §5.2 | `rkaf:BridgeValidationResult` |
| `JustificationChainHopShape` | Rulespec Core §2.4 | `rkaf:JustificationChainHop` |

The shapes validate the Rulespec overlay only. They do NOT validate Formspec internals (field syntax, validation rules, display logic) or WOS internals (workflow runtime, routing, handoffs). The hard-won boundary between Rulespec and its consumers is preserved.

The key enforced rules:

1. **Every `rkaf:GeneratedWorkProduct` must declare `justifiedByAssertion` + `bridgeContractVersion` + at least one of `usageEligibility` or `proposedUsageEligibility`.** Rulespec-generated artifacts without justification metadata are not auditable.
2. **A `formspec:Field` or `wos:WorkflowStep` carrying any Rulespec overlay property** (`justifiedByAssertion`, `usageEligibility`, `proposedUsageEligibility`, `collectsEvidenceType`, `requiresEvidenceType`) **must also declare `bridgeContractVersion`.** Preexisting artifacts can carry Rulespec justification overlay without being typed as GeneratedWorkProduct (per Rulespec Core §6.1), but they must still preserve the bridge contract version so consumers can evaluate the overlay against a known contract.
3. **A `BridgeValidationResult` with `result=acceptedWithWarnings` or `result=rejected` must include at least one structured indicator** (`warnings`, `errors`, `ineligibleAssertions`, `unresolvedConcepts`, `registryUnavailable`, `registryVersionOutOfRange`, `staleDependencies`, `staleConceptCache`, `suggestedRemediation`, or `noRemediationReason`). Otherwise the result is unactionable.
4. **`JustificationChainHop.predicate` may include `rkaf:implements`** (distinct from `AuthorityChainHop` which forbids it). The implements predicate describes substantive realization, not authority transmission.

## 2. The pyshacl evaluation bug

The pattern `sh:if [...] ; sh:then [...]` is part of SHACL Advanced Features. It is documented as supported in pyshacl. But empirical testing during Batch 4 showed:

- **`sh:if + sh:then [ sh:property ... ]` (Pattern A):** MISSED defects in minimal test
- **`sh:if + sh:then [ sh:or (...) ]` (Pattern B):** MISSED defects in minimal test
- **`sh:or ( [sh:not [precondition]] requirement-branches... )` (Pattern C):** CAUGHT defects
- **`sh:sparql [...]` (Pattern D):** CAUGHT defects
- **`sh:or (...)` with sh:not inside property shape (Pattern E):** CAUGHT defects

Patterns A and B — both forms of `sh:if`/`sh:then` — fail to fire when the focus node violates the conditional requirement. This was verified with isolated minimal test cases and again with cross-batch synthetic defect injection.

The impact: **eight conditional shapes across Batches 1.1, 2, 3, and 4 were not functioning as designed for the entire v0.1-rc1 era.** Their constraints existed in the TTL files, parsed correctly, and reported PASS — but they did not actually evaluate the conditional logic against fixture data.

### Affected shapes

| Shape | Originally batched | Conditional logic |
|---|---|---|
| `BridgeValidationResultShape` | Batch 1.1 | rejected → remediation OR noRemediationReason |
| `OperationalAssertionEvidenceShape` | Batch 1.1 | R2/A3/P4 → hasEvidence |
| `AuthorityAssertionShape` | Batch 1.1 | A3 → authorityKind + hasApplicability + qualified evidence |
| `MappingAssertionShape` | Batch 2 | closeMatch + operational → MappingApplicabilityContext |
| `ConceptLifecyclePacketShape` | Batch 2 | split/merge/replacedBy → successorConcepts |
| `MappingConflictShape` | Batch 2 | operational/publicationBlocking severity → artifact reference |
| `RevalidationClosureEventShape` | Batch 3 | revalidatedWithSuccessor → successor reference |
| `FullBridgeValidationResultShape` | Batch 4 | acceptedWithWarnings/rejected → structured indicator |

### Pattern C rewrite

Each affected shape was rewritten from:

```turtle
sh:if [ <precondition> ] ;
sh:then [ <requirement> ] .
```

to:

```turtle
sh:or (
  [ sh:not [ <precondition> ] ]
  <requirement-branches-flattened>
) .
```

This is pure SHACL Core (no Advanced Features needed) and is reliably evaluated by pyshacl. The SEMANTICS are identical to the original intent: "if precondition holds, then requirement must be satisfied" becomes "either precondition does not hold, or requirement is satisfied."

For multi-requirement conditionals (e.g., A3 assertions requiring authorityKind + hasApplicability + qualified evidence), the requirement-branch uses `sh:and` to combine the multiple sub-requirements.

### Verification

Synthetic defect injection on all 8 patched shapes:

| # | Test | Result |
|---|---|---|
| 1 | OperationalAssertionEvidenceShape: R2 without hasEvidence | **CAUGHT** |
| 2 | AuthorityAssertionShape: A3 without hasApplicability | **CAUGHT** |
| 3 | AuthorityAssertionShape: A3 without authorityKind | **CAUGHT** |
| 4 | BridgeValidationResultShape: rejected without remediation | **CAUGHT** |
| 5 | MappingAssertionShape: closeMatch at operational without applicability | **CAUGHT** |
| 6 | ConceptLifecyclePacketShape: split without successorConcepts | **CAUGHT** |
| 7 | MappingConflictShape: operationalConflict without artifact | **CAUGHT** |
| 8 | RevalidationClosureEventShape: revalidatedWithSuccessor without successor | **CAUGHT** |
| 9 | FullBridgeValidationResultShape: non-accepted without structured indicator | **CAUGHT** |
| 10 | GeneratedWorkProductJustificationShape: missing justifiedByAssertion | **CAUGHT** |
| 11 | GeneratedWorkProductJustificationShape: missing bridgeContractVersion | **CAUGHT** |
| 12 | GeneratedWorkProductJustificationShape: missing both eligibility forms | **CAUGHT** |

12 / 12 caught. The shapes are now functioning.

## 3. The six latent fixture defects

After the Pattern C rewrite, validation produced 6 violations. All were classified as **fixture defects**, not shape over-strictness. Each is something the spec's prose required from day one but the broken SHACL never enforced.

### Defect 1: `amend-001` (local-operational) — A3 missing authorityKind and hasApplicability

The local amendment authority assertion was labeled `A3AuthorityCritical` but did not declare `authorityKind` or `hasApplicability`. Per Rulespec Core §3, A3 assertions must declare both.

**Patch:** added `authorityKind = rkaf:organizational` and an inline `ApplicabilityContext` with `scopeKind = organizational` and `scopeDescription = "CSBG Category B intake program at this agency; local amendment authority"`.

### Defect 2: `rescission-001` (statutory) — A3 missing authorityKind and hasApplicability

The statutory rescission assertion was labeled `A3AuthorityCritical` and had rescissionEvidence as evidence, but lacked authorityKind and hasApplicability.

**Patch:** added `authorityKind = rkaf:statutory` and an inline `ApplicabilityContext` describing the rescinded provision's scope.

### Defect 3: `delegation-derives-from-statute` (statutory) — A3 missing hasApplicability

A3 assertion linking HHS delegation to its statutory source. Had authorityKind=delegated and authorityCitation evidence, but lacked applicability.

**Patch:** added inline `ApplicabilityContext` with `scopeKind = delegation`.

### Defect 4: `regulation-derives-from-delegation` (statutory) — A3 missing hasApplicability

A3 assertion linking 45 CFR 96.30 to the HHS delegation. Had authorityKind=regulatory and authorityCitation evidence, but lacked applicability.

**Patch:** added inline `ApplicabilityContext` with `scopeKind = regulatoryProvision`.

### Defect 5: `caa-42-2026-07-01-001` (mapping) — acceptedWithWarnings without warnings

BridgeValidationResult with `result = acceptedWithWarnings` had empty `errors` and `staleDependencies` arrays (producing no triples) and no `warnings` array at all. The substantive warning ("LocalConcept resolves via closeMatch mapping that is not yet locally adopted") existed only as prose in `effectiveUsageEligibilityRationale` — not in any structured indicator.

**Patch:** added a structured `warnings` entry with the substantive warning text.

### Defect 6: `case-4-unreachable` (registry-failure-conflict) — rejected without remediation or noRemediationReason

BridgeValidationResult with `result = rejected`, indicator `registryUnavailable` pointing to the unreachable registry, but no `suggestedRemediation` and no `noRemediationReason`. Per Batch 1.1 patch 8, rejected MUST have one of those two — the registryUnavailable indicator alone is informative but doesn't satisfy the remediation requirement.

**Patch:** added `noRemediationReason = rkaf:noActionableRemediation`. The registry is genuinely unreachable; there is no actionable remediation the bridge can offer.

## 4. Triple count drift

| Fixture | Pre-Batch-4 | Post-Batch-4 | Delta | Cause |
|---|---:|---:|---:|---|
| local-operational-v0.2 | 350 | 355 | +5 | authorityKind + applicability blank node (4 triples) on amend-001 |
| mapping-v0.1 | 319 | 320 | +1 | warnings entry on caa-42-2026-07-01-001 |
| statutory-authority-v0.1 | 294 | 307 | +13 | rescission-001 authorityKind+applicability (5); delegation hasApplicability (4); regulation hasApplicability (4) |
| registry-failure-conflict-v0.1 | 223 | 224 | +1 | noRemediationReason on case-4-unreachable |
| **Total** | **1,186** | **1,206** | **+20** | — |

## 5. Coverage matrix

The five new Batch 4 shapes target types that appear across the fixtures:

| Shape | Local Op | Mapping | Statutory | Registry Failure |
|---|:---:|:---:|:---:|:---:|
| GeneratedWorkProductJustificationShape | ✓ (3) | ✓ (4) | ✓ (2) | — |
| FormspecFieldJustificationShape | ✓ (3) | ✓ (4) | ✓ (1) | — |
| WOSStepJustificationShape | — | — | ✓ (1) | — |
| FullBridgeValidationResultShape | ✓ (2) | ✓ (4) | ✓ (3) | ✓ (9) |
| JustificationChainHopShape | — | — | — | — (gap) |

## 6. Coverage gap flagged

Per the editorial discipline (no fixture force-fits to satisfy coverage):

- **`JustificationChainHopShape`** — no fixture target. The shape correctly allows `implements` as a hop predicate (distinct from `AuthorityChainHop` which forbids it), but no current fixture instantiates `rkaf:JustificationChainHop`. The statutory fixture's `authorityChainTraversal` uses `AuthorityChainHop` exclusively because all hops are authority-transmission edges. A future fixture exercising substantive realization (e.g., a generated work product whose justification chain traces through a `rkaf:implements` edge) will activate this shape.

This follows the same accepted pattern as `ConceptMintingAuthorityShape` (Batch 2), `SupersessionPacketShape` (Batch 3), and `MaterialRevisionPacketShape` (Batch 3): keep the shape as a written-down constraint; do not force-fit fixtures.

## 7. Implications for the v0.1-rc1 freeze

This is the most significant finding from any batch so far. The v0.1-rc1 frozen package shipped with three conditional shapes that did not actually fire:

- `BridgeValidationResultShape` (rejected → remediation)
- `OperationalAssertionEvidenceShape` (R2/A3/P4 → real evidence)
- `AuthorityAssertionShape` (A3 → authorityKind + hasApplicability + qualified evidence)

The v0.1-rc1 fixtures **happened to** mostly satisfy these constraints because they were written from the spec text, not from running shape validation. But four fixture entities did NOT satisfy the constraints, and the broken shapes hid those defects. After the Pattern C rewrite, those four entities surfaced as violations and were patched.

The v0.1-rc1 frozen archive in `/mnt/user-data/outputs/` remains untouched — that record stands as the v0.1-rc1 release at the time of freeze, including the latent bug. The Batch 4 deliverable ships **patched versions** of all four shape files (same file names, new content, new SHA-256 hashes) with the documented Pattern C rewrites.

This is a structural fix, not a semantic change. The intended constraints of every conditional shape were always what their TTL prose described. Pattern C is a faithful expression of that intent in a SHACL idiom that pyshacl evaluates correctly.

### Versioning recommendation

The combined shape package should be tagged **v0.1.1** when published, to signal:

- Spec semantics unchanged from v0.1-rc1
- Shape SHA-256 hashes changed (Pattern C rewrite)
- Six fixture defects patched (latent in v0.1-rc1)
- All synthetic defect tests now caught (12/12)
- Full fixture validation clean (1,206 triples, 0 violations)

## 8. Batch 4 deliverables

| Path | SHA-256 |
|---|---|
| `shapes/rkaf-shapes-core-v0.1.ttl` (Pattern C rewrites for 3 conditional shapes) | `228fe0f496a63ba3457e459689584409f16e013303b8097116b0090f63d8d93a` |
| `shapes/rkaf-shapes-conceptregistry-v0.1.ttl` (Pattern C rewrites for 3 conditional shapes) | `0f849e53ad6fa18b78f338cd74119bfcb57fe7f83198d2fcdf7dcc5c76ab2b33` |
| `shapes/rkaf-shapes-lifecycle-v0.1.ttl` (Pattern C rewrite for 1 conditional shape) | `7e6bc972d467d5a409063a978c17e37e9a93ddec3061b8e396baeb6d4b7009e3` |
| `shapes/rkaf-shapes-justification-v0.1.ttl` (Batch 4 NEW, Pattern C from drafting) | `75bf5d74b67dd31a46b975da27c748c4b8abef25623c2ae62148c92b4cdef766` |
| `fixtures/context.jsonld` (v0.2, unchanged from Batch 2/3) | `e29452da358440595b3104ede35b6db37c31b1bf70bbc52b16801adac8930f96` |
| `fixtures/local-operational-v0.2.jsonld` (Batch 4 patched: amend-001) | `f76c057a0035c12220239ff29fc07db5d6748afda9dbaa4062ae2563bae99fc7` |
| `fixtures/mapping-v0.1.jsonld` (Batch 4 patched: caa-42-2026-07-01-001) | `cf4ac0022e5a58d3c0e1baff594d083bf01894307391fba885c6beedaf689859` |
| `fixtures/statutory-authority-v0.1.jsonld` (Batch 4 patched: 3 A3 assertions) | `6317db74c1e743f8432f16122a6b1b94d12272ed0cec52f11f8ab7d7cce0238b` |
| `fixtures/registry-failure-conflict-v0.1.jsonld` (Batch 4 patched: case-4-unreachable) | `5c67cdab3fd2d7cf527941b3adfae691f9b1db7b35428095b4a63120f6d0ecdd` |
| `ci_validate.py` (multi-mode: core, batch2, batch3, batch4) | `b6211b42058938c84da8834458512af8e1c1a37fc006490417122adf6dc08d8b` |

## 9. What Batch 4 establishes

Beyond the prior three batches, the combined four-batch shape set now structurally enforces:

1. **Generated work product justification.** Every `rkaf:GeneratedWorkProduct` must declare `justifiedByAssertion` + `bridgeContractVersion` + eligibility (current or proposed). Without these, the artifact is not Rulespec-auditable.

2. **Rulespec overlay completeness for consumer artifacts.** When a `formspec:Field` or `wos:WorkflowStep` carries ANY Rulespec overlay property, it must also carry `bridgeContractVersion`. The overlay cannot exist as a partial/orphaned attribution; consumers must be able to evaluate it against a known bridge contract.

3. **Bridge result actionability.** Non-accepted `BridgeValidationResult` instances must include at least one structured indicator. Prose rationales are insufficient; the consumer needs machine-readable signal.

4. **Authority vs justification chain distinction.** `JustificationChainHopShape` explicitly allows `rkaf:implements` as a predicate, while `AuthorityChainHopShape` (Batch 1.1 patch 7) forbids it. This load-bearing distinction is now enforced in both directions: authority chains cannot smuggle in realization edges, and justification chains can carry them when needed.

5. **(Foundational fix)** The eight previously-broken conditional shapes now actually evaluate their constraints, providing genuine structural enforcement of:
   - R2/A3/P4 evidence requirements
   - A3 authority + applicability + qualified evidence requirements
   - Rejected bridge result remediation requirements
   - closeMatch mapping applicability requirements
   - Lifecycle split/merge/replacedBy successor requirements
   - Operational/publication mapping conflict artifact references
   - revalidatedWithSuccessor closure successor references

## 10. Conformance level — combined four-batch package

The combined Core + Batch 2 + Batch 3 + Batch 4 shape set structurally enforces:

- **Rulespec Core v0.1 — structurally enforced** (and now actually firing conditional constraints)
- **ConceptRegistry-Core v0.1.2 — structurally enforced**
- **ConceptRegistry-Lifecycle — structurally enforced for packet structure**; runtime cache/TTL behavior remains bridge-implementation conformance
- **ConceptRegistry-Federated — partial**; mapping conflicts validated; cross-org sync deferred
- **Generated Work Product overlay — structurally enforced**; Rulespec justification metadata is now required on every Rulespec-generated artifact

The package is structurally complete enough for **v0.1.1 release tagging** (semantics unchanged from v0.1-rc1; shape implementation fixed; fixtures defect-patched).

## 11. What remains as future work

Per the established editorial discipline, deferred:

- **Runtime conformance test layer.** Cascade closure correctness, reducer output correctness, registry TTL behavior, authority-chain traversal output, concept cache TTL, registry-unavailable behavior, PointInTimeException behavior, LocalAdoption orphaning, safeAutomaticMigration replaceInPlace. These need a test layer beyond SHACL — fixture-specific expected-output JSON files that consumers diff against their actual implementation output. **Mike's Batch 3 review specified the design: input fixture + lifecycle event → expected affected set + authority chain status + PIT exception acceptance.** This is now the next layer.

- **Repo publication operational tasks.** Hosting `https://rulespec.org/context/v1.jsonld` and `/v2.jsonld`. Versioned fixture snapshots in the repo for strict per-mode CI counts. README updated with the post-rc1 batch narrative. Tagging v0.1.1 once external review concludes.

- **Future fixture coverage.** A fixture that exercises `JustificationChainHop` with `implements` predicates (a generated work product whose justification chain traces through realization edges, not just authority transmission). A fixture that exercises `SupersessionPacket` (full-document supersession). A fixture that exercises `MaterialRevisionPacket` (distinct from amendment).

- **SHACL-Core compatibility profile.** The package now uses SHACL Core for all conditional shapes (Pattern C is pure Core). Only `qualifiedValueShape`/`qualifiedMinCount` (in AuthorityAssertionShape) still requires SHACL Advanced. A future audit could replace this single AF dependency to make the package SHACL Core-only.

## 12. Reproducibility

```bash
# Multi-mode CI gate — four conformance modes
python3 ci_validate.py --mode core      # Core shapes only,                                  1,183 triples
python3 ci_validate.py --mode batch2    # Core + ConceptRegistry,                            1,184 triples
python3 ci_validate.py --mode batch3    # Core + ConceptRegistry + Lifecycle,                1,186 triples
python3 ci_validate.py --mode batch4    # Core + ConceptRegistry + Lifecycle + Justification, 1,206 triples (default)
```

Each mode is independently runnable. The historical triple counts (1,183, 1,184, 1,186) correspond to fixture states at each batch's acceptance; the current state (1,206) reflects the +20 triples from Batch 4 fixture defect patches.

## Sign-off

Batch 4 is the most consequential batch so far. Two parallel outcomes:

1. **Five new shapes** validate the generated-artifact and bridge-justification consumer boundary, with the Rulespec/Formspec/WOS overlay distinction preserved.

2. **Eight broken conditional shapes** discovered, classified, rewritten with Pattern C, and verified by synthetic defect injection. Six previously-hidden fixture defects surfaced and patched. The v0.1-rc1 era is now structurally honest: every conditional constraint in the package actually fires.

This is the discipline working: shapes catch real defects, including defects in OTHER shapes. By adding Batch 4 with synthetic defect testing, the package discovered and fixed problems it had been carrying since the v0.1-rc1 freeze.

Four batches, four iteration arcs (251→14→0, 7→0, 2→0, [discovered] 6→0). Zero spec drift. Zero new vocabulary. The package is ready for v0.1.1 release tagging once external review concludes, and the next layer (runtime conformance tests) is now well-specified.
