# Rulespec SHACL Shapes

This directory contains the four SHACL shape files that structurally validate Rulespec data. Each file anchors on specific sections of the spec; together they enforce the structural surface of Rulespec v0.1.1.

## Files

### `rkaf-shapes-core-v0.1.ttl` — Core assertion and bridge shapes

Anchors on Rulespec Core §2 (assertions), §3 (evidence/attestation), §4 (lifecycle), §5 (bridge model).

| Shape | Purpose |
|---|---|
| `TrustZoneEligibilityShape` | Trust zone × usage eligibility compatibility matrix |
| `RelationshipAssertionShape` | Base required structure for all assertions |
| `OperationalAssertionEvidenceShape` | R2/A3/P4 assertions require real evidence (Pattern C) |
| `AuthorityAssertionShape` | A3 assertions require authorityKind + applicability + qualified evidence (Pattern C) |
| `EvidenceBindingShape` | Evidence binding structure with evidence role |
| `AttestationShape` | Attestation decision from closed enum or extension URI |
| `AttestationScopeShape` | Attestation scope from closed enum or extension URI |
| `LocalAdoptionShape` | Local adoption with adoptionAuthorityKind restricted to non-legal kinds |
| `ApplicabilityContextShape` | Applicability with scopeKind |
| `AuthorityChainHopShape` | Authority chain hop forbidding `rkaf:implements` |
| `BridgeValidationResultShape` | Bridge result with conditional remediation requirement (Pattern C) |

### `rkaf-shapes-conceptregistry-v0.1.ttl` — Concept registry shapes

Anchors on ConceptRegistry spec §1-§10.

| Shape | Purpose |
|---|---|
| `RegisteredConceptShape` | Registered concept structure |
| `LocalConceptShape` | Local concept with definedInScope IRI |
| `ConceptRegistryShape` | Concept registry structure |
| `ConceptMintingAuthorityShape` | Concept minting authority (no fixture target; coverage gap) |
| `MappingAssertionShape` | closeMatch + operational → MappingApplicabilityContext (Pattern C) |
| `MappingApplicabilityContextShape` | Applicability with applicationDomain and evidencePurpose |
| `ConceptResolutionResultShape` | Resolution result with usageCeiling |
| `SuggestedRemediationShape` | Remediation with kind enum |
| `ConceptLifecyclePacketShape` | split/merge/replacedBy → successorConcepts (Pattern C) |
| `MappingConflictShape` | operational/publicationBlocking → artifact reference (Pattern C) |
| `BridgeConsumerRegistrationShape` | Consumer with supportedEvaluationAnchors |

### `rkaf-shapes-lifecycle-v0.1.ttl` — Lifecycle packet and revalidation shapes

Anchors on Rulespec Core §4.

| Shape | Purpose |
|---|---|
| `AmendmentPacketShape` | Amendment packet structure |
| `RescissionPacketShape` | Rescission packet structure |
| `SupersessionPacketShape` | Supersession packet structure (no fixture target; coverage gap) |
| `MaterialRevisionPacketShape` | Material revision packet structure (no fixture target; coverage gap) |
| `RevalidationEventShape` | Revalidation event with target and queue |
| `RevalidationClosureEventShape` | revalidatedWithSuccessor → successor reference (Pattern C) |
| `PointInTimeExceptionShape` | PIT exception with evaluationAnchor + retains |

### `rkaf-shapes-justification-v0.1.ttl` — Consumer artifact justification overlay shapes

Anchors on Rulespec Core §5 and §6.

#### Conceptual center (universal, predicate-targeted)

| Shape | Targets | Purpose |
|---|---|---|
| `GeneratedWorkProductJustificationShape` | `rkaf:GeneratedWorkProduct` | Rulespec overlay type itself |
| `ConsumerArtifactJustificationShape` | subjects of `rkaf:justifiedByAssertion` | Universal bridgeContractVersion requirement |
| `DataCollectionArtifactJustificationShape` | subjects of `rkaf:collectsEvidenceType` | Full overlay required on evidence-collecting artifacts |
| `ProcessArtifactJustificationShape` | subjects of `rkaf:requiresEvidenceType` | Full overlay required on evidence-gating processes |
| `FullBridgeValidationResultShape` | `rkaf:BridgeValidationResult` | Non-accepted results need structured indicators (Pattern C) |
| `JustificationChainHopShape` | `rkaf:JustificationChainHop` | Allows `rkaf:implements` predicate (no fixture target; coverage gap) |

#### Example specializations (illustrative, not load-bearing)

| Shape | Targets | Status |
|---|---|---|
| `FormspecFieldJustificationShape` | `formspec:Field` | Example specialization (Pattern C) |
| `WOSStepJustificationShape` | `wos:WorkflowStep` | Example specialization (Pattern C) |

Removing the two example specializations would not weaken validation; the generic predicate-targeted shapes catch the same defects.

## SHACL profile

- Profile: **Rulespec-SHACL-AF**
- All conditional shapes use **Pattern C** (`sh:or` with `sh:not`) for reliable pySHACL evaluation
- Only `qualifiedValueShape` / `qualifiedMinCount` (in `AuthorityAssertionShape`) requires SHACL Advanced Features; all other shapes are SHACL Core compatible
- Validation requires `pyshacl >= 0.31.0` with `advanced=True` and `inference="rdfs"`

## Pattern C idiom

Conditional constraints follow the form:

```turtle
ShapeX
  sh:targetClass T ;
  sh:or (
    [ sh:not [ <precondition> ] ]
    <requirement-branches-flattened>
  ) ;
  sh:message "..." .
```

For multi-requirement conditionals, the requirement branch uses `sh:and`:

```turtle
sh:or (
  [ sh:not [ <precondition> ] ]
  [ sh:and (
      [ <requirement-A> ]
      [ <requirement-B> ]
      [ <requirement-C> ]
  ) ]
) .
```

See `CONTRIBUTING.md` for the full rationale and `reports/batch4-validation-report.md` for the discovery story.

## Why eight shapes were rewritten in v0.1.1

pySHACL 0.31.0 does not correctly evaluate `sh:if`/`sh:then` patterns. Eight conditional shapes across v0.1-rc1 and post-rc1 batches were parsing correctly and reporting PASS but were not actually evaluating their constraints against fixture data. All eight have been rewritten using Pattern C. See `reports/batch4-validation-report.md` for the full discovery and verification trail.

## Loading order

Shapes are intended to be loaded together by the validation gate. Internal references (e.g., shape A using a sub-shape defined in shape B) do exist; load all four files into a single shape graph before validating. The CI gate (`tools/ci_validate.py`) handles this automatically.

## Coverage matrix

See `reports/v0.1.1-release-manifest.md` for the per-shape fixture coverage matrix. Four accepted coverage gaps are documented there.
