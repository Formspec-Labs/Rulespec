# Rulespec Conformance Fixture v0.2

> **Note**: This narrative was written pre-ADR-0093. `BridgeValidationResult` code blocks below show the legacy flat indicator arrays (`rkaf:warnings`, `rkaf:errors`, `rkaf:staleDependencies`, `rkaf:registryUnavailable`, `rkaf:registryVersionOutOfRange`). The current shape uses a single `rkaf:findings` list of `rkaf:Finding` `@id`s — see ADR-0093.

Status: revised worked trace, absorbing decisions through Pass 3
Replaces: rkaf-pass-2-worked-trace.md (Pass 2)
Bridge contract version: `rkaf-bridge/1.0`

## Delta from Pass 2

1. **`assertionState` removed from assertion bodies.** Origin, trust zone, safety label, usage eligibility, and applicability live on the assertion; effective review/adoption state is computed per scope by reduction over attestations + adoptions.
2. **`prov:wasDerivedFrom` replaces `rkaf:discoveryProvenance`.** Promotion attestation records the decision.
3. **Applicability normalized.** `rkaf:hasApplicability` on assertions; `rkaf:proposesApplicability` on attestations; `rkaf:adoptsApplicability` on LocalAdoption.
4. **`PolicyResourceVersion` wraps wiki revisions** via `rkaf:realizedByArtifact`. Lifecycle predicates (`amends`, `supersedes`, `rescinds`) target ResourceVersions, not Artifacts.
5. **Explicit `RevisionClassification` step** decides `editorialRevisionOf` vs `materiallyRevises` before any cascade is triggered.
6. **`AmendmentPacket` carries `rkaf:cascadeAlgorithm: rkaf:CascadeClosureV1`** and a normatively-computed affected set.
7. **`RevalidationClosureEvent`** replaces prose `closesWhen`.
8. **ConceptRegistry references** every `collectsEvidenceType` / `requiresEvidenceType` reference.
9. **`EvaluationAnchor` vocabulary** used on `PointInTimeException`.
10. **`BridgeValidationResult`** emitted by Formspec on packet ingestion (one `accepted`, one `acceptedWithWarnings`).
11. **`adoptionAuthorityKind: localOperational`** on LocalAdoption provides the chain terminus.
12. **`staleForCurrentUse`** status on affected fields/assertions after cascade.
13. **`rkaf:bridgeContractVersion`** declared on packets and generated artifacts.

## Scope deliberately exercised

`candidateRelatedTo` → promotion to `requiresEvidenceType` → AI promotion attestation → human `endorseWithQualifier` → `LocalAdoption` (localOperational) → generated Formspec field → `BridgeValidationResult` (accepted) → reviewer `object` → successor assertion via `supersedesAssertion` → revised field → source revision → `RevisionClassification` → `materiallyRevises` on artifact → `amends` on PolicyResourceVersion → `AmendmentPacket` cascade → `BridgeValidationResult` (acceptedWithWarnings) → `RevalidationEvent` → successor assertion → field v3 → `RevalidationClosureEvent`.

Out of scope for this fixture (would require a second one): statute/regulation-grounded chains with `hasAuthority`/`derivesAuthorityFrom`, `rescinds` cascade, `editorialRevisionOf` (the non-cascading branch — noted at Step 16), cross-organization sync semantics.

---

## Phase 1: Capture and structure

### Step 1 — Artifact (wiki page revision)

```json
{
  "@context": "https://rulespec.org/context/v1.jsonld",
  "@id": "https://example.org/artifact/wiki-csbg-eligibility-rev-1247",
  "@type": "rkaf:Artifact",
  "rkaf:sourceType": "mediawiki-page-revision",
  "rkaf:contentHash": "sha256:7a3f4b9e...c91d",
  "rkaf:mimeType": "text/x-wiki",
  "rkaf:capturedAt": "2026-05-10T14:00:00-05:00",
  "rkaf:capturedBy": "https://example.org/connector/mediawiki-v2",
  "rkaf:sourceUrl": "https://wiki.example.org/csbg-policy/Eligibility?oldid=1247",
  "rkaf:accessScope": "internal",
  "rkaf:sourceAuthorityHint": "https://example.org/source-authority/caa-42-internal-wiki"
}
```

### Step 2 — SourceFragment

```json
{
  "@context": "https://rulespec.org/context/v1.jsonld",
  "@id": "https://example.org/fragment/wiki-csbg-eligibility-rev-1247/sec-3-p2",
  "@type": "rkaf:SourceFragment",
  "rkaf:artifactId": "https://example.org/artifact/wiki-csbg-eligibility-rev-1247",
  "rkaf:fragmentType": "paragraph",
  "rkaf:locator": "section[@id='income-verification']/p[2]",
  "rkaf:selector": {
    "@type": "oa:TextQuoteSelector",
    "oa:exact": "Applicants for benefit category B must provide documentation establishing household income for the prior twelve months.",
    "oa:prefix": "Income verification requirements.",
    "oa:suffix": "Acceptable documentation includes..."
  },
  "rkaf:sourceVersion": "rev-1247",
  "rkaf:accessScope": "internal"
}
```

