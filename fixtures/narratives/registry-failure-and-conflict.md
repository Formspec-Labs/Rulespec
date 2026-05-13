# Rulespec Registry Failure and Conflict Fixture v0.1

Status: Editor's Draft, final conformance fixture for v0.1 conformance set
Companion to: Rulespec Core, Rulespec Conformance Fixture v0.2 (local-operational), Rulespec Mapping Fixture v0.1, Rulespec Statutory Authority Fixture v0.1, Rulespec ConceptRegistry v0.1.2
Bridge contract: `rkaf-bridge/1.0`

## Purpose

Closes the conformance matrix. Exercises ten remaining behaviors in a single compact fixture: registry cache freshness, registry unavailability, registry version-range mismatch, high-severity mapping conflicts, canonical mapping resolution, safe automatic migration, and LocalConcept promotion to RegisteredConcept.

## Test cases exercised

| # | Case | Step(s) |
|---|---|---|
| 1 | Fresh cache → `accepted` | 2 |
| 2 | Stale cache, non-critical concept → `acceptedWithWarnings` | 3 |
| 3 | Stale cache, A3 authority-critical concept → `rejected` | 4 |
| 4 | No cache + registry unreachable → `rejected` | 5 |
| 5 | Registry version out of declared range → `acceptedWithWarnings` | 6 |
| 6 | `operationalConflict` mapping dispute → shared artifact `staleForCurrentUse` | 7 |
| 7 | `publicationBlocking` mapping dispute → publication refused | 8 |
| 8 | `CanonicalMapping` from registry authority resolves conflict | 9 |
| 9 | `safeAutomaticMigration: replaceInPlace` → no stale transition | 10 |
| 10 | LocalConcept promotion → `ConceptRegistrationEvent` + auto `exactMatch` mapping | 11 |

---

## Step 1: BridgeConsumerRegistration

```json
{
  "@context": "https://rulespec.org/context/v1.jsonld",
  "@id": "https://example.org/consumer/caa-42-formspec/registration",
  "@type": "rkaf:BridgeConsumerRegistration",
  "rkaf:consumer": "https://example.org/consumer/caa-42-formspec",
  "rkaf:organization": "https://example.org/org/caa-42",
  "rkaf:bridgeContractVersion": "rkaf-bridge/1.0",
  "rkaf:supportedEvaluationAnchors": [
    "rkaf:applicationSubmissionTime",
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
  "rkaf:supportedAutomaticMigrations": ["rkaf:replaceInPlace"],
  "rkaf:supportedAuthorityKinds": [
    "rkaf:statutory",
    "rkaf:regulatory",
    "rkaf:delegated",
    "rkaf:localOperational"
  ]
}
```

## Step 2 — Case 1: Fresh cache, accepted

A field references `registry:HouseholdIncomeEvidence`. Consumer has a fresh cache entry. Validation proceeds against cache.

```json
{
  "@id": "https://example.org/bridge-validation/case-1-fresh-cache",
  "@type": "rkaf:BridgeValidationResult",
  "rkaf:packetId": "https://example.org/form-field/caa-42-intake/income-docs/v3",
  "rkaf:consumer": "https://example.org/consumer/caa-42-formspec",
  "rkaf:bridgeContractVersion": "rkaf-bridge/1.0",
  "rkaf:result": "rkaf:accepted",
  "rkaf:conceptResolutionResults": [
    {
      "@type": "rkaf:ConceptResolutionResult",
      "rkaf:inputConcept": "https://registry.example.gov/concepts/HouseholdIncomeEvidence",
      "rkaf:resolvedConcept": "https://registry.example.gov/concepts/HouseholdIncomeEvidence",
      "rkaf:resolutionStatus": "rkaf:resolvedDirect",
      "rkaf:resolutionMethod": "rkaf:cacheServed",
      "rkaf:registryVersion": "2026-04-01",
      "rkaf:cacheStatus": "rkaf:fresh",
      "rkaf:cacheAgeSeconds": 1200,
      "rkaf:usageCeiling": "rkaf:localOperationalUse",
      "rkaf:warnings": [],
      "rkaf:errors": []
    }
  ],
  "prov:generatedAtTime": "2026-08-01T10:00:00-05:00"
}
```

