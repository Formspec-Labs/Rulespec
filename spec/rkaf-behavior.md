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

### §1.4 — Output

For evaluations carrying a scope:
```
{ byScope: { "<scope-iri>": "<rkaf:level>", ... } }
```

For workspace-wide evaluations (no scope):
```
{ effectiveUsageEligibility: "<rkaf:level>", rationale: "<string>" }
```

---

## §2 — CascadeClosureV1

Transitive closure over the **inverse** of the edges listed in v0.1 §4.3, scoped to nodes that are active/adopted at the triggering `LifecycleEvent.effectiveDate`. The algorithm name `rkaf:CascadeClosureV1` is the L4 conformance identifier; partner implementations MUST emit this string.

### §2.1 — Tracked edges (the inverse-traversal set)

Twelve edge predicates, all traversed BACKWARD:

```
 1. rkaf:derivedFromFragment           ← cascade reaches the deriver
 2. rkaf:justifiedByAssertion          ← cascade reaches every work product
 3. rkaf:hasAuthority                  ← cascade reaches every dependent decision
 4. rkaf:derivesAuthorityFrom          ← cascade reaches every downstream hop
 5. rkaf:implements                    ← cascade reaches every realization
 6. rkaf:requiresEvidenceType          ← cascade reaches every requirement consumer
 7. rkaf:collectsEvidenceType          ← cascade reaches every collector
 8. rkaf:operationallyDependsOn        ← cascade reaches every dependent
 9. rkaf:supersedesAssertion           ← cascade reaches every superseded predecessor
10. rkaf:supersedesWorkProduct         ← cascade reaches every superseded product
11. rkaf:LocalAdoption.targetAssertion ← cascade reaches every adoption
12. rkaf:assertsObject (concept-typed) plus the 5 SKOS mapping edges
    (exactMatch / closeMatch / broadMatch / narrowMatch / relatedMatch)
                                       ← concept-lifecycle cascade
```

### §2.2 — Algorithm

```text
fn cascade_closure_v1(
    seed_node_id: IRI,
    graph: &Graph,
    as_of: DateTime,
) -> Set<IRI>:

    let active_filter = node => node.is_active_or_adopted_at(as_of)
    let visited = HashSet::new()
    let queue = VecDeque::from([seed_node_id])

    while let Some(current_id) = queue.pop_front():
        if visited.contains(current_id) { continue }
        visited.insert(current_id)
        for predicate in [TRACKED_EDGE_PREDICATES]:
            for incoming_node in graph.incoming(current_id, predicate):
                if active_filter(incoming_node):
                    queue.push_back(incoming_node.@id)

    return visited
```

### §2.3 — Termination + cycle safety

The graph is finite. The visited set prevents revisiting. **Cycles are not normatively prohibited** (a `Warrant` MAY have `hasPredecessor` pointing back at itself per the edge fixture `warrant-self-predecessor-edge.jsonld`); the algorithm tolerates them via the visited check.

### §2.4 — Output

```
{ affectedSet: ["<@id>", ...], algorithm: "rkaf:CascadeClosureV1" }
```

`affectedSet` is an unordered set; the test harness compares as a set. The algorithm IRI is required for L4 verdicts.

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

**Predicate:** for every `PointInTimeException` honored by a `BridgeValidationResult`, the `evaluationAnchor` is in the consumer's `BridgeConsumerRegistration.supportedEvaluationAnchors`.

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

### §6.1 — Severity assignment

- `rkaf:operationalConflict` — default when at least one mapping uses `skos:exactMatch` AND targets differ.
- `rkaf:informational` — all mappings are non-exact (`closeMatch`, `broaderMatch`, etc.) AND targets differ.
- `rkaf:publicationBlocking` — RESERVED for mappings where at least two carry `lifecycleState: approved` AND targets differ. (Plan 7c codification — not yet exercised by a fixture.)
- `rkaf:authorityCritical` — RESERVED for the publicationBlocking condition plus at least one mapping in a registry the consumer trusts at L4 authority level. (Plan 7c.)

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
