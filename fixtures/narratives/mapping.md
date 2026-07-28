# Rulespec Mapping Fixture v0.1

> **Historical, non-conforming editorial record.** This narrative predates
> `0.2.0-pre.8` and MUST NOT be used as current authoring guidance. It retains
> retired assertion-origin, concept-status, inline evidence, and
> concept-mapping forms so the earlier worked trace remains auditable. Current
> normative examples are the JSON-LD fixtures validated by
> `tools/ci_validate.py` and the specifications under `spec/`.

> **Note**: This narrative was written pre-ADR-0093. `BridgeValidationResult` code blocks below show the legacy flat indicator arrays (`rkaf:warnings`, `rkaf:errors`, `rkaf:staleDependencies`, `rkaf:registryUnavailable`, `rkaf:registryVersionOutOfRange`). The current shape uses a single `rkaf:findings` list of `rkaf:Finding` `@id`s — see ADR-0093.

Status: Editor's Draft conformance fixture for ConceptRegistry-Lifecycle and -Federated
Companion to: Rulespec Core, Rulespec Conformance Fixture v0.2, Rulespec ConceptRegistry v0.1.1
Bridge contract: `rkaf-bridge/1.0`

## Purpose

The v0.2 local-operational fixture exercises ConceptRegistry-Core via direct registered-concept resolution. This fixture exercises the rest: LocalConcept resolution at four mapping strengths, `LocalAdoption` of a mapping, lifecycle split cascade, and federated mapping conflict at `informational` severity.

## Scenario

Two community action agencies use the public-benefits-evidence registry from v0.2. Each mints its own local terminology and asserts mappings:

- **CAA-42** has the `caa-42:IncomeDocs` LocalConcept and asserts a `skos:closeMatch` to `registry:HouseholdIncomeEvidence`.
- **CAA-77** has the `caa-77:HouseholdIncomeProof` LocalConcept and asserts only a `skos:broadMatch` to `registry:HouseholdIncomeEvidence`.

Both orgs run intake forms that reference their LocalConcepts. The fixture walks each through draft → operational → registry split → revalidation.

## Test cases exercised

1. **Pre-adoption closeMatch.** Mapping asserted but not locally adopted. Field allowed at `draftGenerationAllowed`; warning surfaced.
2. **Adopted closeMatch.** Mapping has `LocalAdoption`; field promoted to `localOperationalUse` with `MappingApplicabilityContext` constraining purpose.
3. **broadMatch only.** Mapping is `skos:broadMatch`; field refused for operational use, allowed at `draftGenerationAllowed` with explicit `unresolvedForOperationalUse` status.
4. **Concept split.** Registry splits `HouseholdIncomeEvidence` into two successors. CAA-42's operational field transitions to `staleForCurrentUse`; CAA-77's draft field is also affected. Disambiguation produces successor mappings; closure event resolves.

Plus: an `informational` `MappingConflict` between CAA-42's `closeMatch` and CAA-77's `broadMatch` (different local terms mapping to the same registry concept at different strengths).

---

## Phase 1: Pre-existing registry concept

### Step 1 — Registered concept (from v0.2 context, restated for self-containment)

```json
{
  "@id": "https://registry.example.gov/concepts/HouseholdIncomeEvidence",
  "@type": ["skos:Concept", "rkaf:RegisteredConcept"],
  "skos:prefLabel": "Household income evidence",
  "rkaf:managedByRegistry": "https://registry.example.gov/registries/public-benefits-evidence",
  "rkaf:conceptScope": "rkaf:public",
  "rkaf:conceptStatus": "rkaf:registered",
  "rkaf:registeredAt": "2025-11-01T00:00:00-05:00"
}
```

### Step 2 — Registry

```json
{
  "@id": "https://registry.example.gov/registries/public-benefits-evidence",
  "@type": "rkaf:ConceptRegistry",
  "rkaf:registryName": "Public Benefits Evidence Concept Registry",
  "rkaf:namespacePrefix": "https://registry.example.gov/concepts/",
  "rkaf:mintingAuthority": "https://registry.example.gov/authorities/pbe-curation-board",
  "rkaf:governanceModel": "rkaf:federatedCuration",
  "rkaf:resolutionEndpoint": "https://registry.example.gov/api/v1/concepts/",
  "rkaf:registryVersion": "2026-04-01"
}
```

## Phase 2: CAA-42 mints LocalConcept and asserts closeMatch

### Step 3 — CAA-42 LocalConcept

```json
{
  "@id": "https://example.org/concepts/caa-42/IncomeDocs",
  "@type": ["skos:Concept", "rkaf:LocalConcept"],
  "skos:prefLabel": "Income docs",
  "skos:altLabel": ["proof of household income"],
  "rkaf:definedInScope": "https://example.org/org/caa-42",
  "rkaf:conceptScope": "rkaf:organization",
  "rkaf:conceptStatus": "rkaf:localActive"
}
```

