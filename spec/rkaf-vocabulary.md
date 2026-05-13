# Rulespec Vocabulary v0.2 — Full Term Reference

> Mechanically-consumable. One row per term. Source of truth for code generators and projectors.
>
> Status: pre-release, normative. Mechanical consumers parse the table by markdown row. The `Required fixtures` column is enforced by `tools/vocab_audit.py` — every named fixture MUST exist under `fixtures/` as a `<name>.jsonld` file.

## v0.2 universal primitives (§§4.1-4.6 of `spec/rkaf-core.md`)

| Term | IRI | Kind | Domain | Range | Cardinality | Required fixtures |
|---|---|---|---|---|---|---|
| rkaf:Artifact | https://rulespec.org/ns/v1#Artifact | Class | — | — | — | artifact-eli-positive, artifact-doi-positive, artifact-cid-positive |
| rkaf:hasArtifactIdentifier | https://rulespec.org/ns/v1#hasArtifactIdentifier | Property | rkaf:Artifact | xsd:string \| IRI | 1..* | artifact-eli-positive |
| rkaf:artifactIdentifierScheme | https://rulespec.org/ns/v1#artifactIdentifierScheme | Property (closed enum) | rkaf:Artifact | rkaf:ArtifactIdentifierScheme | 1..* | artifact-eli-positive |
| rkaf:SourceFragment | https://rulespec.org/ns/v1#SourceFragment | Class | — | — | — | sourcefragment-oa-textquote-positive, sourcefragment-oa-xpath-positive, sourcefragment-aknt-eid-positive, sourcefragment-uslm-section-positive |
| rkaf:bindsArtifact | https://rulespec.org/ns/v1#bindsArtifact | Property | rkaf:SourceFragment | rkaf:Artifact | 1 | sourcefragment-oa-textquote-positive |
| rkaf:hasSelector | https://rulespec.org/ns/v1#hasSelector | Property | rkaf:SourceFragment | oa:Selector OR rkaf:Selector | 1..* | sourcefragment-oa-textquote-positive |
| rkaf:selectorKind | https://rulespec.org/ns/v1#selectorKind | Property (closed enum) | rkaf:SourceFragment | rkaf:SelectorKind | 1..* | sourcefragment-oa-textquote-positive |
| rkaf:EvidenceBinding | https://rulespec.org/ns/v1#EvidenceBinding | Class | — | — | — | evidencebinding-positive, evidencebinding-no-evidence-reason-positive, evidencebinding-missing-negative |
| rkaf:bindsAssertion | https://rulespec.org/ns/v1#bindsAssertion | Property | rkaf:EvidenceBinding | rkaf:Assertion | 1 | evidencebinding-positive |
| rkaf:bindsSourceFragment | https://rulespec.org/ns/v1#bindsSourceFragment | Property | rkaf:EvidenceBinding | rkaf:SourceFragment | 0..* | evidencebinding-positive |
| rkaf:noEvidenceReason | https://rulespec.org/ns/v1#noEvidenceReason | Property (closed enum) | rkaf:EvidenceBinding | rkaf:NoEvidenceReason | 0..1 | evidencebinding-no-evidence-reason-positive |
| rkaf:Warrant | https://rulespec.org/ns/v1#Warrant | Class | — | — | — | warrant-legal-positive, warrant-scientific-positive, warrant-cross-family-transition-positive |
| rkaf:hasWarrant | https://rulespec.org/ns/v1#hasWarrant | Property | rkaf:Assertion / rkaf:EvidenceBinding | rkaf:Warrant | 1..* | warrant-legal-positive |
| rkaf:warrantKind | https://rulespec.org/ns/v1#warrantKind | Property (closed enum) | rkaf:Warrant | rkaf:WarrantKind | 1 | warrant-legal-positive |
| rkaf:warrantFamily | https://rulespec.org/ns/v1#warrantFamily | Property (closed enum) | rkaf:Warrant | rkaf:WarrantFamily | 1 | warrant-legal-positive |
| rkaf:hasAuthority | https://rulespec.org/ns/v1#hasAuthority | Property (legal specialization of hasWarrant) | rkaf:Assertion | rkaf:Authority | 1..* | warrant-legal-positive |
| rkaf:ConfidenceRecord | https://rulespec.org/ns/v1#ConfidenceRecord | Class | — | — | — | confidencerecord-uncalibrated-positive, confidencerecord-calibrated-positive, confidencerecord-score-theater-negative |
| rkaf:hasConfidence | https://rulespec.org/ns/v1#hasConfidence | Property | rkaf:Assertion | rkaf:ConfidenceRecord | 0..* | confidencerecord-uncalibrated-positive |
| rkaf:confidenceMethod | https://rulespec.org/ns/v1#confidenceMethod | Property (closed enum) | rkaf:ConfidenceRecord | rkaf:ConfidenceMethod | 1 | confidencerecord-uncalibrated-positive |
| rkaf:calibrationStatus | https://rulespec.org/ns/v1#calibrationStatus | Property (closed enum) | rkaf:ConfidenceRecord | rkaf:CalibrationStatus | 1 | confidencerecord-uncalibrated-positive |
| rkaf:AccessScope | https://rulespec.org/ns/v1#AccessScope | Class | — | — | — | accessscope-public-positive, accessscope-organizationVisible-positive, accessscope-leak-negative |
| rkaf:hasAccessScope | https://rulespec.org/ns/v1#hasAccessScope | Property | rkaf:Assertion / rkaf:Attestation / rkaf:EvidenceBinding / rkaf:SourceFragment | rkaf:AccessScope | 0..1 | accessscope-public-positive |
| rkaf:accessScopeKind | https://rulespec.org/ns/v1#accessScopeKind | Property (closed enum) | rkaf:AccessScope | rkaf:AccessScopeKind | 1 | accessscope-public-positive |