## Step 3 — Case 2: Stale cache, non-critical concept, acceptedWithWarnings

Same concept, but the cache is past its 4h TTL (non-critical concept in `federatedCuration` registry). The consumer continues with stale cache and warns.

```json
{
  "@id": "https://example.org/bridge-validation/case-2-stale-non-critical",
  "@type": "rkaf:BridgeValidationResult",
  "rkaf:packetId": "https://example.org/form-field/caa-42-intake/income-docs/v3",
  "rkaf:consumer": "https://example.org/consumer/caa-42-formspec",
  "rkaf:result": "rkaf:acceptedWithWarnings",
  "rkaf:conceptResolutionResults": [
    {
      "@type": "rkaf:ConceptResolutionResult",
      "rkaf:inputConcept": "https://registry.example.gov/concepts/HouseholdIncomeEvidence",
      "rkaf:resolvedConcept": "https://registry.example.gov/concepts/HouseholdIncomeEvidence",
      "rkaf:resolutionStatus": "rkaf:resolvedDirect",
      "rkaf:resolutionMethod": "rkaf:staleCacheServed",
      "rkaf:registryVersion": "2026-04-01",
      "rkaf:cacheStatus": "rkaf:stale",
      "rkaf:cacheAgeSeconds": 21600,
      "rkaf:usageCeiling": "rkaf:localOperationalUse",
      "rkaf:warnings": [
        {
          "@type": "rkaf:StaleConceptCacheWarning",
          "rkaf:warningCode": "rkaf:staleCacheUsedNonCritical",
          "rkaf:detail": "Cache age 21600s exceeds 14400s TTL for federatedCuration registry. Non-A3 concept; stale served per ConceptRegistry §6.2."
        }
      ]
    }
  ],
  "rkaf:staleConceptCache": [
    "https://registry.example.gov/concepts/HouseholdIncomeEvidence"
  ],
  "prov:generatedAtTime": "2026-08-01T16:00:00-05:00"
}
```

## Step 4 — Case 3: Stale cache, A3 authority-critical concept, rejected

A different validation targets a federal regulation concept used in an A3 authority chain (from the statutory fixture). Stale cache MUST refuse.

```json
{
  "@id": "https://example.org/bridge-validation/case-3-stale-A3",
  "@type": "rkaf:BridgeValidationResult",
  "rkaf:packetId": "https://example.org/wos/caa-42-intake/verify-identity/v1",
  "rkaf:consumer": "https://example.org/consumer/caa-42-wos",
  "rkaf:result": "rkaf:rejected",
  "rkaf:conceptResolutionResults": [
    {
      "@type": "rkaf:ConceptResolutionResult",
      "rkaf:inputConcept": "https://registry.example.gov/concepts/IdentityEvidence",
      "rkaf:resolutionStatus": "rkaf:unresolvedRegistryUnavailable",
      "rkaf:cacheStatus": "rkaf:stale",
      "rkaf:cacheAgeSeconds": 21600,
      "rkaf:usageCeiling": "rkaf:notEligible",
      "rkaf:errors": [
        {
          "@type": "rkaf:ConceptResolutionError",
          "rkaf:errorCode": "rkaf:staleCacheRefusedForA3",
          "rkaf:detail": "Concept used in A3 authority-critical context; stale cache MUST NOT be served per ConceptRegistry §6.2. Refresh required before validation can proceed."
        }
      ]
    }
  ],
  "rkaf:suggestedRemediation": {
    "@type": "rkaf:SuggestedRemediation",
    "rkaf:remediationAction": "rkaf:refreshRegistryCache",
    "rkaf:targetRegistry": "https://registry.example.gov/registries/public-benefits-evidence"
  }
}
```

## Step 5 — Case 4: No cache + registry unreachable, rejected

A field references a concept never seen before. Registry is unreachable.