### Step 4 — closeMatch mapping (asserted, not adopted)

Mapping is an assertion. Baseline `usageEligibility: reviewQueueOnly`. Includes `MappingApplicabilityContext` per §4.4.

```json
{
  "@id": "https://example.org/assertion/caa-42-mapping-001",
  "@type": "rkaf:RelationshipAssertion",
  "rkaf:assertsSubject": "https://example.org/concepts/caa-42/IncomeDocs",
  "rkaf:assertsPredicate": "skos:closeMatch",
  "rkaf:assertsObject": "https://registry.example.gov/concepts/HouseholdIncomeEvidence",
  "rkaf:assertionOrigin": "rkaf:humanAsserted",
  "rkaf:hasTrustZone": "rkaf:Z4AttestedAssertion",
  "rkaf:hasSafetyLabel": "rkaf:R2ReviewedOperational",
  "rkaf:usageEligibility": "rkaf:reviewQueueOnly",
  "rkaf:hasApplicability": {
    "@type": "rkaf:MappingApplicabilityContext",
    "rkaf:operationalScope": "csbg-benefit-category-b-intake",
    "rkaf:evidencePurpose": ["eligibility-determination"],
    "rkaf:excludesPurposes": ["fraud-investigation", "tax-audit"]
  },
  "rkaf:hasEvidence": [
    {
      "@type": "rkaf:EvidenceBinding",
      "rkaf:evidenceRole": "rkaf:mappingRationale",
      "rkaf:rationaleText": "Local 'Income docs' is used in CAA-42 intake to mean the same evidence category as registry HouseholdIncomeEvidence within CSBG benefit category B eligibility determination."
    }
  ],
  "rkaf:scope": "https://example.org/org/caa-42",
  "prov:wasAttributedTo": "https://example.org/user/caa-42-program-analyst-1",
  "prov:generatedAtTime": "2026-07-01T10:00:00-05:00"
}
```

### Step 5 — CAA-42 draft field using LocalConcept (pre-adoption)

```json
{
  "@id": "https://example.org/form-field/caa-42-intake/income-docs/v1",
  "@type": ["rkaf:GeneratedWorkProduct", "formspec:Field"],
  "formspec:fieldName": "income_docs",
  "formspec:label": "Income docs (household)",
  "formspec:dataType": "file-upload",
  "rkaf:collectsEvidenceType": "https://example.org/concepts/caa-42/IncomeDocs",
  "rkaf:justifiedByAssertion": ["https://example.org/assertion/caa-42-req-002"],
  "rkaf:consumerLifecycleState": "rkaf:draft",
  "rkaf:usageEligibility": "rkaf:draftGenerationAllowed",
  "rkaf:bridgeContractVersion": "rkaf-bridge/1.0",
  "rkaf:hasApplicability": {
    "@type": "rkaf:ApplicabilityContext",
    "rkaf:benefitCategory": "B",
    "rkaf:evidencePurpose": "eligibility-determination"
  }
}
```

### Step 6 — BridgeConsumerRegistration (CAA-42 Formspec)

```json
{
  "@id": "https://example.org/consumer/caa-42-formspec/registration",
  "@type": "rkaf:BridgeConsumerRegistration",
  "rkaf:consumer": "https://example.org/consumer/caa-42-formspec",
  "rkaf:organization": "https://example.org/org/caa-42",
  "rkaf:bridgeContractVersion": "rkaf-bridge/1.0",
  "rkaf:supportedEvaluationAnchors": [
    "rkaf:applicationSubmissionTime",
    "rkaf:eligibilityDeterminationTime",
    "rkaf:currentTime",
    "rkaf:effectivePeriodStart"
  ],
  "rkaf:supportsRegistryVersionRange": [
    {
      "rkaf:registry": "https://registry.example.gov/registries/public-benefits-evidence",
      "rkaf:minVersion": "2026-01-01",
      "rkaf:maxVersion": "2026-12-31"
    }
  ],
  "rkaf:supportedAutomaticMigrations": ["rkaf:replaceInPlace"]
}
```

### Step 7 — BridgeValidationResult (case 1: pre-adoption closeMatch, draft-only)