## v0.2 Studio-derived promotions (§5 of `spec/rkaf-core.md`)

| Term | IRI | Kind | Domain | Range | Cardinality | Required fixtures |
|---|---|---|---|---|---|---|
| rkaf:AILineage | https://rulespec.org/ns/v1#AILineage | Class | — | — | — | ailineage-positive, ailineage-missing-approver-negative |
| rkaf:hasAILineage | https://rulespec.org/ns/v1#hasAILineage | Property | rkaf:Assertion | rkaf:AILineage | 0..1 (REQUIRED if assertionOrigin AI-touched) | ailineage-positive |
| rkaf:MappingState | https://rulespec.org/ns/v1#MappingState | Class (closed enum carrier) | — | — | — | mappingstate-positive |
| rkaf:mappingState | https://rulespec.org/ns/v1#mappingState | Property (closed enum) | any mapping-bearing | rkaf:MappingState | 1 | mappingstate-positive |
| rkaf:RetentionPolicy | https://rulespec.org/ns/v1#RetentionPolicy | Class | — | — | — | retentionpolicy-positive |
| rkaf:hasRetentionPolicy | https://rulespec.org/ns/v1#hasRetentionPolicy | Property | rkaf:Artifact / rkaf:Assertion / rkaf:Attestation / rkaf:EvidenceBinding | rkaf:RetentionPolicy | 0..1 | retentionpolicy-positive |
| rkaf:Workspace | https://rulespec.org/ns/v1#Workspace | Class | — | — | — | workspace-positive |
| rkaf:projectsTo | https://rulespec.org/ns/v1#projectsTo | Property | any | IRI | 0..* | covered by projector fixtures (Plan 5) |
| rkaf:llmHint | https://rulespec.org/ns/v1#llmHint | Annotation property | any vocabulary term | rkaf:LLMHint | 0..1 | covered by projector fixtures (Plan 5) |

## Abstract anchoring contract (§7)

| Term | IRI | Kind | Domain | Range | Cardinality | Required fixtures |
|---|---|---|---|---|---|---|
| rkaf:anchoredBy | https://rulespec.org/ns/v1#anchoredBy | Property | rkaf:Assertion / rkaf:Overlay | IRI | 0..* | covered by Plan 9 |
| rkaf:anchorType | https://rulespec.org/ns/v1#anchorType | Property | anchor IRI | IRI | 1 | covered by Plan 9 |

## Codified Vocabulary — additional terms (§6)

Beyond the v0.2 normative tier in §5, the following terms are codified as CUE constraints under `constraints/core/` and generated into JSON Schema (`compiled/json-schema/core/`), Rust (`crates/rkaf-core/src/generated/`), TypeScript, and SHACL targets via `tools/constraints_compile.py`. Each carries at least one positive fixture under `fixtures/`.

**Classes** (each backed by a CUE shape, a JSON Schema, and a Rust struct):