```json
{
  "@id": "https://example.org/bridge-validation/case-4-unreachable",
  "@type": "rkaf:BridgeValidationResult",
  "rkaf:packetId": "https://example.org/form-field/caa-42-intake/new-field-draft",
  "rkaf:consumer": "https://example.org/consumer/caa-42-formspec",
  "rkaf:result": "rkaf:rejected",
  "rkaf:conceptResolutionResults": [
    {
      "@type": "rkaf:ConceptResolutionResult",
      "rkaf:inputConcept": "https://registry.example.gov/concepts/EmploymentVerification",
      "rkaf:resolutionStatus": "rkaf:unresolvedRegistryUnavailable",
      "rkaf:cacheStatus": "rkaf:notCached",
      "rkaf:errors": [
        {
          "@type": "rkaf:ConceptResolutionError",
          "rkaf:errorCode": "rkaf:registryUnreachableNoCache",
          "rkaf:detail": "Registry resolution endpoint returned no response within timeout; concept not in cache. Cannot proceed."
        }
      ]
    }
  ],
  "rkaf:registryUnavailable": [
    "https://registry.example.gov/registries/public-benefits-evidence"
  ]
}
```

## Step 6 — Case 5: Registry version out of declared range

The registry has advanced to `rkaf:registryVersion: "2027-01-01"`. The consumer's `BridgeConsumerRegistration` declares support through `2026-12-31`. The consumer continues with warnings; the result depends on whether any A3 concept is referenced (here, non-A3, so warning only).

```json
{
  "@id": "https://example.org/bridge-validation/case-5-version-out-of-range",
  "@type": "rkaf:BridgeValidationResult",
  "rkaf:packetId": "https://example.org/form-field/caa-42-intake/income-docs/v3",
  "rkaf:consumer": "https://example.org/consumer/caa-42-formspec",
  "rkaf:result": "rkaf:acceptedWithWarnings",
  "rkaf:registryVersionOutOfRange": [
    {
      "@type": "rkaf:RegistryVersionOutOfRange",
      "rkaf:registry": "https://registry.example.gov/registries/public-benefits-evidence",
      "rkaf:currentVersion": "2027-01-01",
      "rkaf:consumerMaxVersion": "2026-12-31",
      "rkaf:detail": "Registry has advanced beyond consumer's declared supported range. Consumer continuing with cached resolution; should update BridgeConsumerRegistration."
    }
  ],
  "rkaf:warnings": [
    {
      "@type": "rkaf:RegistryVersionWarning",
      "rkaf:warningCode": "rkaf:registryVersionOutOfRange",
      "rkaf:appliesTo": "https://registry.example.gov/registries/public-benefits-evidence",
      "rkaf:remediation": "Update BridgeConsumerRegistration.supportsRegistryVersionRange.maxVersion."
    }
  ]
}
```

## Step 7 — Case 6: operationalConflict on shared form

CAA-42 and CAA-77 share a regional intake form for a multi-org program. CAA-42's `closeMatch` mapping (from Mapping Fixture v0.1) and CAA-77's competing `closeMatch` mapping point to different registered concepts. The shared form depends on both. Severity: `operationalConflict`.

```json
{
  "@id": "https://registry.example.gov/annotation/mapping-conflict-002",
  "@type": "rkaf:MappingConflict",
  "rkaf:conflictingMappings": [
    "https://example.org/assertion/caa-42-mapping-001",
    "https://example.org/assertion/caa-77-mapping-002"
  ],
  "rkaf:relatedConcept": "https://example.org/concepts/regional/IncomeProof",
  "rkaf:sharedArtifact": "https://example.org/form-field/regional-intake/income-shared",
  "rkaf:severity": "rkaf:operationalConflict",
  "rkaf:severityRationale": "Shared regional intake form depends on both mappings; they resolve to different registered concepts (W2Filers vs NonW2Filers without disambiguation). Operational use blocked until conflict resolved.",
  "rkaf:detectedAt": "2026-09-15T00:00:00-05:00"
}
```