```json
{
  "@id": "https://example.org/bridge-validation/caa-42-2026-07-01-001",
  "@type": "rkaf:BridgeValidationResult",
  "rkaf:packetId": "https://example.org/form-field/caa-42-intake/income-docs/v1",
  "rkaf:consumer": "https://example.org/consumer/caa-42-formspec",
  "rkaf:bridgeContractVersion": "rkaf-bridge/1.0",
  "rkaf:result": "rkaf:acceptedWithWarnings",
  "rkaf:effectiveUsageEligibility": "rkaf:draftGenerationAllowed",
  "rkaf:effectiveUsageEligibilityRationale": "LocalConcept resolves via closeMatch mapping, but mapping is not yet locally adopted. Ceiling held at draftGenerationAllowed per ConceptRegistry §5.2.",
  "rkaf:conceptResolutionResults": [
    {
      "@type": "rkaf:ConceptResolutionResult",
      "rkaf:inputConcept": "https://example.org/concepts/caa-42/IncomeDocs",
      "rkaf:resolvedConcept": "https://registry.example.gov/concepts/HouseholdIncomeEvidence",
      "rkaf:resolutionStatus": "rkaf:resolvedViaMapping",
      "rkaf:resolutionMethod": "rkaf:closeMatchAwaitingAdoption",
      "rkaf:mappingAssertion": "https://example.org/assertion/caa-42-mapping-001",
      "rkaf:registryVersion": "2026-04-01",
      "rkaf:cacheStatus": "rkaf:fresh",
      "rkaf:usageCeiling": "rkaf:draftGenerationAllowed",
      "rkaf:warnings": [
        {
          "@type": "rkaf:ConceptResolutionWarning",
          "rkaf:warningCode": "rkaf:closeMatchNotAdopted",
          "rkaf:detail": "Mapping caa-42-mapping-001 is closeMatch but lacks LocalAdoption in CAA-42 scope. Promote to operational by adopting the mapping."
        }
      ]
    }
  ],
  "rkaf:errors": [],
  "rkaf:staleDependencies": [],
  "prov:generatedAtTime": "2026-07-01T10:30:00-05:00"
}
```

## Phase 3: CAA-42 adopts the mapping; field promoted

### Step 8 — LocalAdoption of the mapping assertion

```json
{
  "@id": "https://example.org/adoption/caa-42-mapping-001",
  "@type": "rkaf:LocalAdoption",
  "rkaf:organization": "https://example.org/org/caa-42",
  "rkaf:targetAssertion": "https://example.org/assertion/caa-42-mapping-001",
  "rkaf:adoptionStatus": "rkaf:adoptedForLocalOperations",
  "rkaf:usageEligibility": "rkaf:localOperationalUse",
  "rkaf:adoptionAuthorityKind": "rkaf:localOperational",
  "rkaf:adoptionScope": "csbg-benefit-category-b-intake",
  "rkaf:authorizedBy": "https://example.org/user/caa-42-program-director-1",
  "rkaf:adoptsApplicability": {
    "@type": "rkaf:MappingApplicabilityContext",
    "rkaf:operationalScope": "csbg-benefit-category-b-intake",
    "rkaf:evidencePurpose": ["eligibility-determination"]
  },
  "prov:generatedAtTime": "2026-07-05T14:00:00-05:00"
}
```

### Step 9 — Promoted field v2

```json
{
  "@id": "https://example.org/form-field/caa-42-intake/income-docs/v2",
  "@type": ["rkaf:GeneratedWorkProduct", "formspec:Field"],
  "formspec:fieldName": "income_docs",
  "formspec:label": "Income docs (household)",
  "formspec:dataType": "file-upload",
  "rkaf:collectsEvidenceType": "https://example.org/concepts/caa-42/IncomeDocs",
  "rkaf:justifiedByAssertion": ["https://example.org/assertion/caa-42-req-002"],
  "rkaf:supersedesWorkProduct": "https://example.org/form-field/caa-42-intake/income-docs/v1",
  "rkaf:consumerLifecycleState": "rkaf:operational",
  "rkaf:usageEligibility": "rkaf:localOperationalUse",
  "rkaf:bridgeContractVersion": "rkaf-bridge/1.0",
  "rkaf:hasApplicability": {
    "@type": "rkaf:ApplicabilityContext",
    "rkaf:benefitCategory": "B",
    "rkaf:evidencePurpose": "eligibility-determination"
  }
}
```

### Step 10 — BridgeValidationResult (case 2: adopted closeMatch, operational)

```json
{
  "@id": "https://example.org/bridge-validation/caa-42-2026-07-05-001",
  "@type": "rkaf:BridgeValidationResult",
  "rkaf:packetId": "https://example.org/form-field/caa-42-intake/income-docs/v2",
  "rkaf:consumer": "https://example.org/consumer/caa-42-formspec",
  "rkaf:bridgeContractVersion": "rkaf-bridge/1.0",
  "rkaf:result": "rkaf:accepted",
  "rkaf:effectiveUsageEligibility": "rkaf:localOperationalUse",
  "rkaf:effectiveUsageEligibilityRationale": "Mapping caa-42-mapping-001 locally adopted; field's evidence purpose ('eligibility-determination') is within mapping's MappingApplicabilityContext.evidencePurpose. Ceiling raised to localOperationalUse.",
  "rkaf:conceptResolutionResults": [
    {
      "@type": "rkaf:ConceptResolutionResult",
      "rkaf:inputConcept": "https://example.org/concepts/caa-42/IncomeDocs",
      "rkaf:resolvedConcept": "https://registry.example.gov/concepts/HouseholdIncomeEvidence",
      "rkaf:resolutionStatus": "rkaf:resolvedViaMapping",
      "rkaf:resolutionMethod": "rkaf:closeMatchLocallyAdopted",
      "rkaf:mappingAssertion": "https://example.org/assertion/caa-42-mapping-001",
      "rkaf:registryVersion": "2026-04-01",
      "rkaf:cacheStatus": "rkaf:fresh",
      "rkaf:usageCeiling": "rkaf:localOperationalUse",
      "rkaf:warnings": [],
      "rkaf:errors": []
    }
  ],
  "prov:generatedAtTime": "2026-07-05T14:30:00-05:00"
}
```

