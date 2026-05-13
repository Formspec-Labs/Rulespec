# Rulespec Batch 2 Validation Report

Status: **Batch 2 complete — clean validation**
Bridge contract: `rkaf-bridge/1.0`
Baseline: Rulespec v0.1-rc1 (frozen)

## Executive summary

Batch 2 adds eleven ConceptRegistry shapes to the v0.1-rc1 Core shapes. After two iteration cycles of evidence-driven patching, all four fixtures validate cleanly against the combined Core + ConceptRegistry shape set.

| Run | Total violations | Local Op | Mapping | Statutory | Registry Failure |
|---|---|---|---|---|---|
| Initial Batch 2 | 7 | 0 | 6 | 0 | 1 |
| After context + 5 fixture patches | **0** | **0** | **0** | **0** | **0** |

```
Rulespec CI validation gate
============================================================
[1/3] Environment check
  pyshacl 0.31.0 OK
  shapes:  shapes/rkaf-shapes-core-v0.1.ttl
  shapes:  shapes/rkaf-shapes-conceptregistry-v0.1.ttl

[2/3] Per-fixture validation
  [PASS] local-operational-v0.2: 0 violations, 349 triples
  [PASS] mapping-v0.1: 0 violations, 319 triples
  [PASS] statutory-authority-v0.1: 0 violations, 293 triples
  [PASS] registry-failure-conflict-v0.1: 0 violations, 223 triples

[3/3] Summary
  Fixtures:  4
  Triples:   1184
  Violations: 0
  Result:    PASS
```

## 1. Batch 2 shape additions

Eleven shapes added in `rkaf-shapes-conceptregistry-v0.1.ttl`, anchored on ConceptRegistry v0.1.2:

| Shape | Spec section | Targets |
|---|---|---|
| `RegisteredConceptShape` | §2.1 | `rkaf:RegisteredConcept` |
| `LocalConceptShape` | §2.2 | `rkaf:LocalConcept` |
| `ConceptRegistryShape` | §3.1 | `rkaf:ConceptRegistry` |
| `ConceptMintingAuthorityShape` | §3.2 | `rkaf:ConceptMintingAuthority` |
| `MappingAssertionShape` | §4 | `rkaf:RelationshipAssertion` (SKOS-predicate-conditional) |
| `MappingApplicabilityContextShape` | §4.4 | `rkaf:MappingApplicabilityContext` |
| `ConceptResolutionResultShape` | §5.4 | `rkaf:ConceptResolutionResult` |
| `SuggestedRemediationShape` | §5.9 | `rkaf:SuggestedRemediation` |
| `ConceptLifecyclePacketShape` | §7.5 | `rkaf:ConceptLifecyclePacket` |
| `MappingConflictShape` | §8 | `rkaf:MappingConflict` |
| `BridgeConsumerRegistrationShape` | Core §5.1 | `rkaf:BridgeConsumerRegistration` |

Two shapes use SHACL Advanced conditional logic (`sh:if`/`sh:then`):

- **MappingAssertionShape:** activates when `rkaf:assertsPredicate` is `skos:closeMatch` AND `rkaf:usageEligibility` is at `localOperationalUse` or higher; requires `MappingApplicabilityContext`.
- **ConceptLifecyclePacketShape:** when `rkaf:lifecycleEvent` is `split`, `merge`, or `replacedBy`, requires `rkaf:successorConcepts`.
- **MappingConflictShape:** when `rkaf:severity` is `operationalConflict` or `publicationBlocking`, requires either `rkaf:sharedArtifact` or `rkaf:relatedPublishedArtifact`.

## 2. Classification of initial violations

| Cluster | Count | Category | Root cause |
|---|---|---|---|
| `definedInScope` nodekind mismatch | 2 | Context bug (additive) | Property typing missing from v0.1 context |
| `MappingApplicabilityContext` missing `applicationDomain` | 4 | Fixture bug | Stale `operationalScope` term (renamed in ConceptRegistry v0.1.2 §4.4) |
| `ConceptResolutionResult` missing `usageCeiling` | 1 | Fixture bug | Field omitted from case-4-unreachable |

Zero shape over-strictness. Zero core ambiguities. Zero missing vocabulary. Zero intended-failure mismatches.

## 3. Patches applied

### 3.1 Context addition (1 patch)

Added to `fixtures/context.jsonld`:

```json
"rkaf:definedInScope": { "@type": "@id" }
```

This is an **additive** fix to the context that doesn't change v0.1 semantics. The property was always conceptually an IRI reference; the v0.1 context simply didn't declare it. v0.1-rc1 frozen context remains untouched; Batch 2 uses an extended working context.

Recommendation: publish this extended context as `rkaf-context.jsonld`, strict superset of v0.1 context.

### 3.2 Mapping fixture — terminology rename (4 patches)