```json
{
  "@id": "https://example.org/bridge-validation/case-6-operational-conflict",
  "@type": "rkaf:BridgeValidationResult",
  "rkaf:packetId": "https://example.org/form-field/regional-intake/income-shared",
  "rkaf:consumer": "https://example.org/consumer/regional-formspec",
  "rkaf:result": "rkaf:acceptedWithWarnings",
  "rkaf:warnings": [
    {
      "@type": "rkaf:OperationalConflictWarning",
      "rkaf:affectedWorkProduct": "https://example.org/form-field/regional-intake/income-shared",
      "rkaf:transitionTo": "rkaf:staleForCurrentUse",
      "rkaf:detail": "Operational conflict mapping-conflict-002 affects this artifact. Per ConceptRegistry §8, artifact transitions to staleForCurrentUse until conflict resolved or scoped."
    }
  ],
  "rkaf:staleDependencies": [
    "https://example.org/form-field/regional-intake/income-shared"
  ]
}
```

## Step 8 — Case 8: CanonicalMapping resolves the conflict

The registry's `ConceptMintingAuthority` issues a canonical mapping. Both prior mappings continue to exist scoped to their orgs, but the canonical attestation establishes the registry-blessed interpretation. The shared artifact revalidates.

```json
{
  "@id": "https://registry.example.gov/attestation/canonical-mapping-001",
  "@type": "rkaf:Attestation",
  "rkaf:assertsPredicate": "rkaf:attestsTo",
  "rkaf:targetAssertion": "https://example.org/assertion/caa-77-mapping-002",
  "rkaf:attestor": "https://registry.example.gov/authorities/pbe-curation-board",
  "rkaf:attestorType": "rkaf:ConceptMintingAuthority",
  "rkaf:decision": "rkaf:declareCanonicalMapping",
  "rkaf:scope": "rkaf:public",
  "rkaf:rationale": "For regional intake forms in the public-benefits-evidence registry's scope, caa-77-mapping-002 (closeMatch to HouseholdIncomeEvidence-NonW2Filers) is canonical when applicant declares non-W2 filer status; caa-42-mapping-001 remains operational within CAA-42's org scope but is not canonical for the shared regional form.",
  "prov:generatedAtTime": "2026-09-20T00:00:00-05:00"
}
```

```json
{
  "@id": "https://example.org/bridge-validation/case-8-canonical-resolved",
  "@type": "rkaf:BridgeValidationResult",
  "rkaf:packetId": "https://example.org/form-field/regional-intake/income-shared",
  "rkaf:consumer": "https://example.org/consumer/regional-formspec",
  "rkaf:result": "rkaf:accepted",
  "rkaf:effectiveUsageEligibilityRationale": "Conflict mapping-conflict-002 resolved by canonical-mapping-001 attestation from pbe-curation-board. Regional form revalidates against canonical mapping for shared scope.",
  "rkaf:conceptResolutionResults": [
    {
      "@type": "rkaf:ConceptResolutionResult",
      "rkaf:inputConcept": "https://example.org/concepts/regional/IncomeProof",
      "rkaf:resolvedConcept": "https://registry.example.gov/concepts/HouseholdIncomeEvidence-NonW2Filers",
      "rkaf:resolutionStatus": "rkaf:resolvedViaMapping",
      "rkaf:resolutionMethod": "rkaf:exactMatchTrusted",
      "rkaf:mappingAssertion": "https://example.org/assertion/caa-77-mapping-002",
      "rkaf:resolutionTrustedVia": "https://registry.example.gov/attestation/canonical-mapping-001",
      "rkaf:usageCeiling": "rkaf:localOperationalUse"
    }
  ]
}
```

## Step 9 — Case 7: publicationBlocking conflict

A separate scenario: a planned public release of regional guidance depends on a still-unresolved conflict. Severity escalates to `publicationBlocking`.

```json
{
  "@id": "https://registry.example.gov/annotation/mapping-conflict-003",
  "@type": "rkaf:MappingConflict",
  "rkaf:conflictingMappings": [
    "https://example.org/assertion/org-a-mapping-005",
    "https://example.org/assertion/org-b-mapping-005"
  ],
  "rkaf:relatedPublishedArtifact": "https://example.org/guidance/regional-eligibility-handbook-2027",
  "rkaf:severity": "rkaf:publicationBlocking",
  "rkaf:severityRationale": "Conflicting mappings used in guidance scheduled for publication 2027-01-15. Publication blocked until canonical resolution or scoped retraction."
}
```

