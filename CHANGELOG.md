# Changelog

All notable changes to PKAF are documented in this file.

The format is loosely based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
adapted for a specification + shape + fixture project.

## [v0.1.1] — 2026-05-12 — Structural validation fix and consumer-justification shapes

### Added

- **Consumer artifact overlay shape vocabulary** (`shapes/pkaf-shapes-justification-v0.1.ttl`)
  - `GeneratedWorkProductJustificationShape` — validates the PKAF overlay type
  - `ConsumerArtifactJustificationShape` — universal shape targeting subjects of `pkaf:justifiedByAssertion`
  - `DataCollectionArtifactJustificationShape` — universal shape targeting subjects of `pkaf:collectsEvidenceType`
  - `ProcessArtifactJustificationShape` — universal shape targeting subjects of `pkaf:requiresEvidenceType`
  - `FullBridgeValidationResultShape` — structured output requirement on non-accepted bridge results
  - `JustificationChainHopShape` — allows `pkaf:implements` predicate (distinct from `AuthorityChainHop`)
  - `FormspecFieldJustificationShape` — documented example specialization
  - `WOSStepJustificationShape` — documented example specialization

- **Multi-mode CI gate** (`tools/ci_validate.py --mode core | batch2 | batch3 | batch4`)
  - Four conformance modes selectable via flag
  - Per-fixture triple-count drift detection
  - JSON output mode for CI pipelines

- **Public framing as universal ontology**
  - README rewritten: PKAF positioned as universal evidence-backed assertion / authority / concept / lifecycle / justification ontology
  - Consumer systems (search engines, wikis, form builders, workflow engines, case systems, content management, AI assistants, publication tools, auditing tools, knowledge graphs) framed as examples, not anchors
  - Fixtures explicitly labeled as stress tests for the consumer overlay pattern, not dependencies

### Fixed

- **pySHACL `sh:if`/`sh:then` evaluation bug.** Eight conditional shapes across Batches 1.1, 2, 3, and 4 were not actually firing as designed. All eight rewritten using Pattern C (`sh:or` with `sh:not`), which pySHACL evaluates reliably:
  - `BridgeValidationResultShape` (Batch 1.1) — rejected → remediation OR noRemediationReason
  - `OperationalAssertionEvidenceShape` (Batch 1.1) — R2/A3/P4 → hasEvidence required
  - `AuthorityAssertionShape` (Batch 1.1) — A3 → authorityKind + hasApplicability + qualified evidence
  - `MappingAssertionShape` (Batch 2) — closeMatch + operational → MappingApplicabilityContext
  - `ConceptLifecyclePacketShape` (Batch 2) — split/merge/replacedBy → successorConcepts
  - `MappingConflictShape` (Batch 2) — operational/publicationBlocking severity → artifact reference
  - `RevalidationClosureEventShape` (Batch 3) — revalidatedWithSuccessor → successor reference
  - `FullBridgeValidationResultShape` (Batch 4) — non-accepted → structured indicator

- **Six latent fixture defects** surfaced by the corrected constraints, all patched:
  - `amend-001` (local-operational): added `authorityKind = pkaf:organizational` and `ApplicabilityContext`
  - `rescission-001` (statutory): added `authorityKind = pkaf:statutory` and `ApplicabilityContext`
  - `delegation-derives-from-statute` (statutory): added `ApplicabilityContext`
  - `regulation-derives-from-delegation` (statutory): added `ApplicabilityContext`
  - `caa-42-2026-07-01-001` (mapping): added structured `warnings` entry
  - `case-4-unreachable` (registry-failure-conflict): added `noRemediationReason = pkaf:noActionableRemediation`

### Changed

- **Triple count:** 1,186 → 1,206 (+20 from fixture defect patches)
- **Shape implementation:** Pattern C rewrites change all eight conditional shape SHA-256 hashes (semantics unchanged)
- **JSON-LD context:** `_meta` block added to `pkaf-context-v0.2.jsonld` documenting it as a strict additive superset of v0.1

### Unchanged from v0.1-rc1

- **Specification text** (`spec/pkaf-core-v0.1.md`, `spec/pkaf-concept-registry-v0.1.2.md`) — semantically identical
- **Fixture narratives** — substantively identical
- **Vocabulary** — no new terms added; only the additive `pkaf:definedInScope` context typing carried forward from Batch 2

### Conformance signature

```
Mode:       batch4 (Core + ConceptRegistry + Lifecycle + Justification)
Shapes:     4 files
Fixtures:   4
Triples:    1,206
Violations: 0
Result:     PASS
```

### Coverage gaps accepted

Four shapes have no fixture target. They remain structurally correct and will activate when future fixtures instantiate the relevant entity type:

- `ConceptMintingAuthorityShape` — full mint-authority instances not exercised
- `SupersessionPacketShape` — full-document supersession not exercised
- `MaterialRevisionPacketShape` — material revision distinct from amendment not exercised
- `JustificationChainHopShape` — justification chains with `pkaf:implements` predicate not exercised

---

## [v0.1-rc1] — 2026-05-12 — Initial release candidate

### Added

- **PKAF Core specification** (`spec/pkaf-core-v0.1.md`)
  - Assertions, evidence, attestations, adoption, authority chain
  - Bridge model and consumer artifact overlay
  - Lifecycle packets, revalidation, point-in-time exceptions
  - Cascade closure algorithm specification

- **ConceptRegistry specification** (`spec/pkaf-concept-registry-v0.1.2.md`)
  - Registered concepts, local concepts, mappings
  - Mapping applicability contexts
  - Concept resolution and usage ceiling
  - ConceptRegistry-Core / Lifecycle / Federated conformance levels

- **JSON-LD context** (`context/pkaf-context-v0.1.jsonld`)

- **Core SHACL shapes** (`shapes/pkaf-shapes-core-v0.1.ttl`)
  - 8 shape sets covering trust zones, assertions, evidence, attestations, adoption, authority, applicability, bridge validation

- **Four conformance fixtures**
  - `local-operational-v0.2.jsonld` — CSBG eligibility lifecycle
  - `mapping-v0.1.jsonld` — Concept registry mappings
  - `statutory-authority-v0.1.jsonld` — Statutory rescission with authority chain
  - `registry-failure-conflict-v0.1.jsonld` — Nine registry failure scenarios

- **Multi-pass validation arc:** 251 → 14 → 0 violations
- **1,183 triples, 0 violations** at v0.1-rc1 freeze

### Known issues at v0.1-rc1 (discovered and fixed in v0.1.1)

- Three conditional shapes (`BridgeValidationResultShape`, `OperationalAssertionEvidenceShape`, `AuthorityAssertionShape`) used the `sh:if`/`sh:then` SHACL Advanced Features pattern which pySHACL 0.31.0 does not evaluate reliably. The constraints existed in the TTL files and parsed correctly, but did not fire against fixture data. v0.1-rc1 fixtures *happened to* mostly satisfy these constraints but four latent defects were hidden by the broken evaluation. All addressed in v0.1.1.
