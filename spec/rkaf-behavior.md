# Rulespec Layer 5 — Behavioral Contracts

**Status:** Normative · **Version pin:** `VERSION` file at repo root · **Profile:** L4 conformance per `spec/rkaf-conformance.md` §4

This document specifies the **runtime behavioral contracts** Rulespec implementations MUST honor. Layer 1 (Vocabulary) and Layer 2 (Constraints) constrain document *shape*; Layer 5 constrains document *meaning under operations*. Algorithms here are normative — `rkaf-runtime` is the reference implementation; partner runtimes MUST produce identical outputs on the conformance corpus under `fixtures/behavior/`.

This spec is what makes `L4: pass` mean something. A consumer that ships only shape validation (L2 + L3) but ignores the contracts here cannot claim L4.

---

## §1 — UsageEligibility reducer

The `usageEligibility` lattice (per `constraints/core/usage-eligibility.cue`):

```
rkaf:notEligible < rkaf:searchOnly < rkaf:reviewQueueOnly < rkaf:draftGenerationAllowed
                < rkaf:localOperationalUse < rkaf:publicationAllowed < rkaf:officialUse
```

### §1.1 — Inputs

The reducer is a pure function of:

| Input | Source | Type |
|---|---|---|
| `assertion.baseline_eligibility` | `rkaf:Assertion.rkaf:usageEligibility` | `rkaf:UsageEligibility` |
| `assertion.@id` | the Assertion under evaluation | IRI |
| `assertion.consumerLifecycleState` | `rkaf:Assertion.rkaf:consumerLifecycleState` (if set) | `rkaf:ConsumerLifecycleState` (closed enum) |
| `assertion.applicability_set` | `rkaf:Assertion.rkaf:hasApplicability` (zero or more `ApplicabilityScope` IRIs) | `Set<IRI>` |
| `active_adoptions(assertion.@id)` | every `rkaf:LocalAdoption` where `targetAssertion == assertion.@id` AND `adoptionStatus == rkaf:active` | `Set<LocalAdoption>` |
| `consumer.capability_cap` | consumer's declared maximum eligibility | `rkaf:UsageEligibility` |
| `consumer.evaluation_scope` | the scope IRI the consumer is asking about | IRI \| `None` |
| `honored_pit_exceptions(assertion.@id)` | every `rkaf:PointInTimeException` where `retainsAssertion == assertion.@id` AND `exception.evaluationAnchor ∈ consumer.supported_anchors` | `Set<PointInTimeException>` |

### §1.2 — Algorithm

```text
fn reduce_usage_eligibility(
    assertion: &Assertion,
    graph: &Graph,
    consumer: &BridgeConsumerRegistration,
    eval_scope: Option<IRI>,
) -> UsageEligibility:

    // Step 1 — applicability gate
    if eval_scope.is_some()
       AND not assertion.applicability_set.is_empty()
       AND eval_scope.unwrap() not in assertion.applicability_set:
        return rkaf:notEligible

    // Step 2 — start with the baseline
    let baseline = assertion.baseline_eligibility OR rkaf:notEligible

    // Step 3 — lifecycle stale check
    let lifecycle_floor =
        if assertion.consumerLifecycleState == rkaf:staleForCurrentUse
           AND honored_pit_exceptions.is_empty():
            rkaf:notEligible
        else:
            baseline

    // Step 4 — local-adoption broadening (the ONLY upward operation)
    let after_adoptions =
        for la in active_adoptions:
            if eval_scope.is_some() AND la.adoptionScope == eval_scope.unwrap():
                lifecycle_floor = max_on_lattice(lifecycle_floor, la.usageEligibility)
        lifecycle_floor

    // Step 5 — consumer capability cap (narrowing only)
    let capped = min_on_lattice(after_adoptions, consumer.capability_cap)

    return capped
```

### §1.3 — Invariants

