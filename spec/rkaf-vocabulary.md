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
| foaf:primaryTopic | http://xmlns.com/foaf/0.1/primaryTopic | Property (FOAF mode-1 import) | rkaf:Artifact | IRI | 0..1 | artifact-primary-topic-positive |
| dcterms:hasFormat | http://purl.org/dc/terms/hasFormat | Property (DCTERMS mode-1 import) | rkaf:Artifact | rkaf:Artifact | 0..* | artifact-cross-posting-positive |
| dcterms:isFormatOf | http://purl.org/dc/terms/isFormatOf | Property (DCTERMS mode-1 import) | rkaf:Artifact | rkaf:Artifact | 0..* | artifact-cross-posting-positive |
| dcterms:isVersionOf | http://purl.org/dc/terms/isVersionOf | Property (DCTERMS mode-1 import) | rkaf:Artifact | IRI | 0..* | artifact-version-lineage-positive |
| prov:wasRevisionOf | http://www.w3.org/ns/prov#wasRevisionOf | Property (PROV-O mode-1 import) | rkaf:Artifact | rkaf:Artifact | 0..* | artifact-version-lineage-positive |
| rkaf:hasContentDigest | https://rulespec.org/ns/v1#hasContentDigest | Property | rkaf:Artifact | xsd:string (`sha256:<64 hex>`) | 0..1 (1 when versionLineageEvidence present) | artifact-content-digest-positive, artifact-version-lineage-positive |
| rkaf:versionLineageEvidence | https://rulespec.org/ns/v1#versionLineageEvidence | Property | rkaf:Artifact | rkaf:SourceFragment | 0..* (1..* when dcterms:isVersionOf or prov:wasRevisionOf present) | artifact-version-lineage-positive |
| rkaf:SourceFragment | https://rulespec.org/ns/v1#SourceFragment | Class (rdfs:subClassOf oa:SpecificResource) | — | — | — | sourcefragment-oa-textquote-positive, sourcefragment-oa-xpath-positive, sourcefragment-aknt-eid-positive, sourcefragment-uslm-section-positive, sourcefragment-position-selector-positive |
| oa:hasSource | http://www.w3.org/ns/oa#hasSource | Property (OA 1.0 import) | rkaf:SourceFragment | rkaf:Artifact | 1 | sourcefragment-oa-textquote-positive |
| oa:hasSelector | http://www.w3.org/ns/oa#hasSelector | Property (OA 1.0 import) | rkaf:SourceFragment | oa:Selector | 1..* | sourcefragment-oa-textquote-positive |
| oa:exact | http://www.w3.org/ns/oa#exact | Property (OA 1.0 import) | oa:TextQuoteSelector | xsd:string | 1 (on TextQuoteSelector) | sourcefragment-oa-textquote-positive |
| oa:prefix | http://www.w3.org/ns/oa#prefix | Property (OA 1.0 import) | oa:TextQuoteSelector | xsd:string | 0..1 | sourcefragment-oa-textquote-positive |
| oa:suffix | http://www.w3.org/ns/oa#suffix | Property (OA 1.0 import) | oa:TextQuoteSelector | xsd:string | 0..1 | sourcefragment-oa-textquote-positive |
| oa:start | http://www.w3.org/ns/oa#start | Property (OA 1.0 import) | oa:TextPositionSelector | xsd:integer (>= 0) | 1 (on TextPositionSelector) | sourcefragment-position-selector-positive |
| oa:end | http://www.w3.org/ns/oa#end | Property (OA 1.0 import) | oa:TextPositionSelector | xsd:integer (>= 0) | 1 (on TextPositionSelector) | sourcefragment-position-selector-positive |
| rkaf:selectorKind | https://rulespec.org/ns/v1#selectorKind | Property (closed enum) | rkaf:SourceFragment | rkaf:SelectorKind | 1..* | sourcefragment-oa-textquote-positive |
| rkaf:coordinateSystem | https://rulespec.org/ns/v1#coordinateSystem | Property (closed enum) | oa:TextPositionSelector | rkaf:CoordinateSystem | 1 (on TextPositionSelector) | sourcefragment-position-selector-positive |
| rkaf:sourceArtifactDigest | https://rulespec.org/ns/v1#sourceArtifactDigest | Property | rkaf:SourceFragment | xsd:string (`sha256:<64 hex>`) | 0..1 | sourcefragment-position-selector-positive |
| rkaf:fragmentContentDigest | https://rulespec.org/ns/v1#fragmentContentDigest | Property | rkaf:SourceFragment | xsd:string (`sha256:<64 hex>`) | 0..1 | sourcefragment-position-selector-positive |
| rkaf:FragmentIdentityScheme | https://rulespec.org/ns/v1#FragmentIdentityScheme | Closed enum (2 values) | — | — | — | conceptassignment-carrier-local-fragment-positive |
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
| rkaf:RelationshipAssertion | https://rulespec.org/ns/v1#RelationshipAssertion | Class (specialization of rkaf:Assertion) | — | — | — | relationshipassertion-denied-positive, relationshipassertion-affirmed-positive |
| rkaf:assertsSubject | https://rulespec.org/ns/v1#assertsSubject | Property | rkaf:RelationshipAssertion / rkaf:ValueAssertion | IRI | 1 | relationshipassertion-denied-positive, valueassertion-date-positive |
| rkaf:assertsPredicate | https://rulespec.org/ns/v1#assertsPredicate | Property | rkaf:RelationshipAssertion / rkaf:ValueAssertion | IRI | 1 | relationshipassertion-denied-positive, valueassertion-date-positive |
| rkaf:assertsObject | https://rulespec.org/ns/v1#assertsObject | Property | rkaf:RelationshipAssertion | IRI | 1 | relationshipassertion-denied-positive |
| rkaf:assertionPolarity | https://rulespec.org/ns/v1#assertionPolarity | Property (closed enum) | rkaf:RelationshipAssertion / rkaf:ValueAssertion | rkaf:AssertionPolarity | 1 | relationshipassertion-denied-positive, relationshipassertion-affirmed-positive |
| rkaf:ValueAssertion | https://rulespec.org/ns/v1#ValueAssertion | Class (specialization of rkaf:Assertion) | — | — | — | valueassertion-date-positive, valueassertion-denied-integer-positive, valueassertion-ai-suggested-positive |
| rkaf:assertsValue | https://rulespec.org/ns/v1#assertsValue | Property (typed literal) | rkaf:ValueAssertion | JSON-LD value object over rkaf:ValueDatatype | 1 | valueassertion-date-positive |
| rkaf:assertedAt | https://rulespec.org/ns/v1#assertedAt | Property | rkaf:Assertion / rkaf:Justification | xsd:dateTime | 0..1 | valueassertion-date-positive |
| rkaf:supersedesAssertion | https://rulespec.org/ns/v1#supersedesAssertion | Property | rkaf:Assertion | rkaf:Assertion | 0..* | valueassertion-ai-suggested-positive |
| rkaf:assertionOrigin | https://rulespec.org/ns/v1#assertionOrigin | Property (closed enum; assertion envelope) | any `#AssertionEnvelope` composer — rkaf:Assertion / rkaf:RelationshipAssertion / rkaf:ValueAssertion / rkaf:ConceptAssignment / rkaf:RelationChangeEvent / rkaf:ClosureClaim | rkaf:AssertionOrigin | 1 | relationshipassertion-denied-positive, conceptassignment-fragment-direct-positive |
| rkaf:hasJustification | https://rulespec.org/ns/v1#hasJustification | Property (assertion envelope) | any `#AssertionEnvelope` composer — rkaf:Assertion / rkaf:RelationshipAssertion / rkaf:ValueAssertion / rkaf:ConceptAssignment / rkaf:RelationChangeEvent / rkaf:ClosureClaim | rkaf:Justification | 0..1 | modelcard-minimal-positive |
| rkaf:consumerLifecycleState | https://rulespec.org/ns/v1#consumerLifecycleState | Property (closed enum; consumer disposition) | any `#ConsumerDisposition` composer — the envelope composers above — and rkaf:GeneratedWorkProduct, which is NOT a composer: it restates this one property by hand (`constraints/core/generated-work-product.cue`) and takes neither of `#ConsumerDisposition`'s other two | rkaf:ConsumerLifecycleState | 0..1 | generatedworkproduct-positive |
| rkaf:SourceClaimant | https://rulespec.org/ns/v1#SourceClaimant | Class | — | — | — | sourceclaimant-named-positive, sourceclaimant-issuer-positive |
| rkaf:hasSourceClaimant | https://rulespec.org/ns/v1#hasSourceClaimant | Property | rkaf:Assertion | rkaf:SourceClaimant | 0..1 | valueassertion-denied-integer-positive |
| rkaf:claimsAssertion | https://rulespec.org/ns/v1#claimsAssertion | Property | rkaf:SourceClaimant | rkaf:Assertion | 1 | sourceclaimant-named-positive |
| rkaf:claimantAttribution | https://rulespec.org/ns/v1#claimantAttribution | Property (closed enum) | rkaf:SourceClaimant | rkaf:ClaimantAttribution | 1 | sourceclaimant-named-positive, sourceclaimant-issuer-positive |
| rkaf:claimantText | https://rulespec.org/ns/v1#claimantText | Property | rkaf:SourceClaimant | xsd:string | 0..1 (1 when claimantNamedInSource) | sourceclaimant-named-positive |
| rkaf:claimantIdentity | https://rulespec.org/ns/v1#claimantIdentity | Property | rkaf:SourceClaimant | IRI | 0..1 | sourceclaimant-named-positive |
| rkaf:attributedInFragment | https://rulespec.org/ns/v1#attributedInFragment | Property | rkaf:SourceClaimant | rkaf:SourceFragment | 0..* | sourceclaimant-named-positive |
| rkaf:ExtractionActivity | https://rulespec.org/ns/v1#ExtractionActivity | Class | — | — | — | extractionactivity-model-positive, extractionactivity-deterministic-positive |
| rkaf:hasExtractionProvenance | https://rulespec.org/ns/v1#hasExtractionProvenance | Property | rkaf:Assertion | rkaf:ExtractionActivity | 0..1 | valueassertion-ai-suggested-positive |
| rkaf:extractionMethod | https://rulespec.org/ns/v1#extractionMethod | Property (closed enum) | rkaf:ExtractionActivity | rkaf:ExtractionMethod | 1 | extractionactivity-model-positive |
| rkaf:extractionRun | https://rulespec.org/ns/v1#extractionRun | Property | rkaf:ExtractionActivity | IRI | 1 | extractionactivity-model-positive |
| rkaf:extractedBy | https://rulespec.org/ns/v1#extractedBy | Property | rkaf:ExtractionActivity | IRI | 1 | extractionactivity-model-positive |
| rkaf:extractorVersion | https://rulespec.org/ns/v1#extractorVersion | Property | rkaf:ExtractionActivity | xsd:string | 1 | extractionactivity-model-positive |
| rkaf:requestContractDigest | https://rulespec.org/ns/v1#requestContractDigest | Property | rkaf:ExtractionActivity | xsd:string (`sha256:<64 hex>`) | 0..1 (REQUIRED if extractionMethod is rkaf:modelExtraction) | extractionactivity-model-positive |
| rkaf:extractionModelRef | https://rulespec.org/ns/v1#extractionModelRef | Property | rkaf:ExtractionActivity | IRI | 0..1 (1 when modelExtraction) | extractionactivity-model-positive |
| rkaf:extractionPromptRef | https://rulespec.org/ns/v1#extractionPromptRef | Property | rkaf:ExtractionActivity | IRI | 0..1 | extractionactivity-model-positive |
| rkaf:inputDigest | https://rulespec.org/ns/v1#inputDigest | Property | rkaf:ExtractionActivity | xsd:string (`sha256:<64 hex>`) | 0..* | extractionactivity-model-positive |
| rkaf:extractionAttempt | https://rulespec.org/ns/v1#extractionAttempt | Property | rkaf:ExtractionActivity | xsd:integer (>= 1) | 0..1 | extractionactivity-model-positive |

