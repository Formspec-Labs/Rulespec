# Rulespec Behavior — Layer 5 runtime contracts

Status: Editor's Draft, normative.
Companion to: `spec/rkaf-core.md`, `spec/rkaf-vocabulary.md`, `spec/rkaf-concept-registry.md`.

## 0. Purpose

This document specifies the runtime-behavioral contracts that Rulespec consumers MUST implement to claim conformance — the contracts that are *not* CUE-validatable shape:

- The `usageEligibility` reducer (Layer 1 lattice composition under runtime constraints)
- The `CascadeClosureV1` algorithm (lifecycle-packet affected-set computation)
- The 10 bridge contract rules (consumer behavior governing packet ingest)
- Point-in-time exception evaluation
- Stale transition semantics on lifecycle ingest

Shape conformance is enforced by `rkaf-validate` (JSON Schema gate) and `tools/ci_validate.py` (SHACL gate). Behavioral conformance is enforced by the consumer's runtime implementation against the contracts below, and verified by the future Layer 6 conformance suite (Plan 7).

The full v0.1 normative prose remains preserved at `archive/v0.1/spec/rkaf-core.md` and `archive/v0.1/spec/rkaf-concept-registry-v0.1.2.md`. This document is the active-tree summary plus the codification roadmap; full text lives in the archive and is the authoritative reference until codification lands.

## 1. The `usageEligibility` reducer [Normative]

### 1.1 Lattice

`rkaf:usageEligibility` is a 7-level lattice (`constraints/core/usage-eligibility.cue`):

```
rkaf:notEligible
  < rkaf:searchOnly
  < rkaf:reviewQueueOnly
  < rkaf:draftGenerationAllowed
  < rkaf:localOperationalUse
  < rkaf:publicationAllowed
  < rkaf:officialUse
```

### 1.2 Reducer inputs

Effective `usageEligibility` for an artifact is computed by combining:

1. **Assertion baseline** — the `usageEligibility` declared on the source Assertion (Layer 1 shape).
2. **Scoped LocalAdoption grants** — every `rkaf:LocalAdoption` over the Assertion whose `adoptionScope` covers the consumer's evaluation scope.
3. **Lifecycle status** — `rkaf:LifecycleEvent` records that affect the Assertion (revalidation, supersession, rescission). A lifecycle event MAY lower OR block eligibility; it MUST NOT raise it.
4. **Applicability constraints** — `rkaf:ApplicabilityScope` on the Warrant chain. Out-of-scope artifacts compute to `rkaf:notEligible` regardless of other inputs.
5. **Consumer capabilities** — declared via `rkaf:BridgeConsumerRegistration.supportedAuthorityKinds` / `supportedEvaluationAnchors` / `supportedAutomaticMigrations`. Unsupported kinds yield `rkaf:notEligible`.

### 1.3 Reducer invariants

- **Consumers MAY narrow, MUST NOT broaden.** A consumer's reducer output is always ≤ the lattice value computed from the inputs above.
- **LocalAdoption is the only authorized broadener.** A `rkaf:LocalAdoption` with `adoptionAuthorityKind ∈ {organizational, localOperational, contractual, publication}` MAY raise the effective `usageEligibility` within its declared scope. **It MUST NOT substitute for a broken/expired/rescinded `hasAuthority` / `derivesAuthorityFrom` chain when the assertion requires external `legal` / `statutory` / `regulatory` / `delegated` authority** (`archive/v0.1/spec/rkaf-core.md` §2.5 — structurally enforced via the closed enum on `LocalAdoption.adoptionAuthorityKind`).
- **Cache permitted, recompute required on event ingest.** Implementations MAY cache an effective state per scope, but MUST recompute on every attestation / adoption / lifecycle event affecting the assertion.

### 1.4 Codification status

The lattice is codified as `#UsageEligibility` in `constraints/core/usage-eligibility.cue`. The reducer algorithm itself is **runtime behavior**, not shape. Implementations MUST follow the inputs + invariants above; the reducer's exact composition (e.g., min vs max vs custom) is implementation-defined provided the invariants hold.

## 2. CascadeClosureV1 [Normative]

### 2.1 Purpose

Lifecycle packets (`rkaf:LifecycleEvent` with `lifecycleEventKind ∈ {amendment, supersession, rescission, materialRevision, conceptLifecycle}`) declare an *affected set* — the transitive closure of assertions / authorities / work products / adoptions impacted by the change. `rkaf:CascadeClosureV1` is the canonical algorithm name; consumers declare conformance to this algorithm by name in `rkaf:LifecycleEvent.cascadeAlgorithm`.

### 2.2 Algorithm