```json
{
  "@id": "https://example.org/bridge-validation/case-7-publication-blocking",
  "@type": "rkaf:BridgeValidationResult",
  "rkaf:packetId": "https://example.org/guidance/regional-eligibility-handbook-2027",
  "rkaf:consumer": "https://example.org/consumer/regional-publication-service",
  "rkaf:result": "rkaf:rejected",
  "rkaf:effectiveUsageEligibility": "rkaf:notEligible",
  "rkaf:errors": [
    {
      "@type": "rkaf:PublicationBlockingConflictError",
      "rkaf:appliesTo": "https://example.org/guidance/regional-eligibility-handbook-2027",
      "rkaf:detail": "Publication refused due to publicationBlocking severity mapping-conflict-003. Resolve via CanonicalMapping or scope retraction before publication can proceed."
    }
  ],
  "rkaf:suggestedRemediation": {
    "@type": "rkaf:SuggestedRemediation",
    "rkaf:remediationAction": "rkaf:requestCanonicalMapping",
    "rkaf:targetRegistry": "https://registry.example.gov/registries/public-benefits-evidence",
    "rkaf:humanReviewRequired": true
  }
}
```

## Step 10 — Case 9: safeAutomaticMigration replaceInPlace, no stale transition

The registry deprecates a concept with a single declared successor and a declared safe automatic migration. Consumer supports `rkaf:replaceInPlace`. Affected fields auto-update without going stale.

```json
{
  "@id": "https://registry.example.gov/packets/lifecycle-replace-in-place-001",
  "@type": "rkaf:ConceptLifecyclePacket",
  "rkaf:lifecycleEvent": "rkaf:replacedBy",
  "rkaf:subjectConcept": "https://registry.example.gov/concepts/OldIncomeFormatX",
  "rkaf:successorConcepts": [
    "https://registry.example.gov/concepts/CurrentIncomeFormatX"
  ],
  "rkaf:effectiveDate": "2026-10-01T00:00:00-05:00",
  "rkaf:bridgeContractVersion": "rkaf-bridge/1.0",
  "rkaf:cascadeAlgorithm": "rkaf:CascadeClosureV1",
  "rkaf:safeAutomaticMigration": "rkaf:replaceInPlace",
  "rkaf:safeAutomaticMigrationRationale": "Concept identity is unchanged in substance; only naming refined. Single deterministic successor. References can be rewritten without disambiguation.",
  "rkaf:affectedWorkProducts": [
    "https://example.org/form-field/caa-42-intake/format-x-field"
  ]
}
```

```json
{
  "@id": "https://example.org/bridge-validation/case-9-auto-migration",
  "@type": "rkaf:BridgeValidationResult",
  "rkaf:packetId": "https://registry.example.gov/packets/lifecycle-replace-in-place-001",
  "rkaf:consumer": "https://example.org/consumer/caa-42-formspec",
  "rkaf:result": "rkaf:accepted",
  "rkaf:warnings": [
    {
      "@type": "rkaf:AutomaticMigrationApplied",
      "rkaf:appliesTo": "https://example.org/form-field/caa-42-intake/format-x-field",
      "rkaf:migrationType": "rkaf:replaceInPlace",
      "rkaf:fromConcept": "https://registry.example.gov/concepts/OldIncomeFormatX",
      "rkaf:toConcept": "https://registry.example.gov/concepts/CurrentIncomeFormatX",
      "rkaf:detail": "Per ConceptRegistry §7.5: packet declares safeAutomaticMigration: replaceInPlace AND consumer BridgeConsumerRegistration declares support. Field's collectsEvidenceType reference auto-updated. No staleForCurrentUse transition."
    }
  ],
  "rkaf:staleDependencies": []
}
```

## Step 11 — Case 10: LocalConcept promotion

CAA-42's `caa-42:IncomeDocs` LocalConcept is promoted to a RegisteredConcept. The registry's authority issues a `ConceptRegistrationEvent`; a new RegisteredConcept is published; an automatic `exactMatch` mapping connects the LocalConcept to the new RegisteredConcept.

