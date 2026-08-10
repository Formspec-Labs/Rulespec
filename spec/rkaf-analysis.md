# Rulespec Document-Analysis Module v0.2

Status: **Normative**, except §6 (`rkaf:ClosureClaim`), which is
**Experimental and DISABLED**.

CUE source: `constraints/analysis/`.
Hand-authored shapes: `shapes/rkaf-shapes-analysis.ttl`.
Compiled targets: `compiled/<target>/analysis/` and
`crates/rkaf-core/src/generated/analysis/`.
Vocabulary rows: `spec/rkaf-vocabulary.md`, "Document-analysis module".

---

## 1. What this module is, and where it sits

This module defines the generic contracts for **comparing relations across
document versions**: how a source-stated change to a relation is recorded, how
one comparison run is framed and resolved, what a resolver decision has to
show, and what a neutral analytical finding may say.

It is **not the kernel** and **not a profile**.

```text
constraints/core/        the universal kernel
constraints/analysis/    this module
constraints/profiles/*   domain profiles
```

The dependency direction is **kernel <- analysis <- profiles**, and every
arrow in it is one-way:

* The **kernel never depends on this module.** No shape under
  `constraints/core/` may reference an analysis shape or mention an analysis
  term. `AnalysisModuleTests.test_kernel_never_references_an_analysis_shape`
  and `test_kernel_declares_no_analysis_term` fail the build if one does.
* **This module may compose kernel shapes**, and does:
  `#RelationChangeEvent` and `#ClosureClaim` both compose
  `#AssertionEnvelope`, so construction origin, AI lineage, extraction
  provenance, source claimant, confidence, consumer disposition, supersession,
  and assertion time have exactly one home each.
* **This module declares nothing jurisdiction-specific.** No US term, no
  citation grammar, no proceeding, no legal-effect vocabulary. It says nothing
  about what a change or a finding *means* in any legal system.
* **Profiles may depend on this module.** A regulatory, scientific, judicial,
  legislative, contractual, procurement, or oversight profile may interpret
  these records — differently from each other, or not at all (§7).

### 1.1 Why it is a module and not part of the kernel

The kernel says what an assertion, an artifact, a fragment, and a warrant are.
Comparison is a *process* over those primitives, with its own policy versions,
detector versions, resolver protocols, and snapshots. A consumer that stores
and exchanges Rulespec assertions does not automatically run comparisons, and
must not inherit a comparison vocabulary it never produces. Keeping the two
apart is what lets the kernel stay small enough to adopt shallowly.

**One kernel-side file names this module, and it is exempt on purpose.**
`shapes/rkaf-shapes-core.ttl` is an *umbrella*: an `owl:Ontology` whose
`owl:imports` list aggregates every shipped v0.2 shape graph, and
`<https://rulespec.org/shapes/analysis>` sits on that list beside
`studio-promotions` and `conceptregistry`. That is a declaration of
**membership in the shipped set**, not composition: no kernel shape targets an
analysis class, no kernel shape mentions an analysis term, and
`conformance_lib.shacl_shape_paths()` globs `shapes/*.ttl` rather than
resolving imports, so the entry does not change what any gate loads. The
exemption is pinned rather than trusted —
`AnalysisModuleTests.test_kernel_shape_file_names_analysis_only_as_an_umbrella_import`
fails the build if the aggregate import stops being the *only* mention of this
module in that file, or if any analysis-owned `rkaf:` term appears in it.

### 1.2 The four semantic cases, kept apart

The module exists to stop one collapse: folding every negative or changed
signal into a single flag. Each evidence situation has its own
representation, and they are not degrees of one another.

| Evidence situation | Representation |
|---|---|
| A source affirms the relation | affirmed `rkaf:RelationshipAssertion` (kernel) |
| A source denies the relation | denied `rkaf:RelationshipAssertion` (kernel) |
| A source adopts, removes, suspends, or replaces the relation | `rkaf:RelationChangeEvent` (§2) |
| Accepted assertions disagree | `rkaf:RelationFinding` (§5) over a comparison (§3) |
| A gate failed | `rkaf:comparisonNotComparable` outcome (§3.2) |
| A gate could not decide | `rkaf:comparisonUnknown` outcome (§3.2) |
| The source says nothing | no record at all; **unknown** |
| A rule gives the change legal or policy effect | profile-owned interpretation (§7) |

There is deliberately **no representation for "the relation was expected and
not observed"**. That case requires a proven closure boundary, closure is
disabled (§6), and outside a proven boundary silence is
`rkaf:comparisonUnknown`.

---

## 2. `rkaf:RelationChangeEvent`

A `rkaf:RelationChangeEvent` records that a source **changes** a relation.

### 2.1 A change is not a polarity

"The Secretary removes the designation" does not assert that the designation
never held. It says a designation that held is being taken away, at some stage
of some process, with some intended effect time. Recording that as a denied
assertion destroys the distinction between *this was never true* and *this
stopped being true* — the distinction every later comparison depends on.