## Phase 4: CAA-77 — broadMatch case

### Step 11 — CAA-77 LocalConcept

```json
{
  "@id": "https://example.org/concepts/caa-77/HouseholdIncomeProof",
  "@type": ["skos:Concept", "rkaf:LocalConcept"],
  "skos:prefLabel": "Household income proof",
  "rkaf:definedInScope": "https://example.org/org/caa-77",
  "rkaf:conceptScope": "rkaf:organization",
  "rkaf:conceptStatus": "rkaf:localActive"
}
```

### Step 12 — broadMatch mapping (S1 discovery only)

CAA-77 mapped their LocalConcept as broader than the registered concept (they may also accept items the registered concept excludes).

```json
{
  "@id": "https://example.org/assertion/caa-77-mapping-001",
  "@type": "rkaf:RelationshipAssertion",
  "rkaf:assertsSubject": "https://example.org/concepts/caa-77/HouseholdIncomeProof",
  "rkaf:assertsPredicate": "skos:broadMatch",
  "rkaf:assertsObject": "https://registry.example.gov/concepts/HouseholdIncomeEvidence",
  "rkaf:assertionOrigin": "rkaf:humanAsserted",
  "rkaf:hasTrustZone": "rkaf:Z4AttestedAssertion",
  "rkaf:hasSafetyLabel": "rkaf:S1SearchOnly",
  "rkaf:usageEligibility": "rkaf:searchOnly",
  "rkaf:hasEvidence": [
    {
      "@type": "rkaf:EvidenceBinding",
      "rkaf:evidenceRole": "rkaf:mappingRationale",
      "rkaf:rationaleText": "CAA-77 accepts a broader set of evidence than the registry concept defines, including informal employer letters and household budget statements."
    }
  ],
  "rkaf:scope": "https://example.org/org/caa-77",
  "prov:generatedAtTime": "2026-07-10T09:00:00-05:00"
}
```

### Step 13 — CAA-77 attempts operational field

CAA-77 tries to use the LocalConcept on an intake field with intended `usageEligibility: localOperationalUse`. The consumer will refuse the operational promotion.

```json
{
  "@id": "https://example.org/form-field/caa-77-intake/income-proof/v1",
  "@type": ["rkaf:GeneratedWorkProduct", "formspec:Field"],
  "formspec:fieldName": "income_proof",
  "formspec:label": "Household income proof",
  "formspec:dataType": "file-upload",
  "rkaf:collectsEvidenceType": "https://example.org/concepts/caa-77/HouseholdIncomeProof",
  "rkaf:justifiedByAssertion": ["https://example.org/assertion/caa-77-req-001"],
  "rkaf:consumerLifecycleState": "rkaf:proposedForOperational",
  "rkaf:proposedUsageEligibility": "rkaf:localOperationalUse",
  "rkaf:bridgeContractVersion": "rkaf-bridge/1.0"
}
```

### Step 14 — BridgeValidationResult (case 3: broadMatch refused operationally)

