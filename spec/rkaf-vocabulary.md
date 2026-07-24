# Rulespec Vocabulary v0.2 — Full Term Reference

> Mechanically-consumable. One row per term. Source of truth for code generators and projectors.
>
> Status: pre-release, normative. Mechanical consumers parse the table by markdown row. The `Required fixtures` column is enforced by `tools/vocab_audit.py` — every named fixture MUST exist under `fixtures/` as a `<name>.jsonld` file.

## v0.2 universal primitives (§§4.1-4.6 of `spec/rkaf-core.md`)

| Term | IRI | Kind | Domain | Range | Cardinality | Required fixtures |
|---|---|---|---|---|---|---|
| rkaf:Artifact | https://rulespec.org/ns/v1#Artifact | Class | — | — | — | artifact-eli-positive, artifact-doi-positive, artifact-cid-positive, artifact-us-cfr-positive, artifact-us-usc-positive, artifact-us-frdoc-positive, artifact-us-regsgov-positive, artifact-us-pl-positive, artifact-us-eo-positive |
| rkaf:hasArtifactIdentifier | https://rulespec.org/ns/v1#hasArtifactIdentifier | Property | rkaf:Artifact | IRI | 1..* | artifact-eli-positive |
| rkaf:artifactIdentifierScheme | https://rulespec.org/ns/v1#artifactIdentifierScheme | Property (closed enum) | rkaf:Artifact | rkaf:ArtifactIdentifierScheme | 1..* | artifact-eli-positive |
| rkaf:hasRegulatoryIdentifier | https://rulespec.org/ns/v1#hasRegulatoryIdentifier | Property | rkaf:Artifact | IRI | 0..1 | artifact-us-cfr-positive |
| rkaf:regulatoryIdentifierScheme | https://rulespec.org/ns/v1#regulatoryIdentifierScheme | Property (closed enum) | rkaf:Artifact | rkaf:USRegulatoryIdentifierScheme | 0..1 | artifact-us-cfr-positive |
| foaf:primaryTopic | http://xmlns.com/foaf/0.1/primaryTopic | Property (FOAF mode-1 import) | rkaf:Artifact | IRI | 0..1 | artifact-primary-topic-positive |
| dcterms:hasFormat | http://purl.org/dc/terms/hasFormat | Property (DCTERMS mode-1 import) | rkaf:Artifact | rkaf:Artifact | 0..* | artifact-cross-posting-positive |
| dcterms:isFormatOf | http://purl.org/dc/terms/isFormatOf | Property (DCTERMS mode-1 import) | rkaf:Artifact | rkaf:Artifact | 0..* | artifact-cross-posting-positive |
| rkaf:SourceFragment | https://rulespec.org/ns/v1#SourceFragment | Class (rdfs:subClassOf oa:SpecificResource) | — | — | — | sourcefragment-oa-textquote-positive, sourcefragment-oa-xpath-positive, sourcefragment-aknt-eid-positive, sourcefragment-uslm-section-positive |
| oa:hasSource | http://www.w3.org/ns/oa#hasSource | Property (OA 1.0 import) | rkaf:SourceFragment | rkaf:Artifact | 1 | sourcefragment-oa-textquote-positive |
| oa:hasSelector | http://www.w3.org/ns/oa#hasSelector | Property (OA 1.0 import) | rkaf:SourceFragment | oa:Selector | 1..* | sourcefragment-oa-textquote-positive |
| oa:exact | http://www.w3.org/ns/oa#exact | Property (OA 1.0 import) | oa:TextQuoteSelector | xsd:string | 1 (on TextQuoteSelector) | sourcefragment-oa-textquote-positive |
| oa:prefix | http://www.w3.org/ns/oa#prefix | Property (OA 1.0 import) | oa:TextQuoteSelector | xsd:string | 0..1 | sourcefragment-oa-textquote-positive |
| oa:suffix | http://www.w3.org/ns/oa#suffix | Property (OA 1.0 import) | oa:TextQuoteSelector | xsd:string | 0..1 | sourcefragment-oa-textquote-positive |
| rkaf:selectorKind | https://rulespec.org/ns/v1#selectorKind | Property (closed enum) | rkaf:SourceFragment | rkaf:SelectorKind | 1..* | sourcefragment-oa-textquote-positive |
| rkaf:EvidenceBinding | https://rulespec.org/ns/v1#EvidenceBinding | Class | — | — | — | evidencebinding-positive, evidencebinding-no-evidence-reason-positive, evidencebinding-missing-negative |
| rkaf:bindsAssertion | https://rulespec.org/ns/v1#bindsAssertion | Property | rkaf:EvidenceBinding | rkaf:Assertion | 1 | evidencebinding-positive |
| rkaf:bindsSourceFragment | https://rulespec.org/ns/v1#bindsSourceFragment | Property | rkaf:EvidenceBinding | rkaf:SourceFragment | 0..* | evidencebinding-positive |
| rkaf:noEvidenceReason | https://rulespec.org/ns/v1#noEvidenceReason | Property (closed enum) | rkaf:EvidenceBinding | rkaf:NoEvidenceReason | 0..1 | evidencebinding-no-evidence-reason-positive |
| rkaf:Warrant | https://rulespec.org/ns/v1#Warrant | Class | — | — | — | warrant-legal-positive, warrant-scientific-positive, warrant-cross-family-transition-positive |
| rkaf:hasWarrant | https://rulespec.org/ns/v1#hasWarrant | Property | rkaf:Assertion / rkaf:EvidenceBinding | rkaf:Warrant | 1..* | warrant-legal-positive |
| rkaf:warrantKind | https://rulespec.org/ns/v1#warrantKind | Property (closed enum) | rkaf:Warrant | rkaf:WarrantKind | 1 | warrant-legal-positive |
| rkaf:warrantFamily | https://rulespec.org/ns/v1#warrantFamily | Property (closed enum) | rkaf:Warrant | rkaf:WarrantFamily | 1 | warrant-legal-positive |
| rkaf:hasAuthority | https://rulespec.org/ns/v1#hasAuthority | Property (legal specialization of hasWarrant) | rkaf:Assertion / rkaf:Proceeding | rkaf:Authority | 1..* on Assertion; 0..* on Proceeding | warrant-legal-positive, proceeding-partner-positive |
| rkaf:ConfidenceRecord | https://rulespec.org/ns/v1#ConfidenceRecord | Class | — | — | — | confidencerecord-uncalibrated-positive, confidencerecord-calibrated-positive, confidencerecord-score-theater-negative |
| rkaf:hasConfidence | https://rulespec.org/ns/v1#hasConfidence | Property | rkaf:Assertion | rkaf:ConfidenceRecord | 0..* | confidencerecord-uncalibrated-positive |
| rkaf:confidenceMethod | https://rulespec.org/ns/v1#confidenceMethod | Property (closed enum) | rkaf:ConfidenceRecord | rkaf:ConfidenceMethod | 1 | confidencerecord-uncalibrated-positive |
| rkaf:calibrationStatus | https://rulespec.org/ns/v1#calibrationStatus | Property (closed enum) | rkaf:ConfidenceRecord | rkaf:CalibrationStatus | 1 | confidencerecord-uncalibrated-positive |
| rkaf:AccessScope | https://rulespec.org/ns/v1#AccessScope | Class | — | — | — | accessscope-public-positive, accessscope-organizationVisible-positive, accessscope-leak-negative |
| rkaf:hasAccessScope | https://rulespec.org/ns/v1#hasAccessScope | Property | rkaf:Assertion / rkaf:Attestation / rkaf:EvidenceBinding / rkaf:SourceFragment | rkaf:AccessScope | 0..1 | accessscope-public-positive |
| rkaf:accessScopeKind | https://rulespec.org/ns/v1#accessScopeKind | Property (closed enum) | rkaf:AccessScope | rkaf:AccessScopeKind | 1 | accessscope-public-positive |