Polarity is therefore **structurally absent**. `#RelationChangeEvent` composes
`#AssertionEnvelope` and deliberately **not** `#AssertionProposition`
(subject, predicate, **polarity**).

The compiled carriers are open-world, so absence in the CUE is not
enforcement. A conforming `rkaf:RelationChangeEvent` **MUST NOT** carry
`rkaf:assertionPolarity`, `rkaf:assertsSubject`, `rkaf:assertsPredicate`, or
`rkaf:assertsObject`. `rkaf:RelationChangeEventNoPolarityShape` in
`shapes/rkaf-shapes-analysis.ttl` rejects a record that carries one anyway.

The relation being changed is named by its own three predicates —
`rkaf:changeSubject`, `rkaf:changePredicate`, `rkaf:changeObject` — precisely
so a change event is **not** indexable as an assertion by a consumer that
queries the assertion predicates.

### 2.2 A change event is not a `rkaf:LifecycleEvent`

An `rkaf:LifecycleEvent` records what happened to a **resource** — an
Artifact, a Warrant, an Assertion — and seeds `rkaf:CascadeClosureV1`
revalidation over that resource (`spec/rkaf-behavior.md`). A change event
records what a source says about a **relation between two resources**, may be
merely proposed, and seeds nothing. Publishing one as the other would let a
proposed removal cascade as though it had already taken effect. The two
vocabularies are disjoint and neither subclasses the other.

### 2.3 Operations

`rkaf:relationChangeOperation` is REQUIRED and closed over four values. They
are four different evidence situations, not four degrees of one negative
signal.

| Value | Meaning |
|---|---|
| `rkaf:relationAdoption` | the relation is created or recognized |
| `rkaf:relationRemoval` | the relation is taken away |
| `rkaf:relationSuspension` | the relation is held in abeyance, not ended |
| `rkaf:relationReplacement` | the relation's object is exchanged for another |

A **suspension is not a removal**: a suspended relation is expected to resume,
and collapsing the two loses the expectation. A **replacement is not a
removal**: it names a successor. A `rkaf:relationReplacement` therefore
**MUST** carry `rkaf:replacementRelationObject`; a replacement that does not
name the successor carries no information `rkaf:relationRemoval` does not
already carry.

### 2.4 Stages

`rkaf:relationChangeStage` is REQUIRED and closed over five values:
`rkaf:changeProposed`, `rkaf:changeDecided`, `rkaf:changeEffective`,
`rkaf:changeWithdrawn`, `rkaf:changeStageUnclear`.

`rkaf:changeStageUnclear` is a **first-class value, not a gap**. A source that
states a change without a decidable stage must be recordable as such; dropping
the record or guessing a stage both convert uncertainty into a claim.

The stage says **nothing about legal operativeness**. Whether
`rkaf:changeEffective` means a rule is operative is a profile question (§7).

### 2.5 Times

Three times are kept apart:

* `rkaf:assertedAt` (from the envelope) — when the **record** was made;
* `rkaf:relationChangeTime` — the time the **source** attaches to the change;
* `rkaf:changeIntendedEffectiveTime` — when the source says the change is
  **intended to take effect**.

Both change-specific times are optional in general: a source may state a
removal with no date at all, and requiring one would make producers invent it.
A change at stage `rkaf:changeEffective` — one the source says is *already* in
effect — **MUST** carry `rkaf:changeIntendedEffectiveTime`, because without it
the record cannot be ordered against the baseline it would be compared to.

### 2.6 Evidence

`rkaf:changeEvidence` is REQUIRED with at least one member, class-ranged to
`rkaf:SourceFragment`. A change event with no citable region is a rumour:
there is nothing to re-read and nothing to re-derive it from.

---

## 3. `rkaf:RelationComparisonContext`

A `rkaf:RelationComparisonContext` is the **immutable record of one
comparison**: the frame it ran in and the outcome it reached.

### 3.1 The frame

Everything that could change the answer is bound on the context, so a result
is reproducible and auditable without re-deriving it:

| Property | What it pins |
|---|---|
| `rkaf:comparisonBaselineArtifact`, `rkaf:comparisonObservedArtifact` | which two Artifact versions were compared |
| `rkaf:comparisonExpectedAssertion` | which baseline assertion the run answered for |
| `rkaf:comparisonConsumer`, `rkaf:comparisonScope` | whose acceptance was read, under which scope |
| `rkaf:comparisonEvaluationTime` | when it was evaluated |
| `rkaf:comparisonPolicyVersion` | which comparison policy applied |
| `rkaf:comparisonDetector`, `rkaf:comparisonDetectorVersion` | which implementation ran |
| `rkaf:comparisonSnapshot` | which immutable source snapshot was read |

All are REQUIRED. Consumer and scope are required because acceptance is
consumer-scoped (`#ConsumerDisposition`): a comparison that does not name its
consumer has not said which acceptance it read. Evaluation time is required
because acceptance and applicability are both time-dependent.