Transitive closure over the **inverse** of these edges, scoped to active/adopted state at packet `effectiveDate`:

- `rkaf:derivedFromFragment`
- `rkaf:justifiedByAssertion`
- `rkaf:hasAuthority`
- `rkaf:derivesAuthorityFrom`
- `rkaf:implements`
- `rkaf:requiresEvidenceType`
- `rkaf:collectsEvidenceType`
- `rkaf:operationallyDependsOn`
- `rkaf:supersedesAssertion`
- `rkaf:supersedesWorkProduct`
- `rkaf:LocalAdoption.targetAssertion`
- (Concept-lifecycle additions) `rkaf:assertsObject` where object is a concept, and the SKOS mapping edges `skos:closeMatch` / `skos:exactMatch` / `skos:broader` / `skos:narrower` / `skos:related` / `skos:mappingRelation`.

### 2.3 Output

The closure output is the set of affected assertions, authority assertions, work products, and adoptions. The `rkaf:LifecycleEvent` MUST carry this set; the algorithm name (`rkaf:CascadeClosureV1`) is the conformance identifier.

### 2.4 Codification status

Algorithm is runtime behavior. The `LifecycleEvent` shape is codified in `constraints/core/lifecycle-event.cue`; the algorithm itself remains prose.

## 3. The 10 bridge contract rules [Normative]

Consumer behavior governing packet ingest. A `rkaf:BridgeValidationResult` records compliance; an `rkaf:Attestation` records bridge-detected issues.

1. **No Rulespec-backed authority inference outside of `hasAuthority` / `derivesAuthorityFrom` / `LocalAdoption`.** Consumers MUST NOT synthesize new authority edges from inference, similarity, or retrieval.
2. **`usageEligibility` is computed via the reducer (§1).** Consumers MAY narrow, MUST NOT broaden.
3. **`authorityKind` preserved and surfaced.** Consumers MUST NOT substitute one kind for another. Federation refuses unsupported kinds with structured errors.
4. **Declared `EvaluationAnchor` support.** Consumers refuse packets carrying point-in-time exceptions whose anchors aren't in `BridgeConsumerRegistration.supportedEvaluationAnchors`. Refusal is structured (`rkaf:errors[]`), not silent.
5. **Cascade-driven `staleForCurrentUse` transition.** When a consumer receives a lifecycle packet affecting an operational artifact, the artifact transitions to `rkaf:staleForCurrentUse` unless the packet declares a `rkaf:safeAutomaticMigration` the consumer supports. Stale artifacts MUST NOT be used for new operational cases until a `RevalidationClosureEvent` references the open `RevalidationEvent`.
6. **Concept resolution per ConceptRegistry.** Concept resolution results (`rkaf:ConceptResolutionResult`) establish semantic compatibility, NOT authority. Both validations MUST pass independently for operational use.
7. **Justification chains MUST terminate at `hasAuthority` / `derivesAuthorityFrom` (A3) or `LocalAdoption` (localOperational or stronger).** A chain that terminates short is broken; the `BridgeValidationResult` records the break with `authorityChainStatus: rkaf:broken`.
8. **Bridge-emitted attestations for consumer-detected issues.** Stale dependencies, registry unavailability, version mismatches MUST be emitted as `rkaf:Attestation` records targeting the affected artifacts.
9. **`rkaf:bridgeContractVersion` declared.** Every `LifecycleEvent` and `BridgeValidationResult` declares the contract version it conforms to. Unsupported versions are refused with structured errors.
10. **Generated artifacts preserve Rulespec justification metadata.** `rkaf:GeneratedWorkProduct` overlays preserve `justifiedByAssertion`, `bridgeContractVersion`, `usageEligibility` through projection / regeneration / serialization.

### 3.1 Codification status

The shapes carrying contract data — `BridgeValidationResult`, `BridgeConsumerRegistration`, `Attestation`, `LifecycleEvent` — are codified. Rule enforcement is runtime behavior.

## 4. Point-in-time exceptions [Normative]

A `LifecycleEvent` MAY include `rkaf:pointInTimeExceptions[]`, each declaring:

- `rkaf:evaluationAnchor` — IRI from the EvaluationAnchor closed enum (or declared extension):
  - `rkaf:applicationSubmissionTime`, `rkaf:eventOccurrenceTime`, `rkaf:eligibilityDeterminationTime`, `rkaf:noticeGenerationTime`, `rkaf:workflowStartTime`, `rkaf:workflowStepStartTime`, `rkaf:currentTime`, `rkaf:effectivePeriodStart`, `rkaf:publicationTime`.