### Step 3 — PolicyResourceVersion wrapping the artifact

```json
{
  "@context": "https://rulespec.org/context/v1.jsonld",
  "@id": "https://example.org/resource/csbg-eligibility-policy/rev-1247",
  "@type": "rkaf:PolicyResourceVersion",
  "rkaf:resourceLineage": "https://example.org/resource/csbg-eligibility-policy",
  "rkaf:versionLabel": "rev-1247",
  "rkaf:effectivePeriodStart": "2025-11-01T00:00:00-05:00",
  "rkaf:realizedByArtifact": "https://example.org/artifact/wiki-csbg-eligibility-rev-1247",
  "rkaf:resourceKind": "internalOrganizationalPolicy",
  "rkaf:accessScope": "internal"
}
```

## Phase 2: Concept registration

### Step 4 — ConceptRegistry entries (SKOS-compatible)

```json
{
  "@context": "https://rulespec.org/context/v1.jsonld",
  "@id": "https://registry.example.gov/concepts/HouseholdIncomeEvidence",
  "@type": ["skos:Concept", "rkaf:RegisteredConcept"],
  "skos:prefLabel": "Household income evidence",
  "skos:altLabel": ["income documentation", "proof of income"],
  "skos:broader": "https://registry.example.gov/concepts/FinancialEligibilityEvidence",
  "skos:narrower": [
    "https://registry.example.gov/concepts/PayStubEvidence",
    "https://registry.example.gov/concepts/FederalTaxReturnEvidence",
    "https://registry.example.gov/concepts/StateTaxReturnEvidence"
  ],
  "rkaf:managedByRegistry": "https://registry.example.gov/registries/public-benefits-evidence",
  "rkaf:conceptScope": "rkaf:public",
  "rkaf:conceptStatus": "rkaf:registered"
}
```

## Phase 3: AI-suggested candidate and promotion

### Step 5 — `candidateRelatedTo` (S1, search-only)

No `assertionState`. Effective state computed from attestations/adoptions per scope.

```json
{
  "@context": "https://rulespec.org/context/v1.jsonld",
  "@id": "https://example.org/assertion/cand-001",
  "@type": "rkaf:RelationshipAssertion",
  "rkaf:assertsSubject": "https://example.org/fragment/wiki-csbg-eligibility-rev-1247/sec-3-p2",
  "rkaf:assertsPredicate": "rkaf:candidateRelatedTo",
  "rkaf:assertsObject": "https://registry.example.gov/concepts/HouseholdIncomeEvidence",
  "rkaf:assertionOrigin": "rkaf:aiSuggested",
  "rkaf:hasTrustZone": "rkaf:Z3ScoredCandidateRelationship",
  "rkaf:hasSafetyLabel": "rkaf:S1SearchOnly",
  "rkaf:usageEligibility": "rkaf:searchOnly",
  "rkaf:hasEvidence": [
    {
      "@type": "rkaf:EvidenceBinding",
      "rkaf:evidenceRole": "rkaf:retrievalSignal",
      "rkaf:bindsSourceFragment": "https://example.org/fragment/wiki-csbg-eligibility-rev-1247/sec-3-p2"
    }
  ],
  "rkaf:hasConfidence": {
    "@type": "rkaf:ConfidenceVector",
    "rkaf:semanticSimilarity": 0.84,
    "rkaf:evidenceStrength": 0.55,
    "rkaf:sourceAuthorityWeight": 0.40,
    "rkaf:overallCandidateScore": 0.68
  },
  "prov:wasGeneratedBy": "https://example.org/methodrun/policy-mapper-2026-05-10-001",
  "prov:wasAttributedTo": "https://example.org/agent/policy-mapper-v1"
}
```

### Step 6 — Promotion: new typed `requiresEvidenceType` assertion

`prov:wasDerivedFrom` links back to the candidate. No `assertionState` field.

```json
{
  "@context": "https://rulespec.org/context/v1.jsonld",
  "@id": "https://example.org/assertion/req-001",
  "@type": "rkaf:RelationshipAssertion",
  "rkaf:assertsSubject": "https://example.org/fragment/wiki-csbg-eligibility-rev-1247/sec-3-p2",
  "rkaf:assertsPredicate": "rkaf:requiresEvidenceType",
  "rkaf:assertsObject": "https://registry.example.gov/concepts/HouseholdIncomeEvidence",
  "rkaf:assertionOrigin": "rkaf:aiPromoted",
  "rkaf:hasTrustZone": "rkaf:Z2ExtractedCandidateClaim",
  "rkaf:hasSafetyLabel": "rkaf:R2ReviewedOperational",
  "rkaf:usageEligibility": "rkaf:reviewQueueOnly",
  "rkaf:hasEvidence": [
    {
      "@type": "rkaf:EvidenceBinding",
      "rkaf:evidenceRole": "rkaf:textualEvidence",
      "rkaf:bindsSourceFragment": "https://example.org/fragment/wiki-csbg-eligibility-rev-1247/sec-3-p2",
      "rkaf:supportingQuote": "must provide documentation establishing household income for the prior twelve months"
    }
  ],
  "prov:wasDerivedFrom": "https://example.org/assertion/cand-001",
  "prov:wasGeneratedBy": "https://example.org/methodrun/policy-mapper-2026-05-10-001",
  "prov:wasAttributedTo": "https://example.org/agent/policy-mapper-v1"
}
```