```json
{
  "@id": "https://example.org/bridge-validation/caa-77-2026-07-10-001",
  "@type": "rkaf:BridgeValidationResult",
  "rkaf:packetId": "https://example.org/form-field/caa-77-intake/income-proof/v1",
  "rkaf:consumer": "https://example.org/consumer/caa-77-formspec",
  "rkaf:bridgeContractVersion": "rkaf-bridge/1.0",
  "rkaf:result": "rkaf:rejected",
  "rkaf:effectiveUsageEligibility": "rkaf:draftGenerationAllowed",
  "rkaf:effectiveUsageEligibilityRationale": "Field requested promotion to localOperationalUse. Concept resolves only via skos:broadMatch (S1 / discovery). broadMatch cannot satisfy operational evidence-type resolution per ConceptRegistry §4.1. Field may continue at draftGenerationAllowed with explicit warning, OR consumer should obtain a closeMatch/exactMatch mapping before promotion.",
  "rkaf:conceptResolutionResults": [
    {
      "@type": "rkaf:ConceptResolutionResult",
      "rkaf:inputConcept": "https://example.org/concepts/caa-77/HouseholdIncomeProof",
      "rkaf:resolvedConcept": "https://registry.example.gov/concepts/HouseholdIncomeEvidence",
      "rkaf:resolutionStatus": "rkaf:unresolvedForOperationalUse",
      "rkaf:resolutionMethod": "rkaf:broadOrNarrowMatchDiscoveryOnly",
      "rkaf:mappingAssertion": "https://example.org/assertion/caa-77-mapping-001",
      "rkaf:registryVersion": "2026-04-01",
      "rkaf:cacheStatus": "rkaf:fresh",
      "rkaf:usageCeiling": "rkaf:searchOnly",
      "rkaf:warnings": [],
      "rkaf:errors": [
        {
          "@type": "rkaf:ConceptResolutionError",
          "rkaf:errorCode": "rkaf:operationalResolutionRequiresStrongerMapping",
          "rkaf:detail": "Only broadMatch available. Operational use requires exactMatch (trusted) or closeMatch (locally adopted with MappingApplicabilityContext)."
        }
      ]
    }
  ],
  "rkaf:suggestedRemediation": "Assert a skos:closeMatch mapping from caa-77:HouseholdIncomeProof to a registered concept, or narrow the LocalConcept definition and assert skos:exactMatch.",
  "prov:generatedAtTime": "2026-07-10T09:30:00-05:00"
}
```

## Phase 5: Informational mapping conflict surfaces

A registry-side observer (or a federated reconciliation process) notes that CAA-42 and CAA-77 both map to `HouseholdIncomeEvidence` at different strengths, suggesting their local concepts may be incompatible. Severity is `informational` because no shared operational artifact depends on both mappings.

### Step 15 — MappingConflict (informational)

```json
{
  "@id": "https://registry.example.gov/annotation/mapping-conflict-001",
  "@type": "rkaf:MappingConflict",
  "rkaf:conflictingMappings": [
    "https://example.org/assertion/caa-42-mapping-001",
    "https://example.org/assertion/caa-77-mapping-001"
  ],
  "rkaf:relatedConcept": "https://registry.example.gov/concepts/HouseholdIncomeEvidence",
  "rkaf:severity": "rkaf:informational",
  "rkaf:severityRationale": "CAA-42 asserts closeMatch (scoped to eligibility-determination); CAA-77 asserts broadMatch. No shared operational artifact or publication depends on both. Recorded for federated awareness; no consumer action required.",
  "rkaf:detectedBy": "https://registry.example.gov/agent/federation-reconciler-v1",
  "rkaf:detectedAt": "2026-07-15T00:00:00-05:00"
}
```

## Phase 6: Registry splits the concept

### Step 16 — ConceptLifecyclePacket (split)

```json
{
  "@id": "https://registry.example.gov/packets/lifecycle-001",
  "@type": "rkaf:ConceptLifecyclePacket",
  "rkaf:lifecycleEvent": "rkaf:split",
  "rkaf:subjectConcept": "https://registry.example.gov/concepts/HouseholdIncomeEvidence",
  "rkaf:successorConcepts": [
    "https://registry.example.gov/concepts/HouseholdIncomeEvidence-W2Filers",
    "https://registry.example.gov/concepts/HouseholdIncomeEvidence-NonW2Filers"
  ],
  "rkaf:effectiveDate": "2027-01-01T00:00:00-05:00",
  "rkaf:bridgeContractVersion": "rkaf-bridge/1.0",
  "rkaf:cascadeAlgorithm": "rkaf:CascadeClosureV1",
  "rkaf:cascadeClosureDescription": "Transitive closure over inverse {collectsEvidenceType, requiresEvidenceType, assertsObject (where object is subjectConcept), skos:exactMatch, skos:closeMatch, skos:broadMatch, skos:narrowMatch, skos:relatedMatch} edges, scoped to active/adopted state at effectiveDate.",
  "rkaf:safeAutomaticMigration": null,
  "rkaf:safeAutomaticMigrationRationale": "Split requires disambiguation between W2Filers and NonW2Filers based on local context. No deterministic in-place rewrite possible.",
  "rkaf:affectedAssertions": [
    "https://example.org/assertion/caa-42-mapping-001",
    "https://example.org/assertion/caa-77-mapping-001"
  ],
  "rkaf:affectedWorkProducts": [
    "https://example.org/form-field/caa-42-intake/income-docs/v2"
  ],
  "rkaf:requiredMigrationActions": [
    {
      "@type": "rkaf:MigrationAction",
      "rkaf:targetAssertion": "https://example.org/assertion/caa-42-mapping-001",
      "rkaf:reason": "Mapping points to subject concept being split. Must be replaced with a mapping to one or both successor concepts after disambiguation.",
      "rkaf:priority": "high"
    },
    {
      "@type": "rkaf:MigrationAction",
      "rkaf:targetWorkProduct": "https://example.org/form-field/caa-42-intake/income-docs/v2",
      "rkaf:reason": "Field operational via caa-42-mapping-001 which is now broken. Field transitions to staleForCurrentUse per ConceptRegistry §7.5.",
      "rkaf:priority": "high"
    }
  ],
  "prov:generatedAtTime": "2026-12-01T00:00:00-05:00"
}
```