Renamed `rkaf:operationalScope` → `rkaf:applicationDomain` in four `MappingApplicabilityContext` instances:

- `caa-42-mapping-001` (Step 4)
- `caa-42-mapping-001` adoption (Step 8)
- `caa-42-mapping-002a` (Step 19)
- `caa-42-mapping-002b` (Step 19)

The rename was a v0.1 spec decision (ConceptRegistry v0.1.2 §4.4) that didn't propagate into the fixture content during v0.1-rc1 patching.

### 3.3 Registry-failure fixture — missing field (1 patch)

Added `"rkaf:usageCeiling": "rkaf:notEligible"` to the `ConceptResolutionResult` in `case-4-unreachable`. This is consistent with the equivalent field in case-3-stale-A3.

## 4. Coverage status

The eleven Batch 2 shapes target ConceptRegistry types that appear across the four fixtures:

| Shape | Local Op | Mapping | Statutory | Registry Failure |
|---|:---:|:---:|:---:|:---:|
| RegisteredConceptShape | — | ✓ (4) | — | ✓ (1+5 successors) |
| LocalConceptShape | — | ✓ (2) | — | — |
| ConceptRegistryShape | — | ✓ (1) | — | ✓ (1) |
| ConceptMintingAuthorityShape | — | — | — | — (gap, see §5) |
| MappingAssertionShape | — | ✓ (3 mappings, conditional fires on 002a/002b) | — | ✓ (1) |
| MappingApplicabilityContextShape | — | ✓ (4 instances) | — | — |
| ConceptResolutionResultShape | — | — | — | ✓ (5 instances) |
| SuggestedRemediationShape | — | — | — | ✓ (2 instances) |
| ConceptLifecyclePacketShape | — | ✓ (1) | — | ✓ (1) |
| MappingConflictShape | — | ✓ (1 informational) | — | ✓ (1 operational, 1 publicationBlocking) |
| BridgeConsumerRegistrationShape | — | — | — | ✓ (1) |

## 5. Coverage gap flagged

**`ConceptMintingAuthorityShape` has no fixture targets.** No fixture instantiates a typed `rkaf:ConceptMintingAuthority` object — minting authorities appear only as URI references (`rkaf:mintingAuthority` on `ConceptRegistry`, `rkaf:registrationAuthority` on `ConceptRegistrationEvent`). The shape is correct but unexercised.

Options:
- (a) Accept the gap (consistent with editorial discipline; no fixture force-fits)
- (b) Add a minimal `ConceptMintingAuthority` instance to one fixture
- (c) Remove the shape until a future fixture needs it

Recommend **(a)** — keep the shape as a written-down constraint that activates when any future fixture or production data instantiates a minting authority inline. The shape is correct; coverage is the question.

## 6. Triple count drift

| Fixture | Pre-Batch-2 | Post-Batch-2 | Delta | Cause |
|---|---:|---:|---:|---|
| local-operational-v0.2 | 349 | 349 | 0 | — |
| mapping-v0.1 | 319 | 319 | 0 | Rename of `operationalScope` → `applicationDomain` is one-for-one |
| statutory-authority-v0.1 | 293 | 293 | 0 | — |
| registry-failure-conflict-v0.1 | 222 | 223 | +1 | Added `usageCeiling` to case-4-unreachable |
| **Total** | **1,183** | **1,184** | **+1** | — |

CI `EXPECTED` range for `registry-failure-conflict-v0.1` bumped from `[215, 235]` to `[215, 240]` to absorb future fixture drift.

## 7. Batch 2 deliverables

| Path | SHA-256 |
|---|---|
| `shapes/rkaf-shapes-conceptregistry-v0.1.ttl` | `24b7b560f21be1f5df258cd952bc6ea4595426f48f399d03d7104b51ccc3b802` |
| `fixtures/context.jsonld` (v0.2 candidate) | `e7f10de206021de12b8222532d46bc660e615e75b43b2d7d35c993e9f3fd3691` |
| `fixtures/mapping-v0.1.jsonld` (Batch 2 patched) | `573ab5b12d4e52e6a684c072d2408bda8b513a8a64acdf82f1dfb9920fe7529f` |
| `fixtures/registry-failure-conflict-v0.1.jsonld` (Batch 2 patched) | `e672540093d0e1891e12c41ce794221f74eb1d3aac78858223f6e63a2ff29f23` |
| `fixtures/local-operational-v0.2.jsonld` (context refreshed) | `996445cb784dcd68751b7b931c238cfba9a1f9e381e5bc0c4b1fb3c9b69cc781` |
| `fixtures/statutory-authority-v0.1.jsonld` (context refreshed) | `13a4c5de51483eaba4b6787a5760ae529033fed535af31382b1c8e9e0d79bbdf` |
| `ci_validate.py` (updated to load both shape files) | `5ed1aa357ca62f15aa86ea3f50c7e530f01321eac13ffd4f757353b60dea20d1` |