### Step 7 — Promotion attestation

```json
{
  "@context": "https://rulespec.org/context/v1.jsonld",
  "@id": "https://example.org/attestation/promo-001",
  "@type": "rkaf:Attestation",
  "rkaf:targetAssertion": "https://example.org/assertion/req-001",
  "rkaf:attestor": "https://example.org/agent/policy-mapper-v1",
  "rkaf:attestorType": "rkaf:AIAgent",
  "rkaf:decision": "rkaf:promoteCandidate",
  "rkaf:scope": "rkaf:reviewQueue",
  "rkaf:visibility": "rkaf:orgVisible",
  "rkaf:rationale": "Subject text contains explicit requirement language identifying an evidence type. Promoting from candidateRelatedTo to typed requiresEvidenceType for human review.",
  "prov:wasDerivedFrom": "https://example.org/assertion/cand-001",
  "prov:generatedAtTime": "2026-05-10T14:05:00-05:00"
}
```

## Phase 4: Human review and adoption

### Step 8 — `endorseWithQualifier` attestation with `proposesApplicability`

```json
{
  "@context": "https://rulespec.org/context/v1.jsonld",
  "@id": "https://example.org/attestation/att-001",
  "@type": "rkaf:Attestation",
  "rkaf:targetAssertion": "https://example.org/assertion/req-001",
  "rkaf:attestor": "https://example.org/user/program-analyst-1",
  "rkaf:attestorType": "rkaf:humanUser",
  "rkaf:role": "rkaf:programAnalyst",
  "rkaf:decision": "rkaf:endorseWithQualifier",
  "rkaf:scope": "rkaf:organization",
  "rkaf:visibility": "rkaf:orgVisible",
  "rkaf:rationale": "Requirement applies only to benefit category B applications. Category A uses self-attestation under separate policy.",
  "rkaf:proposesApplicability": {
    "@type": "rkaf:ApplicabilityContext",
    "rkaf:benefitCategory": "B",
    "rkaf:excludesCategory": ["A"]
  },
  "prov:generatedAtTime": "2026-05-10T15:30:00-05:00"
}
```

### Step 9 — `LocalAdoption` with `adoptsApplicability` and `adoptionAuthorityKind`

LocalAdoption with `adoptionAuthorityKind: localOperational` is the chain terminus for this scenario. No `hasAuthority` assertion needed because the source isn't a legal/regulatory resource.

```json
{
  "@context": "https://rulespec.org/context/v1.jsonld",
  "@id": "https://example.org/adoption/caa-42-req-001",
  "@type": "rkaf:LocalAdoption",
  "rkaf:organization": "https://example.org/org/caa-42",
  "rkaf:targetAssertion": "https://example.org/assertion/req-001",
  "rkaf:adoptionStatus": "rkaf:adoptedForDrafting",
  "rkaf:usageEligibility": "rkaf:draftGenerationAllowed",
  "rkaf:adoptionAuthorityKind": "rkaf:localOperational",
  "rkaf:adoptionScope": "csbg-benefit-category-b-intake-v3",
  "rkaf:authorizedBy": "https://example.org/user/program-director-1",
  "rkaf:basedOnAttestation": [
    "https://example.org/attestation/att-001"
  ],
  "rkaf:adoptsApplicability": {
    "@type": "rkaf:ApplicabilityContext",
    "rkaf:benefitCategory": "B"
  },
  "prov:generatedAtTime": "2026-05-10T15:45:00-05:00"
}
```

## Phase 5: Generation and bridge validation

### Step 10 — Generated Formspec field v1

```json
{
  "@context": "https://rulespec.org/context/v1.jsonld",
  "@id": "https://example.org/form-field/csbg-cat-b-intake/income-documentation",
  "@type": ["rkaf:GeneratedWorkProduct", "formspec:Field"],
  "formspec:fieldName": "income_documentation",
  "formspec:label": "Household income documentation (prior 12 months)",
  "formspec:dataType": "file-upload",
  "formspec:required": true,
  "rkaf:collectsEvidenceType": "https://registry.example.gov/concepts/HouseholdIncomeEvidence",
  "rkaf:justifiedByAssertion": ["https://example.org/assertion/req-001"],
  "rkaf:justificationBackedBy": "https://example.org/adoption/caa-42-req-001",
  "rkaf:derivedFromFragment": ["https://example.org/fragment/wiki-csbg-eligibility-rev-1247/sec-3-p2"],
  "rkaf:reviewStatus": "rkaf:draft",
  "rkaf:usageEligibility": "rkaf:draftGenerationAllowed",
  "rkaf:bridgeContractVersion": "rkaf-bridge/1.0",
  "rkaf:generationRun": "https://example.org/methodrun/formspec-gen-2026-05-10-001",
  "rkaf:hasApplicability": {
    "@type": "rkaf:ApplicabilityContext",
    "rkaf:benefitCategory": "B"
  }
}
```

### Step 11 — `BridgeValidationResult` (accepted)