### Step 17 — BridgeValidationResult on packet ingest (case 4: split cascade)

```json
{
  "@id": "https://example.org/bridge-validation/caa-42-2026-12-01-001",
  "@type": "rkaf:BridgeValidationResult",
  "rkaf:packetId": "https://registry.example.gov/packets/lifecycle-001",
  "rkaf:consumer": "https://example.org/consumer/caa-42-formspec",
  "rkaf:bridgeContractVersion": "rkaf-bridge/1.0",
  "rkaf:result": "rkaf:acceptedWithWarnings",
  "rkaf:warnings": [
    {
      "@type": "rkaf:StaleDependencyWarning",
      "rkaf:affectedWorkProduct": "https://example.org/form-field/caa-42-intake/income-docs/v2",
      "rkaf:transitionTo": "rkaf:staleForCurrentUse",
      "rkaf:detail": "Field depends on mapping caa-42-mapping-001 whose object concept is being split. No safeAutomaticMigration declared by packet AND consumer does not declare support for split-time auto-migration. Field transitions to staleForCurrentUse per ConceptRegistry §7.5."
    }
  ],
  "rkaf:staleDependencies": [
    "https://example.org/form-field/caa-42-intake/income-docs/v2"
  ],
  "rkaf:conceptResolutionResults": [
    {
      "@type": "rkaf:ConceptResolutionResult",
      "rkaf:inputConcept": "https://example.org/concepts/caa-42/IncomeDocs",
      "rkaf:resolvedConcept": "https://registry.example.gov/concepts/HouseholdIncomeEvidence",
      "rkaf:resolutionStatus": "rkaf:unresolvedConceptSplit",
      "rkaf:resolutionMethod": "rkaf:closeMatchLocallyAdopted",
      "rkaf:mappingAssertion": "https://example.org/assertion/caa-42-mapping-001",
      "rkaf:usageCeiling": "rkaf:reviewQueueOnly",
      "rkaf:warnings": [
        {
          "@type": "rkaf:ConceptResolutionWarning",
          "rkaf:warningCode": "rkaf:subjectConceptSplit",
          "rkaf:detail": "Mapped registered concept is in splitInto state. Disambiguate to one or both of: HouseholdIncomeEvidence-W2Filers, HouseholdIncomeEvidence-NonW2Filers."
        }
      ]
    }
  ],
  "prov:generatedAtTime": "2026-12-01T00:10:00-05:00"
}
```

### Step 18 — RevalidationEvent on the affected field

```json
{
  "@id": "https://example.org/revalidation/caa-42-income-docs-postsplit",
  "@type": "rkaf:RevalidationEvent",
  "rkaf:triggeredByPacket": "https://registry.example.gov/packets/lifecycle-001",
  "rkaf:targetAssertion": "https://example.org/assertion/caa-42-mapping-001",
  "rkaf:targetWorkProduct": "https://example.org/form-field/caa-42-intake/income-docs/v2",
  "rkaf:transitionTo": "rkaf:staleForCurrentUse",
  "rkaf:revisedUsageEligibility": "rkaf:reviewQueueOnly",
  "rkaf:queuedFor": "https://example.org/user/caa-42-program-analyst-1",
  "prov:generatedAtTime": "2026-12-01T00:10:00-05:00"
}
```

## Phase 7: CAA-42 disambiguates and closes

CAA-42 determines that for its CSBG benefit category B intake, both filer categories apply. They create two successor mappings.

### Step 19 — Successor mappings

```json
{
  "@id": "https://example.org/assertion/caa-42-mapping-002a",
  "@type": "rkaf:RelationshipAssertion",
  "rkaf:assertsSubject": "https://example.org/concepts/caa-42/IncomeDocs",
  "rkaf:assertsPredicate": "skos:closeMatch",
  "rkaf:assertsObject": "https://registry.example.gov/concepts/HouseholdIncomeEvidence-W2Filers",
  "rkaf:assertionOrigin": "rkaf:humanRevalidation",
  "rkaf:hasTrustZone": "rkaf:Z5LocallyAdopted",
  "rkaf:hasSafetyLabel": "rkaf:R2ReviewedOperational",
  "rkaf:usageEligibility": "rkaf:localOperationalUse",
  "rkaf:hasApplicability": {
    "@type": "rkaf:MappingApplicabilityContext",
    "rkaf:operationalScope": "csbg-benefit-category-b-intake",
    "rkaf:evidencePurpose": ["eligibility-determination"]
  },
  "rkaf:supersedesAssertion": "https://example.org/assertion/caa-42-mapping-001",
  "rkaf:revalidationOf": "https://example.org/revalidation/caa-42-income-docs-postsplit",
  "rkaf:scope": "https://example.org/org/caa-42"
}
```