**Nothing on this record is mutable.** Changing any input produces a
*different* comparison, not an update to this one; a re-run writes a new
context.

### 3.2 Outcomes

`rkaf:comparisonOutcome` is REQUIRED and closed over exactly five values.

| Value | Meaning |
|---|---|
| `rkaf:comparisonSatisfied` | an accepted, equivalent, affirmed observation exists |
| `rkaf:comparisonAffirmedDeniedDiscrepancy` | accepted assertions disagree on the same relation |
| `rkaf:comparisonConflict` | accepted assertions are mutually inconsistent on one side |
| `rkaf:comparisonNotComparable` | an eligibility gate FAILED |
| `rkaf:comparisonUnknown` | a required gate returned unknown |

Two rules govern reading them:

1. `rkaf:comparisonNotComparable` is a **gate result, never a negative fact
   about a source.** It says the comparison was not eligible to run, not that
   the relation is absent.
2. `rkaf:comparisonUnknown` **never becomes** a failure. Absence of a decision
   is its own value.

The set is closed deliberately. A sixth value is a new semantic case, and new
semantic cases enter this contract by review, not by a producer inventing a
string.

`expected_relation_not_observed` is **not** in this enum and is not a finding
kind either (§5). Omission requires a proven closure boundary; closure is
disabled (§6). Until it is enabled by a deliberate contract change, silence
outside a proven boundary is `rkaf:comparisonUnknown`.

### 3.3 The outcome lives on the context, not on the finding

All five outcomes are real results. Only one of them — an affirmed/denied
discrepancy — also produces a `rkaf:RelationFinding`. Putting the outcome on
the finding would make `satisfied`, `conflict`, `not_comparable`, and
`unknown` unrepresentable: the system would have no way to record that it
looked and found no discrepancy. That record is exactly what distinguishes
**checked, nothing found** from **never checked**.

### 3.4 No AI model decides a comparison outcome alone

A model may propose assertions and change events **upstream**, and that
proposal is carried by `rkaf:assertionOrigin` and `rkaf:hasAILineage` on the
proposed record. A model **MUST NOT** produce a comparison outcome. The
comparison kernel is deterministic and evidence-gated: given the same frame,
the same accepted assertions, and the same resolver decisions, it returns the
same outcome.

**Amended 2026-08-09.** The paragraph above forbade a model from touching a
comparison at all, which was too strong: it would forbid the machine-adjudication
resolver protocol this contract now defines (§4 extension,
`rkaf:MachineAdjudicationProof`) outright, even though that protocol never lets
a model decide anything alone. The honest rule keeps the same spirit with the
distinction that was missing:

A model **MAY** produce a `rkaf:MachineAdjudicationProof` — a sealed,
reviewable answer to one comparison QUESTION, carried exactly like any other
resolver's proof (§4). A model **MUST NOT** produce a comparison OUTCOME. The
outcome is produced only by the deterministic lattice folding **two or more
independent** proofs — never by reading one model's proof as the answer. What
"independent" means, and what a claim's cited proof set must retain, is a
cross-node rule over multiple proof records and lives in
`rkaf:MachineAdjudicationIndependentPairShape` and
`rkaf:MachineAdjudicationCompleteSupportShape`
(`shapes/rkaf-shapes-analysis.ttl`), not here — CUE constrains one struct, and
this rule spans several.

So: a model's proof is admissible evidence; a model's OPINION is never the
outcome, and one proof — or a set of proofs that all trace back to one
uncorroborated witness — is exactly the failure mode "no model decides a
comparison outcome alone" still refuses.

### 3.5 Proof obligation

`rkaf:comparisonProofRecord` is class-ranged to `rkaf:ResolverProofRecord` and
is **REQUIRED, with at least one member, for every outcome except
`rkaf:comparisonUnknown`**.

An unknown result may arise before any resolver could be consulted — a missing
input, an unreachable snapshot. A satisfied, discrepant, conflicting, or
not-comparable result is a **claim about evidence** and must show the proofs
that back it.

---

## 4. `rkaf:ResolverProofRecord` and `rkaf:ResolverProofIssuer`

The comparison kernel owns deterministic orchestration and nothing else. It
does not know how a predicate registry, a database, a document parser, a model
provider, or a legal profile works. Each of those implements a narrow
**resolver protocol** and answers one question.

### 4.1 Proof types

`rkaf:proofType` is REQUIRED and closed over seven values, one per active
resolver protocol.

| Value | The question it answers |
|---|---|
| `rkaf:predicateCatalogProof` | is this canonical relation valid, and do two assertions describe the same relation? |
| `rkaf:assertionStateProof` | is this assertion accepted for this consumer, scope, and evaluation time? |
| `rkaf:evidenceBindingProof` | does exact evidence in this artifact version support this assertion occurrence? |
| `rkaf:baselineWarrantProof` | may this assertion serve as the expected baseline under an active warrant? |
| `rkaf:artifactPairingProof` | may these artifact versions be compared for this purpose? |
| `rkaf:scopeComparisonProof` | are the temporal, jurisdictional, conditional, and applicability scopes comparable? |
| `rkaf:machineAdjudicationProof` | what relation does a machine adjudicator find between two things under comparison, over one sealed question? (§4.5) |