```json
{
  "@context": "https://rulespec.org/context/v1.jsonld",
  "@id": "https://example.org/bridge-validation/formspec-2026-05-10-001",
  "@type": "rkaf:BridgeValidationResult",
  "rkaf:packetId": "https://example.org/adoption/caa-42-req-001",
  "rkaf:consumer": "https://example.org/consumer/formspec-studio",
  "rkaf:bridgeContractVersion": "rkaf-bridge/1.0",
  "rkaf:result": "rkaf:accepted",
  "rkaf:effectiveUsageEligibility": "rkaf:draftGenerationAllowed",
  "rkaf:effectiveUsageEligibilityRationale": "Minimum eligibility across justification chain: req-001 (reviewQueueOnly) narrowed by LocalAdoption (draftGenerationAllowed). LocalAdoption authority kind localOperational, sufficient for draft scope.",
  "rkaf:errors": [],
  "rkaf:warnings": [],
  "rkaf:unsupportedAnchors": [],
  "rkaf:unresolvedConcepts": [],
  "rkaf:ineligibleAssertions": [],
  "rkaf:staleDependencies": [],
  "prov:generatedAtTime": "2026-05-10T15:50:00-05:00"
}
```

## Phase 6: Objection, qualification, revised generation

### Step 12 — Legal counsel `object` with narrowing `proposesApplicability`

```json
{
  "@context": "https://rulespec.org/context/v1.jsonld",
  "@id": "https://example.org/attestation/att-002",
  "@type": "rkaf:Attestation",
  "rkaf:targetAssertion": "https://example.org/assertion/req-001",
  "rkaf:targetWorkProduct": "https://example.org/form-field/csbg-cat-b-intake/income-documentation",
  "rkaf:attestor": "https://example.org/user/legal-counsel-1",
  "rkaf:attestorType": "rkaf:humanUser",
  "rkaf:role": "rkaf:legalReviewer",
  "rkaf:decision": "rkaf:object",
  "rkaf:scope": "rkaf:organization",
  "rkaf:visibility": "rkaf:orgVisible",
  "rkaf:rationale": "Source text says 'documentation establishing household income for the prior twelve months' — generated field accepts any file. Per audit guidance, requirement should be qualified to pay stubs or federal/state tax filings.",
  "rkaf:proposesApplicability": {
    "@type": "rkaf:ApplicabilityContext",
    "rkaf:acceptedDocumentTypes": [
      "https://registry.example.gov/concepts/PayStubEvidence",
      "https://registry.example.gov/concepts/FederalTaxReturnEvidence",
      "https://registry.example.gov/concepts/StateTaxReturnEvidence"
    ]
  },
  "prov:generatedAtTime": "2026-05-11T09:15:00-05:00"
}
```

### Step 13 — Successor assertion `req-002`

```json
{
  "@context": "https://rulespec.org/context/v1.jsonld",
  "@id": "https://example.org/assertion/req-002",
  "@type": "rkaf:RelationshipAssertion",
  "rkaf:assertsSubject": "https://example.org/fragment/wiki-csbg-eligibility-rev-1247/sec-3-p2",
  "rkaf:assertsPredicate": "rkaf:requiresEvidenceType",
  "rkaf:assertsObject": "https://registry.example.gov/concepts/HouseholdIncomeEvidence",
  "rkaf:assertionOrigin": "rkaf:humanQualified",
  "rkaf:hasTrustZone": "rkaf:Z5LocallyAdopted",
  "rkaf:hasSafetyLabel": "rkaf:R2ReviewedOperational",
  "rkaf:usageEligibility": "rkaf:localOperationalUse",
  "rkaf:hasEvidence": [
    {
      "@type": "rkaf:EvidenceBinding",
      "rkaf:evidenceRole": "rkaf:textualEvidence",
      "rkaf:bindsSourceFragment": "https://example.org/fragment/wiki-csbg-eligibility-rev-1247/sec-3-p2"
    }
  ],
  "rkaf:hasApplicability": {
    "@type": "rkaf:ApplicabilityContext",
    "rkaf:benefitCategory": "B",
    "rkaf:acceptedDocumentTypes": [
      "https://registry.example.gov/concepts/PayStubEvidence",
      "https://registry.example.gov/concepts/FederalTaxReturnEvidence",
      "https://registry.example.gov/concepts/StateTaxReturnEvidence"
    ],
    "rkaf:timeWindow": "P12M"
  },
  "rkaf:supersedesAssertion": "https://example.org/assertion/req-001",
  "rkaf:basedOnAttestations": [
    "https://example.org/attestation/att-001",
    "https://example.org/attestation/att-002"
  ]
}
```

### Step 14 — New LocalAdoption for `req-002` (operational eligibility)