1. **Consumers MAY narrow. Consumers MUST NOT broaden** — every step except #4 is monotonically narrowing; #4 is bounded to `adoptionScope`. Outside the scope the broadening does not apply.
2. **`LocalAdoption` is the only authorized broadening operation** (v0.1 §1.4 invariant preserved).
3. **Recompute on every event affecting any input.** Cached effective state MUST be invalidated on attestation, adoption, lifecycle event, or PIT exception ingest.
4. **`assertion.consumerLifecycleState == staleForCurrentUse` plus no honored PIT** ⇒ `notEligible` regardless of all other inputs.
5. **Reducer reports unsupported-anchor errors.** §1.2 step 3 computes `honored_pit_exceptions` by intersecting `retainsAssertion == assertion.@id` AND `evaluationAnchor ∈ consumer.supportedEvaluationAnchors`. PITs failing the second clause SHOULD be reported as a separate `rkaf:UnsupportedEvaluationAnchor` diagnostic, NOT silently dropped — Rule 4 (§3.4) fires on the same condition.

### §1.4 — Scope enumeration

The reducer is evaluated per scope. For behavior fixtures, the L4 runtime reads the explicit scope list from `BehaviorTestCase.rkaf:evaluationScopes` (a list of scope IRIs). Production runtimes derive the scope set from the union of:

- All `adoptionScope` values across `LocalAdoption` targeting the assertion
- All `appliesInJurisdiction` values across `assertion.hasApplicability`'s `ApplicabilityScope` records
- The literal IRI `"(workspace)"` representing workspace-wide evaluation (no scope)

### §1.5 — Output

For evaluations carrying explicit scopes:
```
{ byScope: { "<scope-iri>": "<rkaf:level>", ... } }
```

For workspace-wide evaluations (no scope), the runtime treats `eval_scope = None`; step 4's LocalAdoption broadening is skipped (LocalAdoptions are scoped facts) and the output is:
```
{ effectiveUsageEligibility: "<rkaf:level>", rationale: "<string>" }
```

A LocalAdoption with `adoptionScope == "(workspace)"` is intentionally not a thing today; adoptions are always scope-bound. Workspace-wide reduction therefore only sees baseline + lifecycle + consumer cap.

---

## §2 — CascadeClosureV1

Transitive closure over the **inverse** of the *dependency* edges listed below, scoped to nodes that are active/adopted at the triggering `LifecycleEvent.effectiveDate`. The algorithm name `rkaf:CascadeClosureV1` is the L4 conformance identifier; partner implementations MUST emit this string.

### §2.1 — Trigger edges vs. cascade edges

v0.1 §4.3 lists 11 edges as "the cascade closure set." This spec disambiguates two functionally distinct categories:

**Trigger edges** — these *establish the seed* of a cascade but are NOT traversed by the closure algorithm. They identify which node was disrupted (the predecessor in a supersession, the assertion superseded by a new version, etc.). The successor / superseder is not affected by its own act of superseding.

| # | Predicate | Role |
|---|---|---|
| T1 | `rkaf:supersedesAssertion` | Successor's outgoing edge ⇒ predecessor is the cascade seed |
| T2 | `rkaf:supersedesWorkProduct` | Successor's outgoing edge ⇒ predecessor is the cascade seed |
| T3 | `rkaf:LifecycleEvent.appliesTo` | LifecycleEvent's outgoing list ⇒ each entry is a cascade seed |

**Cascade edges** — these *propagate* the affected set, traversed BACKWARD from the seed (find all `M` such that `M.predicate = seed.@id` and recurse).

| # | Predicate | What inverse traversal reaches |
|---|---|---|
| C1 | `rkaf:derivedFromFragment` | Every deriver |
| C2 | `rkaf:justifiedByAssertion` | Every dependent work product |
| C3 | `rkaf:hasAuthority` | Every assertion that cited this authority |
| C4 | `rkaf:derivesAuthorityFrom` | Every downstream chain hop |
| C5 | `rkaf:implements` | Every realization |
| C6 | `rkaf:requiresEvidenceType` | Every requirement consumer |
| C7 | `rkaf:collectsEvidenceType` | Every collector |
| C8 | `rkaf:operationallyDependsOn` | Every dependent |
| C9 | `rkaf:LocalAdoption.targetAssertion` | Every adoption of the seed |
| C10 | `rkaf:assertsObject` (concept-typed) + 5 SKOS mapping edges | Concept-lifecycle propagation |