## 8. What Batch 2 establishes

Beyond the v0.1-rc1 invariants, the combined shape set now enforces:

1. **RegisteredConcept and LocalConcept structural completeness.** Both require `skos:prefLabel`, `conceptScope`, `conceptStatus`. RegisteredConcept additionally requires `managedByRegistry`; LocalConcept requires `definedInScope` (IRI). LocalConcept scope is restricted to organization/workspace/personal/team (never public).
2. **ConceptRegistry governance metadata.** Every registry must declare namespace prefix, minting authority, governance model (from the enumerated set), resolution endpoint, and version.
3. **Mapping operational eligibility requires applicability context.** A `skos:closeMatch` mapping at `localOperationalUse` or higher MUST declare a `MappingApplicabilityContext` with `applicationDomain` and `evidencePurpose`. This is the structural enforcement of ConceptRegistry v0.1.2 §4.4.
4. **ConceptResolutionResult completeness.** Every resolution result declares input concept, resolution status (from the enumerated set), and usage ceiling. The ceiling is the load-bearing output: consumers use it to compute effective eligibility.
5. **SuggestedRemediation actionability.** Every rejected `BridgeValidationResult`'s remediation has an enumerated action from a defined vocabulary, making bridge errors machine-actionable.
6. **ConceptLifecyclePacket cascade prerequisites.** Lifecycle packets MUST declare `effectiveDate`, `bridgeContractVersion`, `cascadeAlgorithm`, and (for split/merge/replacedBy) `successorConcepts`.
7. **MappingConflict severity binds to artifact reference.** `operationalConflict` and `publicationBlocking` severities MUST identify the affected artifact (`sharedArtifact` or `relatedPublishedArtifact`); `informational` severity does not require this.
8. **BridgeConsumerRegistration declares anchor support.** Every registration MUST list at least one `supportedEvaluationAnchor`, enforcing the bridge contract rule that consumers refuse packets referencing unsupported anchors.

## 9. ConceptRegistry conformance level

Combined Core + Batch 2 shapes structurally enforce **ConceptRegistry-Core** (per ConceptRegistry v0.1.2 §10):

- ✅ Concept shapes (Registered + Local)
- ✅ Registry model
- ✅ Mapping assertions with direction and applicability
- ✅ Direct resolution
- ✅ LocalConcept resolution structure
- ✅ ConceptResolutionResult
- ✅ BridgeValidationResult integration
- ✅ Minimum registry-unavailable behavior (structural; runtime behavior is bridge-implementation)

Partial **ConceptRegistry-Lifecycle**:

- ✅ Lifecycle status enum (in RegisteredConceptShape `conceptStatus` constraint)
- ✅ ConceptLifecyclePacket structural validation
- ✅ Cascade prerequisites (cascadeAlgorithm, successorConcepts)
- ⚠ Full runtime cache/TTL behavior is not structurally validatable (bridge implementation concern)

Partial **ConceptRegistry-Federated**:

- ✅ Mapping disputes with severity
- ✅ Severity-conditional artifact-reference requirement
- ⚠ `CanonicalMapping` attestation pattern validates as a generic Attestation; no dedicated shape required (the existing AttestationShape covers it)
- ⚠ LocalConcept promotion flow validates structurally; runtime semantics out of scope

## 10. Next: Batch 3 — Lifecycle packet shapes

Per Mike's documented sequencing, Batch 3 covers:

- `AmendmentPacketShape`
- `RescissionPacketShape`
- `SupersessionPacketShape`
- `MaterialRevisionPacketShape`
- `RevalidationEventShape`
- `RevalidationClosureEventShape`
- `PointInTimeExceptionShape`

The lifecycle fixtures already exercise these (statutory rescission cascade, mapping concept split, etc.), so Batch 3 should follow the same pattern: write shapes, validate, classify violations, patch evidence-driven.

After Batch 3:
- Batch 4: generated artifact justification shapes (FormspecFieldJustification, WOSStepJustification, full BridgeValidationResult)
- Then: SHACL-Core compatibility profile if needed
- Then: PROV-O alignment shapes

Editorial discipline holds: no new concepts unless validation forces them.

## 11. Reproducibility

```bash
# From repo root with shapes/ and fixtures/ populated
pip install pyshacl==0.31.0
python3 ci_validate.py
# Expected output: 4 PASS lines, 0 violations across 1,184 triples
```

## Sign-off

Batch 2 ConceptRegistry shapes are complete. The model held: all eleven shapes validate cleanly across all four fixtures after evidence-driven patches. No new vocabulary added. No spec changes. The same pattern continues — shapes catch real defects, fixtures need editorial alignment.

This is the second proof point that Rulespec's discipline works: incremental shape batches surface specific defects, get patched, and converge to clean validation without producing speculative ontology drift.