```json
{
  "@context": "https://rulespec.org/context/v1.jsonld",
  "@id": "https://example.org/adoption/caa-42-req-002",
  "@type": "rkaf:LocalAdoption",
  "rkaf:organization": "https://example.org/org/caa-42",
  "rkaf:targetAssertion": "https://example.org/assertion/req-002",
  "rkaf:adoptionStatus": "rkaf:adoptedForLocalOperations",
  "rkaf:usageEligibility": "rkaf:localOperationalUse",
  "rkaf:adoptionAuthorityKind": "rkaf:localOperational",
  "rkaf:adoptionScope": "csbg-benefit-category-b-intake-v3",
  "rkaf:authorizedBy": "https://example.org/user/program-director-1",
  "rkaf:basedOnAttestation": [
    "https://example.org/attestation/att-001",
    "https://example.org/attestation/att-002"
  ],
  "rkaf:adoptsApplicability": {
    "@type": "rkaf:ApplicabilityContext",
    "rkaf:benefitCategory": "B"
  },
  "prov:generatedAtTime": "2026-05-11T10:30:00-05:00"
}
```

### Step 15 — Revised Formspec field v2

```json
{
  "@context": "https://rulespec.org/context/v1.jsonld",
  "@id": "https://example.org/form-field/csbg-cat-b-intake/income-documentation/v2",
  "@type": ["rkaf:GeneratedWorkProduct", "formspec:Field"],
  "formspec:fieldName": "income_documentation",
  "formspec:label": "Household income documentation (prior 12 months)",
  "formspec:dataType": "file-upload",
  "formspec:required": true,
  "formspec:acceptedDocumentTypes": ["pay-stub", "federal-tax-return", "state-tax-return"],
  "rkaf:collectsEvidenceType": "https://registry.example.gov/concepts/HouseholdIncomeEvidence",
  "rkaf:justifiedByAssertion": ["https://example.org/assertion/req-002"],
  "rkaf:justificationBackedBy": "https://example.org/adoption/caa-42-req-002",
  "rkaf:supersedesWorkProduct": "https://example.org/form-field/csbg-cat-b-intake/income-documentation",
  "rkaf:reviewStatus": "rkaf:operational",
  "rkaf:usageEligibility": "rkaf:localOperationalUse",
  "rkaf:bridgeContractVersion": "rkaf-bridge/1.0",
  "rkaf:hasApplicability": {
    "@type": "rkaf:ApplicabilityContext",
    "rkaf:benefitCategory": "B"
  }
}
```

## Phase 7: Source revision and classification

### Step 16 — New artifact captured (rev-1302)

```json
{
  "@context": "https://rulespec.org/context/v1.jsonld",
  "@id": "https://example.org/artifact/wiki-csbg-eligibility-rev-1302",
  "@type": "rkaf:Artifact",
  "rkaf:sourceType": "mediawiki-page-revision",
  "rkaf:contentHash": "sha256:9b2c1e7a...e84f",
  "rkaf:capturedAt": "2026-06-15T11:00:00-05:00",
  "rkaf:capturedBy": "https://example.org/connector/mediawiki-v2",
  "rkaf:sourceUrl": "https://wiki.example.org/csbg-policy/Eligibility?oldid=1302",
  "rkaf:precedingArtifact": "https://example.org/artifact/wiki-csbg-eligibility-rev-1247",
  "rkaf:accessScope": "internal"
}
```

### Step 17 — RevisionClassification (gate before cascade)

This step is the non-cascading branch's exit point — if classification had returned `editorialRevisionOf`, no cascade would fire. Including it explicitly forces every artifact-revision to be classified before lifecycle events emit.

```json
{
  "@context": "https://rulespec.org/context/v1.jsonld",
  "@id": "https://example.org/classification/rev-1302",
  "@type": "rkaf:RevisionClassification",
  "rkaf:subjectArtifact": "https://example.org/artifact/wiki-csbg-eligibility-rev-1302",
  "rkaf:priorArtifact": "https://example.org/artifact/wiki-csbg-eligibility-rev-1247",
  "rkaf:classification": "rkaf:materiallyRevises",
  "rkaf:rationale": "Diff changes 'prior twelve months' to 'prior ninety days' — alters evidence time-window scope for an active operational requirement. Material change, not editorial.",
  "rkaf:classifiedBy": "https://example.org/user/program-analyst-1",
  "rkaf:diffSummary": "Section 3, paragraph 2: '12 months' → '90 days'; effective date '2026-06-15'.",
  "prov:generatedAtTime": "2026-06-15T11:05:00-05:00"
}
```

### Step 18 — PolicyResourceVersion rev-1302

```json
{
  "@context": "https://rulespec.org/context/v1.jsonld",
  "@id": "https://example.org/resource/csbg-eligibility-policy/rev-1302",
  "@type": "rkaf:PolicyResourceVersion",
  "rkaf:resourceLineage": "https://example.org/resource/csbg-eligibility-policy",
  "rkaf:versionLabel": "rev-1302",
  "rkaf:effectivePeriodStart": "2026-06-15T00:00:00-05:00",
  "rkaf:realizedByArtifact": "https://example.org/artifact/wiki-csbg-eligibility-rev-1302",
  "rkaf:precedingVersion": "https://example.org/resource/csbg-eligibility-policy/rev-1247",
  "rkaf:resourceKind": "internalOrganizationalPolicy",
  "rkaf:accessScope": "internal"
}
```

### Step 19 — `amends` at ResourceVersion level