### §2.2 — Algorithm

```text
fn cascade_closure_v1(
    seed_node_id: IRI,
    graph: &Graph,
    as_of: DateTime,
) -> Set<IRI>:

    let active_filter = node => node.is_active_or_adopted_at(as_of)
    let visited = HashSet::from([seed_node_id])       // seed IS in affectedSet
    let queue = VecDeque::from([seed_node_id])

    while let Some(current_id) = queue.pop_front():
        for predicate in CASCADE_EDGE_PREDICATES:     // C1..C10 only
            for incoming_node in graph.incoming(current_id, predicate):
                if active_filter(incoming_node):
                    if !visited.contains(incoming_node.@id):
                        visited.insert(incoming_node.@id)
                        queue.push_back(incoming_node.@id)

    return visited
```

### §2.3 — Seed determination

The cascade seed is identified by the trigger edge that initiated the closure:

- A `rkaf:LifecycleEvent` that `appliesTo` an `@id` ⇒ seed is that `@id`.
- A `supersedesAssertion`/`supersedesWorkProduct` relationship ⇒ seed is the *predecessor* (the node being superseded), NOT the successor.

Behavior fixtures carry the seed explicitly as `rkaf:cascadeSeed` on the `BehaviorTestCase`. The L4 runtime reads this field; production runtimes derive the seed from incoming `LifecycleEvent.appliesTo` or from supersession edges.

### §2.4 — Termination + cycle safety

The graph is finite. The visited set prevents revisiting. **Cycles are not normatively prohibited** (a `Warrant` MAY have `hasPredecessor` pointing back at itself per the edge fixture `warrant-self-predecessor-edge.jsonld`); the algorithm tolerates them via the visited check.

### §2.5 — Output

```
{ affectedSet: ["<@id>", ...], algorithm: "rkaf:CascadeClosureV1" }
```

`affectedSet` is an unordered set INCLUDING the seed; the test harness compares as a set. The algorithm IRI is required for L4 verdicts.

---

## §3 — Bridge contract rules (1–10)

Per v0.1 §5.4. Each rule has a decidable predicate over the graph + the consumer's `BridgeConsumerRegistration`. The runtime evaluates one rule at a time; the harness selects via `BehaviorTestCase.contractRuleNumber`.

### §3.1 — Rule 1: No Rulespec-backed authority inference outside the three predicates

**Predicate:** an Assertion `A` carries a legal-family `Warrant` (i.e., `hasWarrant.warrantFamily == rkaf:legal`) but `A` participates in NO `hasAuthority` / `derivesAuthorityFrom` chain AND no `LocalAdoption` targets `A`.

**Verdict on violation:** `rkaf:rejected` with `errorClass: rkaf:UnauthorizedLegalInference`.

### §3.2 — Rule 2: usageEligibility via reducer; narrow OK, broaden NOT

**Predicate:** for every `ConsumerEffectiveDeclaration` `D` in the graph, `D.declaredEffective` is `≤ reduce_usage_eligibility(forAssertion, ..., D.declaredScope)` on the lattice. Higher = broadened, which is forbidden except by LocalAdoption (which the reducer already accounts for in §1.2 step 4).

**Verdict on violation:** `rkaf:rejected` with `errorClass: rkaf:UnauthorizedBroadening`.

### §3.3 — Rule 3: authorityKind preserved; no substitution

**Predicate:** for every `BridgeValidationResult` with a `chainTerminusKind`, the declared kind matches the `authorityKind` of the terminus `Warrant`/`Authority` in the chain.

**Verdict on violation:** `rkaf:rejected` with `errorClass: rkaf:AuthorityKindSubstitution`.

### §3.4 — Rule 4: declared EvaluationAnchor support; unsupported anchors refused

**Predicate:** for every `PointInTimeException` in the graph, the `evaluationAnchor` is in the consumer's `BridgeConsumerRegistration.supportedEvaluationAnchors`. The rule fires on any PIT, not only on those a BVR has chosen to honor — v0.1 §4.6 says consumers MUST refuse unsupported anchors, not silently ignore them.