## v0.2 concept vocabulary and assignments (§4.7 of `spec/rkaf-core.md`)

SKOS owns concept-scheme semantics. The rows below add only what SKOS leaves
open and Rulespec must check mechanically: which facet a scheme controls, who
governs the scheme, and the evidence an assignment stands on. `skos:inScheme`,
`skos:definition`, and `skos:hasTopConcept` are mode-1 SKOS imports used with
their own semantics; Rulespec declares no class range over them, because a
concept or scheme may live in an external thesaurus.

| Term | IRI | Kind | Domain | Range | Cardinality | Required fixtures |
|---|---|---|---|---|---|---|
| rkaf:ConceptScheme | https://rulespec.org/ns/v1#ConceptScheme | Class (skos:ConceptScheme-compatible) | — | — | — | conceptscheme-registry-positive, conceptscheme-local-positive |
| rkaf:schemeFacet | https://rulespec.org/ns/v1#schemeFacet | Property | rkaf:ConceptScheme | IRI | 1 | conceptscheme-registry-positive |
| rkaf:conceptStatus | https://rulespec.org/ns/v1#conceptStatus | Property (closed enum) | rkaf:ConceptScheme / rkaf:RegisteredConcept / rkaf:LocalConcept | rkaf:ConceptStatus | 1 | conceptscheme-registry-positive, concept-registered-positive, localconcept-positive |
| rkaf:managedByRegistry | https://rulespec.org/ns/v1#managedByRegistry | Property | rkaf:ConceptScheme / rkaf:RegisteredConcept / rkaf:ConceptMapping | IRI of a concept registry | 1 on rkaf:RegisteredConcept; on rkaf:ConceptScheme exactly one of managedByRegistry or definedInScope; 0..1 on rkaf:ConceptMapping | conceptscheme-registry-positive, concept-registered-positive |
| rkaf:definedInScope | https://rulespec.org/ns/v1#definedInScope | Property | rkaf:ConceptScheme / rkaf:LocalConcept | IRI of the owning Workspace or organizational scope | 1 on rkaf:LocalConcept; on rkaf:ConceptScheme exactly one of managedByRegistry or definedInScope | conceptscheme-local-positive, localconcept-positive |
| rkaf:conceptScope | https://rulespec.org/ns/v1#conceptScope | Property | rkaf:RegisteredConcept / rkaf:LocalConcept | xsd:string | 1 | concept-registered-positive, localconcept-positive |
| skos:inScheme | http://www.w3.org/2004/02/skos/core#inScheme | Property (SKOS mode-1 import) | rkaf:RegisteredConcept / rkaf:LocalConcept / rkaf:ConceptAssignment | IRI of a concept scheme | 1 | concept-registered-positive, localconcept-positive, conceptassignment-fragment-direct-positive |
| skos:definition | http://www.w3.org/2004/02/skos/core#definition | Property (SKOS mode-1 import) | rkaf:RegisteredConcept / rkaf:LocalConcept / rkaf:ConceptScheme | xsd:string | 0..1 (1 when conceptStatus is rkaf:promoted) | conceptscheme-registry-positive |
| skos:hasTopConcept | http://www.w3.org/2004/02/skos/core#hasTopConcept | Property (SKOS mode-1 import) | rkaf:ConceptScheme | IRI | 0..* | conceptscheme-registry-positive |
| rkaf:ConceptAssignment | https://rulespec.org/ns/v1#ConceptAssignment | Class (composes the Assertion envelope) | — | — | — | conceptassignment-fragment-direct-positive, conceptassignment-document-derived-positive |
| rkaf:assignmentSubject | https://rulespec.org/ns/v1#assignmentSubject | Property | rkaf:ConceptAssignment | rkaf:Artifact or rkaf:SourceFragment | 1 | conceptassignment-fragment-direct-positive |
| rkaf:assignmentSubjectType | https://rulespec.org/ns/v1#assignmentSubjectType | Property (closed enum) | rkaf:ConceptAssignment | rkaf:AssignmentSubjectType | 1 | conceptassignment-fragment-direct-positive, conceptassignment-document-derived-positive |
| rkaf:assignedConcept | https://rulespec.org/ns/v1#assignedConcept | Property | rkaf:ConceptAssignment | IRI of a concept | 1 | conceptassignment-fragment-direct-positive |
| rkaf:assignmentRole | https://rulespec.org/ns/v1#assignmentRole | Property (closed enum) | rkaf:ConceptAssignment | rkaf:ConceptAssignmentRole | 1 | conceptassignment-document-derived-positive |
| rkaf:assignmentDerivation | https://rulespec.org/ns/v1#assignmentDerivation | Property (closed enum) | rkaf:ConceptAssignment | rkaf:AssignmentDerivation | 1 | conceptassignment-fragment-direct-positive, conceptassignment-document-derived-positive |
| rkaf:assignmentEvidence | https://rulespec.org/ns/v1#assignmentEvidence | Property | rkaf:ConceptAssignment | rkaf:SourceFragment | 0..* (1..* when subject is a SourceFragment, and when derivation is direct) | conceptassignment-fragment-direct-positive |
| rkaf:assignmentEvidenceScheme | https://rulespec.org/ns/v1#assignmentEvidenceScheme | Property (closed enum) | rkaf:ConceptAssignment | rkaf:FragmentIdentityScheme | 1 when assignmentEvidence present | conceptassignment-fragment-direct-positive, conceptassignment-carrier-local-fragment-positive |
| rkaf:supportingAssignment | https://rulespec.org/ns/v1#supportingAssignment | Property | rkaf:ConceptAssignment | rkaf:ConceptAssignment | 0..* (1..* when derivation is derived) | conceptassignment-document-derived-positive |
| rkaf:assignmentPolicyVersion | https://rulespec.org/ns/v1#assignmentPolicyVersion | Property | rkaf:ConceptAssignment | xsd:string | 0..1 (1 when supportingAssignment present) | conceptassignment-document-derived-positive |