```json
{
  "@context": "https://rulespec.org/context/v1.jsonld",
  "@id": "https://example.org/assertion/amend-001",
  "@type": "rkaf:RelationshipAssertion",
  "rkaf:assertsSubject": "https://example.org/resource/csbg-eligibility-policy/rev-1302",
  "rkaf:assertsPredicate": "rkaf:amends",
  "rkaf:assertsObject": "https://example.org/resource/csbg-eligibility-policy/rev-1247",
  "rkaf:assertionOrigin": "rkaf:reviewClassified",
  "rkaf:hasTrustZone": "rkaf:Z4AttestedAssertion",
  "rkaf:hasSafetyLabel": "rkaf:A3AuthorityCritical",
  "rkaf:usageEligibility": "rkaf:localOperationalUse",
  "rkaf:hasEvidence": [
    {
      "@type": "rkaf:EvidenceBinding",
      "rkaf:evidenceRole": "rkaf:structuralEvidence",
      "rkaf:basedOnClassification": "https://example.org/classification/rev-1302",
      "rkaf:supportingQuote": "Amended income verification window from prior twelve months to prior ninety days, effective 2026-06-15."
    }
  ],
  "rkaf:amendmentScope": {
    "@type": "rkaf:ProvisionScope",
    "rkaf:affectedFragments": [
      "https://example.org/fragment/wiki-csbg-eligibility-rev-1247/sec-3-p2"
    ]
  }
}
```

### Step 20 — AmendmentPacket with `CascadeClosureV1`

```json
{
  "@context": "https://rulespec.org/context/v1.jsonld",
  "@id": "https://example.org/packet/amendment-001",
  "@type": "rkaf:AmendmentPacket",
  "rkaf:emittedBy": "https://example.org/assertion/amend-001",
  "rkaf:effectiveDate": "2026-06-15T00:00:00-05:00",
  "rkaf:bridgeContractVersion": "rkaf-bridge/1.0",
  "rkaf:cascadeAlgorithm": "rkaf:CascadeClosureV1",
  "rkaf:cascadeClosureDescription": "Transitive closure over inverse {justifiedByAssertion, derivedFromFragment, hasAuthority, derivesAuthorityFrom, implements, requiresEvidenceType, collectsEvidenceType, operationallyDependsOn, supersedesAssertion, supersedesWorkProduct}, scoped to active/adopted state at effectiveDate.",
  "rkaf:affectedAssertions": [
    "https://example.org/assertion/req-002"
  ],
  "rkaf:affectedAuthorityAssertions": [],
  "rkaf:affectedImplementationAssertions": [],
  "rkaf:affectedWorkProducts": [
    "https://example.org/form-field/csbg-cat-b-intake/income-documentation/v2"
  ],
  "rkaf:requiredRevalidationActions": [
    {
      "@type": "rkaf:RevalidationAction",
      "rkaf:targetAssertion": "https://example.org/assertion/req-002",
      "rkaf:reason": "Source fragment materially revised; window changed from P12M to P90D. Reviewer must confirm requiresEvidenceType still applies and update hasApplicability.timeWindow.",
      "rkaf:priority": "high"
    },
    {
      "@type": "rkaf:RevalidationAction",
      "rkaf:targetWorkProduct": "https://example.org/form-field/csbg-cat-b-intake/income-documentation/v2",
      "rkaf:reason": "Field label and timeWindow reference 'prior 12 months'; source now 'prior 90 days'. Revise before continued operational use.",
      "rkaf:priority": "high"
    }
  ],
  "rkaf:pointInTimeExceptions": [
    {
      "@type": "rkaf:PointInTimeException",
      "rkaf:scopeDescription": "applications submitted before 2026-06-15 retain prior assertion",
      "rkaf:retainsAssertion": "https://example.org/assertion/req-002",
      "rkaf:evaluationAnchor": "rkaf:applicationSubmissionTime",
      "rkaf:exceptionEffectivePeriodEnd": "2026-06-15T00:00:00-05:00"
    }
  ],
  "prov:generatedAtTime": "2026-06-15T11:15:00-05:00"
}
```

## Phase 8: Cascade response

### Step 21 — `BridgeValidationResult` (acceptedWithWarnings)

```json
{
  "@context": "https://rulespec.org/context/v1.jsonld",
  "@id": "https://example.org/bridge-validation/formspec-2026-06-15-001",
  "@type": "rkaf:BridgeValidationResult",
  "rkaf:packetId": "https://example.org/packet/amendment-001",
  "rkaf:consumer": "https://example.org/consumer/formspec-studio",
  "rkaf:bridgeContractVersion": "rkaf-bridge/1.0",
  "rkaf:result": "rkaf:acceptedWithWarnings",
  "rkaf:errors": [],
  "rkaf:warnings": [
    {
      "@type": "rkaf:StaleDependencyWarning",
      "rkaf:affectedWorkProduct": "https://example.org/form-field/csbg-cat-b-intake/income-documentation/v2",
      "rkaf:transitionTo": "rkaf:staleForCurrentUse",
      "rkaf:detail": "Field justification chain (req-002) affected by materiallyRevises on source fragment. Field transitions to staleForCurrentUse pending RevalidationClosureEvent."
    }
  ],
  "rkaf:unsupportedAnchors": [],
  "rkaf:unresolvedConcepts": [],
  "rkaf:ineligibleAssertions": [],
  "rkaf:staleDependencies": [
    "https://example.org/form-field/csbg-cat-b-intake/income-documentation/v2"
  ],
  "rkaf:declaredSupportedAnchors": [
    "rkaf:applicationSubmissionTime",
    "rkaf:eligibilityDeterminationTime",
    "rkaf:currentTime",
    "rkaf:effectivePeriodStart"
  ],
  "prov:generatedAtTime": "2026-06-15T11:20:00-05:00"
}
```