**Verdict on violation:** `rkaf:rejected` with `errorClass: rkaf:UnsupportedEvaluationAnchor`.

### §3.5 — Rule 5: cascade staleForCurrentUse transition

**Predicate:** every assertion in the affected set of a recent `LifecycleEvent` has `consumerLifecycleState == rkaf:staleForCurrentUse` UNLESS the event declares a `safeAutomaticMigration` in the consumer's `supportedAutomaticMigrations`.

**Verdict on violation:** `rkaf:rejected` with `errorClass: rkaf:MissingStaleTransition`. Implemented in `stale.rs` (§5 below) and delegated from `bridge.rs`.

### §3.6 — Rule 6: concept resolution ≠ authority

**Predicate:** no `@id` resolving to a `rkaf:Concept` (RegisteredConcept or LocalConcept) appears in any `BridgeValidationResult.usedAsAuthority`.

**Verdict on violation:** `rkaf:rejected` with `errorClass: rkaf:ConceptUsedAsAuthority`. The BVR field `usedAsAuthority` is the carrier (added to `constraints/core/bridge-validation-result.cue`).

### §3.7 — Rule 7: justification chains MUST terminate

**Predicate:** a chain `work_product → justifiedByAssertion → assertion → hasJustification → justification → hasWarrant → warrant` MUST reach `hasAuthority` (or `derivesAuthorityFrom`) OR a `LocalAdoption` somewhere along the chain (including via warrant-side `derivesAuthorityFrom` hops).

**Verdict on violation:** `rkaf:rejected` with `errorClass: rkaf:UnterminatedJustificationChain`.

**Chain-walk depth:** unbounded by spec; runtime uses a visited-set to protect against cycles.

**Warrant↔Authority transition:** `rkaf:Authority` is a specialization of `rkaf:Warrant` (per `archive/v0.1/spec/rkaf-core.md` §2 and the comment block at `constraints/core/authority.cue:1-8`). The chain walker treats every node typed `rkaf:Authority` as also satisfying the `rkaf:Warrant` type for chain-traversal purposes. `derivesAuthorityFrom` hops live on `Authority` nodes and the walker follows them transparently when present.

### §3.8 — Rule 8: bridge-emitted attestations for consumer-detected issues

**Predicate:** for every consumer with a `BridgeIssueAttestationContract` declaring `attestedIssueKinds = K`, every `BridgeValidationResult` from that consumer whose `detectedIssues[]` contains an issue of any kind in `K` MUST be referenced by at least one `rkaf:Attestation` with `targets` containing the BVR's `@id`.

**Verdict on violation:** `rkaf:rejected` with `errorClass: rkaf:UnattestedConsumerIssue`.

**Default attested-issue-kinds** (the closed enum): `staleDep`, `unresolvedConcept`, `brokenAuthority`, `unsupportedAnchor`. Consumers MAY declare a subset; rule fires only over the declared subset.

### §3.9 — Rule 9: bridgeContractVersion declared; unsupported versions refused

**Predicate:** every `BridgeValidationResult.bridgeContractVersion` matches at least one range in the consumer's `BridgeConsumerRegistration.supportsRegistryVersionRange`.

**Range syntax:** semver-range strings (`"^1.0"`, `">=1.0,<2.0"`). Runtime uses the `semver` crate.

**Verdict on violation:** `rkaf:rejected` with `errorClass: rkaf:UnsupportedContractVersion`.

### §3.10 — Rule 10: generated artifacts preserve Rulespec justification metadata

**Predicate:** every `rkaf:GeneratedWorkProduct` carries `justifiedByAssertion`, AND the referenced Assertion's justification chain terminates per Rule 7.