| Term | CUE | Fixture | Purpose |
|---|---|---|---|
| `rkaf:Authority` | `authority.cue` | `authority-positive.jsonld` | Legal-family specialization of Warrant (Core §2). Carries `authorityKind` (hop-local), optional applicability + effective period, chain predecessors. |
| `rkaf:Attestation` | `attestation.cue` | `attestation-positive.jsonld` | Scoped multi-target attestation by a named attestor (Core §3.1). Closed decision + attestor-kind enums. |
| `rkaf:LocalAdoption` | `local-adoption.cue` | `localadoption-positive.jsonld` | Workspace-scoped authorization of an Assertion (Core §3.2). Restricted `adoptionAuthorityKind` per §2.5 invariant. |
| `rkaf:ApplicabilityScope` | `applicability-scope.cue` | `applicabilityscope-positive.jsonld` | Where/to-whom/when a Warrant applies. ELI / ISO 3166 / agency-code IRIs. |
| `rkaf:EffectivePeriod` | `effective-period.cue` | `effectiveperiod-positive.jsonld` | Temporal window. Start required; end / sunset / retroactive optional. |
| `rkaf:LifecycleEvent` | `lifecycle-event.cue` | `lifecycleevent-positive.jsonld` | Audit-trail event (revalidation, amendment, supersession, rescission, material revision, concept lifecycle, promotion, demotion). |
| `rkaf:RegisteredConcept` | `concept.cue` | `concept-registered-positive.jsonld` | Federation-shared Concept minted by a `rkaf:ConceptMintingAuthority`. |
| `rkaf:LocalConcept` | `concept.cue` | (shares fixture) | Workspace-defined Concept, candidate for federation promotion. |
| `rkaf:ConceptMapping` | `concept-mapping.cue` | `conceptmapping-positive.jsonld` | SKOS-mapping between concepts. Closed `mappingPredicate` enum. |
| `rkaf:MappingApplicabilityContext` | `concept-mapping.cue` | (shares fixture) | Scopes a mapping by application-domain + evidence-purpose. |
| `rkaf:ConceptResolutionResult` | `concept-resolution-result.cue` | `conceptresolutionresult-positive.jsonld` | Output of resolving a concept reference against the federation. |
| `rkaf:BridgeValidationResult` | `bridge-validation-result.cue` | `bridgevalidationresult-positive.jsonld` | Control-plane record per packet ingestion: verdict + effective eligibility + authority-chain status + warnings/errors. |

**Closed enums and lattices** (referenced by the classes above):

- `rkaf:usageEligibility` — 7-level lattice from `notEligible` (lowest) to `officialUse` (highest). Consumers MAY narrow; only LocalAdoption MAY broaden within its declared scope.
- `rkaf:hasTrustZone` — `rkaf:Z0` through `rkaf:Z8`. Structural property (kind of object).
- `rkaf:hasSafetyLabel` — `D0` / `S1` / `R2` / `A3` / `P4` plus advisory + authority-critical refinements. Operational property (what the consumer may do).
- `rkaf:authorityKind` — 8-value closed enum, hop-local. Federation refuses unsupported kinds.
- `rkaf:lifecycleEventKind` — 10-value closed enum spanning revalidation/amendment/supersession/etc.
- `rkaf:mappingPredicate` — SKOS-aligned (`skos:exactMatch` / `closeMatch` / `broadMatch` / `narrowMatch` / `relatedMatch`).

**Predicates** (declared in `context/rkaf-context.jsonld` for graph traversal):

- `rkaf:supersedesAssertion` — many-to-many predicate (Core §1.5).
- `rkaf:derivesAuthorityFrom` — hop in an authority chain (Core §2.1).
- `rkaf:hasApplicability` — Warrant → ApplicabilityScope.
- `rkaf:hasEffectivePeriod` — Warrant / Authority → EffectivePeriod.
- `rkaf:bridgeContractVersion` — version pin on lifecycle packets + bridge validation results.

> Behavioral semantics (the `usageEligibility` reducer, the `CascadeClosureV1` algorithm, the 10 bridge contract rules) are normative prose in `archive/v0.1/spec/rkaf-core.md` and are *not* CUE-validatable. CUE + JSON Schema + SHACL validate shape; runtime correctness lives in the consuming SDK (`rkaf-validate`, future Layer 5 SDKs).