## Document-analysis module (`spec/rkaf-analysis.md`)

These terms are defined by `spec/rkaf-analysis.md` and codified under `constraints/analysis/`, which compiles to `compiled/<target>/analysis/` and `crates/rkaf-core/src/generated/analysis/`. The module is neither the kernel nor a profile: it declares generic, jurisdiction-free contracts for comparing relations across document versions, and the dependency direction is kernel <- analysis <- profiles. The kernel under `constraints/core/` declares none of these terms and references none of these shapes (`AnalysisModuleTests` in `tools/test_constraints_compile.py` fails the build if it ever does); this module may compose kernel shapes, and does — `rkaf:RelationChangeEvent` and `rkaf:ClosureClaim` both compose `#AssertionEnvelope`, which is why `rkaf:assertionOrigin`, `rkaf:hasAILineage`, `rkaf:hasExtractionProvenance`, `rkaf:assertedAt`, and the rest of the envelope appear on them without being restated here.

The module declares **no legal-effect vocabulary**. There is no policy-exclusion, rescission, legal-effect, or severity term, and none may be added: a domain reading of a change or a finding belongs to a profile, after that profile's own authority, applicability, deontic, source, and closure rules pass (`spec/rkaf-analysis.md` §7).

`rkaf:ClosureClaim` and its six properties are **Experimental and DISABLED**. `rkaf:closureClaimStatus` is closed over the single value `rkaf:closureClaimDisabled`; no `rkaf:RelationFinding` may reach a `rkaf:ClosureClaim` through any path; no omission finding kind and no closure resolver proof type exist. Inclusion in this mechanically checked table records the shape; it does not enable the record. See `spec/rkaf-analysis.md` §6.