```json
{
  "@id": "https://registry.example.gov/events/concept-registration-001",
  "@type": "rkaf:ConceptRegistrationEvent",
  "rkaf:proposedBy": "https://example.org/user/caa-42-program-director-1",
  "rkaf:proposedFromLocalConcept": "https://example.org/concepts/caa-42/IncomeDocs",
  "rkaf:registeredConcept": "https://registry.example.gov/concepts/HouseholdIncomeEvidence-Generic",
  "rkaf:registrationAuthority": "https://registry.example.gov/authorities/pbe-curation-board",
  "rkaf:effectiveDate": "2026-11-01T00:00:00-05:00",
  "rkaf:rationale": "CAA-42's local concept has been adopted across multiple sibling orgs; promoting to public registry to enable cross-org sharing."
}
```

```json
{
  "@id": "https://registry.example.gov/concepts/HouseholdIncomeEvidence-Generic",
  "@type": ["skos:Concept", "rkaf:RegisteredConcept"],
  "skos:prefLabel": "Household income evidence (generic)",
  "skos:altLabel": ["income docs"],
  "rkaf:managedByRegistry": "https://registry.example.gov/registries/public-benefits-evidence",
  "rkaf:conceptScope": "rkaf:public",
  "rkaf:conceptStatus": "rkaf:registered",
  "rkaf:registeredAt": "2026-11-01T00:00:00-05:00",
  "rkaf:registeredVia": "https://registry.example.gov/events/concept-registration-001"
}
```

```json
{
  "@id": "https://registry.example.gov/assertion/auto-exact-match-001",
  "@type": "rkaf:RelationshipAssertion",
  "rkaf:assertsSubject": "https://example.org/concepts/caa-42/IncomeDocs",
  "rkaf:assertsPredicate": "skos:exactMatch",
  "rkaf:assertsObject": "https://registry.example.gov/concepts/HouseholdIncomeEvidence-Generic",
  "rkaf:assertionOrigin": "rkaf:systemDerived",
  "rkaf:hasTrustZone": "rkaf:Z4AttestedAssertion",
  "rkaf:hasSafetyLabel": "rkaf:R2ReviewedOperational",
  "rkaf:usageEligibility": "rkaf:localOperationalUse",
  "rkaf:trusted": true,
  "rkaf:trustedVia": "rkaf:canonicalMappingFromRegistration",
  "rkaf:basedOnEvent": "https://registry.example.gov/events/concept-registration-001",
  "rkaf:hasEvidence": [
    {
      "@type": "rkaf:EvidenceBinding",
      "rkaf:evidenceRole": "rkaf:registrationEvent",
      "rkaf:supportingEvent": "https://registry.example.gov/events/concept-registration-001"
    }
  ]
}
```

After promotion, all existing references to `caa-42:IncomeDocs` continue to resolve via the auto-generated `exactMatch` mapping. Validation results unchanged in behavior; resolution method shifts from `closeMatchLocallyAdopted` to `exactMatchTrusted` for consumers querying through the LocalConcept.

---

## Conformance assertions exercised

| Spec section | Test case | Step |
|---|---|---|
| ConceptRegistry §6.2 (cache TTL — fresh) | Case 1 | 2 |
| ConceptRegistry §6.2 (cache TTL — stale non-critical) | Case 2 | 3 |
| ConceptRegistry §6.2 (cache TTL — stale A3 refused) | Case 3 | 4 |
| ConceptRegistry §6.2 (registry unreachable) | Case 4 | 5 |
| ConceptRegistry §5.5 (registry version out of range) | Case 5 | 6 |
| ConceptRegistry §8 (operationalConflict → staleForCurrentUse) | Case 6 | 7 |
| ConceptRegistry §8.2 (CanonicalMapping resolution) | Case 8 | 8 |
| ConceptRegistry §8 (publicationBlocking → publication refused) | Case 7 | 9 |
| ConceptRegistry §7.5 (safeAutomaticMigration: replaceInPlace) | Case 9 | 10 |
| ConceptRegistry §9.2 (LocalConcept promotion + auto exactMatch) | Case 10 | 11 |

## Model issues surfaced by this fixture

