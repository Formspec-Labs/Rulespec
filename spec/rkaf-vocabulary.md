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

## Vocabulary backlog — specified but not yet codified (§6)

The following Rulespec terms are part of the normative Vocabulary but have not yet been authored as CUE constraints under `constraints/core/`. They were defined in the pre-rebrand spec (now archived at `archive/v0.1/spec/rkaf-core.md`) and the v0.1 SHACL shape files (`archive/v0.1/shapes/`). Codifying each as a CUE constraint + regenerating JSON Schema + adding typed primitives to `rkaf-core` is open work.

The 17 backlog terms:

`rkaf:Attestation`, `rkaf:LocalAdoption`, `rkaf:Justification`, `rkaf:Authority` (subclass of `rkaf:Warrant`), `rkaf:ApplicabilityScope`, `rkaf:EffectivePeriod`, `rkaf:LifecycleEvent`, `rkaf:supersedesAssertion` (predicate), `rkaf:usageEligibility` (lattice), `rkaf:Concept`, `rkaf:ConceptMapping`, `rkaf:ConceptResolutionResult`, `rkaf:hasTrustZone`, `rkaf:hasSafetyLabel`, `rkaf:bridgeContractVersion`, `rkaf:BridgeValidationResult`, `rkaf:derivesAuthorityFrom`.

`rkaf:Assertion` and `rkaf:ConfidenceRecord` were promoted into the v0.2 normative tier and are codified.

Until the backlog is codified, consumers wanting to use these terms either (a) author them as `additionalProperties` on Rulespec nodes (validated by neither gate — workspace responsibility), or (b) reference the archived v0.1 SHACL shape definitions for semantic guidance.

> The `warrant-cross-family-transition-positive` fixture exercises `rkaf:derivesAuthorityFrom` — it serves as a reminder that the term is in active use but uncodified.