The three **longitudinal** protocols — version lineage, expected coverage, and
closure — are deliberately absent. They exist only to support omission
findings; omission is disabled (§6); and a contract that can mint a closure
proof is a contract in which closure is half-enabled. They enter this enum by
the same deliberate contract change that enables `#ClosureClaim`, not before.

### 4.2 Outcomes

`rkaf:proofOutcome` is REQUIRED and closed over the union of two sets.

**Gate results** — `rkaf:gatePass`, `rkaf:gateFail`, `rkaf:gateUnknown`.

* `rkaf:gateFail` is a **gate result, never a negative fact about a source.**
  A failed eligibility gate makes a comparison `rkaf:comparisonNotComparable`;
  it never becomes a denied assertion.
* `rkaf:gateUnknown` **never becomes** `rkaf:gateFail`.

**Scope relations** — `rkaf:scopeEquivalent`,
`rkaf:scopeObservedSubsumesExpected`, `rkaf:scopeObservedNarrowsExpected`,
`rkaf:scopeOverlaps`, `rkaf:scopeDisjoint`, `rkaf:scopeUnknown`.

A scope comparator returns a **relation**, not a gate result:
`rkaf:scopeOverlaps` is neither a pass nor a failure, and collapsing the six
relations onto pass/fail throws away the direction of containment that decides
whether an expectation applies to the observed version at all.

### 4.3 A proof is content-bound, not merely named

**An opaque string is not proof.** A proof identifier used in a published
result must resolve, inside the same immutable generation or through a pinned
and reachable external record. Four properties make that checkable:

* `rkaf:proofInput` (REQUIRED, ≥1) — WHAT the resolver read.
* `rkaf:proofInputDigest` (optional) — lowercase `sha256:<64 hex>` values
  binding those inputs to exact bytes. Identifiers alone prove which records
  were named; digests prove which **version** of them was read.
* `rkaf:proofRecordDigest` (REQUIRED) — the record's own content digest. A
  consumer that dereferences the proof recomputes this and rejects the proof
  when it differs, so a proof cannot be edited after the result citing it was
  published.
* `rkaf:proofComparisonContext` (REQUIRED) — the comparison the proof was
  issued for. A proof that does not name its comparison can be replayed
  against a different one, which is how a stale pass gets reused.

Requiring `rkaf:proofComparisonContext` only makes the binding **declared**.
That the named comparison is the one actually *citing* the proof is a
statement relating two nodes, which per-property SHACL cannot reach, so it is
enforced by `rkaf:ResolverProofComparisonBindingShape` in
`shapes/rkaf-shapes-analysis.ttl`:

> A `rkaf:ResolverProofRecord` named by a context's
> `rkaf:comparisonProofRecord` **MUST** name that same
> `rkaf:RelationComparisonContext` in `rkaf:proofComparisonContext`.

Without it, a producer takes a 2019 gate pass, cites it from a 2026
comparison, and leaves the proof pointing at the 2019 context: every
per-property constraint passes, and a stale pass backs a fresh discrepancy
finding. `rkaf:proofRecordDigest` does not catch that case — the proof record
is unedited; it is the **citation** that is false. Like the other cross-node
rules, the shape fires only when the proof node is present in the graph, so a
comparison published alone with its proofs dereferenced elsewhere validates as
before.

`rkaf:proofSupportingRecord` is held separate from `rkaf:proofInput` because
these are the **support**, not the subject: an attestation that made an
assertion accepted is not one of the assertions being compared.

`rkaf:proofRationale` is REQUIRED and non-empty. A decision with no stated
reason is not reviewable, and every resolver protocol returns a rationale.

`rkaf:proofEvaluatedAt` and `rkaf:proofSnapshot` are both REQUIRED: the same
resolver over the same inputs at another time, or against another snapshot,
may decide differently, and a proof that hides that is not replayable.

### 4.4 `rkaf:ResolverProofIssuer`

The versioned resolver and policy a proof was issued under —
`rkaf:proofResolver`, `rkaf:proofResolverVersion`, `rkaf:proofPolicy`,
`rkaf:proofPolicyVersion`, all REQUIRED.

It is a **separate node**, referenced by `rkaf:proofIssuer` and class-ranged
to `rkaf:ResolverProofIssuer`, for the same reason Rulespec keeps one
`rkaf:ConfidenceRecord` rather than a score on every assertion: a resolver
version that changes must change in one place, and two proofs claiming the
same issuer must be comparable by IRI rather than by hoping four strings were
copied identically. "Issued by version 3" has to resolve to a record, not to a
version string a reader must trust.

### 4.5 `rkaf:MachineAdjudicationProof` (added 2026-08-09)