1. **`rkaf:trusted` boolean on mapping assertions.** Step 11 sets `rkaf:trusted: true` on the auto-generated exactMatch. The ConceptRegistry §4.5 trusted-mapping rule treats trust as a derived property (a mapping is trusted iff one of four conditions holds). Whether to also expose it as an explicit denormalized boolean is a design question. I used the explicit form here for clarity; the alternative is to leave it implicit and let consumers compute. Recommend: explicit but normatively a non-authoritative cache (same as `resolvedToConcepts`), with the source-of-truth being the four conditions.

2. **`rkaf:resolutionTrustedVia` on `ConceptResolutionResult`.** Step 8 records that the resolution was made trusted via a specific canonical mapping attestation. This is useful audit metadata not currently in the spec. Worth adding to `ConceptResolutionResult` shape.

3. **`rkaf:cacheAgeSeconds` on `ConceptResolutionResult`.** Steps 2–4 include cache age in seconds. The spec describes cache and TTL but doesn't formalize the age field on the resolution result. Worth adding for debugging.

4. **`rkaf:OperationalConflictWarning`, `rkaf:PublicationBlockingConflictError`, `rkaf:AutomaticMigrationApplied`** are new warning/error subtypes I introduced. The warning/error vocabulary is growing; worth a separate small spec listing all warning and error codes with their structures.

5. **`rkaf:sharedArtifact` on `MappingConflict`.** Step 7 indicates the conflicting artifact that triggered the elevated severity. The spec describes severity as a property of the conflict but doesn't formalize how operational/publication artifacts get tied to the conflict. Recommend: add `rkaf:sharedArtifact` (for operational/publication severities) as required when severity is `operationalConflict` or `publicationBlocking`.

6. **`rkaf:declareCanonicalMapping` attestation decision (Step 8).** This is a new attestation decision value, not in the prior decision enumeration. Worth adding to the canonical attestation-decision list alongside `adoptForOperations`, `requestLegalReview`, etc.

7. **Cascade implications of `replacedBy` with `replaceInPlace`.** Step 10's packet has affected work products but no required revalidation actions because the migration is automatic. The cascade closure algorithm needs to distinguish "affected and requires revalidation" from "affected but auto-migrated." Recommend extending the cascade output with an `autoMigratedArtifacts[]` list alongside the existing `requiredRevalidationActions[]`.

8. **LocalConcept post-promotion lifecycle.** After Step 11, the LocalConcept continues to exist alongside the new RegisteredConcept. The spec doesn't currently address whether the LocalConcept should be marked deprecated, kept active, or transitioned to some "promoted" status. I left it as `localActive`. Worth deciding: should there be a `rkaf:promoted` status on LocalConcept indicating it has a canonical RegisteredConcept equivalent?

## Coverage complete — conformance set status

| Capability | Status |
|---|---|
| Candidate-to-typed promotion | ✅ Local operational |
| Attestation and LocalAdoption | ✅ Across all fixtures |
| Formspec field justification | ✅ Local op + mapping + statutory |
| WOS step justification | ✅ Statutory |
| Concept direct resolution | ✅ Local op + this |
| LocalConcept closeMatch | ✅ Mapping |
| broadMatch rejection | ✅ Mapping |
| Concept lifecycle: split | ✅ Mapping |
| Concept lifecycle: replacedBy with auto-migration | ✅ This fixture |
| AmendmentPacket cascade | ✅ Local op |
| RescissionPacket cascade | ✅ Statutory |
| hasAuthority, derivesAuthorityFrom, DelegationInstrument | ✅ Statutory |
| LocalAdoption insufficient after broken authority | ✅ Statutory |
| PointInTimeException | ✅ Local op + statutory |
| Registry cache states (fresh, stale-OK, stale-refused, unreachable) | ✅ This fixture |
| Registry version range mismatch | ✅ This fixture |
| Mapping conflict severities (informational, operational, publication) | ✅ Mapping + this fixture |
| CanonicalMapping resolution | ✅ This fixture |
| LocalConcept promotion | ✅ This fixture |
| safeAutomaticMigration positive path | ✅ This fixture |

**Conformance fixture set is complete for v0.1.** SHACL shape drafting can now begin with full coverage anchors.