### Step 22 — RevalidationEvent (staleForCurrentUse)

```json
{
  "@context": "https://rulespec.org/context/v1.jsonld",
  "@id": "https://example.org/revalidation/req-002-postamend",
  "@type": "rkaf:RevalidationEvent",
  "rkaf:triggeredByPacket": "https://example.org/packet/amendment-001",
  "rkaf:targetAssertion": "https://example.org/assertion/req-002",
  "rkaf:targetWorkProduct": "https://example.org/form-field/csbg-cat-b-intake/income-documentation/v2",
  "rkaf:transitionTo": "rkaf:staleForCurrentUse",
  "rkaf:revisedUsageEligibility": "rkaf:reviewQueueOnly",
  "rkaf:retainedPointInTimeException": {
    "@type": "rkaf:PointInTimeException",
    "rkaf:scopeDescription": "applications submitted before 2026-06-15 retain prior assertion",
    "rkaf:evaluationAnchor": "rkaf:applicationSubmissionTime"
  },
  "rkaf:queuedFor": "https://example.org/user/program-analyst-1",
  "prov:generatedAtTime": "2026-06-15T11:20:00-05:00"
}
```

## Phase 9: Successor and closure

### Step 23 — Successor assertion `req-003` (timeWindow P90D)

```json
{
  "@context": "https://rulespec.org/context/v1.jsonld",
  "@id": "https://example.org/assertion/req-003",
  "@type": "rkaf:RelationshipAssertion",
  "rkaf:assertsSubject": "https://example.org/fragment/wiki-csbg-eligibility-rev-1302/sec-3-p2",
  "rkaf:assertsPredicate": "rkaf:requiresEvidenceType",
  "rkaf:assertsObject": "https://registry.example.gov/concepts/HouseholdIncomeEvidence",
  "rkaf:assertionOrigin": "rkaf:humanRevalidation",
  "rkaf:hasTrustZone": "rkaf:Z5LocallyAdopted",
  "rkaf:hasSafetyLabel": "rkaf:R2ReviewedOperational",
  "rkaf:usageEligibility": "rkaf:localOperationalUse",
  "rkaf:hasEvidence": [
    {
      "@type": "rkaf:EvidenceBinding",
      "rkaf:evidenceRole": "rkaf:textualEvidence",
      "rkaf:bindsSourceFragment": "https://example.org/fragment/wiki-csbg-eligibility-rev-1302/sec-3-p2"
    }
  ],
  "rkaf:hasApplicability": {
    "@type": "rkaf:ApplicabilityContext",
    "rkaf:benefitCategory": "B",
    "rkaf:acceptedDocumentTypes": [
      "https://registry.example.gov/concepts/PayStubEvidence",
      "https://registry.example.gov/concepts/FederalTaxReturnEvidence",
      "https://registry.example.gov/concepts/StateTaxReturnEvidence"
    ],
    "rkaf:timeWindow": "P90D"
  },
  "rkaf:supersedesAssertion": "https://example.org/assertion/req-002",
  "rkaf:revalidationOf": "https://example.org/revalidation/req-002-postamend"
}
```

(LocalAdoption for `req-003` omitted for brevity — same shape as Step 14, targeting `req-003`, with `adoptionStatus: adoptedForLocalOperations`.)

### Step 24 — Formspec field v3

```json
{
  "@context": "https://rulespec.org/context/v1.jsonld",
  "@id": "https://example.org/form-field/csbg-cat-b-intake/income-documentation/v3",
  "@type": ["rkaf:GeneratedWorkProduct", "formspec:Field"],
  "formspec:fieldName": "income_documentation",
  "formspec:label": "Household income documentation (prior 90 days)",
  "formspec:dataType": "file-upload",
  "formspec:required": true,
  "formspec:acceptedDocumentTypes": ["pay-stub", "federal-tax-return", "state-tax-return"],
  "rkaf:collectsEvidenceType": "https://registry.example.gov/concepts/HouseholdIncomeEvidence",
  "rkaf:justifiedByAssertion": ["https://example.org/assertion/req-003"],
  "rkaf:supersedesWorkProduct": "https://example.org/form-field/csbg-cat-b-intake/income-documentation/v2",
  "rkaf:reviewStatus": "rkaf:operational",
  "rkaf:usageEligibility": "rkaf:localOperationalUse",
  "rkaf:bridgeContractVersion": "rkaf-bridge/1.0",
  "rkaf:hasApplicability": {
    "@type": "rkaf:ApplicabilityContext",
    "rkaf:benefitCategory": "B",
    "rkaf:timeWindow": "P90D"
  }
}
```