```json
{
  "@id": "https://example.org/assertion/caa-42-mapping-002b",
  "@type": "rkaf:RelationshipAssertion",
  "rkaf:assertsSubject": "https://example.org/concepts/caa-42/IncomeDocs",
  "rkaf:assertsPredicate": "skos:closeMatch",
  "rkaf:assertsObject": "https://registry.example.gov/concepts/HouseholdIncomeEvidence-NonW2Filers",
  "rkaf:assertionOrigin": "rkaf:humanRevalidation",
  "rkaf:hasTrustZone": "rkaf:Z5LocallyAdopted",
  "rkaf:hasSafetyLabel": "rkaf:R2ReviewedOperational",
  "rkaf:usageEligibility": "rkaf:localOperationalUse",
  "rkaf:hasApplicability": {
    "@type": "rkaf:MappingApplicabilityContext",
    "rkaf:operationalScope": "csbg-benefit-category-b-intake",
    "rkaf:evidencePurpose": ["eligibility-determination"]
  },
  "rkaf:supersedesAssertion": "https://example.org/assertion/caa-42-mapping-001",
  "rkaf:revalidationOf": "https://example.org/revalidation/caa-42-income-docs-postsplit",
  "rkaf:scope": "https://example.org/org/caa-42"
}
```

### Step 20 — Successor field v3

The field now collects evidence resolving to either successor concept. Two `collectsEvidenceType` values; field-level applicability narrows by applicant type at runtime.

```json
{
  "@id": "https://example.org/form-field/caa-42-intake/income-docs/v3",
  "@type": ["rkaf:GeneratedWorkProduct", "formspec:Field"],
  "formspec:fieldName": "income_docs",
  "formspec:label": "Income docs (household)",
  "formspec:dataType": "file-upload",
  "rkaf:collectsEvidenceType": "https://example.org/concepts/caa-42/IncomeDocs",
  "rkaf:resolvedToConcepts": [
    "https://registry.example.gov/concepts/HouseholdIncomeEvidence-W2Filers",
    "https://registry.example.gov/concepts/HouseholdIncomeEvidence-NonW2Filers"
  ],
  "rkaf:justifiedByAssertion": ["https://example.org/assertion/caa-42-req-002"],
  "rkaf:supersedesWorkProduct": "https://example.org/form-field/caa-42-intake/income-docs/v2",
  "rkaf:consumerLifecycleState": "rkaf:operational",
  "rkaf:usageEligibility": "rkaf:localOperationalUse",
  "rkaf:bridgeContractVersion": "rkaf-bridge/1.0",
  "rkaf:hasApplicability": {
    "@type": "rkaf:ApplicabilityContext",
    "rkaf:benefitCategory": "B"
  }
}
```

### Step 21 — RevalidationClosureEvent

```json
{
  "@id": "https://example.org/revalidation-closure/caa-42-income-docs-postsplit",
  "@type": "rkaf:RevalidationClosureEvent",
  "rkaf:triggeredByPacket": "https://registry.example.gov/packets/lifecycle-001",
  "rkaf:closesRevalidationEvent": "https://example.org/revalidation/caa-42-income-docs-postsplit",
  "rkaf:successorAssertions": [
    "https://example.org/assertion/caa-42-mapping-002a",
    "https://example.org/assertion/caa-42-mapping-002b"
  ],
  "rkaf:successorWorkProduct": "https://example.org/form-field/caa-42-intake/income-docs/v3",
  "rkaf:closureDecision": "rkaf:revalidatedWithSuccessor",
  "rkaf:closedBy": "https://example.org/user/caa-42-program-director-1",
  "prov:generatedAtTime": "2026-12-15T11:00:00-05:00"
}
```

---

## Conformance assertions exercised

| Spec section | Test case | Step(s) |
|---|---|---|
| ConceptRegistry §2.2 (LocalConcept rules) | LocalConcept with mapping resolves; without mapping would warn | 3, 5, 7 |
| ConceptRegistry §4.1 (resolution strength) | closeMatch + adoption → operational; broadMatch → S1 only | 7, 10, 14 |
| ConceptRegistry §4.4 (MappingApplicabilityContext required for operational closeMatch) | Required field present on mapping; consumer checks evidence purpose | 4, 8 |
| ConceptRegistry §4.5 (trusted mapping) | LocalAdoption establishes trust for closeMatch | 8 |
| ConceptRegistry §5.4 (ConceptResolutionResult) | Populated for both success and failure cases | 7, 10, 14, 17 |
| ConceptRegistry §5.6 (BridgeValidationResult population) | conceptResolutionResults appear on every validation | 7, 10, 14, 17 |
| ConceptRegistry §7.1 (status → resolution behavior) | splitInto → unresolved for operational; staleForCurrentUse transition | 17 |
| ConceptRegistry §7.5 (lifecycle packet → staleForCurrentUse) | Field transitions because no safeAutomaticMigration declared | 17, 18 |
| ConceptRegistry §8 (MappingConflict + severity) | Informational severity recorded; no operational impact | 15 |
| Rulespec Core (RevalidationEvent / RevalidationClosureEvent reuse) | Lifecycle event triggers RevalidationEvent; successor mappings close it | 18, 21 |
| Rulespec Bridge Rule 2 (reducer, not minimum) | LocalAdoption of mapping raises effective ceiling from baseline `reviewQueueOnly` to `localOperationalUse` within scope | 8, 10 |