## Experimental US rulemaking-process module

These terms are defined by `spec/rkaf-rulemaking.md`. Their status is Experimental; inclusion in the mechanically checked vocabulary does not satisfy the module's stabilization gate.

| Term | IRI | Kind | Domain | Range | Cardinality | Required fixtures |
|---|---|---|---|---|---|---|
| rkaf:RegulatoryAgendaItem | https://rulespec.org/ns/v1#RegulatoryAgendaItem | Class (rulemaking-profile specialization of dcat:Resource) | — | — | — | agenda-item-ordinary-positive, agenda-item-coast-guard-recurring-positive, agenda-item-faa-recurring-positive, agenda-item-repeated-unresolved-positive |
| rkaf:hasAgendaItemIdentifier | https://rulespec.org/ns/v1#hasAgendaItemIdentifier | Property | rkaf:RegulatoryAgendaItem | IRI | 1 | agenda-item-ordinary-positive |
| rkaf:agendaItemIdentifierScheme | https://rulespec.org/ns/v1#agendaItemIdentifierScheme | Property (closed enum) | rkaf:RegulatoryAgendaItem | rkaf:AgendaItemIdentifierScheme | 1 | agenda-item-ordinary-positive |
| rkaf:agendaScopeStatus | https://rulespec.org/ns/v1#agendaScopeStatus | Property (closed enum) | rkaf:RegulatoryAgendaItem | rkaf:AgendaScopeStatus | 0..1 | agenda-item-coast-guard-recurring-positive, agenda-item-repeated-unresolved-positive |
| rkaf:RegulatoryAgendaObservation | https://rulespec.org/ns/v1#RegulatoryAgendaObservation | Class (rdfs:subClassOf rkaf:Artifact and dcat:CatalogRecord) | — | — | — | agenda-observations-multiple-editions-positive |
| rkaf:agendaStage | https://rulespec.org/ns/v1#agendaStage | Property (closed enum) | rkaf:RegulatoryAgendaObservation | rkaf:AgendaStage | 0..1 | agenda-observations-multiple-editions-positive |
| rkaf:agendaPriority | https://rulespec.org/ns/v1#agendaPriority | Property (closed enum) | rkaf:RegulatoryAgendaObservation | rkaf:AgendaPriority | 0..1 | agenda-observations-multiple-editions-positive |
| rkaf:agendaAffectsCitation | https://rulespec.org/ns/v1#agendaAffectsCitation | Property | rkaf:RegulatoryAgendaObservation | `rkaf:us-cfr` IRI | 0..* | agenda-observations-multiple-editions-positive |
| rkaf:agendaAuthorityCitation | https://rulespec.org/ns/v1#agendaAuthorityCitation | Property | rkaf:RegulatoryAgendaObservation | `rkaf:us-usc` or `rkaf:us-pl` IRI | 0..* | agenda-observations-multiple-editions-positive |
| rkaf:AgendaProceedingRelationship | https://rulespec.org/ns/v1#AgendaProceedingRelationship | Class (rdfs:subClassOf dcat:Relationship) | — | — | — | agenda-item-ordinary-positive |
| dcat:qualifiedRelation | http://www.w3.org/ns/dcat#qualifiedRelation | Property (DCAT 3 mode-1 import) | rkaf:RegulatoryAgendaItem | rkaf:AgendaProceedingRelationship | 0..* | agenda-item-ordinary-positive |
| dcterms:relation | http://purl.org/dc/terms/relation | Property (DCAT qualified-relation composition) | rkaf:AgendaProceedingRelationship | rkaf:Proceeding | 1 | agenda-item-ordinary-positive |
| dcat:hadRole | http://www.w3.org/ns/dcat#hadRole | Property (DCAT 3 mode-1 import; fixed role `rkaf:agendaTracksProceeding`) | rkaf:AgendaProceedingRelationship | dcat:Role | 1 | agenda-item-ordinary-positive |
| rkaf:Proceeding | https://rulespec.org/ns/v1#Proceeding | Class (rulemaking-profile specialization of dcat:Resource) | — | — | — | proceeding-partner-positive |
| rkaf:hasProceedingIdentifier | https://rulespec.org/ns/v1#hasProceedingIdentifier | Property | rkaf:Proceeding | IRI | 1 | proceeding-partner-positive |
| rkaf:proceedingIdentifierScheme | https://rulespec.org/ns/v1#proceedingIdentifierScheme | Property (closed enum) | rkaf:Proceeding | rkaf:ProceedingIdentifierScheme | 1 | proceeding-partner-positive |
| rkaf:identifierRegistry | https://rulespec.org/ns/v1#identifierRegistry | Property | rkaf:Proceeding / rkaf:Docket | IRI | 1 when identity scheme is `official-registry`; otherwise 0..1 | proceeding-official-registry-positive |
| rkaf:Docket | https://rulespec.org/ns/v1#Docket | Class | — | — | — | docket-us-regsgov-positive |
| rkaf:hasDocketIdentifier | https://rulespec.org/ns/v1#hasDocketIdentifier | Property | rkaf:Docket | IRI | 1 | docket-us-regsgov-positive |
| rkaf:docketIdentifierScheme | https://rulespec.org/ns/v1#docketIdentifierScheme | Property (closed enum) | rkaf:Docket | rkaf:DocketIdentifierScheme | 1 | docket-us-regsgov-positive |
| rkaf:hasDocket | https://rulespec.org/ns/v1#hasDocket | Property | rkaf:Proceeding | rkaf:Docket | 0..* | proceeding-partner-positive |
| rkaf:CommentPeriod | https://rulespec.org/ns/v1#CommentPeriod | Class | — | — | — | commentperiod-positive |
| rkaf:proceedingStage | https://rulespec.org/ns/v1#proceedingStage | Property (closed enum) | rkaf:Proceeding | rkaf:ProceedingStage | 0..1 | proceeding-partner-positive |
| rkaf:proceedingTerminationCause | https://rulespec.org/ns/v1#proceedingTerminationCause | Property (closed enum) | rkaf:Proceeding | rkaf:ProceedingTerminationCause | 1 when stage is `proceedingConcluded`; otherwise 0..1 | proceeding-concluded-positive |
| rkaf:proceedingAffects | https://rulespec.org/ns/v1#proceedingAffects | Property | rkaf:Proceeding | rkaf:Artifact | 0..* | proceeding-partner-positive |
| rkaf:proceedingAffectsCitation | https://rulespec.org/ns/v1#proceedingAffectsCitation | Property | rkaf:Proceeding | `rkaf:us-cfr` IRI | 0..* | proceeding-partner-positive |
| rkaf:proceedingProduces | https://rulespec.org/ns/v1#proceedingProduces | Property | rkaf:Proceeding | rkaf:Artifact | 0..* | proceeding-partner-positive |
| rkaf:proceedingSupersedes | https://rulespec.org/ns/v1#proceedingSupersedes | Property | rkaf:Proceeding | rkaf:Proceeding | 0..* | proceeding-continuity-positive |
| rkaf:publishedInProceeding | https://rulespec.org/ns/v1#publishedInProceeding | Property | rkaf:Artifact | rkaf:Proceeding | 0..* | artifact-us-frdoc-positive |
| rkaf:commentPeriodFor | https://rulespec.org/ns/v1#commentPeriodFor | Property | rkaf:CommentPeriod | rkaf:Proceeding | 0..*; at least one Proceeding or Docket anchor | commentperiod-positive |
| rkaf:commentPeriodDocket | https://rulespec.org/ns/v1#commentPeriodDocket | Property | rkaf:CommentPeriod | rkaf:Docket | 0..*; at least one Proceeding or Docket anchor | commentperiod-docket-only-positive |
| rkaf:commentPeriodOpenedBy | https://rulespec.org/ns/v1#commentPeriodOpenedBy | Property | rkaf:CommentPeriod | rkaf:Artifact | 0..* | commentperiod-positive |
| rkaf:commentPeriodStart | https://rulespec.org/ns/v1#commentPeriodStart | Property | rkaf:CommentPeriod | xsd:date | 1 | commentperiod-positive |
| rkaf:commentPeriodEnd | https://rulespec.org/ns/v1#commentPeriodEnd | Property | rkaf:CommentPeriod | xsd:date | 1 | commentperiod-positive |
| prov:wasDerivedFrom | http://www.w3.org/ns/prov#wasDerivedFrom | Property (PROV-O import) | rkaf:CommentPeriod / rkaf:AgendaProceedingRelationship | prov:Entity | 1..* | commentperiod-positive, agenda-item-ordinary-positive |