- A scope description.
- `rkaf:retainsAssertion` / `rkaf:retainsWorkProduct` — the carve-out targets.

**Consumers honor the exception only if they support the referenced anchor**; otherwise they MUST refuse the packet rather than ignore the anchor (Rule 4).

### 4.1 Codification status

EvaluationAnchor closed enum is **not yet codified** in CUE; treated as an open set with declared extension URIs until a CUE source file lands. Tracked: extract from `archive/v0.1/spec/rkaf-core.md` §4.7 into `constraints/core/evaluation-anchor.cue`.

## 5. Stale transition [Normative]

When a consumer receives a `LifecycleEvent` whose affected set includes an operational artifact:

1. The artifact's `consumerLifecycleState` (cached, non-authoritative) transitions to `rkaf:staleForCurrentUse`.
2. New operational cases MUST NOT use the artifact until a `RevalidationClosureEvent` references the open `RevalidationEvent` with a `closureDecision` and a successor assertion / work product.
3. Existing in-flight cases MAY honor a `PointInTimeException` if the consumer supports the referenced `evaluationAnchor` and the case's anchor falls in the carve-out window.
4. Implementations MAY cache the transition per scope; revalidation closure MUST clear the cache.

### 5.1 Codification status

`RevalidationEvent` / `RevalidationClosureEvent` are **not yet codified** in CUE; tracked as a follow-up. Today these are described in `archive/v0.1/spec/rkaf-core.md` §4.8 and exist as `LifecycleEvent` instances with `lifecycleEventKind ∈ {revalidation, revalidationClosure}` (`constraints/core/lifecycle-event.cue`).

## 6. Concept resolution interaction [Normative]

Per ConceptRegistry §1.1, concept resolution establishes that two evidence-type references refer to the same evidence concept. It does NOT establish authority. Authority and concept resolution are orthogonal validations; both MUST pass independently for operational use.

### 6.1 Codification status

`ConceptResolutionResult` shape is codified (`constraints/core/concept-resolution-result.cue`). The resolver algorithm and registry-cache behavior are runtime contracts implemented per ConceptRegistry §5.

## 7. Codification roadmap

This document lists every contract that's currently runtime-only. The roadmap to codifying them as CUE constraints + shape gates:

| Contract | Current state | Codification target |
|---|---|---|
| `usageEligibility` lattice | Codified (`#UsageEligibility`) | ✓ Shape complete; reducer remains runtime |
| `CascadeClosureV1` algorithm | Runtime-only | Algorithm cannot be shape-encoded; future: TLA+ spec + cross-implementation conformance fixtures |
| 10 bridge contract rules | Runtime-only | Rule-by-rule conformance fixtures in the Plan 7 conformance suite |
| Point-in-time exceptions | Partial (LifecycleEvent shape codified; evaluationAnchor not) | Author `constraints/core/evaluation-anchor.cue` with closed enum + extension URIs |
| Stale transition | Runtime-only | Conformance fixtures: cascade-driven transition + carve-out evaluation |
| Concept resolution algorithm | Shape codified; algorithm runtime | Conformance fixtures: ambiguous / conflicting / cache-stale resolution paths |
| RevalidationEvent / RevalidationClosureEvent | Subsumed by LifecycleEvent | OPTION: split into dedicated shapes if Plan 7 needs the discriminator |
| EvaluationAnchor closed enum | Open today | Codify in Plan 7 alongside conformance fixtures |
| BridgeConsumerRegistration | Not yet codified | Codify in `constraints/core/bridge-consumer-registration.cue`; matched fixture + SHACL shape |
| GeneratedWorkProduct overlay | Not yet codified | Codify in `constraints/core/generated-work-product.cue` |

These remaining-codification items are tracked as Plan 7 (Conformance) work. Closing them turns Rulespec from a shape spec into a shape + behavior spec.

## 8. Conformance

Implementations claiming Rulespec runtime conformance MUST:

1. Implement the `usageEligibility` reducer per §1 invariants.
2. Implement `CascadeClosureV1` per §2 — the algorithm name in `LifecycleEvent.cascadeAlgorithm` is the conformance identifier.
3. Honor all 10 bridge contract rules per §3.
4. Honor point-in-time exceptions per §4 — refuse unsupported anchors.
5. Implement stale transition per §5.
6. Implement concept resolution per §6 — orthogonal to authority.
7. Emit a `rkaf:BridgeValidationResult` for every packet ingest, recording the verdict per §3.

Shape conformance (`rkaf-validate` + `ci_validate.py`) is required but not sufficient. Behavioral conformance (this document) is required for runtime operation. The Plan 7 conformance suite will provide cross-implementation behavioral test corpora.