A machine adjudicator may answer a sealed comparison question — same,
near-same, target broader, target narrower, or related — over two things under
comparison. `rkaf:MachineAdjudicationProof`
(`constraints/analysis/machine-adjudication.cue`) is how that answer becomes a
resolver proof.

It is **not a second RDF type**, and not a second parallel attestation record
for the same fact — one proof record carries the adjudicated outcome, full
stop. A machine-adjudication proof is a plain `rkaf:ResolverProofRecord` whose
`rkaf:proofType` equals the literal `rkaf:machineAdjudicationProof`, which
REQUIRES five additional properties exactly when that literal is present:

| Property | Carries |
|---|---|
| `rkaf:proofType` | narrowed to the literal `rkaf:machineAdjudicationProof` |
| `rkaf:hasAILineage` | the reviewed model-derivation record behind the call (Core §5.3) |
| `rkaf:independenceGroup` | the sampling or deployment pool this validator run was drawn from |
| `rkaf:adjudicationVerdict` | which relation this adjudication found — `rkaf:verdictSame`, `rkaf:verdictNearSame`, `rkaf:verdictTargetBroader`, `rkaf:verdictTargetNarrower`, `rkaf:verdictRelated` |
| `rkaf:sealedRequestDigest` | `sha256:<64 hex>` over the exact sealed question this proof answered |
| `rkaf:sealedResponseArtifact` | the sealed provider response this proof's verdict was read from |

A distinct `@type` was considered and rejected: `tools/conformance_lib.py`
binds exactly one compiled schema per `@type` IRI, so a second class declaring
`rkaf:ResolverProofRecord` would collide with the base proof record's own
binding, and an `rdfs:subClassOf`-related second `@type` does not help either
— the SHACL suite's `sh:class` constraint component does not apply RDFS
subclass entailment the way `sh:targetClass` does without an explicitly
supplied `ont_graph`, which `tools/ci_validate.py` never supplies. So a
machine-adjudication proof satisfies every cross-node rule written against
`rkaf:ResolverProofRecord` — including `rkaf:ResolverProofComparisonBindingShape`
above — for the plainest possible reason: it always was one. The two shapes
below find it by reading `rkaf:proofType`, never by a second `rdf:type`.

A single machine-adjudication proof, or a set of them that all reduce to one
uncorroborated witness, is not enough to move a comparison outcome (§3.4).
`rkaf:MachineAdjudicationIndependentPairShape` requires, among the
machine-adjudication proofs a claim cites, at least one PAIR that answered the
identical sealed question (`rkaf:sealedRequestDigest` equal) while being
independent on all five axes — `rkaf:proofIssuer` (validator actor),
`rkaf:independenceGroup`, `rkaf:proofIssuer -> rkaf:proofResolver` (provider),
`rkaf:hasAILineage -> rkaf:modelId` (provider model ID), and
`rkaf:sealedResponseArtifact` (response artifact). The fifth axis
(spec/rkaf-refspec.md, corrected 2026-08-09) keeps two proofs that otherwise
differ on the first four from qualifying as independent if they read their
verdicts from one shared sealed response.
`rkaf:MachineAdjudicationCompleteSupportShape` requires that once an
independent pair qualifies, every OTHER machine-adjudication proof that
self-declares support for the same claim and answered the same sealed question
stays cited — discarding a corroborating machine loses evidence (see
`spec/rkaf-refspec.md`, corrected 2026-08-09). Both rules are cross-node — they
reason about the relationship between multiple proof records cited by one
comparison or finding — so, per `shapes/README.md`, they live in
`shapes/rkaf-shapes-analysis.ttl`, not in the CUE source above.

---

## 5. `rkaf:RelationFinding` — neutral

A `rkaf:RelationFinding` says **exactly one thing**: under the named
comparison, accepted assertions disagreed about the same relation.

### 5.1 What it is not

It is **not** a denial, **not** a legal effect, **not** a policy exclusion,
**not** a rescission, **not** a suspension, and **not** a recommendation.

This module declares **no legal-effect terms at all**. There is no
`rkaf:policyExclusion`, no `rkaf:rescinds`, no `rkaf:legalEffect`, and no
severity ladder a consumer could read as one.
`AnalysisModuleTests.test_module_declares_no_legal_effect_term` fails the
build if such a term appears.

### 5.2 Finding kinds

`rkaf:relationFindingKind` is REQUIRED and closed over **one** value:
`rkaf:affirmedDeniedDiscrepancy`.

The single value is the point. Every other evidence situation has its own
representation (§1.2), so a finding kind exists only where none of the others
fit.

`expected_relation_not_observed` is deliberately **not** a value and **MUST
NOT** become one while §6 is disabled. An omission finding is only meaningful
inside a proven closure boundary; without one it converts silence into a
claim, which is the single failure mode this module exists to prevent.
`AnalysisModuleTests.test_no_omission_finding_kind_is_representable` asserts
the absence mechanically, so it cannot be reintroduced as a "small" enum
addition.

### 5.3 What a finding binds