| Term | IRI | Kind | Domain | Range | Cardinality | Required fixtures |
|---|---|---|---|---|---|---|
| rkaf:RelationChangeEvent | https://rulespec.org/ns/v1#RelationChangeEvent | Class (composes the Assertion envelope; NOT an rkaf:Assertion and NOT an rkaf:LifecycleEvent) | — | — | — | relationchangeevent-removal-positive, relationchangeevent-replacement-positive |
| rkaf:changeSubject | https://rulespec.org/ns/v1#changeSubject | Property | rkaf:RelationChangeEvent | IRI | 1 | relationchangeevent-removal-positive |
| rkaf:changePredicate | https://rulespec.org/ns/v1#changePredicate | Property | rkaf:RelationChangeEvent | IRI | 1 | relationchangeevent-removal-positive |
| rkaf:changeObject | https://rulespec.org/ns/v1#changeObject | Property | rkaf:RelationChangeEvent | IRI | 1 | relationchangeevent-removal-positive |
| rkaf:relationChangeOperation | https://rulespec.org/ns/v1#relationChangeOperation | Property (closed enum) | rkaf:RelationChangeEvent | rkaf:RelationChangeOperation | 1 | relationchangeevent-removal-positive, relationchangeevent-replacement-positive |
| rkaf:relationAdoption, rkaf:relationRemoval, rkaf:relationSuspension, rkaf:relationReplacement | `https://rulespec.org/ns/v1#` + each local name in the Term cell | Values of `rkaf:relationChangeOperation` | rkaf:RelationChangeEvent | — | — | relationchangeevent-removal-positive, relationchangeevent-replacement-positive |
| rkaf:relationChangeStage | https://rulespec.org/ns/v1#relationChangeStage | Property (closed enum) | rkaf:RelationChangeEvent | rkaf:RelationChangeStage | 1 | relationchangeevent-removal-positive |
| rkaf:changeProposed, rkaf:changeDecided, rkaf:changeEffective, rkaf:changeWithdrawn, rkaf:changeStageUnclear | `https://rulespec.org/ns/v1#` + each local name in the Term cell | Values of `rkaf:relationChangeStage`; `changeStageUnclear` is a first-class value, not a gap | rkaf:RelationChangeEvent | — | — | relationchangeevent-removal-positive, relationchangeevent-replacement-positive |
| rkaf:relationChangeTime | https://rulespec.org/ns/v1#relationChangeTime | Property | rkaf:RelationChangeEvent | xsd:dateTime | 0..1 | relationchangeevent-removal-positive |
| rkaf:changeIntendedEffectiveTime | https://rulespec.org/ns/v1#changeIntendedEffectiveTime | Property | rkaf:RelationChangeEvent | xsd:dateTime | 0..1 (1 when stage is `rkaf:changeEffective`) | relationchangeevent-replacement-positive |
| rkaf:changeEvidence | https://rulespec.org/ns/v1#changeEvidence | Property | rkaf:RelationChangeEvent | rkaf:SourceFragment | 1..* | relationchangeevent-removal-positive |
| rkaf:replacementRelationObject | https://rulespec.org/ns/v1#replacementRelationObject | Property | rkaf:RelationChangeEvent | IRI | 0..1 (1 when operation is `rkaf:relationReplacement`) | relationchangeevent-replacement-positive |
| rkaf:RelationComparisonContext | https://rulespec.org/ns/v1#RelationComparisonContext | Class (immutable comparison frame and outcome) | — | — | — | relationcomparisoncontext-satisfied-positive, relationfinding-discrepancy-positive |
| rkaf:comparisonBaselineArtifact | https://rulespec.org/ns/v1#comparisonBaselineArtifact | Property | rkaf:RelationComparisonContext | rkaf:Artifact | 1 | relationcomparisoncontext-satisfied-positive |
| rkaf:comparisonObservedArtifact | https://rulespec.org/ns/v1#comparisonObservedArtifact | Property | rkaf:RelationComparisonContext | rkaf:Artifact | 1 | relationcomparisoncontext-satisfied-positive |
| rkaf:comparisonExpectedAssertion | https://rulespec.org/ns/v1#comparisonExpectedAssertion | Property | rkaf:RelationComparisonContext | IRI | 1 | relationcomparisoncontext-satisfied-positive |
| rkaf:comparisonConsumer | https://rulespec.org/ns/v1#comparisonConsumer | Property | rkaf:RelationComparisonContext | IRI | 1 | relationcomparisoncontext-satisfied-positive |
| rkaf:comparisonScope | https://rulespec.org/ns/v1#comparisonScope | Property | rkaf:RelationComparisonContext | IRI | 1 | relationcomparisoncontext-satisfied-positive |
| rkaf:comparisonEvaluationTime | https://rulespec.org/ns/v1#comparisonEvaluationTime | Property | rkaf:RelationComparisonContext | xsd:dateTime | 1 | relationcomparisoncontext-satisfied-positive |
| rkaf:comparisonPolicyVersion | https://rulespec.org/ns/v1#comparisonPolicyVersion | Property | rkaf:RelationComparisonContext | xsd:string | 1 | relationcomparisoncontext-satisfied-positive |
| rkaf:comparisonDetector | https://rulespec.org/ns/v1#comparisonDetector | Property | rkaf:RelationComparisonContext | IRI | 1 | relationcomparisoncontext-satisfied-positive |
| rkaf:comparisonDetectorVersion | https://rulespec.org/ns/v1#comparisonDetectorVersion | Property | rkaf:RelationComparisonContext | xsd:string | 1 | relationcomparisoncontext-satisfied-positive |
| rkaf:comparisonSnapshot | https://rulespec.org/ns/v1#comparisonSnapshot | Property | rkaf:RelationComparisonContext | xsd:string | 1 | relationcomparisoncontext-satisfied-positive |
| rkaf:comparisonOutcome | https://rulespec.org/ns/v1#comparisonOutcome | Property (closed enum) | rkaf:RelationComparisonContext | rkaf:RelationComparisonOutcome | 1 | relationcomparisoncontext-satisfied-positive, relationfinding-discrepancy-positive |
| rkaf:comparisonSatisfied, rkaf:comparisonAffirmedDeniedDiscrepancy, rkaf:comparisonConflict, rkaf:comparisonNotComparable, rkaf:comparisonUnknown | `https://rulespec.org/ns/v1#` + each local name in the Term cell | Values of `rkaf:comparisonOutcome`; `notComparable` is a gate result, never a negative source fact, and `unknown` never becomes a failure | rkaf:RelationComparisonContext | — | — | relationcomparisoncontext-satisfied-positive, relationfinding-discrepancy-positive |
| rkaf:comparisonProofRecord | https://rulespec.org/ns/v1#comparisonProofRecord | Property | rkaf:RelationComparisonContext | rkaf:ResolverProofRecord | 0..* (1..* for every outcome except `rkaf:comparisonUnknown`) | relationcomparisoncontext-satisfied-positive |
| rkaf:ResolverProofIssuer | https://rulespec.org/ns/v1#ResolverProofIssuer | Class (versioned resolver and policy a proof was issued under) | — | — | — | relationcomparisoncontext-satisfied-positive, relationfinding-discrepancy-positive |
| rkaf:proofResolver | https://rulespec.org/ns/v1#proofResolver | Property | rkaf:ResolverProofIssuer | IRI | 1 | relationcomparisoncontext-satisfied-positive |
| rkaf:proofResolverVersion | https://rulespec.org/ns/v1#proofResolverVersion | Property | rkaf:ResolverProofIssuer | xsd:string | 1 | relationcomparisoncontext-satisfied-positive |
| rkaf:proofPolicy | https://rulespec.org/ns/v1#proofPolicy | Property | rkaf:ResolverProofIssuer | IRI | 1 | relationcomparisoncontext-satisfied-positive |
| rkaf:proofPolicyVersion | https://rulespec.org/ns/v1#proofPolicyVersion | Property | rkaf:ResolverProofIssuer | xsd:string | 1 | relationcomparisoncontext-satisfied-positive |
| rkaf:ResolverProofRecord | https://rulespec.org/ns/v1#ResolverProofRecord | Class (content-bound resolver decision) | — | — | — | relationcomparisoncontext-satisfied-positive, relationfinding-discrepancy-positive |
| rkaf:proofType | https://rulespec.org/ns/v1#proofType | Property (closed enum) | rkaf:ResolverProofRecord | rkaf:ResolverProofType | 1 | relationcomparisoncontext-satisfied-positive, relationfinding-discrepancy-positive |
| rkaf:predicateCatalogProof, rkaf:assertionStateProof, rkaf:evidenceBindingProof, rkaf:baselineWarrantProof, rkaf:artifactPairingProof, rkaf:scopeComparisonProof | `https://rulespec.org/ns/v1#` + each local name in the Term cell | Values of `rkaf:proofType`, one per active resolver protocol; the three longitudinal protocols are absent while closure is disabled | rkaf:ResolverProofRecord | — | — | relationcomparisoncontext-satisfied-positive, relationfinding-discrepancy-positive |
| rkaf:proofIssuer | https://rulespec.org/ns/v1#proofIssuer | Property | rkaf:ResolverProofRecord | rkaf:ResolverProofIssuer | 1 | relationcomparisoncontext-satisfied-positive |
| rkaf:proofComparisonContext | https://rulespec.org/ns/v1#proofComparisonContext | Property | rkaf:ResolverProofRecord | rkaf:RelationComparisonContext | 1 | relationcomparisoncontext-satisfied-positive |
| rkaf:proofOutcome | https://rulespec.org/ns/v1#proofOutcome | Property (closed enum) | rkaf:ResolverProofRecord | rkaf:GateStatus or rkaf:ScopeRelation | 1 | relationcomparisoncontext-satisfied-positive |
| rkaf:gatePass, rkaf:gateFail, rkaf:gateUnknown | `https://rulespec.org/ns/v1#` + each local name in the Term cell | Values of `rkaf:proofOutcome` (gate half); `gateFail` is a gate result, never a negative source fact, and `gateUnknown` never becomes `gateFail` | rkaf:ResolverProofRecord | — | — | relationcomparisoncontext-satisfied-positive, relationfinding-discrepancy-positive |
| rkaf:scopeEquivalent, rkaf:scopeObservedSubsumesExpected, rkaf:scopeObservedNarrowsExpected, rkaf:scopeOverlaps, rkaf:scopeDisjoint, rkaf:scopeUnknown | `https://rulespec.org/ns/v1#` + each local name in the Term cell | Values of `rkaf:proofOutcome` (scope half); a scope relation is not a gate result | rkaf:ResolverProofRecord | — | — | covered by `fixtures/edges/resolver-proof-scope-relation-edge.jsonld` |
| rkaf:proofRationale | https://rulespec.org/ns/v1#proofRationale | Property | rkaf:ResolverProofRecord | xsd:string | 1 | relationcomparisoncontext-satisfied-positive |
| rkaf:proofInput | https://rulespec.org/ns/v1#proofInput | Property | rkaf:ResolverProofRecord | IRI | 1..* | relationcomparisoncontext-satisfied-positive |
| rkaf:proofInputDigest | https://rulespec.org/ns/v1#proofInputDigest | Property | rkaf:ResolverProofRecord | xsd:string (`sha256:<64 hex>`) | 0..* | relationfinding-discrepancy-positive |
| rkaf:proofSupportingRecord | https://rulespec.org/ns/v1#proofSupportingRecord | Property | rkaf:ResolverProofRecord | IRI | 0..* | relationfinding-discrepancy-positive |
| rkaf:proofEvaluatedAt | https://rulespec.org/ns/v1#proofEvaluatedAt | Property | rkaf:ResolverProofRecord | xsd:dateTime | 1 | relationcomparisoncontext-satisfied-positive |
| rkaf:proofSnapshot | https://rulespec.org/ns/v1#proofSnapshot | Property | rkaf:ResolverProofRecord | xsd:string | 1 | relationcomparisoncontext-satisfied-positive |
| rkaf:proofRecordDigest | https://rulespec.org/ns/v1#proofRecordDigest | Property | rkaf:ResolverProofRecord | xsd:string (`sha256:<64 hex>`) | 1 | relationcomparisoncontext-satisfied-positive |
| rkaf:RelationFinding | https://rulespec.org/ns/v1#RelationFinding | Class (NEUTRAL analytical observation; carries no legal effect) | — | — | — | relationfinding-discrepancy-positive |
| rkaf:relationFindingKind | https://rulespec.org/ns/v1#relationFindingKind | Property (closed enum) | rkaf:RelationFinding | rkaf:RelationFindingKind | 1 | relationfinding-discrepancy-positive |
| rkaf:affirmedDeniedDiscrepancy | https://rulespec.org/ns/v1#affirmedDeniedDiscrepancy | The ONLY value of `rkaf:relationFindingKind`; no omission kind exists or may be added while closure is disabled | rkaf:RelationFinding | — | — | relationfinding-discrepancy-positive |
| rkaf:findingComparisonContext | https://rulespec.org/ns/v1#findingComparisonContext | Property | rkaf:RelationFinding | rkaf:RelationComparisonContext (whose outcome MUST be `rkaf:comparisonAffirmedDeniedDiscrepancy`) | 1 | relationfinding-discrepancy-positive |
| rkaf:findingComparedAssertion | https://rulespec.org/ns/v1#findingComparedAssertion | Property | rkaf:RelationFinding | IRI of an rkaf:RelationshipAssertion or rkaf:ValueAssertion | 2..* | relationfinding-discrepancy-positive |
| rkaf:findingProofRecord | https://rulespec.org/ns/v1#findingProofRecord | Property | rkaf:RelationFinding | rkaf:ResolverProofRecord | 1..* | relationfinding-discrepancy-positive |
| rkaf:findingDetectedAt | https://rulespec.org/ns/v1#findingDetectedAt | Property | rkaf:RelationFinding | xsd:dateTime | 1 | relationfinding-discrepancy-positive |
| rkaf:findingRationale | https://rulespec.org/ns/v1#findingRationale | Property | rkaf:RelationFinding | xsd:string | 1 | relationfinding-discrepancy-positive |
| rkaf:findingFingerprint | https://rulespec.org/ns/v1#findingFingerprint | Property (correlation key, deliberately not identity) | rkaf:RelationFinding | xsd:string | 0..1 | relationfinding-discrepancy-positive |
| rkaf:ClosureClaim | https://rulespec.org/ns/v1#ClosureClaim | Class — **EXPERIMENTAL AND DISABLED**; shape validity only, never finding evidence | — | — | — | closureclaim-disabled-positive |
| rkaf:closureClaimStatus | https://rulespec.org/ns/v1#closureClaimStatus | Property (closed enum, single value `rkaf:closureClaimDisabled`) | rkaf:ClosureClaim | rkaf:ClosureClaimStatus | 1 | closureclaim-disabled-positive |
| rkaf:closureClaimDisabled | https://rulespec.org/ns/v1#closureClaimDisabled | The only legal value of `rkaf:closureClaimStatus`; the experimental flag that gates the record | rkaf:ClosureClaim | — | — | closureclaim-disabled-positive |
| rkaf:closureArtifact | https://rulespec.org/ns/v1#closureArtifact | Property | rkaf:ClosureClaim | rkaf:Artifact | 1 | closureclaim-disabled-positive |
| rkaf:closureRegion | https://rulespec.org/ns/v1#closureRegion | Property | rkaf:ClosureClaim | rkaf:SourceFragment | 1..* (closure is always local) | closureclaim-disabled-positive |
| rkaf:closurePredicateFamily | https://rulespec.org/ns/v1#closurePredicateFamily | Property | rkaf:ClosureClaim | IRI | 1 | closureclaim-disabled-positive |
| rkaf:closureProfileVersion | https://rulespec.org/ns/v1#closureProfileVersion | Property | rkaf:ClosureClaim | xsd:string | 1 | closureclaim-disabled-positive |
| rkaf:closureMemberDigest | https://rulespec.org/ns/v1#closureMemberDigest | Property | rkaf:ClosureClaim | xsd:string (`sha256:<64 hex>`) | 1 | closureclaim-disabled-positive |
| rkaf:closureReviewedAt | https://rulespec.org/ns/v1#closureReviewedAt | Property | rkaf:ClosureClaim | xsd:dateTime | 0..1 (an unreviewed claim stays representable as unreviewed) | closureclaim-disabled-positive |