**Verdict on violation:** `rkaf:rejected` with `errorClass: rkaf:MissingJustificationMetadata` (missing field) or `rkaf:UnterminatedJustificationChain` (chain incomplete; reuses Rule 7's error).

---

## §4 — PointInTimeException

```text
fn evaluate_pit(
    assertion: &Assertion,
    exception: &PointInTimeException,
    consumer: &BridgeConsumerRegistration,
) -> PitVerdict:

    if exception.retainsAssertion != assertion.@id:
        return PitVerdict::NotApplicable

    if exception.evaluationAnchor not in consumer.supportedEvaluationAnchors:
        // v0.1 §4.6 — consumer MUST refuse, not silently ignore
        return PitVerdict::AnchorUnsupported {
            errorClass: rkaf:UnsupportedEvaluationAnchor
        }

    return PitVerdict::RetainedForAnchor {
        anchor: exception.evaluationAnchor,
    }
```

### §4.1 — Output shape

For a fixture exercising PIT with a supported anchor:
```
{
  "<assertion-id>.effectiveStateForAnchor:<anchor-name>": "rkaf:retainedForPointInTime",
  "<assertion-id>.effectiveStateForCurrentUse": "rkaf:staleForCurrentUse"
}
```

Dual output: the assertion is retained for the anchor scope; outside the anchor the original lifecycle state wins.

---

## §5 — Stale transition

State machine on `Assertion.consumerLifecycleState`:

```
   [active]
       │
       │   LifecycleEvent.affectedSet includes assertion.@id
       │   AND event.safeAutomaticMigration ∉ consumer.supportedAutomaticMigrations
       ▼
[staleForCurrentUse]
       │
       │   RevalidationClosureEvent.closesRevalidation references the open
       │   RevalidationEvent for this assertion AND closureDecision is one of
       │   {rkaf:revalidated, rkaf:supersededBySuccessor, rkaf:retainedForPointInTime}
       ▼
[active or retired, per closureDecision]
```

The transition is deterministic. `closureDecision == rkaf:retired` moves the state to `retired` (a terminal state); other decisions return to `active`.

---

## §6 — Concept resolution with conflict

Given a `LocalConcept` `X` and the set `M = {m₁, m₂, ...}` of `ConceptMapping`s where `m.sourceConcept == X`:

```text
fn resolve_concept(local_concept: &LocalConcept, graph: &Graph) -> ResolutionVerdict:
    let mappings = graph.nodes_by_type("rkaf:ConceptMapping")
                        .filter(|m| m.sourceConcept == local_concept.@id)
                        .collect()

    if mappings.is_empty():
        return ResolutionVerdict::Unresolved

    let unique_targets = mappings.iter().map(|m| m.targetConcept).unique().count()

    if unique_targets == 1:
        return ResolutionVerdict::Resolved { canonical: mappings[0].targetConcept }

    // Multiple distinct targets → conflict
    let severity = if mappings.any(|m| m.mappingRelation == "skos:exactMatch"):
                       rkaf:operationalConflict
                   else:
                       rkaf:informational

    return ResolutionVerdict::Conflict {
        registryConflict: RegistryConflict {
            conflictingEntries: mappings.iter().map(|m| m.@id).collect(),
            severity,
        }
    }
```

### §6.1 — Severity ladder

Decided in order, highest first:

1. **`rkaf:authorityCritical`** — fires when (a) ≥2 mappings carry `lifecycleState: approved`, AND (b) targets differ, AND (c) at least one of those approved mappings has `managedByRegistry` ∈ the consumer's `BridgeConsumerRegistration.trustedRegistries`. Trust-level escalation.
2. **`rkaf:publicationBlocking`** — fires when ≥2 mappings carry `lifecycleState: approved` AND targets differ. (Authority-critical's first two clauses without the trusted-registry clause.) Halts publication-tier emissions.
3. **`rkaf:operationalConflict`** — at least one mapping uses `skos:exactMatch` AND targets differ. Operational impact: bridge MAY accept but MUST surface.
4. **`rkaf:informational`** — all mappings are non-exact (`closeMatch`, `broaderMatch`, etc.) AND targets differ. Informational only.

The `ConceptMapping.lifecycleState` and `ConceptMapping.managedByRegistry` fields land in `constraints/core/concept-mapping.cue`; the consumer's `trustedRegistries` field lands in `constraints/core/bridge-consumer-registration.cue`. The severity assignment is implemented in `crates/rkaf-runtime/src/concept.rs::compute_severity` and exercised by `fixtures/behavior/concept-resolution-publication-blocking.jsonld` and `fixtures/behavior/concept-resolution-authority-critical.jsonld`.

### §6.2 — Output shape

```
{ resolutionResult: "rkaf:resolved" | "rkaf:conflict",
  canonicalConcept?: "<@id>",
  registryConflict?: { conflictingEntries: ["<@id>", ...], severity: "<rkaf:severity>" } }
```

---

## §7 — Expected-output format spec (per contract)

The runtime's `BehaviorVerdict` is compared deep-equal to `BehaviorTestCase.rkaf:expectedOutput`. Per-contract shapes:

| Contract | Output keys |
|---|---|
| `rkaf:UsageEligibilityReducer` | `byScope: { <scope>: <level> }` OR `effectiveUsageEligibility: <level>` + `rationale: <str>` |
| `rkaf:CascadeClosureV1` | `affectedSet: [<@id>, ...]` (set-equal) + `algorithm: "rkaf:CascadeClosureV1"` |
| `rkaf:BridgeContractRule` (per rule) | `bridgeValidationResult: <verdict>` + optional `errorClass: <iri>` + optional `rationale: <str>` |
| `rkaf:PointInTimeException` | `"<assertion-id>.effectiveStateForAnchor:<anchor-name>": <state>` + `"<assertion-id>.effectiveStateForCurrentUse": <state>` |
| `rkaf:ConceptResolutionWithConflict` | `resolutionResult: <verdict>` + optional `canonicalConcept: <@id>` + optional `registryConflict: { conflictingEntries: [<@id>+], severity: <severity> }` |

### §7.1 — errorClass IRI registry (closed; extension via §13.4 RFC)

```
rkaf:UnauthorizedLegalInference      (Rule 1)
rkaf:UnauthorizedBroadening          (Rule 2)
rkaf:AuthorityKindSubstitution       (Rule 3)
rkaf:UnsupportedEvaluationAnchor     (Rule 4 / PIT contract)
rkaf:MissingStaleTransition          (Rule 5)
rkaf:ConceptUsedAsAuthority          (Rule 6)
rkaf:UnterminatedJustificationChain  (Rule 7)
rkaf:UnattestedConsumerIssue         (Rule 8)
rkaf:UnsupportedContractVersion      (Rule 9)
rkaf:MissingJustificationMetadata    (Rule 10)
```

---

## §8 — Open ambiguities resolved

Inherited from v0.1 descriptive prose; this document resolves them:

1. **Reducer applicability intersection** — §1.2 Step 1: if eval scope is not in the assertion's `hasApplicability` set, return `notEligible`.
2. **Bridge rule #7 chain-walk depth** — §3.7: no explicit bound; visited set protects against cycles.
3. **`RegistryConflict` severity assignment** — §6.1: explicit table by `mappingRelation` + `lifecycleState`. Operational is the default.
4. **`closeMatch` vs `exactMatch` disagreement** — §6 algorithm: same `targetConcept` is `resolved` regardless of predicate; different `targetConcept` is `conflict`.
5. **Consumer effective eligibility encoding** — `rkaf:ConsumerEffectiveDeclaration` (constraints/core/consumer-effective-declaration.cue).
6. **When a resolved concept becomes "authority-used"** — `BridgeValidationResult.usedAsAuthority` field.
7. **Which issues require bridge-emitted Attestations** — `BridgeIssueAttestationContract.attestedIssueKinds`; default kinds: `staleDep` / `unresolvedConcept` / `brokenAuthority` / `unsupportedAnchor`.
8. **`bridgeContractVersion` range syntax** — §3.9: semver-range strings parsed by the `semver` crate.

---

## §9 — Reference implementation

`crates/rkaf-runtime/` is the reference implementation. `rkaf-behavior-validate` is the CLI gate `tools/conformance_report.py` shells out to. Partner runtimes MUST produce identical outputs on all fixtures under `fixtures/behavior/`; cross-implementation parity is the L4 conformance contract.

Behavior fixtures live in `fixtures/behavior/`. Each is a `rkaf:BehaviorTestCase` carrying `behaviorContract` (one of the IRIs in §7) + `input` (a JSON-LD graph) + `expectedOutput` (the declared correct result). The runtime computes the contract on the input and deep-equals with the expected output.