* `rkaf:findingComparisonContext` (REQUIRED, class-ranged to
  `rkaf:RelationComparisonContext`) — the comparison being reported. The
  context carries the artifact pair, consumer, scope, evaluation time, policy
  and detector versions, snapshot, and outcome, so the finding restates none
  of them and **cannot disagree with them**.
* `rkaf:findingComparedAssertion` (REQUIRED, **≥2**) — the accepted assertions
  that disagreed. One assertion cannot disagree with itself, and a
  "discrepancy" naming a single record is a mislabelled unilateral claim.
* `rkaf:findingProofRecord` (REQUIRED, ≥1, class-ranged to
  `rkaf:ResolverProofRecord`) — every proof backing the finding. A neutral
  finding is only as reviewable as the gate decisions under it.
* `rkaf:findingDetectedAt` and `rkaf:findingRationale` (both REQUIRED) — when
  the detector produced this occurrence, and why.
* `rkaf:findingFingerprint` (optional) — a stable correlation key grouping
  repeated observations of the same conceptual gap. Deliberately separate from
  the finding's identity: changing any comparison input creates a **new**
  detector occurrence, and the fingerprint is what lets a consumer see that two
  occurrences are about the same thing without merging them into one.

### 5.4 It is not the kernel's `rkaf:Finding`

`constraints/core/finding.cue` declares a generic `rkaf:Finding` (ADR-0093):
the IRI-addressable record of a single validation or audit detection.

`rkaf:RelationFinding` **neither composes nor subclasses it.** Four
incompatibilities decide it:

1. **Severity.** `rkaf:FindingSeverity` is a closed and deliberately
   *actionable* ladder — `rkaf:publicationBlocking`,
   `rkaf:authorityCritical`. Composing it would put precisely the
   readable-as-legal-effect ladder §5.1 forbids onto a record whose purpose is
   neutrality.
2. **Subject.** `rkaf:subject` is one IRI, "the object the finding concerns".
   A relation finding is about a *comparison* between two artifact versions
   over at least two assertions. There is no single subject; forcing one would
   make producers choose arbitrarily and consumers index on the choice.
3. **Waivability, as a reading.** `rkaf:targetFinding` on `rkaf:Attestation`
   is what the kernel's waiver path is spelled with, and waiving a discrepancy
   — *we accept this* — is a **domain act**, reserved to profiles by §7.
   Note the limit of this argument: `rkaf:targetFinding` is a plain string
   with `sh:maxCount 1` and **no class range anywhere**
   (`constraints/core/attestation.cue`), so any IRI is already nameable there,
   a `rkaf:RelationFinding`'s included. Subclassing would not be what first
   opens the path; it would make the waiver *read* as a kernel-sanctioned one.
   This argument is about entitlement to infer, not about a gate, and is not
   claimed as one. Arguments 1, 2, and 4 are the mechanically enforced ones,
   and the decision rests on them.
4. **Kernel purity.** `rkaf:FindingKind` is a closed **kernel** enum with the
   kernel's own RFC path. Adding `rkaf:affirmedDeniedDiscrepancy` to it would
   put an analysis-owned value in a kernel enum — the dependency §1 forbids.

The two coexist without overlapping. A validator that notices a malformed
comparison record emits an `rkaf:Finding` *about that record*; the comparison
itself yields a `rkaf:RelationFinding`. Different producers, different
subjects, different consequences.
`AnalysisModuleTests.test_relation_finding_is_not_the_kernel_finding` fails
the build if the two are merged.

### 5.5 The finding must agree with its comparison

A finding **MUST** bind a context whose `rkaf:comparisonOutcome` is
`rkaf:comparisonAffirmedDeniedDiscrepancy`.

This is a cross-node agreement rule that per-property SHACL cannot reach, so
it is enforced by `rkaf:RelationFindingContextOutcomeAgreementShape` in
`shapes/rkaf-shapes-analysis.ttl`. Without it a producer could attach a
discrepancy finding to a comparison that came back `rkaf:comparisonSatisfied`
— a finding claiming a disagreement the comparison never found.

The shape fires only when the context node is present in the graph, so a
finding published alone, with its context dereferenced elsewhere, validates as
before.

---

## 6. `rkaf:ClosureClaim` — EXPERIMENTAL AND DISABLED

### 6.1 What it would say

A closure claim says that a **named observation process completely
enumerated** a bounded class of relations in a specific source region of a
specific Artifact version, under a declared scope, profile version, and
extraction run.

It is a reviewable claim about a **process**. It is never a property of a
document, and never a property of a corpus or of the world. **Closure is
always local, and revocable.**

| Property | Requirement |
|---|---|
| `rkaf:closureClaimStatus` | REQUIRED; exactly one legal value (§6.3) |
| `rkaf:closureArtifact` | REQUIRED; the Artifact version bounded |
| `rkaf:closureRegion` | REQUIRED, ≥1; the exact `rkaf:SourceFragment` regions enumerated |
| `rkaf:closurePredicateFamily` | REQUIRED; WHAT was enumerated |
| `rkaf:closureProfileVersion` | REQUIRED; the normalization policy that defined the boundary |
| `rkaf:closureMemberDigest` | REQUIRED; `sha256:<64 hex>` over the accepted member set |
| `rkaf:closureReviewedAt` | optional; an unreviewed claim must be representable as unreviewed |

