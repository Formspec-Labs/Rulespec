# PKAF Conformance Fixtures

This directory contains four conformance fixtures that exercise the PKAF structural surface across realistic policy-knowledge scenarios. Each fixture is a JSON-LD document with an inline `@context` referencing the v0.2 PKAF context.

## Boundary reminder

The fixtures use `formspec:Field` and `wos:WorkflowStep` typed entities as **stress tests for the consumer overlay pattern**. They are not dependencies of PKAF. The same overlay can attach to any consumer's native artifact type — search index entries, wiki pages, CMS assets, AI assistant citation cards, case-system tasks, document fragments. The fixtures use form/workflow-shaped artifacts because they are well-understood stress tests, not because PKAF couples to those systems.

## Files

### `local-operational-v0.2.jsonld` (355 triples)

**Scenario:** Local operational policy lifecycle at a single agency.

A community action agency operates an intake program (CSBG Category B). The intake program has internal policies about how income documentation is collected and verified. An assertion (`req-002`) describes the operational requirement. The agency then amends its own policy (`amend-001`), triggering a cascade that revalidates the affected work products and ultimately produces a successor assertion (`req-003`).

**Exercises:**
- Assertions with `R2ReviewedOperational` safety label
- Local adoption with `localOperational` authority kind (NOT legal authority)
- Generated work products typed as `formspec:Field` with PKAF overlay
- `AmendmentPacket` with structural cascade
- `RevalidationEvent` and `RevalidationClosureEvent`
- `PointInTimeException` with `applicationSubmissionTime` anchor
- Successor work product generation (v1 → v2 → v3)

**Narrative:** See `narratives/local-operational.md`.

### `mapping-v0.1.jsonld` (320 triples)

**Scenario:** Concept registry mappings across two community action agencies.

Two agencies (CAA-42 and CAA-77) have local concepts that need to map to a federal registry's canonical concepts. The fixture exercises `skos:closeMatch` and `skos:exactMatch` mappings with `MappingApplicabilityContext`, the usage eligibility ceiling held at `draftGenerationAllowed` until local adoption, and a `ConceptLifecyclePacket` with `split` event that fans out a single concept into two successors.

**Exercises:**
- `RegisteredConcept` and `LocalConcept` with `definedInScope`
- Mapping assertions with `skos:closeMatch` and operational eligibility
- `MappingApplicabilityContext` with `applicationDomain` and `evidencePurpose`
- `ConceptResolutionResult` with `usageCeiling`
- `ConceptLifecyclePacket` (split event) with `successorConcepts`
- `BridgeValidationResult` with `conceptResolutionResults` and `effectiveUsageEligibility`
- Successor work product generation after concept split

**Narrative:** See `narratives/mapping.md`.

### `statutory-authority-v0.1.jsonld` (307 triples)

**Scenario:** Statutory rescission with full authority chain traversal.

A federal statute (`csbg-act-section-1234`) establishes identity-verification authority. HHS delegates administration to OCS; OCS regulates via 45 CFR 96.30. CAA-42 locally adopts the requirement. A subsequent statute (`csbg-restructure-act`) rescinds the original, triggering a cascade that affects the assertion, the local adoption, both generated work products (Formspec field AND WOS step), with a point-in-time exception preserving prior-submitted applications.

**Exercises:**
- A3 authority-critical assertions with `authorityKind` (legal, statutory, regulatory, delegated)
- Authority chain traversal (`AuthorityChainHop` instances) with `hasAuthority` and `derivesAuthorityFrom`
- Both Formspec field AND WOS step typed as `GeneratedWorkProduct` (cross-consumer overlay)
- `associatedWorkflowStep` linking field to step
- `RescissionPacket` with full cascade
- `PointInTimeException` with `applicationSubmissionTime` anchor preserving in-flight cases
- `RevalidationEvent` with `retainedPointInTimeException`

**Narrative:** See `narratives/statutory-authority.md`.

### `registry-failure-conflict-v0.1.jsonld` (224 triples)

**Scenario:** Nine independent registry failure and conflict cases.

This fixture is a stress test for bridge result handling under degraded conditions. Each "case" is a separate `BridgeValidationResult` demonstrating a different failure mode the bridge must handle:

| Case | Scenario |
|---|---|
| case-1-fresh-cache | Baseline: clean resolution with fresh cache |
| case-2-stale-non-critical | Cache stale but non-critical concept |
| case-3-stale-A3 | A3 assertion with stale evidence → `rejected` with `suggestedRemediation` |
| case-4-unreachable | Registry network failure → `rejected` with `noActionableRemediation` |
| case-5-version-out-of-range | Bridge version mismatch → `acceptedWithWarnings` |
| case-6-operational-conflict | Two conflicting mappings at operational severity |
| case-7-publication-blocking | Conflict blocking publication |
| case-8-canonical-resolved | Canonical resolution via federated registry |
| case-9-auto-migration | `safeAutomaticMigration` with `replaceInPlace` |

**Exercises:**
- All `BridgeValidationResult` indicator types (warnings, errors, ineligibleAssertions, unresolvedConcepts, registryUnavailable, registryVersionOutOfRange, staleDependencies, staleConceptCache)
- `SuggestedRemediation` with various remediation kinds
- `MappingConflict` with multiple severity levels
- All structured-indicator code paths required by `FullBridgeValidationResultShape`

**Narrative:** See `narratives/registry-failure-and-conflict.md`.

## Validating

```bash
# From repo root:
python3 tools/ci_validate.py
# default mode is batch4; should report 1,206 triples, 0 violations across all four fixtures
```

To validate against a specific conformance subset:

```bash
python3 tools/ci_validate.py --mode core      # 1,183 triples baseline
python3 tools/ci_validate.py --mode batch2    # 1,184 triples
python3 tools/ci_validate.py --mode batch3    # 1,186 triples
python3 tools/ci_validate.py --mode batch4    # 1,206 triples (default)
```

## context.jsonld

The file `context.jsonld` in this directory is the **fixture-prep source** for the inline `@context` that each fixture carries. It is identical in content to `context/pkaf-context-v0.2.jsonld`. See `context/README.md` for the rationale for this duplication.

## Adding new fixtures

New fixtures should:

1. Cover a scenario not already exercised by the existing four (e.g., supersession, material revision, justification chain with `implements` predicate, a non-Formspec consumer like a search index)
2. Inline the full v0.2 context as `@context`
3. Pass `tools/ci_validate.py --mode batch4` cleanly before being committed
4. Be accompanied by a narrative document in `narratives/`
5. Update the coverage matrix in `reports/v0.1.1-release-manifest.md`

See `CONTRIBUTING.md` for the full editorial discipline.