### Step 25 — `RevalidationClosureEvent`

```json
{
  "@context": "https://rulespec.org/context/v1.jsonld",
  "@id": "https://example.org/revalidation-closure/req-002-postamend",
  "@type": "rkaf:RevalidationClosureEvent",
  "rkaf:triggeredByPacket": "https://example.org/packet/amendment-001",
  "rkaf:closesRevalidationEvent": "https://example.org/revalidation/req-002-postamend",
  "rkaf:successorAssertion": "https://example.org/assertion/req-003",
  "rkaf:successorWorkProduct": "https://example.org/form-field/csbg-cat-b-intake/income-documentation/v3",
  "rkaf:closureDecision": "rkaf:revalidatedWithSuccessor",
  "rkaf:closedBy": "https://example.org/user/program-director-1",
  "prov:generatedAtTime": "2026-06-16T10:30:00-05:00"
}
```

---

## Model issues surfaced by this rewrite

Most of Pass 2's eight issues are closed. A few new ones surfaced while drafting v0.2:

1. **`assertionOrigin` vocabulary needs enumeration.** I used `aiSuggested`, `aiPromoted`, `humanQualified`, `humanRevalidation`, `reviewClassified`. These should be a defined enumeration tied to the trust-zone model. Recommend defining the closed set in PKAO core.

2. **`reviewStatus` on GeneratedWorkProduct vs. assertion-side state.** I used `rkaf:reviewStatus: rkaf:operational` on field v2/v3 — but per the Pass 3 decision, status is computed per scope from attestations/adoptions, not stored. The work-product-side `reviewStatus` is therefore either (a) a denormalized cache that consumers compute on ingest, or (b) needs renaming to something like `rkaf:effectiveReviewStateAtGeneration` to be honest about its semantics. Recommend (a) with a normative rule that the cache is non-authoritative and must be recomputed by any consumer that traverses justifications.

3. **`exceptionEffectivePeriodEnd` on PointInTimeException.** I added this field on Step 20 to bound when the historical exception applies. It's not in the model yet. Worth adding to the `PointInTimeException` shape: `rkaf:exceptionEffectivePeriodStart` / `rkaf:exceptionEffectivePeriodEnd` so consumers know when the exception window closes.

4. **`declaredSupportedAnchors` belongs on the consumer registration, not on every `BridgeValidationResult`.** I included it on the Step 21 result for visibility, but the right home is a consumer-registration record (`rkaf:BridgeConsumerRegistration`) that consumers publish once. Then `BridgeValidationResult` references it. Worth specifying.

5. **`basedOnClassification` evidence-binding role.** Step 19 introduced this to link the `amends` assertion's evidence to the `RevisionClassification`. The evidence-binding model should formalize classifications as a first-class evidence type alongside source fragments and quotes.

6. **`rkaf:revalidationOf` link on the successor assertion (Step 23).** I added this to make the closure-graph traversable from successor → revalidation event → packet → source assertion. Not strictly necessary if the RevalidationClosureEvent carries both ends, but useful for read-model queries. Recommend adding to the assertion shape as optional.

7. **The fixture exercises `localOperational` authority only.** A second fixture grounded in statute/regulation is needed to exercise `hasAuthority` (with `authorityKind: statutory`/`regulatory`), `derivesAuthorityFrom` chains across delegation instruments, and the rule-6 termination conditions for non-local-adoption authority. Suggest naming this fixture `rkaf-fixture-localops.json` and writing a sibling `rkaf-fixture-statutory.json` next.

8. **`rescinds` and `editorialRevisionOf` branches not exercised.** Two short sibling fixtures would close the lifecycle predicate coverage: one where a wiki page has a typo fix (editorial classification, no cascade), one where a policy is rescinded with no replacement (RescissionPacket, downstream assertions blocked).

## What this fixture is ready for

- Anchoring SHACL shapes for `RelationshipAssertion`, `Attestation`, `LocalAdoption`, `PolicyResourceVersion`, `AmendmentPacket`, `RevalidationEvent`, `RevalidationClosureEvent`, `BridgeValidationResult`
- Anchoring a minimal `ConceptRegistry` spec (the registry references in this fixture define the minimum API surface needed)
- Anchoring the cascade closure algorithm specification (`CascadeClosureV1`)
- Anchoring bridge-consumer registration shape

## Recommended next deliverable

ConceptRegistry mini-spec, scoped to:

- concept minting authority and namespace ownership
- `rkaf:RegisteredConcept` vs `rkaf:LocalConcept` shapes
- SKOS mapping rules (`exactMatch`, `closeMatch`, `broadMatch`, `narrowMatch`) and when each is acceptable for `collectsEvidenceType` / `requiresEvidenceType` resolution
- concept deprecation, merge, split lifecycle
- mapping dispute resolution (when Org A's `closeMatch` differs from Org B's)
- consumer resolution behavior (cache TTLs, registry unavailability handling)
- interop requirements (what a public registry must expose; what a local registry MUST declare)

The fixture above gives ConceptRegistry concrete anchors — `HouseholdIncomeEvidence`, `PayStubEvidence`, etc. — to design against rather than abstract concept naming rules.