## Experimental US rulemaking-process module

These terms are defined by `spec/rkaf-rulemaking.md` and codified under `constraints/profiles/us-rulemaking/`, which compiles to `compiled/<target>/profiles/us-rulemaking/` and `crates/rkaf-core/src/generated/profiles/us_rulemaking/`. They are jurisdiction-specific: the universal-primitives table above and the kernel CUE under `constraints/core/` do not declare any of them, and a consumer that does not adopt this profile never sees them. `rkaf:hasRegulatoryIdentifier`, `rkaf:regulatoryIdentifierScheme`, and `rkaf:publishedInProceeding` have `rkaf:Artifact` as their domain because the profile shape `#USRegulatoryArtifact` composes the kernel `#Artifact` rather than minting a parallel class. The twelve proceeding lifecycle kinds below are the same arrangement applied to a VALUE set rather than a property set: they have `rkaf:LifecycleEvent` as their domain because the profile shape `#USLifecycleEvent` composes the kernel `#LifecycleEvent` and binds the assembled union `#ComposedLifecycleEventKind` (kernel ten + profile twelve, the profile's part being `#USProceedingLifecycleEventKind`) to `rkaf:lifecycleEventKind`. The kernel carrier stays open on that property — the compiled kernel types it as a plain string and emits no `sh:in` — so a consumer that loads only the kernel is unconstrained by the property entirely, by the kernel's own ten universal kinds as much as by these twelve, rather than rejecting anything. The closed 22-value set is enforced only by the profile artifacts. Their status is Experimental; inclusion in the mechanically checked vocabulary does not satisfy the module's stabilization gate.

| Term | IRI | Kind | Domain | Range | Cardinality | Required fixtures |
|---|---|---|---|---|---|---|
| rkaf:hasRegulatoryIdentifier | https://rulespec.org/ns/v1#hasRegulatoryIdentifier | Property | rkaf:Artifact | IRI | 0..1 | artifact-us-cfr-positive |
| rkaf:regulatoryIdentifierScheme | https://rulespec.org/ns/v1#regulatoryIdentifierScheme | Property (closed enum) | rkaf:Artifact | rkaf:USRegulatoryIdentifierScheme | 0..1 | artifact-us-cfr-positive |
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
| prov:wasGeneratedBy | http://www.w3.org/ns/prov#wasGeneratedBy | Property (PROV-O mode-1 import) | rkaf:AgendaProceedingRelationship | IRI of the activity that derived the assignment | 1 | agenda-item-ordinary-positive |
| prov:wasAttributedTo | http://www.w3.org/ns/prov#wasAttributedTo | Property (PROV-O mode-1 import) | rkaf:AgendaProceedingRelationship | IRI of the agent the assignment is attributed to | 1 | agenda-item-ordinary-positive |
| prov:generatedAtTime | http://www.w3.org/ns/prov#generatedAtTime | Property (PROV-O mode-1 import) | rkaf:AgendaProceedingRelationship | xsd:dateTime | 1 | agenda-item-ordinary-positive |
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
| rkaf:proceedingPrerule, rkaf:proceedingProposed, rkaf:proceedingSupplemental, rkaf:proceedingFinal, rkaf:proceedingWithdrawn, rkaf:proceedingLongterm, rkaf:proceedingConcluded | `https://rulespec.org/ns/v1#` + each local name in the Term cell | Profile-contributed values of `rkaf:lifecycleEventKind` (stage family) | rkaf:LifecycleEvent | — | — | lifecycleevent-proceeding-stages-positive, lifecycleevent-composed-kind-positive |
| rkaf:proceedingVacated, rkaf:proceedingStayed, rkaf:proceedingRemanded, rkaf:proceedingReinstated, rkaf:proceedingDisapproved | `https://rulespec.org/ns/v1#` + each local name in the Term cell | Profile-contributed values of `rkaf:lifecycleEventKind` (external legal family) | rkaf:LifecycleEvent | — | — | lifecycleevent-partial-vacatur-positive |

`rkaf:proceedingStage` uses the seven stage-family lifecycle IRIs:
`rkaf:proceedingPrerule`, `rkaf:proceedingProposed`,
`rkaf:proceedingSupplemental`, `rkaf:proceedingFinal`,
`rkaf:proceedingWithdrawn`, `rkaf:proceedingLongterm`, and
`rkaf:proceedingConcluded`.

## v0.2 Studio-derived promotions (§5 of `spec/rkaf-core.md`)

| Term | IRI | Kind | Domain | Range | Cardinality | Required fixtures |
|---|---|---|---|---|---|---|
| rkaf:AILineage | https://rulespec.org/ns/v1#AILineage | Class | — | — | — | ailineage-positive, ailineage-malformed-input-context-hash-negative |
| rkaf:hasAILineage | https://rulespec.org/ns/v1#hasAILineage | Property | rkaf:Assertion / rkaf:ConceptAssignment | rkaf:AILineage | 0..1 (REQUIRED if assertionOrigin AI-touched) | ailineage-positive |
| rkaf:humanApprover | https://rulespec.org/ns/v1#humanApprover | Property | rkaf:AILineage | IRI | 0..1 (1 when humanRationale present) | ailineage-positive |
| rkaf:inputContextHash | https://rulespec.org/ns/v1#inputContextHash | Property | rkaf:AILineage | xsd:string (`sha256:<64 hex>`) | 1 | ailineage-positive |
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
| `rkaf:RelationshipAssertion` | `relationship-assertion.cue` | `relationshipassertion-denied-positive.jsonld` | Proposition-bearing Assertion specialization with required subject, predicate, IRI object, explicit polarity, and no stored global state (Core §2.1). |
| `rkaf:ValueAssertion` | `value-assertion.cue` | `valueassertion-date-positive.jsonld` | Proposition-bearing Assertion specialization whose object is a typed literal rather than an IRI (Core §2.2). Closed `rkaf:ValueDatatype` set. |
| `rkaf:SourceClaimant` | `source-claimant.cue` | `sourceclaimant-named-positive.jsonld` | Who the SOURCE says asserts a proposition (Core §2.4). Distinct from the extraction system, the model, and the approver. |
| `rkaf:ExtractionActivity` | `extraction-activity.cue` | `extractionactivity-model-positive.jsonld` | Which run produced an assertion candidate (Core §2.4). Provider-neutral, opaque digests, and no approver — an unreviewed candidate is representable. |
| `rkaf:Attestation` | `attestation.cue` | `attestation-positive.jsonld`, `attestation-tabular-projection-positive.jsonld` | Scoped multi-target attestation by a named attestor (Core §3.1). Closed decision + attestor-kind enums. The second fixture is what the normative L0 attestations table projects to (Conformance §0.1): one approval and one rejection over the same record, neither a field on it. |
| `rkaf:LocalAdoption` | `local-adoption.cue` | `localadoption-positive.jsonld` | Workspace-scoped authorization of an Assertion (Core §3.2). Restricted `adoptionAuthorityKind` per §2.5 invariant. |
| `rkaf:ApplicabilityScope` | `applicability-scope.cue` | `applicabilityscope-positive.jsonld` | Where/to-whom/when a Warrant applies. ELI / ISO 3166 / agency-code IRIs. |
| `rkaf:EffectivePeriod` | `effective-period.cue` | `effectiveperiod-positive.jsonld` | Temporal window. Start required; end / sunset / retroactive optional. |
| `rkaf:LifecycleEvent` | `lifecycle-event.cue` | `lifecycleevent-positive.jsonld` | Audit-trail event for assertion, concept, and proceeding-stage transitions. |
| `rkaf:RegisteredConcept` | `concept.cue` | `concept-registered-positive.jsonld` | Federation-shared Concept minted by a `rkaf:ConceptMintingAuthority`. Requires `skos:prefLabel(1)` and `skos:inScheme(1)`. |
| `rkaf:LocalConcept` | `concept.cue` | `localconcept-positive.jsonld` | Workspace-defined Concept, candidate for federation promotion. Requires `skos:prefLabel(1)` and `skos:inScheme(1)`. |
| `rkaf:ConceptScheme` | `concept.cue` | `conceptscheme-registry-positive.jsonld` | One facet, one controlled category system (Core §4.7). Requires a declared `rkaf:schemeFacet` and either a governing registry or a defining workspace scope. |
| `rkaf:ConceptAssignment` | `concept-assignment.cue` | `conceptassignment-fragment-direct-positive.jsonld` | Evidence-bearing, versioned record that one Artifact or one SourceFragment is associated with one concept (Core §4.7). Composes the Assertion envelope; a segment assignment requires evidence from that segment. |
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
- `rkaf:assertionPolarity` — `rkaf:affirmed` or `rkaf:denied`; applies to the canonical affirmative predicate carried by a `RelationshipAssertion` or `ValueAssertion`.
- `rkaf:hasTrustZone` — `rkaf:Z0` through `rkaf:Z8`. Structural property (kind of object).
- `rkaf:hasSafetyLabel` — `D0` / `S1` / `R2` / `A3` / `P4` plus advisory + authority-critical refinements. Operational property (what the consumer may do).
- `rkaf:authorityKind` — 8-value closed enum, hop-local. Federation refuses unsupported kinds.
- `rkaf:lifecycleEventKind` — closed enum ASSEMBLED from per-module parts. The kernel (`lifecycle-event.cue`) owns ten universal values: revalidation, revalidation closure, amendment, supersession, rescission, material and editorial revision, concept lifecycle, promotion, demotion. The Experimental US rulemaking module (`profiles/us-rulemaking/us-lifecycle-event.cue`) contributes twelve more — seven proceeding-stage transitions and five judicial/congressional proceeding events — giving a 22-value closed set on the composed artifact. The compiler assembles the union at build time; `LifecycleKindOwnershipTests` in `tools/test_constraints_compile.py` proves every value has exactly one declaring module and that the assembled set equals kernel + sum(profiles).
- `rkaf:mappingRelation` — 9-value closed set of SKOS predicates: the five cross-scheme mapping properties (`skos:exactMatch`, `skos:closeMatch`, `skos:broadMatch`, `skos:narrowMatch`, `skos:relatedMatch`), the three in-scheme semantic relations SKOS distinguishes from them (`skos:broader`, `skos:narrower`, `skos:related`), and the generic `skos:mappingRelation`. v0.2 ADDED the three `*Match` members; none was removed. The list is mirrored by `shapes/rkaf-shapes-conceptregistry.ttl`, and the two MUST stay identical — SHACL is conjunctive, so a value present in one and absent from the other is rejected outright.
- `rkaf:CoordinateSystem` — 6-value closed set naming the unit an offset-bearing selector counts in: `rkaf:unicode-codepoint`, `rkaf:utf8-byte`, `rkaf:utf16-code-unit`, `rkaf:xml-node-path`, `rkaf:page-region`, `rkaf:partner-defined`. Required on `oa:TextPositionSelector`; an offset with no declared unit names three different regions (Core §4.2).
- `rkaf:FragmentIdentityScheme` — 2-value closed set naming HOW a cited region is identified: `rkaf:published-fragment` (the IRI names a `rkaf:SourceFragment` node the producer publishes) and `rkaf:carrier-local-fragment` (the IRI is a carrier-local fragment URN, `urn:rkaf:fragment:<percent-encoded artifact IRI>:<start>:<end>:sha256-<64 hex>`, which carries the bindings itself). The scheme fixes the unit at `rkaf:unicode-codepoint` and the selector kind at `oa:TextPositionSelector`, and the interval is half-open `[start, end)`. A tabular carrier that already stores an artifact id, two offsets, and a region digest can cite evidence without publishing a fragments table; the class range, the same-Artifact rule, and every other §4.7.3 rule are unchanged (Core §4.2).
- `rkaf:AssignmentSubjectType` — 2-value closed set: `rkaf:Artifact`, `rkaf:SourceFragment`. Exactly two kinds of thing are taggable, and they are not interchangeable (Core §4.7).
- `rkaf:ConceptAssignmentRole` — 4-value closed set: `rkaf:assignmentPrimary`, `rkaf:assignmentSubstantive`, `rkaf:assignmentMention`, `rkaf:assignmentContextual`. Editorial ordering only; nothing in Rulespec compares two roles.
- `rkaf:AssignmentDerivation` — 2-value closed set: `rkaf:directAssignment` (read off the subject's own text, MUST cite exact regions) and `rkaf:derivedAssignment` (computed from accepted assignments, MUST name them and the policy version that combined them). Orthogonal to `rkaf:assertionOrigin`, which records what CONSTRUCTED the record (Core §4.7).
- `rkaf:ValueDatatype` — 11-member closed set of XSD datatypes a `ValueAssertion` object may carry: `xsd:string`, `xsd:token`, `xsd:boolean`, `xsd:integer`, `xsd:decimal`, `xsd:double`, `xsd:date`, `xsd:dateTime`, `xsd:time`, `xsd:duration`, `xsd:anyURI`. Deliberately narrow — an open datatype IRI would make "typed" mean nothing (Core §2.2).
- `rkaf:claimantAttribution` — 4-value closed set describing how the SOURCE attributes a claim: `rkaf:claimantNamedInSource`, `rkaf:claimantImpliedBySource`, `rkaf:claimantIsDocumentIssuer`, `rkaf:claimantNotStated`. Every value states something about the document, so there is no value for extractor uncertainty; Core §2.4 requires the record to be omitted in that case.
- `rkaf:assertionOrigin` — 7-value closed set naming what CONSTRUCTED the record: `rkaf:humanAsserted`, `rkaf:aiSuggested`, `rkaf:aiPromoted`, `rkaf:humanQualified`, `rkaf:humanRevalidation`, `rkaf:imported`, and `rkaf:deterministicExtraction`. The first six are inherited unchanged from v0.1; the seventh is the one value v0.2 ADDS, for a record a deterministic parser or join produced — a mechanically reproducible derivation rather than an interpretive judgment. The four AI-touched values REQUIRE `rkaf:hasAILineage`; `rkaf:deterministicExtraction` REQUIRES `rkaf:hasExtractionProvenance` and MUST NOT carry AI lineage. `rkaf:imported` is unchanged and undeprecated — it says a record was re-serialized from another system, which is a statement about origin and not about method (Core §2.4).
- `rkaf:extractionMethod` — 5-value closed set naming how a run produced a candidate: `rkaf:deterministicParse`, `rkaf:ruleBasedExtraction`, `rkaf:modelExtraction`, `rkaf:humanExtraction`, `rkaf:importedRecord`. `rkaf:modelExtraction` requires a model reference (Core §2.4).

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