`rkaf:closureRegion` is required with at least one member because a claim that
names no region is a claim about a whole document — which this record must be
**incapable of expressing**. `rkaf:closureMemberDigest` is what makes the
claim checkable at all: "these and only these" is verifiable only against a
content-bound set, and a recomputed digest that differs means the enumeration
is not the one that was reviewed.

`#ClosureClaim` composes `#AssertionEnvelope` and deliberately **not**
`#AssertionProposition`: a closure claim's proposition is "this bounded region
was completely enumerated", not a subject-predicate-object triple, and it
**MUST NOT** carry `rkaf:assertionPolarity`, `rkaf:assertsSubject`,
`rkaf:assertsPredicate`, or `rkaf:assertsObject`.

Absence from the CUE shape is not enforcement — the compiled JSON Schema emits
no `additionalProperties: false` and RDF is open-world — so
`rkaf:ClosureClaimNoPolarityShape` in `shapes/rkaf-shapes-analysis.ttl` closes
it, exactly as `rkaf:RelationChangeEventNoPolarityShape` does for change events
(§2.1). Without it a **disabled** record can be published as a *denied
assertion about a triple*: the §2 collapse, wearing the one `@type` that is
supposed to carry no weight at all.

### 6.2 Why it exists in the contract while disabled

Bounded omission — *a closed later observation lacks an expected relation* —
is the only situation in which silence may be reported as anything other than
unknown, and it is unusable without a closure boundary. Defining the shape
now, disabled, is what keeps the eventual enabling a **reviewed contract
change** rather than an ad-hoc field invented by whichever producer needs it
first.

Closure stays disabled until a frozen real dataset measures closure precision
and recall **separately from extraction**. Until then, silence outside a
proven boundary is `rkaf:comparisonUnknown`.

### 6.3 The disabling, normatively

A `rkaf:ClosureClaim` **MUST NOT** be produced or consumed as evidence for any
finding.

* No `rkaf:RelationFinding` may reference one — directly, through its
  comparison context, or through a cited proof record.
* No omission finding kind exists, and none may be added while this record is
  disabled.
* No closure resolver proof type exists, and none may be added while this
  record is disabled.

A `rkaf:ClosureClaim` appearing in a conforming document is a **shape-validity
artifact only**. It records what the eventual claim looks like, and it carries
no weight in any comparison.

### 6.4 How the disabling is enforced

Four independent mechanisms, so that no single edit can quietly enable it.

1. **The experimental flag.** `rkaf:closureClaimStatus` is REQUIRED and closed
   over exactly one value, `rkaf:closureClaimDisabled`. Every compiled target
   — JSON Schema `enum`, SHACL `sh:in`, the Rust and TypeScript enums, the
   Rego value set — rejects any other value. A producer cannot author a claim
   without declaring that it carries no weight, and a consumer reading the
   value knows so without consulting prose. Enabling means editing the enum,
   which **moves the contract digest** and forces every pinned consumer to
   re-accept.
2. **No closure proof type.** `#ResolverProofType` (§4.1) declares none, so a
   closure decision cannot be minted as a proof record and cited by a
   comparison.
3. **Unreachability in the graph.**
   `rkaf:ClosureClaimNotFindingEvidenceShape` in
   `shapes/rkaf-shapes-analysis.ttl` fails any graph in which a
   `rkaf:RelationFinding` **reaches** a `rkaf:ClosureClaim` — through one of
   its own properties, or **transitively, at any depth**, through its
   comparison context, the proof records it or its context cite, the
   assertions it compared, and the records those in turn lean on
   (`rkaf:comparisonProofRecord`, `rkaf:comparisonExpectedAssertion`,
   `rkaf:proofSupportingRecord`, `rkaf:proofInput`,
   `rkaf:supersedesAssertion`, `rkaf:hasJustification`).

   The depth is unbounded on purpose. "Disabled" must mean *unreachable*, not
   merely *un-named*, and not "un-named at distance one" either: a producer
   routing the claim through `rkaf:proofSupportingRecord` would otherwise have
   enabled omission by indirection, and — because that property is deliberately
   unranged (§6.5, `l0-ranges.cue`) and a proof record may cite another proof
   record — *any* fixed hop count is walked around by interposing one more
   proof. An earlier form of this shape enumerated four one-hop routes and was
   walked around exactly that way. The traversal is restricted to the
   evidence-bearing predicates listed above rather than an unrestricted
   wildcard, so an unrelated node that merely *mentions* a shape-validity
   claim does not fail a finding elsewhere in the same document — §6.3 permits
   the claim to appear, and forbids the finding reaching it.