`rkaf:proceedingStage` uses the seven stage-family lifecycle IRIs:
`rkaf:proceedingPrerule`, `rkaf:proceedingProposed`,
`rkaf:proceedingSupplemental`, `rkaf:proceedingFinal`,
`rkaf:proceedingWithdrawn`, `rkaf:proceedingLongterm`, and
`rkaf:proceedingConcluded`.

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
| `rkaf:LifecycleEvent` | `lifecycle-event.cue` | `lifecycleevent-positive.jsonld` | Audit-trail event for assertion, concept, and proceeding-stage transitions. |
| `rkaf:RegisteredConcept` | `concept.cue` | `concept-registered-positive.jsonld` | Federation-shared Concept minted by a `rkaf:ConceptMintingAuthority`. Requires `skos:prefLabel(1)`. |
| `rkaf:LocalConcept` | `concept.cue` | `localconcept-positive.jsonld` | Workspace-defined Concept, candidate for federation promotion. Requires `skos:prefLabel(1)`. |
| `skos:prefLabel` | `http://www.w3.org/2004/02/skos/core#prefLabel` | Property (SKOS 2.0 import) | `rkaf:RegisteredConcept`, `rkaf:LocalConcept` | `xsd:string` | **1** (required) | `concept-registered-positive.jsonld`, `localconcept-positive.jsonld` |
| `skos:altLabel` | `http://www.w3.org/2004/02/skos/core#altLabel` | Property (SKOS 2.0 import) | `rkaf:RegisteredConcept`, `rkaf:LocalConcept` | `xsd:string` | 0..* | — |
| `skos:broader` | `http://www.w3.org/2004/02/skos/core#broader` | Property (SKOS 2.0 import) | `rkaf:RegisteredConcept`, `rkaf:LocalConcept` | IRI | 0..1 | — |
| `skos:narrower` | `http://www.w3.org/2004/02/skos/core#narrower` | Property (SKOS 2.0 import) | `rkaf:RegisteredConcept`, `rkaf:LocalConcept` | IRI | 0..* | — |
| `skos:related` | `http://www.w3.org/2004/02/skos/core#related` | Property (SKOS 2.0 import) | `rkaf:RegisteredConcept`, `rkaf:LocalConcept` | IRI | 0..* | — |
| `rkaf:ConceptMapping` | `concept-mapping.cue` | `conceptmapping-positive.jsonld` | SKOS-mapping between concepts. Closed `mappingPredicate` enum. |
| `rkaf:MappingApplicabilityContext` | `concept-mapping.cue` | `mappingapplicabilitycontext-positive.jsonld` | Scopes a mapping by application-domain + evidence-purpose. |
| `rkaf:ConceptResolutionResult` | `concept-resolution-result.cue` | `conceptresolutionresult-positive.jsonld` | Output of resolving a concept reference against the federation. |
| `rkaf:BridgeValidationResult` | `bridge-validation-result.cue` | `bridgevalidationresult-positive.jsonld` | Control-plane record per packet ingestion: verdict + effective eligibility + authority-chain status + `findings: [rkaf:Finding @id, …]` (ADR-0093 Phase C replaces the prior flat `warnings/errors/staleDependencies/registryUnavailable/registryVersionOutOfRange` arrays with this typed IRI list). |
| `rkaf:BridgeConsumerRegistration` | `bridge-consumer-registration.cue` | `bridgeconsumerregistration-positive.jsonld` | Bridge consumer capability declaration (Core §5.1): supported authority kinds, evaluation anchors, registry version ranges, automatic migrations. |
| `rkaf:RegistryConflict` | `registry-conflict.cue` | `registryconflict-positive.jsonld` | Two or more registry entries disagree on the same canonical claim (Appendix A; v0.1.2 §8 MappingConflict generalization). Closed severity enum. |
| `rkaf:Justification` | `justification.cue` | `justification-positive.jsonld` | Warrant-family-agnostic grounding record carried by ConceptMapping or other nodes (`hasJustification` predicate). Generalizes v0.1.2's authority-chain hop. |
| `rkaf:GeneratedWorkProduct` | `generated-work-product.cue` | `generatedworkproduct-positive.jsonld` | Overlay type for downstream consumer artifacts (forms, workflows, notices) that Rulespec cascades over. Carries `justifiedByAssertion` + `bridgeContractVersion`. (Core §6.1; bridge rule #10.) |
| `rkaf:PointInTimeException` | `point-in-time-exception.cue` | `pointintimeexception-positive.jsonld` | Carried by a LifecycleEvent: retains an Assertion or WorkProduct for an in-flight case anchored to a specific `EvaluationAnchor`. Consumers MUST honor only when the anchor is in their supported set. (Core §4.6.) |
| `rkaf:EvaluationAnchor` | `evaluation-anchor.cue` | `evaluationanchor-positive.jsonld` | Closed enum of 9 anchor kinds (`applicationSubmissionTime`, `eventOccurrenceTime`, `eligibilityDeterminationTime`, `noticeGenerationTime`, `workflowStartTime`, `workflowStepStartTime`, `currentTime`, `effectivePeriodStart`, `publicationTime`). Used by PIT + BridgeConsumerRegistration. (Core §4.7.) |
| `rkaf:RevalidationEvent` | `revalidation-event.cue` | `revalidationevent-positive.jsonld` | Emitted on cascade ingest; remains open until a paired `RevalidationClosureEvent` references it. Target is an Assertion or WorkProduct; carries an optional successor list. (Core §4.8.) |
| `rkaf:RevalidationClosureEvent` | `revalidation-event.cue` | `revalidationevent-positive.jsonld` | Closes a `RevalidationEvent` with a deterministic closure decision and optional successor Assertion or WorkProduct. (Core §4.8.) |
| `rkaf:BridgeIssueAttestationContract` | `bridge-issue-attestation-contract.cue` | `bridgeissueattestationcontract-positive.jsonld` | Enumerates which `BridgeValidationResult` issue kinds MUST yield a matching `Attestation` for the BVR to be acceptable. Load-bearing for bridge rule #8. (Plan 7b §3.) |
| `rkaf:ConsumerEffectiveDeclaration` | `consumer-effective-declaration.cue` | `consumereffectivedeclaration-positive.jsonld` | A consumer's declared effective `usageEligibility` for an Assertion in a given scope. The reducer's output MUST equal or exceed this on the lattice; a higher declared value is forbidden broadening (bridge rule #2). (Plan 7b §3.) |
| `rkaf:Finding` | `finding.cue` | `finding-positive.jsonld` | First-class IRI-addressable record of a single validation/audit detection. Promoted in ADR-0093 from `BridgeValidationResult`'s flat string arrays so downstream primitives can REFERENCE a Finding by IRI — enables waiver-shaped Attestations (`rkaf:targetFinding`), Trellis anchoring of validation outcomes, and Studio readiness-tier projection. Carries closed `findingKind` + `severity` enums. |

**Closed enums and lattices** (referenced by the classes above):

- `rkaf:usageEligibility` — 7-level lattice from `notEligible` (lowest) to `officialUse` (highest). Consumers MAY narrow; only LocalAdoption MAY broaden within its declared scope.
- `rkaf:hasTrustZone` — `rkaf:Z0` through `rkaf:Z8`. Structural property (kind of object).
- `rkaf:hasSafetyLabel` — `D0` / `S1` / `R2` / `A3` / `P4` plus advisory + authority-critical refinements. Operational property (what the consumer may do).
- `rkaf:authorityKind` — 8-value closed enum, hop-local. Federation refuses unsupported kinds.
- `rkaf:lifecycleEventKind` — 22-value closed enum spanning revalidation, amendment, supersession, concept transitions, seven experimental proceeding-stage transitions, and five judicial/congressional proceeding events.
- `rkaf:mappingPredicate` — SKOS-aligned (`skos:exactMatch` / `closeMatch` / `broadMatch` / `narrowMatch` / `relatedMatch`).

**Predicates** (declared in `context/rkaf-context.jsonld` for graph traversal):

- `rkaf:supersedesAssertion` — many-to-many predicate (Core §1.5).
- `rkaf:derivesAuthorityFrom` — hop in an authority chain (Core §2.1).
- `rkaf:hasApplicability` — Warrant → ApplicabilityScope.
- `rkaf:hasEffectivePeriod` — Warrant / Authority / ApplicabilityScope / Attestation → EffectivePeriod. Plan 7d extends the domain to `Attestation`; same predicate, same semantics (validity window for the bearer). `cascade::is_active` reads exactly this edge across all domains.
- `rkaf:revokedAt` — Attestation → xsd:dateTime (Plan 7d). Retraction marker. If set and ≤ evaluation time, the Attestation is no longer effective regardless of `hasEffectivePeriod`. Universal across legal, scientific, editorial, AI-substrate attestations.
- `rkaf:lastVerifiedAt` — Attestation / SourceFragment / EvidenceBinding / BridgeValidationResult → xsd:dateTime (Plan 7d). When the bearer was last reconfirmed against its source. ORTHOGONAL to lifecycle state: lifecycle answers "is this in force?", freshness answers "when did we last check?". Consumers MAY narrow eligibility based on a max-staleness window. Lifecycle decisions MUST NOT be gated by freshness, and freshness MUST NOT be gated by lifecycle (§5 normative invariant).
- `rkaf:verifiedBy` — Attestation / SourceFragment / EvidenceBinding / BridgeValidationResult → IRI of verifier (Plan 7d). Pairs with `lastVerifiedAt`; identifies the party that performed the most recent reconfirmation.
- `rkaf:targetFinding` — Attestation → IRI of `rkaf:Finding` (ADR-0093 Phase B, RFC-pending). When set, the Attestation is acting AS a waiver / override of the targeted Finding. The Attestation decides what to DO (accept, waive, escalate) about a detection the Finding has IRI-addressably recorded. Decoupled because: (a) the Finding stays a stable referenceable record across reviews; (b) multiple Attestations may target the same Finding over its lifetime; (c) Trellis can anchor Finding IRIs uniformly across consumer systems.
- `rkaf:bridgeContractVersion` — version pin on lifecycle packets + bridge validation results.
- `rkaf:maxAttestationStalenessDays` — BridgeConsumerRegistration → xsd:integer (Plan 7e.2). Optional freshness window in days. When set, the L4 reducer (§1.2 step 5.5) narrows usageEligibility one lattice step downward if any relevant Attestation's `lastVerifiedAt` is older than `evaluation_time - maxAttestationStalenessDays`. Absent ⇒ no freshness gate. Strictly downward-narrowing; never broadens.
- `rkaf:evaluationTime` — BehaviorTestCase → xsd:dateTime (Plan 7e.2). Optional fixture input that drives the reducer's freshness gate. Absent ⇒ gate skipped (no freshness check). Production runtimes derive `evaluation_time` from packet context (e.g., the BVR's `validatedAt` or the workflow's evaluation instant).

> Behavioral semantics (the `usageEligibility` reducer, the `CascadeClosureV1` algorithm, the 10 bridge contract rules) are normative prose in `spec/rkaf-behavior.md` and are *not* CUE-validatable. CUE + JSON Schema + SHACL validate shape; runtime correctness is gated by `rkaf-behavior-validate`.