## Model issues surfaced by this fixture

1. **`rkaf:resolvedToConcepts` on a field with multiple successor mappings (Step 20).** I introduced this field to represent that v3 collects evidence resolvable to either of two registered concepts. The current spec has `collectsEvidenceType` as a single value pointing at the LocalConcept; the resolved registered concepts are downstream of the mapping graph. This works but consumers querying "what registered concept does this field collect?" would need to traverse mappings. Recommend formalizing `rkaf:resolvedToConcepts` as a denormalized cache on the field (non-authoritative, recomputable), parallel to the `consumerLifecycleState` decision.

2. **`rkaf:proposedUsageEligibility` (Step 13).** I needed a way to express "consumer wants to promote to localOperationalUse but the bridge is being asked to validate that intent." The current spec has `usageEligibility` as the artifact's effective ceiling. Introducing `proposedUsageEligibility` lets the consumer ask "would this be allowed?" without committing. Worth adding as an optional field on generated work products in proposal state.

3. **`rkaf:suggestedRemediation` on `BridgeValidationResult` (Step 14).** I added this as free text. For machine-actionable remediation, it should be structured: `{action: createMapping, predicate: skos:closeMatch, fromConcept, toConcept, requiredApplicability}`. Worth structuring before this becomes a UX surface.

4. **Multiple successor mappings from one LocalConcept (Steps 19a/19b).** Both are valid; the LocalConcept legitimately maps to both successors. The fixture treats them as sibling assertions with the same `supersedesAssertion` target. This works but raises a question: does `supersedesAssertion` need to be set-valued (one mapping replaced by two)? Currently it's a single reference; both successors point at the same old mapping. Consumers querying "what superseded mapping-001?" would get two results, which is correct but worth normatively confirming.

5. **`safeAutomaticMigration: null` (Step 16).** I used `null` to indicate "no safe migration declared." JSON-LD doesn't have semantics for null vs missing. Cleaner: omit the property entirely when no migration is declared, and let the absence of the property be the signal. The `safeAutomaticMigrationRationale` should be present only when explicitly chosen to be null-by-design (rare).

6. **Concept-side vs assertion-side scope on mappings.** Mapping assertions carry `rkaf:scope` (the asserting org), but mappings also have `MappingApplicabilityContext.operationalScope` (the program area). These are different things — one is about "who asserts," one is about "where the mapping applies." The naming could cause confusion; recommend renaming `MappingApplicabilityContext.operationalScope` to `programScope` or `applicationDomain` to avoid the collision.

## Conformance coverage matrix

This fixture, combined with Rulespec Conformance Fixture v0.2, exercises:

- **ConceptRegistry-Core:** ✅ direct resolution (v0.2), LocalConcept resolution (this fixture), mapping shapes with direction/applicability (this fixture), `ConceptResolutionResult` population (this fixture), basic registry-unavailable behavior (not exercised — needs companion fixture)
- **ConceptRegistry-Lifecycle:** ✅ split lifecycle cascade (this fixture), `staleForCurrentUse` propagation (this fixture), normative status table (split exercised; deprecation, merge, withdrawal not exercised — partial)
- **ConceptRegistry-Federated:** Partial — informational MappingConflict (this fixture), no `operationalConflict`/`publicationBlocking`/`authorityCritical` severity, no `CanonicalMapping`, no LocalConcept promotion. A second federated fixture would close these.

## Recommended companion fixtures

1. **Statutory fixture** (already planned) — `hasAuthority`, `derivesAuthorityFrom`, `authorityKind: statutory/regulatory/delegated`, `DelegationInstrument`, `RescissionPacket`.
2. **Registry-unavailable fixture** — short fixture exercising cache TTL boundaries, stale-cache use for non-critical concepts, refused-for-A3, registry-out-of-version-range.
3. **High-severity mapping conflict fixture** — `operationalConflict` and `publicationBlocking` severities, `CanonicalMapping` resolution by registry authority.
4. **LocalConcept promotion fixture** — full §9 promotion flow with `ConceptRegistrationEvent` and auto-generated `exactMatch` mapping.

Each can be small (5–10 steps) and target a single conformance edge.