4. **Build-time assertions.** `AnalysisModuleTests` in
   `tools/test_constraints_compile.py` fails the build if the status enum
   grows a second value, if any property anywhere in the contract is
   class-ranged to `rkaf:ClosureClaim`, if a closure proof type appears, or if
   any fixture contains both a `rkaf:ClosureClaim` node and a
   `rkaf:RelationFinding` node. Two fixtures are exempt and named in the test —
   the negatives that prove mechanism 3 fires, one at depth 1 and one at
   depth 2. Naming them rather than pattern-matching means deleting either,
   which would let the shape be removed or its depth quietly re-bounded with no
   gate noticing, also fails the build. Types are compared by **expanded IRI**,
   so a fixture that spells `rkaf:ClosureClaim` out in full, or aliases it in
   an inline `@context`, does not slip past the scan.

Enabling closure means changing all four. That is the point: it must be a
reviewed contract change, never an accident.

**Which sinks carry which mechanism.** Mechanisms 1 and 2 are closed enums, so
every compiled target enforces them: JSON Schema, SHACL, Rust, TypeScript, and
Rego all reject a second status value and a closure proof type. Mechanism 4 is
a build-time gate over this repository. Mechanism 3 is **SHACL-path only** —
reachability is a statement about a path between nodes, and no JSON Schema,
Rust type, or Rego value set can express it. A consumer validating through
`rkaf-validate` (JSON Schema) alone therefore gets 1, 2, and 4 but not 3, and
must run the SHACL suite to get graph-level unreachability. The same holds for
the other hand-authored rules in `shapes/rkaf-shapes-analysis.ttl` — §2.1 and
§6.1 polarity absence, §4.3 proof binding, §5.5 outcome agreement — and for
the kernel's own cross-node `rkaf:ConceptAssignment` rules. It is an
architectural property of the layering, not a gap specific to this module.

### 6.5 No class-ranged edge into a disabled record

`constraints/analysis/semantics/l0-ranges.cue` deliberately declares no range
naming `rkaf:ClosureClaim`. Declaring one would give some property a
class-ranged edge **into** a disabled record, which is the first half of
consuming it as evidence.

Four analysis properties are unranged for a different reason — the range is
real but is not one class. `rkaf:proofInput` names *what a resolver read*,
which is an assertion, an artifact version, a fragment, a warrant, or an
attestation depending on the protocol; `rkaf:comparisonExpectedAssertion` and
`rkaf:findingComparedAssertion` may each be a `rkaf:RelationshipAssertion` or a
`rkaf:ValueAssertion`; and `rkaf:proofSupportingRecord` is the open *support*
slot — evidence, warrant, attestation, or another proof record. SHACL
`sh:class` names exactly one class, so a range on any of them would reject
conforming documents rather than describe them.

That `rkaf:proofSupportingRecord` is unranged is **load-bearing** for §6.4
mechanism 3, not incidental: because a proof record may cite another proof
record, a citation chain has no natural depth limit, which is why the
unreachability shape traverses these edges transitively instead of enumerating
a fixed number of hops.

---

## 7. Domain interpretation belongs to profiles

The generic layer emits **neutral** findings and **neutral** change events.

A regulatory profile may interpret a qualified finding as policy exclusion,
rescission, suspension, or another domain result — **only after its own
authority, applicability, deontic, source, and closure rules pass**. That
interpretation belongs to the profile's vocabulary, never to this module's.

Scientific, judicial, legislative, contractual, procurement, and oversight
profiles may interpret the same generic record differently, or not at all.

Two consequences are normative here:

* A consumer **MUST NOT** read `rkaf:relationChangeStage` as legal
  operativeness, or `rkaf:relationFindingKind` as legal effect. Neither
  vocabulary carries that meaning.
* A profile that wants such a reading **MUST** declare its own terms under
  `constraints/profiles/<profile>/` and state its own gate. It may depend on
  this module; this module never depends on it.

---

## 8. Conformance and wiring

| Concern | Where |
|---|---|
| Shape source | `constraints/analysis/*.cue` |
| Class ranges | `constraints/analysis/semantics/l0-ranges.cue` |
| Cross-node + absence rules | `shapes/rkaf-shapes-analysis.ttl` |
| JSON-LD term definitions | `context/rkaf-context.jsonld` |
| Vocabulary rows | `spec/rkaf-vocabulary.md`, "Document-analysis module" |
| Six compiled targets | `compiled/{json-schema,shacl,typescript,cue,rego}/analysis/` and `crates/rkaf-core/src/generated/analysis/` (Rust) |
| Rust re-exports | `rkaf_core::generated::analysis::*` |
| Fixture parity | `tools/constraints_parity.py` |
| Semantic tests | `AnalysisModuleTests` in `tools/test_constraints_compile.py` |

Everything in this module is covered by the same contract digest as the
kernel and the profiles: `tools/l0_mapping_audit.py` walks
`constraints/analysis/` alongside `constraints/core/` and
`constraints/profiles/`, so a consumer pinning a digest pins these shapes too.
