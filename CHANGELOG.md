# Changelog

All notable changes to Rulespec are documented in this file.

The format is loosely based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
adapted for a specification + shape + fixture project.

## Unreleased — US regulatory identifiers, L0 conformance, and rulemaking module

### Added

- **`rkaf:formspec-need`, a thirteenth `rkaf:artifactIdentifierScheme` value**
  (Core §4.1, "Formspec Need identity"). It denotes a Formspec Needs Document
  `url` + `need.id` pair — `<docUrl>#<needId>`, with an OPTIONAL `@<revision>`
  suffix pinning the wording a citation saw. A Need carries an integer
  `revision` covering its statement and grounding, so an assertion that pins
  the wording it read uses the suffixed form and one tracking the Need as
  currently worded omits it.

  The value buys exactly one thing: the **reverse edge**. A Formspec Need
  already cites a Rulespec assertion as evidence that the need is legitimate;
  registering the scheme makes the other direction first-class, so a compliance
  finding, an adopted policy position, or a regulator's determination can name
  the product commitment it is about. The same citation was always expressible
  under `rkaf:partner-defined`, but a Need citation was then
  indistinguishable from any other partner URI in federation queries. That
  indistinguishability was the whole cost of not registering it, and it is a
  cost only Rulespec could remove — the enum is closed and Rulespec owns it,
  so this is the one direction Formspec cannot reach from its own side.

  Precedent for naming an external scheme in the universal vocabulary is
  already thick: `rkaf:eli`, `rkaf:uslm`, `rkaf:aknt-eId`, `rkaf:doi`,
  `rkaf:isbn`, and `rkaf:issn` all do it. The charter's "universal ontology,
  not consumer-coupled" boundary is about SHAPES, and this adds none — it adds
  one value to a list whose entire purpose is naming external identifier
  grammars.

  **The kernel closes the value set but NOT a grammar over it**, and the
  distinction is worth stating because the proposal assumed otherwise.
  `rkaf:hasArtifactIdentifier` and `rkaf:artifactIdentifierScheme` are both
  1..*, so no positional correspondence exists between an identifier and a
  scheme; the per-scheme grammar idiom — a conditional keyed on the scheme
  value, as in `rkaf:us-cfr` and its five siblings — is available only where
  the identifier/scheme pair is scalar, which it is in the US rulemaking
  profile (rulemaking §5.2) and is not here. Closing a pattern over the
  1..* identifier list would force EVERY co-declared identifier on a
  multi-scheme Artifact to match the Needs grammar, which is wrong.

  So the tag is a DECLARATION of the grammar the producer claims, not a check
  on it. A producer asserting `rkaf:formspec-need` over a bare Needs Document
  URL is non-conforming — that URL is a current-state page, the class §4.1
  rejects for eCFR — but the non-conformance is a producer obligation in the
  same posture as §4.7.3 rule 3 and the `rkaf:extractionMethod` agreement in
  §2.4: a shape cannot require what it cannot see. §4.1's immutable-edition
  rule has never been mechanically checked for ANY scheme, so the negative
  fixture below fails on the missing declaration rather than on detected
  mutability.

  Coverage: one positive fixture (an assertion citing a product Need as its
  evidence subject, through the full Assertion → EvidenceBinding →
  SourceFragment → Artifact chain), one negative (a bare Needs Document URL
  carried with no scheme tag), two parity rows, and a
  `rkaf:ArtifactIdentifierScheme` entry in the vocabulary's closed-enum list,
  which had none.

  BREAKING under §3's reject-unrecognized-values rule: a consumer pinned to
  the twelve-value set rejects the thirteenth. It lands before the first
  release for exactly that reason.

  Proposal of record: `thoughts/specs/2026-07-27-formspec-need-identifier-scheme.md`
  (RS-P3), from the Formspec Needs Specification's Appendix C.
- **`rkaf:publishedInDocket` — document-to-docket membership, stated directly**
  (rulemaking §5, new §5.3;
  `constraints/profiles/us-rulemaking/us-regulatory-artifact.cue`). Domain
  `rkaf:Artifact`, range `rkaf:Docket`, 0..*, registered in the profile's
  `l0-ranges.cue` so the compiled SHACL carries `sh:class rkaf:Docket`.

  Federal Register metadata says which docket a document belongs to; the
  profile had no way to write it down. The only docket edge was
  `rkaf:hasDocket` on `rkaf:Proceeding`, so the fact was reachable only by
  routing through a Proceeding — which requires a producer to model
  proceedings at all. A producer holding a documents table and a dockets table
  and no proceedings model had two options, mint a surrogate Proceeding it had
  no evidence for or drop the fact, and both are worse than a direct edge.

  §5.3 states how the two edges relate: they are independent, not substitutes.
  `rkaf:hasDocket` is Proceeding → Docket (which containers a proceeding's
  activity lives in); `rkaf:publishedInDocket` is Artifact → Docket (which
  container THIS publication was filed under). Neither implies the other, a
  consumer MUST NOT infer either from the other, and the standing §3.2 rule
  that docket membership never establishes proceeding identity is unchanged. A
  producer with all three facts MAY emit all three edges, and MUST NOT mint a
  Docket node from a document alone — a Docket carries its own required
  identity.

  Purely additive: no existing document changes verdict. Coverage: one
  positive fixture with a parity row, one class-range negative gated through
  `tools/validate_negatives.py` (the route every `sh:class` negative takes,
  since JSON Schema cannot follow a reference).

  Driven by consumer evidence: `../spicy-regs/docs/evidence/`
  `single-document-rulespec-projection-2026-07-28/README.md`, finding G2 and
  judgment call J4.
- **`rkaf:deterministicExtraction`, a seventh `rkaf:assertionOrigin` value**
  (Core §2.4, "Deterministic origin"). The v0.1 set had six values and none of
  them meant "a deterministic parser or join produced this". A producer with
  machine-derived records had exactly two honest-adjacent options and both were
  wrong: `rkaf:aiSuggested` is false, and `rkaf:imported` says only that the
  record came from somewhere else. The real method then had to hang off
  `rkaf:hasExtractionProvenance`, which is OPTIONAL — so the one fact that
  distinguished the record was droppable, and no gate would notice.

  The value's meaning is narrow and stated: the record is a **mechanically
  reproducible derivation, not an interpretive judgment**. Re-running the named
  run over the same inputs MUST yield the same proposition, and nothing about
  the record claims anyone read the source and decided anything.

  `rkaf:hasExtractionProvenance` is REQUIRED when the origin is
  `rkaf:deterministicExtraction`, on every compiled target — the same
  conditional idiom the four AI-touched origins use for `rkaf:hasAILineage`,
  emitted as a Pattern-C `sh:or` guard in SHACL, an `if`/`then` in JSON Schema,
  and the generated Rust and TypeScript validators. A claim of reproducibility
  that names no run is not one. The referenced activity's
  `rkaf:extractionMethod` MUST be `rkaf:deterministicParse` or
  `rkaf:ruleBasedExtraction`; that half is a producer obligation rather than a
  mechanical check, because the activity may legally live in another document
  and no shape can require agreement it cannot see (the same posture as §4.7.3
  rule 3).

  The value is NOT AI-touched: it carries no `rkaf:hasAILineage` requirement,
  and the §3.5 inverse rule forbids lineage on it.
  `shapes/rkaf-shapes-pattern-c.ttl`'s message named two values that have not
  existed since v0.1 (`reviewClassified`, `systemDerived`) and is corrected in
  the same change. `rkaf:imported` is unchanged and undeprecated — it remains
  the right value for re-serializing another system's published records.

  Coverage: one positive fixture (assertion plus the materialized
  `rkaf:ExtractionActivity` it names), one negative (deterministic origin, no
  provenance edge), two parity rows, and a `rkaf:assertionOrigin` entry in the
  vocabulary's closed-enum list, which had none because the enum was inherited
  wholesale from v0.1. Core §3 now records that this is the one inherited enum
  v0.2 extends.

  BREAKING under §3's reject-unrecognized-values rule: a consumer pinned to the
  six-value set rejects the seventh. It lands before the first release for
  exactly that reason.

  Driven by consumer evidence: `../spicy-regs/docs/evidence/`
  `single-document-rulespec-projection-2026-07-28/README.md`, findings G3 and
  J1.
- **Machine-legible scope carve-outs in the L0 conformance-file format** —
  `excluded_terms` and `excluded_tables` (Conformance §0.1, "Scope
  carve-outs"). `terms_used` said what a declaration COVERED; what it
  deliberately left out lived in `notes` prose, which no tool reads. "We do not
  map concept assignments this quarter" and "we stopped mapping concept
  assignments last quarter" were therefore the same sentence to every gate, and
  a scope that SHRANK looked exactly like a scope that had always been that
  shape.

  `tools/l0_mapping_audit.py` now validates both keys. Each is optional and
  each, when present, is a non-empty duplicate-free list. Every
  `excluded_terms` entry MUST be a REGISTERED contract term and MUST NOT appear
  in `terms_used` or any mapping block: registration stops a carve-out naming a
  predicate the contract never had, which would read as coverage of something
  Rulespec does not define, and the not-mapped rule stops a declaration
  claiming a term twice, in and out at once. Every `excluded_tables` entry MUST
  NOT name a table any mapping block maps; tables are carrier-local strings, so
  they are checked against the mapping rather than against the contract.
  `MappingAudit` gained a `tables` field to carry that comparison.

  Absent means the implementation **said nothing** about what it left out. It
  is NOT read as the complement of `terms_used`, and no rule treats it that
  way, so no declaration written before the keys existed acquires a claim it
  never made — stated as a test rather than assumed
  (`test_a_declaration_without_carve_outs_is_unchanged`). What the keys buy is
  a diff: widening is a term leaving `excluded_terms` and appearing in
  `terms_used`, narrowing is the reverse, and each is one hunk in review
  instead of a paragraph nobody re-reads.

  Driven by consumer evidence: `../spicy-regs/docs/decisions.md`, entry
  "2026-07-27 — Contract-assumption validation results" (recorded
  simplification "machine-legible scope carve-outs (`excluded_terms:`) instead
  of freeform notes prose").
- **The carrier-local fragment URN, a second registered identity form for a
  cited region** (Core §4.2, §4.7.3). `rkaf:assignmentEvidence` has range
  `rkaf:SourceFragment`, and for a tabular carrier that range was a requirement
  to PUBLISH A TABLE rather than a requirement to know anything: a carrier
  holding an artifact identifier, a start offset, an end offset, and a digest
  of the selected text already holds every binding a fragment needs, yet could
  not claim the term without also maintaining and joining a fragments carrier.

  `rkaf:FragmentIdentityScheme` is the new closed two-value enum —
  `rkaf:published-fragment` (the cited IRI names a published
  `rkaf:SourceFragment` node) and `rkaf:carrier-local-fragment` (the cited IRI
  carries the bindings itself):

  ```text
  urn:rkaf:fragment:<percent-encoded artifact IRI>:<start>:<end>:sha256-<64 hex>
  ```

  Four grammar decisions are load-bearing. The interval is half-open
  `[start, end)` counted in Unicode CODE POINTS, and the scheme FIXES both the
  unit and `oa:TextPositionSelector` rather than declaring them per value — a
  derived identifier that left the unit to be guessed would reintroduce exactly
  the instability `rkaf:coordinateSystem` exists to remove. The artifact
  component is percent-encoded against the RFC 3986 unreserved set with
  uppercase hex triplets — the encoding `ENCODE_FOR_URI` produces — so it stays
  one unambiguous component in a colon-delimited URN and is comparable without
  a decoder. The digest is spelled `sha256-` so the component contributes no
  colon, and its scope is the selected text, not the Artifact. And
  `rkaf:sourceArtifactDigest` is deliberately NOT carried: the derived form
  pins the quoted text and not the document state around it, which is the one
  binding it gives up.

  `rkaf:assignmentEvidenceScheme` is REQUIRED whenever
  `rkaf:assignmentEvidence` is present, exactly as
  `rkaf:regulatoryIdentifierScheme` is required whenever
  `rkaf:hasRegulatoryIdentifier` is. Both identity forms are absolute IRIs, so
  the grammar a value must satisfy is not recoverable from the value and only
  the declaration says which one is being claimed. Declaring
  `rkaf:carrier-local-fragment` binds every cited value to the derived grammar
  on all six compiled targets.

  Two hand-authored shapes close what the compiled carrier cannot reach.
  `rkaf:ConceptAssignmentCarrierLocalEvidenceDeclaredShape` rejects a value in
  the `urn:rkaf:fragment:` namespace on a record that did not declare the
  derived scheme — registering the form has to mean the namespace is checked
  wherever it appears, not wherever a producer volunteers a declaration, and
  the rule is a per-VALUE conditional keyed on that value's own lexical form,
  which the projector's single-pattern list carrier cannot express.
  `rkaf:CarrierLocalFragmentUrnSourceAgreementShape` requires a materialized
  fragment to carry the `oa:hasSource` its own URN encodes; without it, every
  rule that leans on `oa:hasSource` — the same-Artifact evidence rule above all
  — could be reading a source the identifier contradicts.

  The class range STANDS. A carrier-local URN does not escape it; it satisfies
  it by construction, because the artifact, the offsets, the unit, the selector
  kind, and the region digest are all recoverable by parsing. At L0 that is the
  whole story and no fragments carrier is required. At L1–L4 the unit of
  validation is a graph, so a graph that cites the URN materializes the node it
  denotes — a mechanical expansion introducing no fact the URN did not already
  carry, shown end to end in
  `fixtures/conceptassignment-carrier-local-fragment-positive.jsonld`.

  Coverage: one positive fixture, four negatives (evidence with no scheme, a
  malformed derived URN, an undeclared namespace squat, and a materialized
  fragment whose `oa:hasSource` contradicts its URN), three new parity rows for
  the two negatives and the positive both compiled targets see, and three L0
  audit tests. `rkaf:assignmentEvidence` joins the scheme-bearing terms in
  `tools/l0_mapping_audit.py`, so an L0 mapping that mints evidence names the
  registered scheme it minted under, and §0.1 gains the worked mapping.

  Driven by consumer evidence: `../spicy-regs/docs/decisions.md`, entry
  "2026-07-27 — Contract-assumption validation results"
  ("`assignmentEvidence` stays unclaimed at L0 (SourceFragment range, no
  fragments carrier)", and the recorded simplification "letting
  `assignmentEvidence` cite a carrier-local fragment URN derived from
  offsets"). Offsets match `../spicy-regs/docs/ontology.md`, "Anchor
  semantics": Python Unicode code points over half-open `[start, end)`
  intervals, with the region digest covering
  `field_text[start_char:end_char]`.
- **A normative tabular attestation pattern for L0 carriers**
  (`spec/rkaf-conformance.md` §0.1, "Attestation as a table"). Core §3.1 and
  §4.7.3 put approval, rejection, and revocation in an `rkaf:Attestation`
  TARGETING the record — never in a field on it — and that rule is about the
  shape of the graph, not about the serialization. A Parquet, SQL, or CSV
  producer previously had to infer how to satisfy it and reasonably concluded
  that a per-row provenance block was close enough. The subsection states the
  pattern instead of leaving it to be derived: a separate attestations table,
  one row per Attestation node, the approved record's identity appearing only
  in the `rkaf:targets` join column, and six columns carrying attestor,
  attestor kind, targets (≥1), the closed decision, scope, and decision time.

  Four rules carry the meaning the table has to preserve. An `approved_by` or
  `approval_status` column on the approved record's own table is NOT an
  Attestation and MUST NOT be mapped to `rkaf:decision` or `rkaf:attestor` —
  it carries no attestor kind, no scope, no decision time, no revocation, and
  it cannot represent two attestors disagreeing about one record. Rejection is
  a ROW: `rkaf:rejected` and `rkaf:abstained` are members of the same closed
  set as `rkaf:approved`, an absent row means UNREVIEWED, and a carrier that
  expresses rejection by deleting a row has made rejection unrepresentable.
  Revocation is `rkaf:revokedAt` on the surviving row, not a delete. And
  `rkaf:targets` is many and points from the Attestation outward, so a
  single-target column is a narrowing of the pattern rather than the pattern.
  Inlining the six columns into the record's own table is permitted as a
  storage choice when the rows still project to separate Attestation nodes,
  and it caps the carrier at one attestation per record.

  The worked mapping is executable, not illustrative:
  `L0MappingAuditTests.test_the_normative_conformance_examples_are_executable`
  audits every `rkaf-l0-mapping` block in the conformance spec, so a term,
  domain, range, value kind, or enum target that drifts out of the contract
  fails the build instead of shipping as prose a consumer would copy.
  `fixtures/attestation-tabular-projection-positive.jsonld` is what two rows
  project to — one approval and one rejection over the same
  `rkaf:ConceptAssignment` — and is gated at L1, L2, and L3.

  Driven by consumer evidence: `../spicy-regs/docs/decisions.md`, entry
  "2026-07-27 — Contract-assumption validation results" ("approval requires a
  real contract-shaped `attestations` table (the per-row provenance block is
  not an Attestation; rejection must be recordable, never implied by
  omission)").
- **The document-analysis module** (`spec/rkaf-analysis.md`, CUE under
  `constraints/analysis/`) — generic, jurisdiction-free contracts for comparing
  relations across document versions. It is a THIRD tree beside the kernel and
  the profiles, compiling to the same six targets under an `analysis` sub-path
  (`compiled/<target>/analysis/`, `crates/rkaf-core/src/generated/analysis/`).
  The dependency direction is kernel <- analysis <- profiles, and every arrow
  is one-way: the kernel references no analysis shape and declares no analysis
  term, the module composes kernel shapes and mentions no jurisdiction, and a
  profile may depend on it. `AnalysisModuleTests` in
  `tools/test_constraints_compile.py` fails the build on any of those arrows
  reversing.

  It exists because comparison is a *process* over the kernel primitives, with
  its own policy versions, detector versions, resolver protocols, and
  snapshots. A consumer that stores and exchanges assertions does not
  automatically run comparisons and must not inherit a vocabulary it never
  produces.

  - `rkaf:RelationChangeEvent` (Analysis §2) — a source-stated
    `rkaf:relationAdoption`, `rkaf:relationRemoval`, `rkaf:relationSuspension`,
    or `rkaf:relationReplacement`, with a stage, the source's own event time,
    and an intended effect time held apart from `rkaf:assertedAt`. It composes
    `#AssertionEnvelope` and deliberately NOT `#AssertionProposition`, so
    **polarity is structurally absent**: "the Secretary removes the
    designation" does not assert the designation never held, and recording it
    as a denied assertion destroys the difference between *never true* and
    *stopped being true* — the difference every later comparison rests on.
    `rkaf:RelationChangeEventNoPolarityShape` rejects a record that carries the
    proposition predicates anyway, because the compiled carriers are open-world
    and absence in CUE is not enforcement. It is also not an
    `rkaf:LifecycleEvent`: that records what happened to a RESOURCE and seeds
    `CascadeClosureV1`; this records what a source says about a RELATION, may
    be merely proposed, and seeds nothing. Two conditionals: an
    `rkaf:changeEffective` stage REQUIRES an effective time (otherwise the
    record cannot be ordered against a baseline), and an
    `rkaf:relationReplacement` REQUIRES `rkaf:replacementRelationObject` (a
    replacement that does not name the successor is a removal wearing another
    label). `rkaf:changeStageUnclear` is a first-class value, not a gap.
  - `rkaf:RelationComparisonContext` (Analysis §3) — the immutable record of
    ONE comparison: artifact pair, baseline assertion, consumer, scope,
    evaluation time, policy version, detector and detector version, snapshot,
    and outcome. Changing any input produces a DIFFERENT comparison, not an
    update. `rkaf:comparisonOutcome` is closed over five values —
    `satisfied`, `affirmedDeniedDiscrepancy`, `conflict`, `notComparable`,
    `unknown` — where `notComparable` is a gate result and never a negative
    fact about a source, and `unknown` never becomes a failure. The outcome
    lives on the CONTEXT rather than on the finding so that "checked, nothing
    found" stays representable and distinguishable from "never checked"; only
    the discrepancy case also produces a finding. No AI model may produce a
    comparison outcome. `rkaf:comparisonProofRecord` is REQUIRED for every
    outcome except `unknown`.
  - `rkaf:ResolverProofRecord` and `rkaf:ResolverProofIssuer` (Analysis §4) —
    content-bound gate decisions. Six proof types, one per active resolver
    protocol; outcomes are the union of `rkaf:gatePass` / `gateFail` /
    `gateUnknown` and the six scope relations, because a scope comparator
    returns a RELATION and collapsing `rkaf:scopeOverlaps` onto pass/fail
    throws away the containment direction that decides whether an expectation
    applies at all. **An opaque string is not proof**: `rkaf:proofInput`
    (≥1), optional `rkaf:proofInputDigest`, a REQUIRED
    `rkaf:proofRecordDigest`, a REQUIRED `rkaf:proofComparisonContext`, a
    REQUIRED non-empty rationale, and both an evaluation time and a snapshot.
    Requiring `rkaf:proofComparisonContext` only DECLARES the binding, so
    `rkaf:ResolverProofComparisonBindingShape` enforces it across nodes: a
    context whose `rkaf:comparisonProofRecord` names a proof issued for some
    other comparison fails validation. That is the stale-pass replay the
    property exists to prevent, and `rkaf:proofRecordDigest` cannot see it —
    the proof record is unedited; the CITATION is what is false.
    The issuer is a separate node referenced by IRI, for the same reason
    Rulespec keeps one `rkaf:ConfidenceRecord`: a resolver version that changes
    must change in one place.
  - `rkaf:RelationFinding` (Analysis §5) — **neutral**. It says exactly one
    thing: under the named comparison, accepted assertions disagreed about the
    same relation. `rkaf:relationFindingKind` has ONE value,
    `rkaf:affirmedDeniedDiscrepancy`, because every other evidence situation
    has its own representation. It binds its comparison context, at least TWO
    compared assertions (one assertion cannot disagree with itself), and at
    least one proof record.
    `rkaf:RelationFindingContextOutcomeAgreementShape` closes the cross-node
    gap per-property SHACL cannot reach: a discrepancy finding may not be
    attached to a comparison that came back `satisfied`. The module declares NO
    legal-effect vocabulary at all — no policy exclusion, no rescission, no
    severity ladder — and `AnalysisModuleTests` fails the build if one appears.
    Domain interpretation belongs to a profile, after that profile's own
    authority, applicability, deontic, source, and closure rules pass.
- `rkaf:ClosureClaim` (Analysis §6) — **EXPERIMENTAL AND DISABLED**. A bounded
  claim that a named process completely enumerated a relation family in named
  regions of one Artifact version, under a declared profile version, with a
  content digest over the accepted member set. Closure is always local and
  revocable; `rkaf:closureRegion` is REQUIRED with ≥1 member so that a claim
  about a whole document is not expressible.

  It MUST NOT be produced or consumed as evidence for any finding. Four
  independent mechanisms enforce that, so no single edit can quietly enable it:
  (1) `rkaf:closureClaimStatus` is REQUIRED and closed over the single value
  `rkaf:closureClaimDisabled` on every compiled target, so enabling moves the
  contract digest and forces every pinned consumer to re-accept; (2)
  `#ResolverProofType` declares no closure, coverage, or lineage proof type, so
  a closure decision cannot be minted and cited; (3)
  `rkaf:ClosureClaimNotFindingEvidenceShape` fails any graph in which a
  `rkaf:RelationFinding` REACHES a claim — directly, or TRANSITIVELY at any
  depth through its context, the proofs it or its context cite, the assertions
  it compared, and the records those lean on — because "disabled" must mean
  unreachable rather than un-named, and not "un-named at distance one" either:
  `rkaf:proofSupportingRecord` is unranged and a proof may cite another proof,
  so any fixed hop count is walked around by interposing one more record; and
  (4) `AnalysisModuleTests` fails the build if the status enum grows a value,
  if any property in any range registry is class-ranged to
  `rkaf:ClosureClaim`, if a closure proof type appears, if an omission finding
  kind appears, or if any fixture other than the two negatives proving the
  shape fires (at depth 1 and depth 2) contains both a ClosureClaim and a
  RelationFinding — matched on the EXPANDED type IRI, so an expanded or
  aliased spelling cannot slip past the scan. Mechanisms 1, 2, and 4 are
  cross-target; mechanism 3 is SHACL-path only, because reachability is a
  statement about a path between nodes that no JSON Schema, Rust type, or Rego
  value set can express (Analysis §6.4).

  `rkaf:ClosureClaimNoPolarityShape` additionally rejects a claim carrying
  `rkaf:assertionPolarity` or the proposition predicates, mirroring
  `rkaf:RelationChangeEventNoPolarityShape`: without it a DISABLED record could
  be published as a denied assertion about a triple.

  There is deliberately no `expected_relation_not_observed` — not as a
  comparison outcome, not as a finding kind. Omission is only meaningful inside
  a proven closure boundary; outside one, silence is `rkaf:comparisonUnknown`.
  Closure stays disabled until a frozen real dataset measures closure precision
  and recall separately from extraction.
- `rkaf:ConceptScheme` (Core §4.7.1) — one facet, one controlled category
  system, compatible with `skos:ConceptScheme`. SKOS owns scheme semantics and
  this shape restates none of them; it adds the two things SKOS leaves open and
  Rulespec must check: `rkaf:schemeFacet` (WHICH facet the scheme controls, as a
  producer- or profile-owned IRI, deliberately not a kernel enum) and an
  ownership disjunction — a scheme is governed by a registry or defined in a
  workspace scope, the same seam `RegisteredConcept` / `LocalConcept` already
  draw for concepts.
- `rkaf:ConceptAssignment` (Core §4.7.3) — an evidence-bearing, versioned record
  that one Artifact or one SourceFragment is associated with one concept. It
  composes `#AssertionEnvelope`, so construction origin, AI lineage, extraction
  provenance, source claimant, confidence, consumer disposition, supersession,
  and assertion time have one home each rather than a parallel set of
  assignment-shaped copies. Approval stays an `rkaf:Attestation` targeting the
  record. `#AssertionProposition` is deliberately NOT composed: an assignment's
  proposition is the subject-concept pair, and composing the triple core would
  demand an `rkaf:assertsPredicate` every assignment fills with a placeholder.

  Four conditionals carry the directional rule the carrier evidence turns on: a
  `rkaf:SourceFragment` subject REQUIRES `rkaf:assignmentEvidence`; a
  `rkaf:directAssignment` REQUIRES the same; a `rkaf:derivedAssignment`
  REQUIRES `rkaf:supportingAssignment`; and naming supporting assignments
  REQUIRES `rkaf:assignmentPolicyVersion`. Segment evidence may support a
  document tag; a document tag may shortlist candidates for a segment and can
  never prove one. Without that asymmetry one mistaken document tag propagates
  to every segment and the segments then confirm the document.

  Two hand-authored shapes in `shapes/rkaf-shapes-core.ttl` close what those
  per-property conditionals cannot reach.
  `rkaf:ConceptAssignmentFragmentSubjectEvidenceShape` re-keys the evidence
  obligation on the subject node's own `rdf:type`: the compiled conditional
  fires on the self-declared `rkaf:assignmentSubjectType` literal, so
  relabelling one segment assignment `rkaf:Artifact` bought the document-tag
  treatment for a fragment subject and let the document tag prove the section
  tag. `rkaf:ConceptAssignmentEvidenceSameArtifactShape` requires every cited
  evidence fragment to name the same `oa:hasSource` Artifact as the subject
  fragment; the class range alone was satisfied by one fragment of any
  document, which would have let a single unrelated preamble carry every
  segment tag in a corpus. That the cited region is the subject's OWN region
  needs selector arithmetic across coordinate systems, so Core §4.7.3 states it
  as a producer obligation rather than claiming it is checked.
- Artifact version identity enforcement (Core §4.1). `rkaf:hasContentDigest`
  (lowercase `sha256:<64 hex>`) and `rkaf:versionLineageEvidence` (range
  `rkaf:SourceFragment`), plus three conditionals that make the existing
  prohibition checkable instead of advisory: declaring `dcterms:isVersionOf` or
  `prov:wasRevisionOf` REQUIRES cited lineage evidence, and cited lineage
  REQUIRES a content digest. Neither rule asserts a lineage claim is true; they
  make it resolve to exact coordinates in an actual source, held by a state that
  is addressable by content — which a shared title, a RIN, an embedding score,
  or a retrieval rank never is. `dcterms:hasFormat` / `isFormatOf` are
  deliberately NOT guarded: two renderings of one state are not a version claim.

  `dcterms:isVersionOf` keeps NO class range, and a test pins that absence.
  Rulespec still declines to mint a universal Work / Expression / Manifestation
  hierarchy; a range here would be that hierarchy arriving through the range
  registry instead of through the spec.
- SourceFragment identity bindings (Core §4.2). `oa:hasSource` is now an
  absolute IRI with range `rkaf:Artifact` — it was a bare `string`, so a
  fragment could name a workspace, a label, or nothing resolvable and every
  target accepted it. Added `rkaf:sourceArtifactDigest` (which STATE of the
  Artifact the coordinates address) and `rkaf:fragmentContentDigest` (the exact
  region text they select), both `sha256:<64 hex>`.
- `oa:TextPositionSelector` as a typed selector contract, with the OA offset
  predicates `oa:start` / `oa:end` (xsd:integer, >= 0), an ordering rule that
  rejects an inverted range, and a REQUIRED `rkaf:coordinateSystem` from a
  closed six-value set. An offset with no declared unit is not a coordinate:
  `4180` names three different positions depending on whether the producer
  counted Unicode code points, UTF-8 bytes, or UTF-16 code units, and the three
  diverge at the first non-ASCII character. The unit sits on the SELECTOR, not
  the fragment, because a fragment carrying both a quote and a position selector
  has exactly one coordinate system and it is the position selector's.

  `rkaf:SourceFragmentSelectorKindAgreementShape`
  (`shapes/rkaf-shapes-core.ttl`) binds the fragment's declared
  `rkaf:selectorKind` to a selector actually typed `oa:TextPositionSelector`.
  Without it the whole selector contract was opt-in: the offset and unit rules
  fire only on a node the producer voluntarily typed, so a dangling selector
  IRI, or an untyped node carrying `oa:start` / `oa:end` and no unit, passed
  every target. Scoped to the position selector, because that is the kind whose
  reproducibility Rulespec constrains; the bare-value forms other kinds use
  stay legal.
- Both OA selector classes are now registered with the L2 dispatchers. Core
  §4.2 compiles shapes for `oa:TextQuoteSelector` and
  `oa:TextPositionSelector`, but `crates/rkaf-validate/build.rs` and
  `tools/conformance_lib.py` bound only `rkaf:`-prefixed `@type`s, so neither
  class was ever embedded: `rkaf-validate` returned exit 0 on an inverted range
  and on offsets with no declared unit, and `tools/conformance_report.py`
  reported those negatives as L2 = pass. `oa:TextPositionSelector` is also the
  only class in the repo with a NUMERIC `x-rkaf-order`, so the numeric branch of
  the ordering check was unreachable in `rkaf-validate` — the entry below was
  true of `tools/constraints_parity.py` alone. Both dispatchers now walk a
  shared prefix set, and `crates/rkaf-validate-cli/tests/cli_smoke.rs` pins the
  exit code. Residual, stated in Core §4.2: both dispatchers walk the root and
  the top-level `@graph` only, so an INLINE selector is not an L2 target.
- `rkaf:ValueAssertion`, the second proposition-bearing Assertion
  specialization, whose object is a typed literal rather than an IRI. Core
  §2.1 deferred typed-literal objects pending "a coordinated JSON-LD, CUE, and
  projector migration"; §2.2 is that migration and lifts the deferral. The
  object is a JSON-LD value object (`@value` lexical form plus `@type`
  datatype) closed over the eleven-member `rkaf:ValueDatatype` set, and the
  same set is enforced by every target: JSON Schema `enum`, one SHACL
  `sh:datatype` alternative per member under `sh:nodeKind sh:Literal`,
  `crate::TypedLiteral<ValueDatatype>` in Rust, and a generated membership
  check in TypeScript.
- Value-object support in the constraint compiler. An inline nested struct
  declaring `@value` — JSON-LD's own definition of a value object — projects
  to all six targets, with the value object emitted CLOSED on every target
  (`additionalProperties: false` in JSON Schema, `deny_unknown_fields` on
  `TypedLiteral`, and in TypeScript an undeclared JSON-LD member typed `never`
  plus a generated member check in `validate<Shape>`) so a language-tagged
  literal is rejected everywhere `cue vet` rejects it. A value object whose
  `@type` is not a closed enum is a `CompileError` rather than a silently
  weaker artifact.

  A nested struct that is NOT a value object is unchanged: it keeps the
  pre-existing lossy hoist (inner fields flattened onto the outer shape, outer
  property typed as a plain string), which the adversarial corpus is authored
  against. That hoist is a known degradation, not a guardrail — an inner
  `"@type"` overwrites the outer shape's class discriminator, so a schema
  minted from such a source would validate the wrong class. Tightening it
  belongs to whichever change re-authors those sources.
- `rkaf:SourceClaimant` (Core §2.4) — who the SOURCE says asserts a
  proposition, with a closed `rkaf:claimantAttribution` set, separate verbatim
  claimant text and resolved identity, and attribution fragments distinct from
  the assertion's own evidence. A claimant named in the source must carry the
  naming text.
- `rkaf:ExtractionActivity` (Core §2.4) — which run produced an assertion
  candidate. Provider-neutral by construction: every field is a Rulespec-owned
  IRI, a version string, or an opaque `sha256:` digest, including a single
  `rkaf:requestContractDigest` over the whole secret-free request contract. It
  requires no approver, so an unreviewed model candidate is representable; a
  model extraction must name its model.
- Assertion envelope edges for the separated records: `rkaf:hasSourceClaimant`,
  `rkaf:hasExtractionProvenance`, `rkaf:hasConfidence`, `rkaf:hasAccessScope`,
  `rkaf:supersedesAssertion`, and `rkaf:assertedAt`. All optional and additive.

### Changed

- **Core §2.1 decides the direct-edge / reified-assertion pair** ("Projected
  edges and reified assertions"). The same edge could be stated twice — as a
  profile predicate on a node and as a `rkaf:RelationshipAssertion` over the
  same triple — and the contract said nothing about when a producer should
  emit which or how a consumer reconciles them, so a provenance-stripping
  projection double-counted. Both forms stay; neither is deprecated. The
  decision fixes their roles:

  - a **direct edge is the queryable projection** — traversable by a consumer
    that does not reason over assertions, carrying no provenance, polarity,
    confidence, or disposition;
  - a **`rkaf:RelationshipAssertion` is the provenance-bearing source of
    truth** — the record every primitive keyed to an assertion IRI points at.

  Deduplication is the rule that makes emitting both safe: where a direct
  edge's subject, predicate, and object equal an assertion's, the edge IS that
  assertion's projection, and a consumer MUST treat the pair as one statement —
  never as two independent sources agreeing.

  Producer obligations: a producer emitting a `rkaf:affirmed` assertion whose
  triple a profile predicate can express SHOULD also emit that edge, and MUST
  NOT emit it for a `rkaf:denied`, superseded, or retracted assertion — a plain
  edge carries no polarity, so projecting a denial asserts its opposite. A
  graph whose direct edge is denied by a co-present assertion is
  non-conforming; the assertion wins. Consumer obligation: a direct edge with
  no matching assertion is legal and unbacked — a consumer MUST NOT assume an
  assertion exists elsewhere and MUST NOT manufacture one.

  Stated as producer obligations and consumer rules rather than shapes, and
  the spec says why: no shape can require a producer to project an edge it
  chose not to project, and matching a direct predicate against a reified
  triple means comparing a predicate IRI to a property VALUE, which SHACL does
  not express. `spec/rkaf-rulemaking.md` §5.3 and §8 point at the rule instead
  of restating it. Documentation only; the contract digest is unchanged.

  Driven by consumer evidence: `../spicy-regs/docs/evidence/`
  `single-document-rulespec-projection-2026-07-28/README.md`, finding G5 — that
  projection states proceeding→docket twice, as `rkaf:hasDocket` and as a
  reified assertion, with nothing telling a consumer they are one fact.
- **`rkaf:requestContractDigest` is REQUIRED for `rkaf:modelExtraction` and
  OPTIONAL for the other four methods** (Core §2.4,
  `constraints/core/extraction-activity.cue`). The field presumes a
  REQUEST-SHAPED extraction — a run that sent instructions, a schema, and a
  configuration somewhere and got an answer back. A deterministic table parse
  sends nothing and has no such contract, so a universal requirement left a
  producer exactly one conforming move: define an envelope, hash it, cite the
  result. That yields a real digest naming a contract the run never published,
  which is worse than an absent field, and it is what a real consumer had to do.

  Expressed as a conditional rather than made optional everywhere, using the
  same `if extractionMethod == …` idiom the shape already used for
  `rkaf:extractionModelRef` — so the guard that requires a model call to name
  its model now requires it to name its contract too, in one branch. The other
  four methods MAY still carry the digest and SHOULD whenever the run genuinely
  issued a contract (`rkaf:ruleBasedExtraction` over a versioned published
  ruleset is the common case). When present under any method it MUST name a
  contract the run actually issued; a digest over an envelope minted to satisfy
  the field is non-conforming. Consumers MUST NOT read an absent digest as an
  unaudited run — for a deterministic method the reproduction handles are
  `rkaf:inputDigest`, `rkaf:extractedBy`, and `rkaf:extractorVersion`.

  `fixtures/negatives/extraction-activity-missing-request-contract-digest-negative.jsonld`
  was re-pointed from a deterministic parse to a model call, because that is
  now where the defect lives; it keeps its name and its FAIL verdict.
  `fixtures/extractionactivity-deterministic-no-request-contract-positive.jsonld`
  is the new capability, gated at L1–L3 with a parity row.

  BREAKING only in the permissive direction for producers. Breaking for a
  consumer that treated the digest as always-present on an `ExtractionActivity`.

  Driven by consumer evidence: `../spicy-regs/docs/evidence/`
  `single-document-rulespec-projection-2026-07-28/README.md`, findings J2 and
  G4.
- **The SHACL emitter carries every requirement of a conditional, not the
  first** (`tools/constraints_compile.py`). A `ConditionalBranch` with two
  `then_require` entries compiled to a Pattern-C `sh:or` naming only
  `then_require[0]`; the JSON Schema and TypeScript legs already emitted both,
  so the divergence was SHACL-only. No conditional in the tree had ever
  required more than one property, so nothing exercised it until
  `rkaf:modelExtraction` came to require both a model reference and a request
  digest — at which point `tools/constraints_parity.py` reported the negative
  fixture passing SHACL and failing JSON Schema. This is the silent-pass class
  `constraints/adversarial/conditional-silent-pass.cue` is about, one layer
  down: the shape file reads as a correct conditional while enforcing a strict
  subset of the source. Each requirement is now its own `sh:property` inside
  the same branch node, so the branch holds only when all of them hold.
  `ShapeCompositionTests::test_a_conditional_requiring_two_properties_reaches_shacl_intact`
  is the regression, and it fails on the old emitter. Every single-requirement
  guard in the tree compiles byte-identically.
- **Core §2.4 states the `prov:wasDerivedFrom` class range in prose.** The
  declared range has been `prov:Entity` since the range registry shipped
  (`constraints/semantics/l0-ranges.cue`), and every compiled shape carrying
  the edge enforces it with `sh:class prov:Entity`
  (`compiled/shacl/core/{assertion,relationship-assertion,concept-assignment}.ttl`).
  §2.4 presented the field as a plain IRI list and said nothing about the
  class, so the requirement was reachable only by reading generated Turtle. The
  new **Derivation** paragraph says it normatively: a producer citing a
  derivation source at L1–L4 MUST materialize that source as a node typed
  `prov:Entity` in the same document, an IRI described nowhere stays legal as a
  cross-document reference, and the typed node may carry nothing but `@id` and
  `@type`. Documentation only — no shape, fixture, or generated artifact moved,
  and the contract digest is unchanged.

  Driven by consumer evidence: `../spicy-regs/docs/evidence/`
  `single-document-rulespec-projection-2026-07-28/README.md`, finding G1 — the
  single authoring failure in that projection was six `sh:class prov:Entity`
  violations, mechanical to fix and unpredictable from the spec.
- **Ten temporal terms now expand as `xsd:dateTime` instead of as plain
  strings** (`context/rkaf-context.jsonld`). `rkaf:attestedAt`,
  `rkaf:revokedAt`, `rkaf:adoptedAt`, `rkaf:openedAt`, `rkaf:closedAt`,
  `rkaf:declaredAt`, `rkaf:resolvedAt`, `rkaf:validatedAt`,
  `rkaf:retroactiveFrom`, and `rkaf:sunsetAt` are all declared `// xsd:dateTime`
  in their CUE shapes and had no term definition in the context at all, so the
  declared datatype never reached the wire. An `rkaf:Attestation`'s time
  arrived as an untyped literal while `rkaf:assertedAt` — one record away, the
  same temporal semantics — arrived typed, and nothing objected: the compiled
  attestation shape checks cardinality, not datatype
  (`compiled/shacl/core/attestation.ttl`). `rkaf:rationale` joins them as
  `xsd:string`, matching `rkaf:claimantText` and the other free-text terms.

  `context/README.md` had listed the datatype convention as *not gated* and
  named these ten as the standing deviations. It is a gate now:
  `TypedValueCarrierTests::test_every_xsd_annotated_term_carries_that_datatype_in_the_context`
  reads the `// xsd:…` annotation off every `constraints/**/*.cue` declaration
  and requires the matching coercion, so an annotated term cannot lose its
  datatype again. The remaining 20 CUE property terms with no context entry are
  reference- and string-valued and stay under the by-hand convention; adding
  `@id` coercions to them would change what their values MEAN on the wire and
  belongs to whichever change re-authors those shapes.

  BREAKING for a consumer that string-matched these values out of expanded RDF:
  they now arrive as typed literals. No producer change is required — the
  lexical form is untouched, and every in-tree fixture round-trips unchanged.

  Driven by consumer evidence: `../spicy-regs/docs/evidence/`
  `single-document-rulespec-projection-2026-07-28/README.md`, finding G6.
- **`enum_map` now covers closed enums registered with `@type: @id`**
  (`tools/l0_mapping_audit.py`, Conformance §0.1). The audit accepted
  `enum_map` only on `value_kind: vocab`, which left `rkaf:decision` and
  `rkaf:assertionOrigin` — closed sets the context coerces with `@id` rather
  than `@vocab` — with no way to declare closed-enum discipline at all. Their
  only route was a transform, whose output the audit checks for IRI SHAPE and
  never for membership, so a typo in the template minted an unregistered
  decision and passed. Both coercions put the value on the wire as an IRI;
  `enum_map` is now valid for either, and an `iri` mapping that declares one
  no longer also has to declare a transform. `enum_map` remains closed to
  terms with no registered enum, so an open IRI property cannot use it to
  dodge the transform requirement.
- **`rkaf:AILineage` no longer requires `rkaf:humanApprover`** (Core §2.4,
  §5.3). This resolves the open conflict recorded in the previous entry. The
  AI-touched `rkaf:assertionOrigin` values still REQUIRE `rkaf:hasAILineage`,
  and that requirement is now satisfied by an approver-free lineage — so
  `rkaf:aiSuggested`, whose entire meaning is *unreviewed candidate*, no longer
  forces the producer to name a reviewer who does not exist. Approval is where
  it always belonged: an `rkaf:Attestation` targeting the assertion.

  The shape still refuses a review attributed to nobody. When
  `rkaf:humanRationale` is present, `rkaf:humanApprover` is REQUIRED: a stated
  human reason with no human named reads as approved while leaving no one
  accountable, which is a worse record than an honest unreviewed candidate.

  Two negative fixtures were affected, and no coverage was lost.
  `fixtures/negatives/a-i-lineage-missing-human-approver-negative.jsonld` keeps
  its verdict and its name — it states a rationale, so it now fails the rule
  above. `fixtures/ailineage-missing-approver-negative.jsonld` no longer
  described a defect and was replaced by
  `fixtures/ailineage-malformed-input-context-hash-negative.jsonld`.
- `rkaf:inputContextHash` is now a digest rather than a free string: lowercase
  `sha256:<64 hex>`, the lexical contract `rkaf:requestContractDigest` and
  `rkaf:inputDigest` already use. A hash that cannot be compared across runs
  makes a derivation unreplayable, which is the only thing the field is for.
  `fixtures/modelcard-minimal-positive.jsonld` carried a 32-hex placeholder and
  was corrected; its verdict is unchanged.
- `skos:inScheme` is REQUIRED (1) on `rkaf:RegisteredConcept` and
  `rkaf:LocalConcept`, and `skos:definition` is REQUIRED when
  `rkaf:conceptStatus` is `rkaf:promoted`. A facet-free concept is exactly the
  term that later merges with a same-spelled term from another facet, and a
  promoted concept with no definition records the outcome of a review whose
  central artifact was never written down. Rulespec declares no class range over
  `skos:inScheme` — the scheme may be an external `skos:ConceptScheme`.
- `#SkosMappingPredicate` gains SKOS's three remaining mapping properties:
  `skos:broadMatch`, `skos:narrowMatch`, `skos:relatedMatch`. SKOS separates
  in-scheme semantic relations (`broader` / `narrower` / `related`) from the
  cross-scheme mapping properties, and the earlier set carried only the former,
  so aligning to an external thesaurus meant borrowing an in-scheme relation and
  misstating the alignment. Purely additive: no value was removed and every
  existing mapping stays valid. `shapes/rkaf-shapes-conceptregistry.ttl` mirrors
  the set, and a test pins the two lists identical — SHACL is conjunctive, so a
  value in one and not the other is rejected outright.
- Ordered-field enforcement now compares numbers as numbers, in every gate that
  reads `x-rkaf-order`. The keyword is the type-agnostic carrier for a CUE
  ordering branch, but `tools/constraints_parity.py` and `rkaf-validate`
  compared string values only, so date intervals were enforced and every numeric
  interval was silently skipped — leaving those targets weaker than the
  `sh:lessThanOrEquals` compiled from the same source line. Mixed types are
  still not compared; inventing an order across JSON types would produce a
  verdict the CUE never stated.

  `tools/conformance_report.py` did not read the keyword at all. It is a JSON
  Schema EXTENSION, so `jsonschema` ignores it and the reporter's L2 column read
  `pass` on an inverted pair that both other gates rejected. The reporter now
  applies it, and the single Python implementation lives in
  `tools/conformance_lib.violates_order` rather than in a private copy per
  caller; `crates/rkaf-validate/src/lib.rs` carries the Rust twin.
- `shapes/rkaf-shapes-studio-promotions.ttl` relaxes its hand-authored
  `rkaf:humanApprover` row to `sh:maxCount 1` plus the node-kind check. It
  merges by IRI with the compiled `rkaf:AILineageShape`, so leaving `sh:minCount
  1` there would have kept the removed requirement in force through the back
  door.
- `constraints/core/assertion.cue` now names the two halves of an assertion
  separately: `#AssertionProposition` (subject, predicate, polarity —
  immutable) and `#ConsumerDisposition` (usage eligibility, consumer lifecycle
  state, access scope — mutable and consumer-scoped). The envelope composes
  the disposition and never the proposition; both proposition-bearing forms
  compose both. Core §2.3 states the rule normatively. No wire change: the
  compiled targets carry the same fields they carried before.
- `#AssertionPolarity` moved from `relationship-assertion.cue` to
  `assertion.cue`, beside the proposition core it belongs to, because
  `rkaf:ValueAssertion` closes over the same two values. The definition name
  and its values are unchanged.

### Added — US regulatory identifiers, L0 conformance, and the rulemaking module

- Six closed US regulatory-identifier values for CFR, U.S. Code, Federal
  Register document, regulations.gov document/comment, public-law, and
  Executive-order citations. They are separate from immutable Artifact
  identity and carry CUE-generated normalization constraints.
- Dedicated `Proceeding` and mutable `Docket` identity predicates and schemes,
  with explicit `hasDocket` links so a docket cannot stand in for a
  proceeding.
- Positive and negative normalization fixtures for every new scheme,
  including docket, document, malformed identifier, malformed date, and
  reversed-interval cases.
- An L0 Vocabulary conformance path for non-JSON-LD carriers. Its normative
  `yaml rkaf-l0-mapping` format pins the exact Rulespec contract, declares
  subject/domain/range/direction/value semantics, and executes transform
  samples through `tools/l0_mapping_audit.py`.
- The Experimental `spec/rkaf-rulemaking.md` module with CUE-generated Docket,
  Proceeding, and CommentPeriod types, proceeding-stage lifecycle values,
  versioned CFR targets, published-document links, and authority-chain
  composition.
- A curated EPA RIN `2060-AV16` reference corpus with source provenance,
  validation-result metadata, and a dedicated validation gate.
- A durable `RegulatoryAgendaItem` identified by each RIN, an editioned
  `RegulatoryAgendaObservation`, and a provenance-bearing qualified
  agenda-item-to-Proceeding relationship. RIN equality never establishes
  Proceeding identity.
- FOAF `primaryTopic` and the scoped DCAT 3 qualified-relation pattern as
  public-ontology seams for document-to-subject and qualified relationship
  modeling.
- Dublin Core `isVersionOf` and PROV-O `wasRevisionOf` on immutable Artifacts,
  with a cross-target lineage fixture. The generic core composes public version
  lineage instead of minting Work or Expression classes.

### Changed

- Incorporated the Spicy Regs full-corpus findings: proceeding stage is
  optional when unknown, CommentPeriod requires qualified PROV-O evidence, and
  Federal Register source values outside `YYYY-NNNNN` use a normative
  permanent-publication URL fallback without a false `rkaf:us-frdoc` claim.
- Incorporated the 2026-07-23 post-implementation architecture review: a
  normative cross-posting pattern (`spec/rkaf-rulemaking.md` §4.1 and core
  §4.1) — one Artifact per source posting, at most one regulatory-identifier
  pair each, postings linked with `dcterms:hasFormat`/`isFormatOf`; a
  `rkaf:us-regsgov` legacy-identifier fallback mirroring the `us-frdoc` rule;
  a documented rationale for the unprefixed `proceedingStage` value IRIs; and
  an explicit §8 agenda for the condition-2 independent review.
- Extended the US rulemaking reference corpus to exercise all seven US
  regulatory schemes: the cross-posted regulations.gov posting of the proposed
  rule (`rkaf:us-regsgov`), Public Law 91-604 in the authority chain
  (`rkaf:us-pl`), and referenced Executive Order 13990 (`rkaf:us-eo`).
- `tools/compile_all.sh` now runs `tools/repin_contract_digest.py`, so the
  contract digests embedded in the L0 conformance example and the corpus
  manifest re-pin with the compile instead of by hand-edited follow-up
  commits.
- Replaced the temporary RIN-as-Proceeding-evidence model. Proceedings now use
  independent partner or official-registry identity; Unified Agenda stage,
  priority, target, and authority context remains on the editioned observation.
- Added a legacy migration from RIN-identified Proceedings and
  `hasProceedingEvidenceIdentifier` to agenda-item identity plus
  evidence-qualified relationships.
- Completed a local paired Spicy Regs corpus exercise and deterministic rerun.
  The candidate remains unpublished and Experimental pending a release,
  refreshed conformance declarations, and non-originating consumer review.
- Moved the twelve `rkaf:proceeding*` lifecycle kinds out of the universal
  kernel into the US rulemaking profile
  (`constraints/profiles/us-rulemaking/us-lifecycle-event.cue`). There is still
  ONE `rkaf:LifecycleEvent` class and one `rkaf:lifecycleEventKind` property:
  the kernel declares the ten universal kinds and leaves its carriers open on
  that property, the profile declares its twelve, and the compiler assembles
  the closed 22-value union at build time onto a profile shape that composes
  the kernel one. Conformance, `rkaf-validate`, and the SHACL suite bind the
  composed artifact, so every previously enforced kind is still enforced and no
  GATED fixture verdict changed (see the ungated L3 change noted below).
  Consumer surface: `rkaf_core::LifecycleEvent`'s
  `lifecycle_event_kind` field is now `String` (open, matching the kernel
  carrier) and the closed 22-value type is `rkaf_core::ComposedLifecycleEventKind`,
  carried by the new `rkaf_core::USLifecycleEvent`. TypeScript gains
  `ComposedLifecycleEventKind` / `USProceedingLifecycleEventKind` in
  `compiled/typescript/profiles/us-rulemaking/us-lifecycle-event.ts`;
  `LifecycleEventKind` in the kernel module is now the ten universal kinds.
- Compiled SHACL now closes enums that a DIFFERENT CUE file declares:
  `target_shacl()` takes the same cross-file enum registry the
  json-schema/rust/typescript emitters take. This closes adversarial-review
  finding F2 (a profile overlay silently dropped the kernel's `sh:in`) and
  retires the `KNOWN_DROPPED_SHACL_ENUM_CLOSURES` pin.

  The scope is wider than the one overlay that motivated it. Threading the
  registry adds **16 `sh:in` closures across 10 compiled shapes — 15 of them on
  KERNEL shapes**, only one on the profile overlay
  (`rkaf:artifactIdentifierScheme` on
  `compiled/shacl/profiles/us-rulemaking/us-regulatory-artifact.ttl`). The
  kernel shapes that gained a closure, and the properties they now constrain:

  | Compiled shape | Property now closed |
  |---|---|
  | `core/assertion.ttl` | `rkaf:usageEligibility`, `rkaf:consumerLifecycleState` |
  | `core/bridge-consumer-registration.ttl` | `rkaf:capabilityCap`, `rkaf:supportedAuthorityKinds` |
  | `core/bridge-validation-result.ttl` | `rkaf:chainTerminusKind`, `rkaf:detectedIssues`, `rkaf:effectiveUsageEligibility` |
  | `core/concept-mapping.ttl` | `rkaf:usageEligibility` |
  | `core/concept-resolution-result.ttl` | `rkaf:usageCeiling` |
  | `core/consumer-effective-declaration.ttl` | `rkaf:declaredEffective` |
  | `core/local-adoption.ttl` | `rkaf:usageEligibility` |
  | `core/point-in-time-exception.ttl` | `rkaf:evaluationAnchor` |
  | `core/relationship-assertion.ttl` | `rkaf:assertionOrigin`, `rkaf:usageEligibility`, `rkaf:consumerLifecycleState` |

  Every one of these was already closed in the CUE source and in the JSON
  Schema, Rust, and TypeScript targets; SHACL alone was shipping them open.
  L3 is therefore STRICTER for these properties than it was before this
  release. Data that relied on SHACL accepting an out-of-enum value on any of
  them will now fail L3.
- `context/rkaf-context.jsonld` — added the missing `@type` coercions on
  `rkaf:capabilityCap` (`@id`, matching its `rkaf:usageEligibility` sibling)
  and `rkaf:lifecycleState` (`@vocab`). Both are enum-valued terms whose
  values reached RDF as plain literals, which no IRI-valued `sh:in` can match.

  This repaired one fixture verdict, in a column that is reported but NOT
  gated: `fixtures/behavior/concept-resolution-publication-blocking.jsonld`
  goes **L3 fail -> pass**. Its `rkaf:lifecycleState: "rkaf:approved"` values
  previously reached RDF as plain literals and could not match the IRI-valued
  `sh:in` on `core/concept-mapping.ttl`; with the `@vocab` coercion they arrive
  as IRIs and the shape is satisfied. `tools/conformance_report.py` does not
  gate L3 for `behavior` fixtures (their `rkaf:input` graph may carry
  declarative stubs), so this moved no divergence count — the fixture was
  green before and is green now, and the note explaining the permitted L3
  failure has simply disappeared. It is recorded here because a verdict that
  changes without a gate noticing is exactly the kind of change a reader of
  this file should not have to rediscover. All other 312 shared fixture rows
  are verdict-identical across L1/L2/L3.

### Deferred by contract

- The Spicy Regs L0 certificate remains in the consumer repository beside its
  carrier mapping and corpus evidence; this repository does not mirror or
  overstate that external claim.
- These changes remain Unreleased after `v0.2.0-pre.7`; that tag records the
  prerequisite consolidation and intentionally excludes this feature.

## v0.2.0-pre.7 — Constraint, runtime, and composition consolidation

This release consolidates the work from Plans 6a and 7a–7e: the Rust SDK and
constraint pipeline, complete L1–L4 conformance coverage, behavioral runtime
contracts, ADR-0093 `rkaf:Finding` promotion, temporal and freshness semantics,
and disciplined composition with public vocabularies. The detailed change
records follow.

### SKOS predicate composition on Concept; prefLabel(1) enforced at L1 + L3 (PKA-2szi)

The normative mandate at `spec/rkaf-concept-registry.md` for `skos:prefLabel (1)` on every `rkaf:RegisteredConcept` / `rkaf:LocalConcept` was previously unenforced — producers could omit the label and pass validation. This entry closes the gap with explicit L1 (CUE → JSON Schema) AND L3 (SHACL `sh:minCount 1`) enforcement, plus optional `skos:altLabel` / `skos:broader` / `skos:narrower` / `skos:related` composition.

#### Added — SKOS predicate-level composition + dual-layer enforcement

- `context/rkaf-context.jsonld` — added JSON-LD term definitions for `skos:prefLabel`, `skos:altLabel` (set), `skos:broader`, `skos:narrower` (set), `skos:related` (set).
- `constraints/core/concept.cue` — extended `#RegisteredConcept` and `#LocalConcept` with required `skos:prefLabel` (cardinality 1) and optional skos: relations.
- `compiled/shacl/core/concept.ttl` — regenerated with `sh:property [ sh:path skos:prefLabel ; sh:minCount 1 ]` on both Concept shapes. SHACL compiler taught `@prefix skos:`.
- `compiled/json-schema/core/concept.schema.json` — regenerated with `skos:prefLabel` in `required[]` on both shapes.
- `fixtures/negatives/local-concept-missing-pref-label-negative.jsonld` + `fixtures/negatives/registered-concept-missing-pref-label-negative.jsonld` — new negative fixtures; FAIL-AS-EXPECTED at both L1 (JSON Schema) and L3 (SHACL).
- 8 behavior fixtures + 2 edge fixtures (`fixtures/behavior/{bridge-rule-6-*,concept-resolution-*}.jsonld` + `fixtures/edges/{local-concept-deprecated,registered-concept-promoted}-edge.jsonld`) updated to carry `skos:prefLabel` on embedded Concept nodes.
- `spec/rkaf-concept-registry.md` — extended with normative enforcement note citing both layers.
- First-attempt commit `396bbfa` enforced at L1 only and shipped negative fixtures the SHACL gate failed to catch as UNEXPECTED-PASS. That commit was reverted as `4661052`; this entry is the re-do.

### DPV composition into AccessScope (PKA-gb5c)

Cohort A landing per §9 composition-discipline framework. Matches the `eli:consolidates` (commit `08b7997`) and OA selector (commit `a5515b5`) precedents: cross-namespace predicate imports with L1/L3 declining to constrain DPV's range. Converts §9.2 DPV alignment overclaim into a concrete typed interop point for GDPR/HIPAA buyer audience.

#### Added — DPV predicate-level composition

- `context/rkaf-context.jsonld` — added JSON-LD term definitions for `dpv:hasPersonalDataCategory` (`@type: @id`, `@container: @set`), `dpv:hasLegalBasis` (`@type: @id`), and `dpv:hasPurpose` (`@type: @id`) adjacent to the existing ELI block. The `dpv:` prefix was already declared; these entries make the multi-valued IRI-typed semantics explicit at the context layer.
- `constraints/core/access-scope.cue` — extended `#AccessScope` with three optional cross-namespace fields: `dpv:hasPersonalDataCategory?`, `dpv:hasLegalBasis?`, `dpv:hasPurpose?`. No range constraints; DPV owns its taxonomy.
- `spec/rkaf-core.md §9.2` — extended the DPV alignment row with explicit predicate names (`dpv:hasPersonalDataCategory`, `dpv:hasLegalBasis`, `dpv:hasPurpose`), DPV version pin (DPV 2.3, 2026-02-25), and forward-migration clause. Converts the existing overclaim placeholder into a concrete typed alignment row matching the ELI/OA row shape.
- `spec/rkaf-core.md §4.6` — normative SHOULD text already present from the PKA-03og §9 reshape; no change required.
- `context/COMPOSE-PATTERNS.md` Pattern 3 (AccessScope locus) — added `dpv:` composition recipe block showing HIPAA-PHI and GDPR-PII cases, with pointer to the new fixture.
- `fixtures/edges/access-scope-with-dpv-composition-positive.jsonld` — new edge fixture demonstrating two `regulatoryRestricted` AccessScope nodes composing `dpv:hasPersonalDataCategory` + `dpv:hasLegalBasis` (one HIPAA-PHI case, one GDPR-PII case with optional `dpv:hasPurpose`).
- No SHACL shape over `dpv:*` predicates; no L1 enforcement of cardinality. Partner producers conform to DPV's own taxonomy. Closed-taxonomy debt unchanged; net new vocabulary classes 0.

### OA selector composition: predicate-level imports + SourceFragment subClassOf (PKA-ehze + PKA-f03y)

Cohort A landing per §9 composition-discipline framework. Closes the §9.4 inversion where Rulespec imported W3C Web Annotation Ontology but used rkaf-namespaced attachment predicates. Matches the `eli:consolidates` precedent (commit `08b7997`).

#### Changed — OA predicate-level composition (breaking JSON-LD wire shape)

- `context/rkaf-context.jsonld` — removed `rkaf:hasSelector` and `rkaf:bindsArtifact` term definitions; added `oa:hasSelector` (`@type: @id`), `oa:hasSource` (`@type: @id`), `oa:exact` / `oa:prefix` / `oa:suffix` (`@type: xsd:string`).
- `spec/rkaf-vocabulary.md` — vocabulary table rows updated from rkaf-prefixed to oa-prefixed predicates.
- `constraints/core/source-fragment.cue` — fields renamed; `#TextQuoteSelectorPayload` shape added for `oa:exact` / `oa:prefix` / `oa:suffix` composition.
- `compiled/json-schema/core/source-fragment.schema.json`, `compiled/shacl/core/source-fragment.ttl`, `crates/rkaf-core/src/generated/source_fragment.rs` — regenerated.
- `spec/rkaf-core.md` — §4.2 prose updated; §9.1 OA row pinned to OA 1.0 with forward-migration clause; declares `rkaf:SourceFragment rdfs:subClassOf oa:SpecificResource`.
- All affected positive fixtures (11) renamed predicate keys.
- **Wire-shape break:** producers emitting `rkaf:hasSelector` or `rkaf:bindsArtifact` must rename to `oa:hasSelector` / `oa:hasSource`. v0.2 pre-1.0 closed-taxonomy timing.

### §9 reshape: four-mode composition classifier + four-cohort treatment (PKA-03og)

Replaces the §9.1 (Imports) / §9.2 (Alignments) two-mode taxonomy with the four-mode classifier (Direct predicate import / Class-tag / URI-value / Pattern citation) derived from corpus evidence in the post-fs-pmf4 alias audit. Spec credibility tightening; zero behavior change.

#### Changed — §9 structure

- `spec/rkaf-core.md §1 Namespaces` — Imported list trimmed to mode-1 only (`prov:`, `oa:`, `skos:`, `eli:`); Aligned list trimmed to mode-2/3 only (`aknt:`, `uslm:`, `dpv:`, `odrl:`). Cohort C/D prefixes removed.
- `spec/rkaf-core.md §9.1` — renamed "Imports — mode-1 direct predicate imports"; rows now list only ontologies with predicate-level imports declared in `context/rkaf-context.jsonld`. ELI promoted here from §9.2 to reflect actual composition shape.
- `spec/rkaf-core.md §9.2` — Alignments tightened to mode-2/3 with explicit notes: ODRL row clarifies overlay-projector composition (Cohort B); DPV row points to PKA-gb5c as the active Cohort A landing; aknt: / uslm: rows carry forward-compat notes.
- `spec/rkaf-core.md §9.2.1` — new "Modes of composition" subsection with four-mode classifier table.
- `spec/rkaf-core.md §9.2.2` — new "See also — partner ontologies for future projection" subsection housing Cohort C demotions (`lrml:`, `rrmv:`, `eco:`, `sepio:`, `cito:`, `dcterms:`) with promotion criteria.
- `spec/rkaf-core.md §9.4` — examples updated; framework-memo cross-reference added.
- `spec/rkaf-core.md §12 References` — DCTERMS, LegalRuleML, ECO/SEPIO moved from Normative to Informative to match §9.2.2 cohort assignments.
- `context/rkaf-context.jsonld` — Cohort D dead-weight prefix declarations dropped (`dcat:`, `nano:`, `schemaorg:`); `_meta.relationship` + `_meta.delta_from_v0.1` rewritten to reflect the four-mode taxonomy.

### §9 composition-discipline framework + drift cleanups

#### Documented — composition-discipline framework

- `thoughts/specs/2026-05-20-section-9-composition-discipline.md` — new framework memo. Establishes the measurement metric for §9 composition decisions: `(User Value [real + theoretical]) × (Architectural Debt Reduction)`, explicitly NOT time or session-cost. Documents the four composition modes (direct predicate / class-tag / URI-value / pattern citation), the four-cohort treatment (Compose / Clarify / Demote / Drop), per-cohort precedents (ELI = Cohort A landed; DPV = Cohort A next), and the 5-question decision framework for evaluating future §9 candidates.

#### Removed — dead predicate; renamed legacy holdover

- `context/rkaf-context.jsonld` — removed `rkaf:sourceFragment` (lowercase) JSON-LD term definition. v0.1 holdover; absent from vocabulary table, CUE constraints, compiled artifacts, Rust generated code, spec body. Only used in v0.1-era narrative fixtures (since renamed).
- `fixtures/narratives/{local-operational,statutory-authority}.md` — 5 occurrences of `rkaf:sourceFragment` renamed to `rkaf:bindsSourceFragment` (the canonical v0.2 predicate at `spec/rkaf-vocabulary.md:20`).

#### Added — drift fix: lastVerifiedAt datetime typing

- `context/rkaf-context.jsonld` — added `rkaf:lastVerifiedAt` with `@type: xsd:dateTime`. Predicate was used in 5 CUE shapes + vocabulary spec + normative orthogonality invariant but missing from context, causing string-literal serialization instead of typed datetime in JSON-LD output. Drift introduced during Plan 7d landing.

### AI-governance vocabulary review (ADR 0149)

#### Documented — no vocabulary diff

- `thoughts/adr/0149-pkaf-compose-patterns-vs-ai-governance-vocabulary.md` (stack-level) rejects six proposed AI-governance vocabulary additions (`rkaf:Projection`, `rkaf:Proposal` + Promotion, `rkaf:RetrievalPolicy`, `rkaf:SourceVersion`, `rkaf:AnswerTraceBundle`, `rkaf:MaterializedEdge`) as wholesale or near-wholesale duplications of existing primitives. Net new core terms: 0. Net new classes: 0. Closed-taxonomy discipline preserved.
- `context/COMPOSE-PATTERNS.md` ships six reader-facing recipes showing the existing-primitive composition that satisfies each rejected proposal, with line-level citations to `spec/`, `constraints/core/`, `context/rkaf-context.jsonld`, and `crates/rkaf-runtime/`. First place a consumer looks when tempted to propose new vocabulary.
- `thoughts/plans/2026-05-21-eli-consolidates-spike.md` queues a bounded ~1-day investigation into whether `eli:consolidates` composes directly into the rkaf context (via `owl:equivalentProperty`) for multi-predecessor source consolidation, or whether a single `rkaf:consolidates` predicate (no class) is warranted. **Resolved 2026-05-20** — outcome: direct import of `eli:consolidates`. See "Resolved — ELI-consolidates spike (Outcome 1)" below. (Spike file was renamed mid-investigation from `eli-i-consolidates-spike.md` to `eli-consolidates-spike.md` after confirming the predicate is in ELI core, not ELI-I.)

#### Resolved — ELI-consolidates spike (Outcome 1: direct import)

- `context/rkaf-context.jsonld` — added JSON-LD term definitions for `eli:consolidates` and `eli:consolidated_by` (both `@type: @id`, `@container: @set`) adjacent to the existing PROV-O block. The `eli:` prefix was already declared (L16); these entries make the multi-valued IRI-typed semantics explicit at the context layer. Eight lines added.
- `spec/rkaf-core.md §9.2` — extended the ELI alignment row to name `eli:consolidates` and `eli:consolidated_by` for multi-predecessor consolidation edges, with normative guidance on the consolidation-vs-supersession semantic distinction (consolidation: predecessors remain legally extant; supersession: predecessors become historical) and a cross-reference to `rkaf:supersedesAssertion` (§6, Lifecycle primitives). Confirms ELI 1.5 design (predicate non-functional; rdfs:comment explicitly directs repeated use). Spike found the predicate is in ELI core (not ELI-I as the spike title suggested); spike filename retained for path stability.
- `context/COMPOSE-PATTERNS.md` Pattern 4 — replaced the "Open question (under spike)" note with: (a) a worked recipe showing one consolidated text incorporating three predecessor acts via `eli:consolidates`; (b) a "Consolidation vs supersession — when to use which" decision table covering `eli:consolidates`, `rkaf:supersedesAssertion`, and `rkaf:LifecycleEvent`; (c) a pointer to the new fixture.
- `fixtures/edges/consolidates-multi-predecessor-edge.jsonld` — new edge fixture (4-node `@graph`: 3 predecessor assertions + 1 consolidated text linking via `eli:consolidates`).
- No constraint changes; no SHACL changes; no compiled-artifact regeneration. PKAF declines to constrain a non-PKAF-namespaced predicate at L1 — partner producers conform to ELI's own domain/range (`LegalExpression ∪ LegalResource`). §9.4 discipline ("do not reinvent — if a public ontology owns the local problem, Rulespec uses it") satisfied. Closed-taxonomy debt unchanged; net new vocabulary classes still 0.

### Plan 7e + ADR-0093 review follow-ups

Coordinated cleanup pass closing the actionable findings from three neutral semi-formal reviews: Plan 7e APPROVE-WITH-NITS (6 items, F1-F6 below), the `b6c24de` polish-commit nit review (4 items, N1-N3), and a cross-stack Studio cutover port (ADR-0093 derive).

#### Changed — Plan 7e review F1 + F4 — freshness gate now requires effectiveness

- `crates/rkaf-runtime/src/reducer.rs::narrow_for_freshness` now iterates `temporal::effective_attestations_at(graph, evaluation_time)` and filters by `rkaf:targets contains assertion_id`. Revoked or out-of-period Attestations are silently excluded from the freshness narrowing — they're already excluded from the authority chain, so narrowing freshness on their basis was over-firing. `effective_attestations_at` (Plan 7e.1's shared helper) now has its first real production caller.
- `spec/rkaf-behavior.md` §1.2 Step 5.5 — normative paragraph updated: "any effective Attestation (per `temporal::effective_at`) targeting the assertion @id" replaces "any Attestation targeting the assertion @id". Pseudocode aligned. Strictness clause extended to cover `revokedAt` + `effectivePeriod{Start,End}` + dangling `hasEffectivePeriod` IRIs (propagated through `effective_attestations_at`).

#### Added — Plan 7e review F5 — richer rationale when freshness narrows

- `reducer::evaluate` now emits `"freshness gate narrowed from <baseline> to <after-freshness> (maxAttestationStalenessDays=<n>)"` as the rationale whenever Step 5.5 actually narrows the effective level (workspace-wide reduction path). Implemented via a new internal `reduce_for_scope_traced` returning a `ScopeResult` trace; the public `reduce_for_scope` wrapper is unchanged. `rationale` is in `INFORMATIONAL_OUTPUT_KEYS` so existing fixtures continue to match.

#### Added — Plan 7e review F6 — malformed-`lastVerifiedAt` behavior fixture

- `fixtures/behavior/usage-eligibility-reducer-freshness-malformed-negative.jsonld` exercises the Step 5.5 strict-error path on `Attestation.rkaf:lastVerifiedAt = "not-a-date"` using the `rkaf:expectedRuntimeError: "rkaf:MalformedTestCase"` pattern. Wired into `tests/behavior_fixtures.rs::reducer_freshness_malformed_negative`. Conformance: **235 → 236 fixtures, 0 divergences**.

#### Refactored — Plan 7e review F2 + F3 — `RuntimeError::iri_tag` extracted

- New `RuntimeError::iri_tag(&self) -> &'static str` returning the 7 fixture-facing IRI strings. Replaces the duplicated inline match arms in `crates/rkaf-runtime/tests/behavior_fixtures.rs` and `crates/rkaf-runtime-cli/src/main.rs`. New `runtime_error_iri_tag_mapping` unit test pins the variant → IRI mapping (one assert per variant).
- Both call sites now carry an inline comment documenting that `OutputMismatch` arm precedence is deliberate (a fixture declaring `rkaf:expectedRuntimeError = "rkaf:OutputMismatch"` is unreachable by design — fixtures use `rkaf:expectedOutput` for the success path).

#### Changed — Polish review N1 + N2 + N3 — `b6c24de` cleanup

- **N1 — CHANGELOG.** Long-tail entries for Finding-6 + Observation-7 marked as closed in `b6c24de` (`fixtures/context.jsonld` removed; narrative annotations + Finding fixture self-containment landed).
- **N2 — Dead exclusion references.** Dropped `context.jsonld` skip-branch in `crates/rkaf-validate/tests/fixture_validation.rs`; removed the docstring enumeration in `tools/conformance_report.py`; cleared the `NON_FIXTURE_NAMES` set in `tools/conformance_lib.py` (kept the predicate as an empty reserve for future non-fixture siblings — comment explains why).
- **N3 — `fixtures/README.md`.** Added the inverse-clause: "Inline the referenced node when the fixture's primary purpose is to exercise the relationship itself; use a cross-fixture reference when the fixture isolates a single class for shape validation."

#### Changed — ADR-0093 cross-stack derive — Studio cutover ported into PKAF

- `policy-studio/`'s post-cutover schema surface (`WaiverAttestationRef` collapse of 4 waiver-flavor clumps + `ValidationFinding.waiver: $ref WaiverAttestationRef` + `lifecycleState` enum sans `waived` + rkaf:Finding-aligned `findingKind`/`detectedAt`/`detectedBy`/`subject` + `findingKind` now required + `parsingWaiver` / `sensitivityWaiver` on SourceVersion / ServiceBinding) is now mirrored into `profiles/studio/schema-source/` (the Rulespec-owned source of truth that derive.sh transforms into `schemas-derived/`). Touched: `wos-studio-common.schema.json` (+`WaiverAttestationRef` $def), `wos-studio-readiness.schema.json` (Finding alignment + waiver field), `wos-studio-binding.schema.json` (sensitivityWaiver), `wos-studio-source.schema.json` (parsingWaiver).
- `profiles/studio/derive.sh` re-emitted `schemas-derived/` + `SHA256SUMS` to match.
- Rename hygiene: 2 stray `PKAF` brand tokens (carried over from the Studio repo prose) renamed to `Rulespec` in the schema descriptions; `tools/rename_audit.py` now clean.

### Plan 7e: runtime contracts use Plan 7d + ADR-0093 fields

Plan 7d added optional temporal-bounds + freshness fields to Attestation, SourceFragment, EvidenceBinding, and BridgeValidationResult; ADR-0093 promoted `rkaf:Finding` and refactored `BridgeValidationResult` indicators. Plan 7e turns those shape additions into enforced runtime behavior across three increments.

#### Added — 7e.1 — `effective_attestations_at` shared helper

- New `crates/rkaf-runtime/src/temporal.rs` module exposing `effective_at(att, time, graph)` and `effective_attestations_at(graph, time)`. Plan 7d's "is this attestation in force at T?" predicate now has one canonical implementation; `bridge::rule_8` imports from it. Strictness posture mirrors `cascade::is_active`: dangling EffectivePeriod IRIs and unparseable RFC-3339 literals propagate as `MalformedTestCase`.
- Unit tests cover empty graph, mix of effective/revoked/out-of-period, malformed timestamp propagation, dangling-IRI propagation.

#### Added — 7e.2 — freshness gate (`reducer::reduce_for_scope` Step 5.5)

- New optional `rkaf:maxAttestationStalenessDays: integer` field on `BridgeConsumerRegistration` (`constraints/core/bridge-consumer-registration.cue`).
- New optional `rkaf:evaluationTime: xsd:dateTime` on `BehaviorTestCase` fixtures drives the freshness check; production runtimes derive it from the packet's evaluation instant (e.g. BVR.validatedAt).
- `reducer::reduce_for_scope` gains Step 5.5: when the consumer declares the field AND `evaluation_time` is set, narrow the effective level **one lattice step downward** if any Attestation targeting the subject assertion has `rkaf:lastVerifiedAt` older than `evaluation_time - max_days` (or has no `lastVerifiedAt` at all — absence of a freshness signal counts as stale). Strictly narrowing; never broadens. Skipped when either input is absent. Orthogonal to lifecycle per the Plan 7d invariant.
- `spec/rkaf-behavior.md` §1.2 — algorithm gains the Step 5.5 block plus a normative paragraph spelling out evaluation-time, relevance, absence semantics, and the dangling/malformed strictness posture.
- `spec/rkaf-vocabulary.md` — added `rkaf:maxAttestationStalenessDays` and `rkaf:evaluationTime` predicate rows.
- `context/rkaf-context.jsonld` — declared both predicates with their xsd types.
- Two new behavior fixtures:
  - `usage-eligibility-reducer-freshness-stale-narrows` — 60-day-old `lastVerifiedAt`, 30-day window → narrows publicationAllowed → localOperationalUse.
  - `usage-eligibility-reducer-freshness-fresh-passes` — 5-day-old `lastVerifiedAt`, 30-day window → unchanged baseline.
- `bridge::rule_2` keeps its no-freshness-check posture (passes `None` for `evaluation_time`); Rule 2 enforces a structural invariant, not a runtime freshness check.

#### Added — 7e.3 — dangling-IRI parity for Finding edges

- `bridge::rule_8` now invokes `verify_finding_iris_resolve(graph)` at entry, walking every `Attestation.targetFinding` and `BridgeValidationResult.findings[]`. Any IRI that fails to resolve raises `MalformedTestCase` — parity with `cascade::is_active`'s `rkaf:hasEffectivePeriod` posture (Plan 7c.6).
- `rkaf-runtime-cli` gains `rkaf:expectedRuntimeError` fixture-level support so a behavior fixture MAY assert "the runtime MUST raise this error variant". `tests/behavior_fixtures.rs` mirrors the contract.
- New fixture `bridge-rule-8-target-finding-dangling-negative` exercises the dangling-`targetFinding` path end-to-end; conformance reports 235 fixtures / 0 divergences.
- Unit tests pin `verify_finding_iris_resolve` for: empty graph, resolving target, dangling `targetFinding`, dangling `BVR.findings[]`, resolving `BVR.findings[]`.

### ADR-0093: rkaf:Finding promoted; BVR indicator refactor; Plan 7d review findings closed

Implements stack-level ADR-0093 (Rulespec Finding IRI Addressability) in three phases inside PKAF and closes the actionable findings from the Plan 7d semi-formal-code-review along the way. Net new universal classes: one (`rkaf:Finding`). Breaking shape change on `BridgeValidationResult` (greenfield-justified — no installed base, no sibling-submodule consumers).

#### Added — Phase A (PKAF commit `c28cb3f`)

- **`rkaf:Finding`** — new first-class IRI-addressable primitive at `constraints/core/finding.cue`. Closed `#FindingKind` (9 values: `warning` / `error` / `staleDependency` / `registryUnavailable` / `registryVersionOutOfRange` / `conceptConflict` / `authorityBroken` / `unsupportedAnchor` / `other`). Closed `#FindingSeverity` (4 values: `informational` / `operationalConflict` / `publicationBlocking` / `authorityCritical` — aligned with `#ConflictSeverity` so RegistryConflict and Finding speak the same vocabulary). Shape: required `findingKind` / `detectedAt` / `detectedBy` / `subject`; optional `severity` / `rationale` / `lastVerifiedAt` / `verifiedBy`.
- **7 new fixtures** for Finding: `finding-positive` (two findings in one graph), `finding-minimal-edge`, four required-field negatives (`finding-missing-{finding-kind,detected-at,detected-by,subject}-negative`).
- **Plan 7d follow-up fixes**:
  - **BLOCKER fixed**: `thoughts/specs/2026-05-12-pkaf-as-public-schema-interop-framework.md` §3 — the Plan 7d edit had silently spliced the Access Scope normative MUST clause ("consumers MUST NOT leak content their access scope forbids") onto the tail of the new Freshness entry. Restored Access Scope's original text; Freshness now ends at the lifecycle ≠ freshness orthogonality statement.
  - **MAJOR fixed**: `context/rkaf-context.jsonld` — added `rkaf:verifiedBy` (`@type:@id`) and `rkaf:findingKind` / `rkaf:severity` (`@type:@vocab`) and `rkaf:subject` / `rkaf:detectedBy` (`@type:@id`). Without these, JSON-LD expansion treated IRI references as string literals (breaks SPARQL joins, Trellis anchoring).
  - **MAJOR fixed**: 5 new round-trip tests in `crates/rkaf-core/tests/fixture_round_trip.rs` covering the Plan 7d optional fields on Attestation / SourceFragment / EvidenceBinding / BridgeValidationResult.
  - **FINDING 5 fixed**: `fixtures/attestation-revoked-within-period-positive.jsonld` exercises the "revocation supersedes effective period" semantic claimed by the vocab spec.

#### Added — Phase B (PKAF commit `5bce188`)

- **`rkaf:targetFinding?: string` on Attestation** — optional IRI pointing at a `rkaf:Finding`. When set, the Attestation acts as a waiver / override of the targeted Finding. Plan 7d-deferred field; now live.
- **`fixtures/attestation-waiving-finding-positive.jsonld`** — Finding (staleDependency) + Attestation that waives it under named program-director authority, scoped to in-flight recerts.
- **Context**: `rkaf:targetFinding` declared `@type:@id`.

#### Changed — Phase C (PKAF commit `8f50dd8`) — BREAKING

- **`BridgeValidationResult` indicator refactor.** Removed five flat `[...string]` arrays:
  - `rkaf:warnings` / `rkaf:errors` / `rkaf:staleDependencies` / `rkaf:registryUnavailable` / `rkaf:registryVersionOutOfRange`
  
  Replaced with a single typed `rkaf:findings?: [...string]` (IRIs of `rkaf:Finding` nodes). The `#FindingKind` closed enum on `rkaf:Finding` subsumes the semantic distinctions the prior fields encoded (same five names, now enum values on a typed node, not bucket names on the BVR).
- **Migrated** `fixtures/edges/bridge-validation-result-mixed-warning-edge.jsonld` to use Finding IRIs.
- **Blast radius confirmed minimal**: runtime read NONE of the legacy fields (verified by grep); no sibling submodule consumes them (verified by grep across `policy-studio/`, `trellis/`, `formspec/`, `workspec-server/`, `work-spec/`); 33 behavior fixtures use `rkaf:detectedIssues` + `rkaf:usedAsAuthority` (unaffected).

#### Changed (review-finding follow-up — this commit)

- **`crates/rkaf-core/tests/fixture_round_trip.rs`** — added `round_trip_finding_fixture` (review WARNING 1: Finding had no codegen-layer round-trip coverage despite being a new primitive). Round-trip suite: 26 → 27 tests.
- **`context/rkaf-context.jsonld`** — deduplicated `rkaf:severity` (had conflicting `@id` vs `@vocab` declarations) and `rkaf:subject` (had two identical declarations); kept the Phase A `@vocab` semantics for severity since RegistryConflict's literal `"rkaf:operationalConflict"` resolves identically under either. Added `rkaf:Finding` class IRI declaration to match precedent (every other v0.2 class has one).
- **`constraints/core/finding.cue`** — fixed comment that referenced non-existent `#RegistryConflictSeverity` (actual identifier in `registry-conflict.cue:10` is `#ConflictSeverity`).
- **`thoughts/adr/0093-rkaf-finding-iri-addressability.md`** — reconciled internal contradictions: §Decision header no longer says "(proposal — not yet ratified)"; §Status reflects "PKAF Phases A+B+C: LANDED"; proposed-shape code block updated to match the actual landed enum values (camelCase: `conceptConflict` / `authorityBroken` / `unsupportedAnchor`, not the kebab-case the original draft proposed).

#### Verified

- `cargo test --workspace` — green.
- `cargo test -p rkaf-core --test fixture_round_trip` — **27 passing** (was 19 pre-Plan-7d).
- `cargo test -p rkaf-runtime` — 18 unit + 39 integration, all passing.
- `make test` — full L0-L5 sweep exits 0.
- `conformance_report.py` — **229 fixtures, 0 divergences**.
- `vocab_audit.py` — 33 CUE primitives / 33 covered.
- `codegen_drift_audit.py` — clean.

#### Deferred to Plan 7e

- `effective_attestations_at(time)` runtime filter — uses `hasEffectivePeriod` + `revokedAt` on Attestation.
- `freshness_gate(consumer)` — narrows `usageEligibility` via `lastVerifiedAt` against a consumer-declared max-staleness window.
- Symmetric strict-error for dangling `rkaf:targetFinding` IRIs in `cascade::is_active` (Plan 7c made malformed timestamps loud; Plan 7d-followup made dangling `hasEffectivePeriod` IRIs loud; Finding/targetFinding parity is still open).
- Studio cutover (`policy-studio/` repo) — projects `ValidationFinding` from `rkaf:Finding`; collapses four waiver flavors to `Attestation(targetFinding=…)`.
- Trellis Finding anchoring (`trellis/` repo) — `rkaf:Finding` IRIs as anchored objects under the §4.6 binding contract.

#### Long-tail follow-up (closed in `b6c24de`)

- ~~Migrate or annotate `fixtures/narratives/*.md` and `fixtures/context.jsonld` — both still display the legacy BVR shape (`rkaf:warnings` etc.).~~ — closed: narratives carry inline annotations pointing to the post-ADR-0093 shape; `fixtures/context.jsonld` was removed (unreferenced; canonical context lives at `context/rkaf-context.jsonld`). (Review FINDING 6.)
- ~~Dangling-IRI hygiene for `rkaf:detectedBy` in Finding fixtures.~~ — closed: Finding fixtures now self-contain their `detectedBy` `rkaf:BridgeValidationResult` node. (Review OBSERVATION 7.)

### Plan 7d: Attestation temporal bounds + source freshness + identity boundary

Adds 4 optional fields to existing primitives and 2 normative spec edits. Net new universal classes: zero. Conceptual debt: zero.

Outcome: 8 of 9 Studio knowledge-shaped schemas become retire-able by composing `Attestation` + `EffectivePeriod` + the new freshness fields. The 9th (`wos-studio-identity-subject`) stays Studio-owned per the now-explicit §4.6 identity boundary.

#### Added (Plan 7d)

- **CUE fields on existing primitives.** All optional, additive:
  - `rkaf:Attestation` gains `hasEffectivePeriod` (reuses the existing edge, domain expansion), `revokedAt`, `lastVerifiedAt`, `verifiedBy`.
  - `rkaf:SourceFragment` gains `lastVerifiedAt`, `verifiedBy`.
  - `rkaf:EvidenceBinding` gains `lastVerifiedAt`, `verifiedBy`.
  - `rkaf:BridgeValidationResult` gains `lastVerifiedAt`, `verifiedBy`.
- **5 new positive fixtures**: `attestation-with-effective-period-positive`, `attestation-revoked-positive`, `sourcefragment-with-freshness-positive`, `evidencebinding-with-freshness-positive`, `bridgevalidationresult-with-freshness-positive`.
- **Spec normative**:
  - `thoughts/specs/2026-05-12-pkaf-as-public-schema-interop-framework.md` §3 — new `Authority grant` terminology entry (disambiguates content-grounding `Warrant` from binding-layer user-role grants) + new `Freshness` entry (defines the orthogonality invariant: lifecycle ≠ freshness).
  - §4.6 — renamed "Anchoring and identity are dependency-inverted"; adds normative paragraph naming the identity boundary. Rulespec references identities by IRI; the identity shape belongs to bindings (W3C VC, OIDC, X.509, Trellis, etc.). Partner-level `AuthorityGrant` records likewise belong to bindings.
  - `spec/rkaf-vocabulary.md` — predicate rows extended for `hasEffectivePeriod` (domain += Attestation), and 3 new predicate rows for `revokedAt` / `lastVerifiedAt` / `verifiedBy`.

#### Changed (Plan 7d)

- **Codegen regenerated.** `tools/compile_all.sh` re-emitted `attestation.rs`, `source_fragment.rs`, `evidence_binding.rs`, `bridge_validation_result.rs` (+JSON Schema, SHACL, TS counterparts). +20 lines across the 4 generated Rust files.

#### Falsified (Plan 7d — what was scoped, then dropped)

- **`rkaf:OriginClass` (proposed promotion).** DROPPED. Code-scout pass found this duplicates the existing `#AssertionOrigin` closed enum (`constraints/core/assertion.cue:4-9`) AND name-collides with Studio's existing `OriginClass` (different axis: supply-chain provenance). Promotion would have created a parallel competing taxonomy.
- **`rkaf:Waiver` first-class class (proposed promotion).** DOWNGRADED to optional fields on `Attestation`. Studio's existing waiver implementation is four un-unified data clumps marked `*substrate-pending*`; promoting "Waiver" as a new universal class would have hardened an unfinished design.
- **`rkaf:SourceDocument` (proposed promotion).** DOWNGRADED to Studio-profile-scope. The `kind` enum (`regulation|statute|policy-manual|sop|memo|...`) is authoring-domain flavored; universal federation transport handled by `#Artifact` + ELI/USLM/DOI/CID identifier schemes.
- **`targetFinding` on Attestation.** DEFERRED to stack-level ADR-0093. `BridgeValidationResult` findings are not IRI-addressable today (`warnings` / `errors` / `staleDependencies` are `[...string]` arrays, not nodes with `@id`); promoting `targetFinding` would point at nothing typed.

#### Verified

- `cargo test --workspace` — green.
- `cargo test -p rkaf-runtime` — 18 unit + 39 integration, all passing.
- `make test` — full L0-L5 sweep exits 0.
- `conformance_report.py` — 221 fixtures (216 + 5 new positives), 0 divergences.
- `codegen_drift_audit.py` — clean after regen.
- `vocab_audit.py` — 32 CUE primitives, 32 covered.

#### Open follow-ups

- **Stack-level ADR-0093** (`/Users/mikewolfd/Work/formspec-stack/thoughts/adr/0093-rkaf-finding-iri-addressability.md`) — proposes `rkaf:Finding` as a first-class IRI-addressable shape; unblocks `targetFinding` on `Attestation` and Studio readiness-tier promotion. Filed open; no implementation in this plan.
- **Plan 7e** — runtime behavioral contracts consuming the new fields: `effective_attestations_at(time)` filter and `freshness_gate(consumer)` narrowing. Fixtures exercise the shape first; runtime semantics next cycle.

### L0-L3 coverage completion and gate hardening

Closes the lower-layer coverage gaps that could be hidden by green verdict gates. L0-L3 now has a direct coverage audit in addition to the per-fixture conformance reporter.

#### Added

- **18 new edge fixtures** so `fixtures/edges/` covers every compiled schema class, not just representative classes.
- **`tools/l0_l3_coverage_audit.py`** — coverage gate for L0-L3. It verifies vocabulary/source coverage, JSON-LD parse coverage, positive/negative/edge coverage for all 31 compiled schema classes, and 93/93 required-field negative slots.

#### Changed

- **`Makefile` and CI** now run the L0-L3 coverage audit as a first-class gate.
- **Conformance docs and self-certification** now report 216 total fixtures and complete lower-layer coverage.

#### Verified

- `tools/l0_l3_coverage_audit.py` — 216 normal fixtures, 31/31 schema classes covered by positive, negative, and edge fixtures; 93/93 required-field negative slots covered.
- `tools/conformance_report.py` — 216 fixtures, 0 divergences.

### L4 coverage completion and gate hardening

Closes the remaining L4 branch-coverage gaps that were implemented in the runtime but not represented in `fixtures/behavior/`, and prevents missing L4 execution from reporting as a clean conformance run.

#### Added

- **5 new behavior fixtures**:
  - `cascade-closure-all-edge-predicates` covers every declared CascadeClosureV1 predicate, including SKOS concept-lifecycle edges.
  - `usage-eligibility-reducer-baseline-workspace-positive` covers the no-scope baseline workspace branch.
  - `bridge-rule-5-safe-automatic-migration-positive` covers the Rule 5 safeAutomaticMigration exemption.
  - `concept-resolution-resolved-positive` covers single-target concept resolution.
  - `concept-resolution-unresolved-positive` covers no-mapping concept resolution.
- **`tools/l4_coverage_audit.py`** — branch-coverage gate for L4. It verifies 5/5 contracts, accepted/rejected coverage for all 10 bridge rules, Rule 5 safeAutomaticMigration, 6/6 reducer branches, 2/2 PIT branches, 3 concept outcomes plus 4 severities, cascade `as_of`, and 17/17 cascade predicates.
- **Dynamic Rust fixture sweep** in `crates/rkaf-runtime/tests/behavior_fixtures.rs` so new `fixtures/behavior/*.jsonld` files are exercised by `cargo test` automatically, in addition to named regression tests.

#### Changed

- **`tools/conformance_report.py`** now treats `L4=skip` from a missing `rkaf-behavior-validate` binary as a divergence. A conformance run that did not execute L4 behavior fixtures is not green.
- **`Makefile` and CI** now run the L4 coverage audit as a first-class gate.
- **Conformance docs and self-certification** now report 216 total fixtures and 38 behavior fixtures.

#### Verified

- `tools/l4_coverage_audit.py` — 38 behavior fixtures; all L4 branches covered.
- `rkaf-behavior-validate --json fixtures/behavior/*.jsonld` — 38/38 pass.
- `cargo test -p rkaf-runtime --test behavior_fixtures` — 39 passing, 0 failing.
- `tools/conformance_report.py` — 216 fixtures, 0 divergences.

### Plan 7c: concept severity ladder + cascade `as_of` date predicate + greenfield-strict reducer

Closes the two Plan 7c reservations in `spec/rkaf-behavior.md` and the deferred cascade `as_of` work, then closes the six findings from the Plan 7c semi-formal-code-review.

#### Added (Plan 7c)

- **Concept-resolution 4-level severity ladder** (§6.1, full):
  - `authorityCritical` ⇐ `publicationBlocking` + ≥1 approved mapping in `consumer.trustedRegistries`
  - `publicationBlocking` ⇐ ≥2 mappings with `lifecycleState=approved` AND targets differ
  - `operationalConflict` ⇐ ≥1 mapping with `skos:exactMatch` AND targets differ
  - `informational` ⇐ no exactMatch, targets differ
- **New CUE fields** load-bearing for the ladder:
  - `ConceptMapping.lifecycleState` — closed enum: `proposed` / `underReview` / `approved` / `deprecated` / `retired`
  - `ConceptMapping.managedByRegistry` — IRI identifying the owning registry
  - `BridgeConsumerRegistration.trustedRegistries: [...string]` — authorityCritical-escalation set
- **Cascade `rkaf:cascadeAsOf` literal-date predicate** (§2.4, §2.2 row (b)) — closure scoped to nodes whose attached `EffectivePeriod` contains the `as_of` instant. Timestamps parse as timezone-aware RFC-3339 via `chrono::DateTime::parse_from_rfc3339` and compare as instants (no lex foot-guns; any RFC-3339 offset spelling works).
- **3 new behavior fixtures**: `concept-resolution-publication-blocking`, `concept-resolution-authority-critical`, `cascade-closure-as-of-excludes-expired`.
- **3 new cascade unit tests**: semantic non-Z offset equivalence, out-of-period exclusion, malformed-EffectivePeriod loud error.

#### Changed (Plan 7c — review findings closed)

- **`concept::compute_severity`** — multi-BCR errors from `select_consumer` now propagate via `?` instead of silently degrading to `publicationBlocking`. Return type `Result<&'static str, RuntimeError>`.
- **`cascade::closure` + `is_active`** — accept `Option<&DateTime<FixedOffset>>` rather than `Option<&str>`. Malformed `cascadeAsOf` or `EffectivePeriod.{start,end}` returns `MalformedTestCase` with the offending node + field + raw value — no silent inclusion/exclusion.
- **`reducer::evaluate`** — `rkaf:subjectAssertion` is now REQUIRED on every UsageEligibilityReducer fixture. Removed the "pick the first `rkaf:Assertion`" fallback (greenfield contract; silent selection is unsafe in any graph carrying a justification chain). All 5 existing reducer fixtures updated to declare it explicitly.
- **`spec/rkaf-conformance.md` §4.2** — fixture count corrected for the Plan 7c closeout: 33 at that point (2 cascade · 5 reducer · 2 PIT · 4 concept-resolution · 20 bridge-rule), with breakdown.
- **`crates/rkaf-runtime/Cargo.toml`** — `chrono` (default-features-off; `std`+`clock` only) added for semantic RFC-3339 comparison.
- **Repo hygiene** — two cross-stack proposal documents (formspec generalization, implementation- and spec-side; 1133 lines) swept in by an upstream commit have been moved to the parent stack's `thoughts/proposals/` where they belong. PKAF's `thoughts/proposals/` no longer exists.

#### Verified (Plan 7c)

- `cargo test --workspace` — **all tests passing**; rkaf-runtime now reports 33 integration tests (was 30) + 15 unit tests (was 12, +3 cascade semantic-tz cases).
- `cargo test -p rkaf-runtime` — **48 passing, 0 failing** (15 unit + 33 fixture).
- Behavior fixtures at Plan 7c closeout: 33 in `fixtures/behavior/`, all `L4=pass`.

### Plan 7b: L4 behavioral runtime (`rkaf-runtime` + `rkaf-behavior-validate` CLI)

L4 stops being aspirational. Ships a Rust runtime crate (`crates/rkaf-runtime/`) implementing all 5 algorithmic contracts in `spec/rkaf-behavior.md` — UsageEligibility reducer, CascadeClosureV1, all 10 bridge contract rules, PointInTimeException evaluation, concept resolution with conflict — plus a CLI binary (`rkaf-behavior-validate`) the conformance reporter shells out to. 24 behavior fixtures (6 prior + 18 new bridge-rule fixtures, covering all 10 rules) produce real L4 verdicts.

#### Added (Plan 7b)

- **`spec/rkaf-behavior.md` rewritten** from ~173 lines of descriptive prose to ~470 lines of algorithmic pseudocode + decidable predicates + per-contract output format spec. §7 declares the format per contract; §7.1 closes the errorClass IRI registry; §8 enumerates 8 open ambiguities resolved during codification.
- **7 codified primitives**: `EvaluationAnchor` (9-value closed enum), `PointInTimeException`, `GeneratedWorkProduct`, `RevalidationEvent` + `RevalidationClosureEvent`, plus 3 new support concepts (`ConsumerEffectiveDeclaration`, `BridgeIssueAttestationContract`, BVR fields `usedAsAuthority` + `detectedIssues`). Each ships full vertical slice (CUE + JSON Schema + Rust + SHACL + positive fixture + context entry + rkaf-validate embedded schema + vocab spec §6 row).
- **Additional CUE fields** on existing primitives: `Assertion.{usageEligibility, hasApplicability, hasJustification, hasWarrant, hasAuthority, consumerLifecycleState}`, `BridgeConsumerRegistration.capabilityCap`, `LifecycleEvent.safeAutomaticMigration` — load-bearing for the reducer + bridge rules.
- **`crates/rkaf-runtime/`** — Layer 5 behavioral runtime crate (~1500 LOC). Modules: `graph` (per-`@id` index + by-type index + inverse-edge traversal), `cascade` (BFS over the 10 cascade-edges + 5 SKOS mapping edges per §2.1), `reducer` (5-step lattice composition including applicability gate, PIT-honored override, LocalAdoption broadening, capabilityCap narrowing), `bridge` (10 rule predicates; rule_2 calls `reducer::reduce_for_scope` to stay in lock-step), `pit` (anchor-supported check with proper error verdict on unsupported anchor), `stale` (state machine + safeAutomaticMigration exemption), `concept` (resolver + severity assignment).
- **`crates/rkaf-runtime-cli/`** — `rkaf-behavior-validate` binary. Exit 0/1/2; `--json` emits the per-fixture verdict envelope the conformance reporter consumes.
- **18 new bridge-rule behavior fixtures** — one positive + one negative per rules 1-6 + 8-10. Rule 7 fixture already existed.
- **Integration test** at `crates/rkaf-runtime/tests/behavior_fixtures.rs` — every fixture in `fixtures/behavior/` runs as a `#[test]`.

#### Changed (Plan 7b)

- **`tools/conformance_report.py`** — `_l4_batch_evaluate` shells out to `rkaf-behavior-validate` once with all behavior fixture paths, parses JSON envelope, populates L4 column. L3-fail in behavior fixtures surfaces in `notes` (no longer silently masked). Human table includes L4 column. Binary-missing surfaces as `L4=skip` with a note; the current reporter treats that skip as divergent.
- **`spec/rkaf-conformance.md` §4.2** — L4 gate is no longer "deferred". Points at `rkaf-behavior-validate` + describes the reporter integration.
- **`.github/workflows/constraints-parity.yml`** — workspace `cargo build` step now compiles `rkaf-runtime` + `rkaf-runtime-cli`.

#### Verified

- `cargo test --workspace` — **75 tests passing** (was 39).
- `conformance_report.py` — 161 fixtures, 0 divergences; behavior fixtures show **L4=pass** (was L4=skip).
- `ci_validate.py` — 38 fixtures × 25 shape files, 0 violations, 229 triples.
- `rkaf-behavior-validate --json fixtures/behavior/*.jsonld` → pass=24 fail=0 error=0.

#### Two review checkpoints honored

Both rounds of `semi-formal-code-review` caught real bugs the test corpus didn't surface — same pattern (tests-pass but spec-drift hidden) as the prior backlog-integration review:

- **Phase A review (5fe0ce8)** — 6 BLOCKERs + 7 WARNINGs: missing CUE fields (`safeAutomaticMigration`, `capabilityCap`), fixture typos (`UntermimatedJustificationChain`), ambiguous CascadeClosureV1 (trigger vs cascade edges), invalid enum values in fixtures, vacuous inner-@graph L2 gate. All closed in commit 7b43431.
- **Phase G review (035a0f6)** — 4 BLOCKERs + 7 WARNINGs: reducer missing applicability gate + rule_2 inline reducer drift, PIT unsupported-anchor silent-degradation, Rule 10 missing chain check, cascade missing 5 SKOS mapping edges. All closed in this commit.

#### Honest gaps (intentionally deferred)

- **Multi-BCR graphs** — `stale.rs`, `reducer.rs` step 5, and `bridge.rs` rule_9 pick the first BridgeConsumerRegistration via `.next()`. Single-consumer is the v0.2 assumption; federated scenarios are post-Plan-7b.
- **Cascade `as_of` active filter** — promised in §2.2 but not threaded through the implementation. Closure visits every reachable node regardless of lifecycle state.
- **Six coverage-gap fixtures** identified by review (Rule 7 positive standalone, capabilityCap narrowing, `informational` severity branch, reducer applicability gate, reducer+PIT composition, PIT unsupported-anchor error verdict) — the code paths now exist; explicit regression fixtures are post-Plan-7b work.

---

### Plan 7a: shape conformance (L1–L4) + complete negative coverage

Closes the §10.1 fixture-coverage target for shape conformance. Defines what "Rulespec-compliant" means as a graded contract (L1 Parse / L2 Shape / L3 Constraint / L4 Behavior). Adds a per-fixture conformance reporter, a self-certification document template + reference implementation entry, and 71 mechanically-generated negative fixtures.

#### Added

- **`spec/rkaf-conformance.md`** — normative spec defining L1 (Parse), L2 (Shape — JSON Schema), L3 (Constraint — SHACL + Pattern-C), L4 (Behavior — runtime contracts per `spec/rkaf-behavior.md`). Includes per-level gate identifiers, self-certification requirements, the §10.1 corpus targets, the adoption-depth-gradient interaction matrix, and the rationale for consumer-declared (vs authority-certified) conformance pre-1.0.
- **`tools/conformance_report.py`** — per-fixture L1/L2/L3 reporter. Walks `fixtures/` (excluding the cross-gate adversarial / projector envelopes), classifies each fixture as positive/negative/edge, runs all three gates, surfaces divergences. Three modes: human table (default), `--json` (machine-readable), `--self-certify` (emits a YAML self-cert doc).
- **`tools/generate_negatives.py`** — mechanical generator. For each codified class, walks the JSON Schema's `required` list and emits one "missing-required-field" negative fixture per field, preserving the surrounding document context from the matching positive. Single source of truth: edit the positive, regenerate the negatives.
- **`fixtures/negatives/`** — 71 generated negative fixtures across 23 classes. Every required field of every codified class now has an explicit "this field missing fails validation" gate.
- **`conformance/self-certification.template.yaml`** — partner self-certification template; minimum fields documented.
- **`conformance/partners/rulespec-reference.yaml`** — self-cert document for this repo's reference implementation. Declares L1+L2+L3 at D3, L4 not-claimed (pending Plan 7b).

#### Changed

- **`fixtures/local-operational-positive.jsonld` archived.** This was the renamed v0.1 fixture preserved during the squash; it carried v0.1 Artifact / SourceFragment patterns that don't satisfy the v0.2 `hasArtifactIdentifier` / `bindsArtifact` required fields. Moved to `archive/v0.1/fixtures/local-operational-v0.2.jsonld` as the legacy reference it always was.
- **CI workflow.** `tools/conformance_report.py` wired into `constraints-parity.yml` as the post-cargo gate. Exit-1 on any divergence between expected and actual fixture verdicts.

#### Verified

| Gate | Result |
|---|---|
| `cargo test --workspace` | 39 tests, 0 failures |
| `tools/ci_validate.py` (SHACL) | 33 fixtures × 19 shape files, 0 violations, 198 triples |
| `tools/validate_negatives.py` | 4/4 FAIL-AS-EXPECTED |
| `tools/conformance_report.py` | **108 fixtures (37 positive + 71 negative), 0 divergences** |
| `tools/vocab_audit.py` | 37/39 declared in spec |
| `tools/rename_audit.py` | CLEAN |
| `tools/constraints_parity.py` | 0 release blockers |
| `tools/projector_parity.py` | 7/7 round-trip OK |
| `tools/version_sync.py --check` | clean |

#### Coverage shift

Per spec §10.1: every codified class needs positive + negative (+ optional edge) fixtures.

| Class | Positive | Negative (auto-generated) |
|---|---|---|
| Artifact | ✓ (3 variants: eli/doi/cid) | 2 (hasArtifactIdentifier, artifactIdentifierScheme) |
| SourceFragment | ✓ (4 variants) | 3 (bindsArtifact, hasSelector, selectorKind) |
| EvidenceBinding | ✓ (2 variants) | 1 (bindsAssertion) |
| Warrant | ✓ (3 variants) | 2 (warrantKind, warrantFamily) |
| ConfidenceRecord | ✓ (2 variants) | 4 (confidenceMethod/calibrationStatus/basis/generatedBy) |
| AccessScope | ✓ (2 variants) | 1 (accessScopeKind) |
| AILineage | ✓ | 7 (modelId/modelVersion/promptTemplateRef/temperature/inputContextHash/humanApprover) |
| Assertion | — (in @graph elsewhere) | covered via EvidenceBinding/Warrant edges |
| Authority | ✓ | 1 (authorityKind) |
| Attestation | ✓ | 5 (attestor/attestorKind/targets/decision/attestationScope/attestedAt) |
| LocalAdoption | ✓ | 8 (organization/targetAssertion/adoptionStatus/usageEligibility/adoptionAuthorityKind/adoptionScope/authorizedBy/adoptedAt) |
| ApplicabilityScope | ✓ | 1 (appliesInJurisdiction) |
| EffectivePeriod | ✓ | 1 (effectivePeriodStart) |
| LifecycleEvent | ✓ | 4 (lifecycleEventKind/effectiveDate/emittedBy/appliesTo) |
| RegisteredConcept | ✓ | 3 (managedByRegistry/conceptScope/conceptStatus) |
| ConceptMapping | ✓ | 3 (sourceConcept/targetConcept/mappingRelation) |
| ConceptResolutionResult | ✓ | 3 (inputConcept/resolutionStatus/resolvedAt) |
| BridgeValidationResult | ✓ | 6 (packetId/consumer/bridgeContractVersion/result/effectiveUsageEligibility/effectiveUsageEligibilityRationale/validatedAt) |
| BridgeConsumerRegistration | ✓ | 7 (consumer/bridgeContractVersion/registeredAt/supportedEvaluationAnchors/supportsRegistryVersionRange/supportedAutomaticMigrations/supportedAuthorityKinds) |
| RegistryConflict | ✓ | 3 (conflictingEntries/severity/detectedAt) |
| Justification | ✓ | 1 (hasWarrant) |
| MappingState | ✓ | (enum-only; no class-level required fields beyond @type) |
| RetentionPolicy | ✓ | (closed enum, schema doesn't enumerate required @type-only) |
| Workspace | ✓ | 1 (workspaceId) |

L1: every fixture parses (108/108).
L2: every positive validates clean against compiled JSON Schema; every negative surfaces ≥1 JSON Schema violation.
L3: same at the SHACL gate.
L4: framework defined (spec/rkaf-conformance.md §4); fixtures deferred to Plan 7b.

#### Deferred to Plan 7b

- **Edge fixtures.** §10.1 wants positive + negative + **edge** per class. Edge fixtures need domain judgment (boundary dates, multi-typed nodes, empty-but-valid arrays, etc.) — authoring deferred until a class's edge cases surface from real adoption.
- **L4 behavior conformance fixtures.** Per `spec/rkaf-behavior.md` §7 roadmap: reducer-correctness, cascade-closure, bridge-rule, point-in-time-exception, stale-transition fixtures. Need a runtime impl to validate against — paired with whoever ships Plan 5.5 or Plan 7b.
- **Cross-property invariant fixtures** beyond what's already in `archive/v0.1/shapes/`. The 5 adversarial + 3 AI-extraction fixtures cover the documented JSON-Schema/SHACL divergence corpus; deeper Pattern-C coverage is post-Plan-7a.

### Second-pass spec re-scan: 3 more codifications + SHACL emitter bug

A second careful re-read of `thoughts/specs/2026-05-12-pkaf-as-public-schema-interop-framework.md` surfaced three primitives the spec names but we hadn't codified.

#### Added

- **`rkaf:RegistryConflict`** (`registry-conflict.cue`, `registryconflict-positive.jsonld`) — Appendix A explicitly names it as the generalization of v0.1.2's `MappingConflict` (concept-registry §8). Closed `severity` enum (`informational` / `operationalConflict` / `publicationBlocking` / `authorityCritical`); ≥2 conflicting entries; optional applicability scope.
- **`rkaf:BridgeConsumerRegistration`** (`bridge-consumer-registration.cue`, `bridgeconsumerregistration-positive.jsonld`) — §7.1 names "Bridge Contract Registry" as one of three normative registries; Core §5.1 specifies the registration record's properties. Carries `consumer`, `bridgeContractVersion`, `supportedEvaluationAnchors`, `supportsRegistryVersionRange`, `supportedAutomaticMigrations`, and `supportedAuthorityKinds` (the last typed against the cross-file `AuthorityKind` enum).
- **`rkaf:Justification`** (`justification.cue`, `justification-positive.jsonld`) — §1.1 abstract primitive list names "justification" alongside attestation, adoption, etc. `spec/rkaf-concept-registry.md` §2.5 describes `rkaf:hasJustification` carrying a `Justification` with `hasWarrant`. Warrant-family-agnostic; generalizes v0.1.2's authority-chain hop into any-family grounding.

#### Fixed (SHACL emitter bug surfaced by RegistryConflict)

- **Duplicate `sh:minCount` predicates.** When a property is both `required` (auto-`sh:minCount 1`) AND has `list.MinItems(N)` cardinality (`sh:minCount N`), the SHACL target previously emitted both predicates on the same property block. pySHACL 0.31+ refuses with `MinCountConstraintComponent must have at most one sh:minCount`. Fix: consolidate to `max(required ? 1 : 0, list_min_items)`. Affects every property with both flags set; surfaced first by `RegistryConflict.conflictingEntries` (`list.MinItems(2)` and required).

#### Coverage

- `cargo test --workspace`: 36 → **39 tests passing** (3 new round-trip tests).
- `tools/ci_validate.py` (SHACL): 30 → **33 fixtures × 19 shape files**, 0 violations, **198 triples** (up from 173).
- `tools/vocab_audit.py`: 34 → **37 required terms declared** in spec.
- `rkaf-validate` `EMBEDDED_SCHEMAS`: 20 → **23 entries** (some classes share schema files).

#### Remaining intentional gaps (not blockers)

Per `spec/rkaf-behavior.md` §7 codification roadmap, these are deferred to Plan 7 (Conformance) work:

- Lifecycle packet subclasses (`AmendmentPacket`, `SupersessionPacket`, etc.) — subsumed today into `LifecycleEvent` with `lifecycleEventKind` enum; explicit subclass shapes deferred.
- `GeneratedWorkProduct` overlay class — Core §6.1.
- `DelegationInstrument`, `AuthorityChainHop` — Core §2.3–§2.4 (chain-traversal infrastructure).
- `RevalidationEvent` / `RevalidationClosureEvent` — Core §4.8; today covered by generic `LifecycleEvent`.
- `EvaluationAnchor` closed enum — Core §4.7; today carried as open IRI string.
- Pre-Assertion candidate state (Studio's `ExtractedClaim`) — Studio-profile-scoped per earlier decision; not promoted to universal Vocabulary.

These are not in the active-spec normative list; they're Plan 7 codification candidates documented in the behavior spec's roadmap.

### All deferred gaps closed

Follow-up to the review-driven fixes: close every remaining gap noted as deferred or informational in the prior CHANGELOG entry. The semi-formal review's findings 6 and 7 are now closed.

#### Added

- **`spec/rkaf-behavior.md`** — new normative document covering the Layer 5 runtime contracts: `usageEligibility` reducer invariants, `CascadeClosureV1` algorithm, the 10 bridge contract rules, point-in-time exception evaluation, stale transition semantics. Includes a codification roadmap mapping each runtime contract to its current state (shape-codified / partial / runtime-only) and the path to fuller codification under Plan 7 (Conformance). The full v0.1 normative prose remains preserved at `archive/v0.1/spec/rkaf-core.md` as the authoritative reference until the roadmap completes.

#### Changed

- **`tools/ci_validate.py` extended.** The SHACL gate now validates the 10 §6 codified additional terms via the CUE-compiled SHACL shapes at `compiled/shacl/core/`. 10 new shape files added to the `SHAPES` list; 10 new fixtures added to `EXPECTED`. Gate now validates **30 fixtures across 16 shape files** (was 20 across 6); 0 violations, 173 triples.
- **`tools/vocab_audit.py` recognizes the §6 codified-terms table layout.** Previously the audit only parsed §5's 7-cell layout (`| Term | IRI | … | Required fixtures |`); my §6 uses a 4-cell layout (`| Term | CUE | Fixture | Purpose |`). The audit now detects either header signature and reads the matching column. Required-fixtures count: 24 → 34; remaining "extras" are `context.jsonld` (shared JSON-LD context, by design) and `local-operational-positive.jsonld` (preserved v0.1 fixture).
- **`rkaf:mappingPredicate` → `rkaf:mappingRelation`.** The hand-authored `shapes/rkaf-shapes-conceptregistry.ttl` (the canonical reference for ConceptRegistry §2.2) declares the property as `mappingRelation` with allowed values `skos:closeMatch` / `exactMatch` / `broader` / `narrower` / `related` / `mappingRelation`. My new CUE had drifted to `mappingPredicate` with the `Match`-suffixed SKOS variants. Aligned the CUE + fixture + context to the canonical spelling.
- **`spec/README.md` rewritten.** Previously referenced nonexistent filenames (`rkaf-core-v0.1.md`, `rkaf-concept-registry-v0.1.2.md`) — a pre-existing staleness the review surfaced. Now enumerates every active spec document (`rkaf-core.md`, `rkaf-vocabulary.md`, `rkaf-concept-registry.md`, `rkaf-behavior.md`, the three projector carrier conventions) with current paths, and points at `archive/v0.1/` for historical reference. `tools/rename_audit.py` allowlists this file (historical PKAF references are intentional context).
- **`OneOrMany<T>` doc-comment** in `crates/rkaf-core/src/lib.rs` now discloses the empty-array permissiveness: `[]` deserializes as `Many(vec![])`, bypassing `list.MinItems(N)` at the Rust layer. JSON Schema (`rkaf-validate`) and SHACL (`tools/ci_validate.py`) catch cardinality on their respective gates.

#### Verified (post-fix)

- `cargo test --workspace`: **36 tests, 0 failures**.
- `tools/ci_validate.py` (SHACL): **30 fixtures across 16 shape files, 0 violations, 173 triples**.
- `tools/validate_negatives.py`: 4/4 FAIL-AS-EXPECTED.
- `tools/vocab_audit.py`: **34/36 fixtures declared in spec (2 informational extras)**.
- `tools/rename_audit.py`: CLEAN.
- `tools/constraints_parity.py`: 0 release blockers.
- `tools/projector_parity.py`: 7/7 round-trip OK.
- `tools/version_sync.py --check`: clean.

#### Status of the original review findings

| Finding | Severity | Status |
|---|---|---|
| 1. Broken cross-file `$ref`s in 4 schemas | BLOCKER | ✓ fixed (auto-discovered enum registry) |
| 2. `@type` field never emitted in Rust | WARNING | ✓ fixed (consult `s.type_iri`) |
| 3. Zero coverage on 10 new fixtures | WARNING | ✓ fixed (`STRICT_POSITIVE` + 9 new round-trip tests) |
| 4. False "no API drift" claim | WARNING | ✓ fixed (CHANGELOG disclosed; rename aligns Rust with v0.1 spec) |
| 5. Hardcoded `_RUST_CROSS_FILE_ENUMS` dict | WARNING | ✓ fixed (auto-discovered registry shared with JSON Schema target) |
| 6. Layer 1 / Layer 5 seam + `spec/README.md` staleness | NIT/OBSERVATION | ✓ fixed (`spec/rkaf-behavior.md` created; `spec/README.md` rewritten) |
| 7. `OneOrMany<T>` empty-array permissiveness | OBSERVATION | ✓ fixed (doc-comment discloses) |
| Deferred: SHACL gate not validating new vocab | (deferred) | ✓ fixed (compiled SHACL wired into `ci_validate.py`) |
| Deferred: Layer 5 behavioral semantics | (deferred) | ✓ fixed (`spec/rkaf-behavior.md`) |
| Audit: §6 table silently bypassed | (informational) | ✓ fixed (audit recognizes both header signatures) |

Every flag the semi-formal review raised is closed. The active tree has no remaining deferred gaps from the backlog-integration work.

### Vocabulary backlog integration: review-driven follow-ups

A semi-formal code review of the initial backlog integration surfaced one BLOCKER and four WARNINGs. All are addressed here.

#### Fixed (review follow-ups)

- **BLOCKER: cross-file enum `$ref`s in compiled JSON Schemas.** The Rust target had a `_RUST_CROSS_FILE_ENUMS` registry; the JSON Schema target did not. As a result, 4 of 10 new positive fixtures (`conceptmapping-positive`, `conceptresolutionresult-positive`, `localadoption-positive`, `bridgevalidationresult-positive`) failed validation at runtime with `Invalid reference: #/$defs/UsageEligibility` errors. **Fix:** `tools/constraints_compile.py` now scans every sibling CUE file at startup (`_scan_global_enum_registry`), builds an enum-name → source-file map, and the JSON Schema target inlines cross-file enum definitions into each consuming schema's `$defs`. The Rust target was migrated off the hardcoded `_RUST_CROSS_FILE_ENUMS` dict onto the same auto-discovered registry. (Findings 1 + 5.)
- **`@type` field was never emitted in generated Rust structs.** The parser diverts `@type` into `shape.type_iri` before the property loop; the Rust target was looking for `@type` in `s.properties` and never finding it, making the `pub type_: String` + `default_type()` constructor emission dead code. **Fix:** consult `s.type_iri` directly. 21 of 24 generated modules now emit `@type` (the 3 without are pure enum-only files). (Finding 2.)
- **Missing test coverage on the 10 new fixtures.** None were in `STRICT_POSITIVE` (rkaf-validate) or as round-trip tests (rkaf-core). The BLOCKER above was invisible because the coverage gap concealed it. **Fix:** all 10 fixtures added to `STRICT_POSITIVE`; 9 new round-trip tests added (one per backlog class — Authority, Attestation, LocalAdoption, ApplicabilityScope, EffectivePeriod, LifecycleEvent, ConceptMapping, ConceptResolutionResult, BridgeValidationResult). Round-trip test count: 7 → 16. Total workspace test count: 20 → 36. (Finding 3.)

#### Disclosed (review-prompted API-break narrative)

The "no public API drift" claim in the prior CHANGELOG entry was wrong. The CUE→Rust pivot is a public API break, intentional and aligned with the v0.1 normative spec:

| Before | After | Rationale |
|---|---|---|
| `AssertionOrigin::HumanAuthored` | `AssertionOrigin::HumanAsserted` | Matches `archive/v0.1/spec/rkaf-core.md:21` ("rkaf:humanAsserted"). The previous Rust spelling was a hand-authored drift. |
| `Warrant::new(kind, family)` constructor | (removed) | Generated structs use `Warrant { type_: Warrant::default_type(), warrant_kind, warrant_family, ... }`. |
| `Assertion::new(origin)` constructor | (removed) | Same — direct struct literal construction. |
| `AssertionOrigin::is_ai_touched()` helper | (removed) | The v0.1 spec doesn't normatively define an AI-touched subset of origins; the helper was a Studio-side concern that incorrectly leaked into Layer 1. |
| (absent) | `AssertionOrigin::Imported` variant | New variant matching `archive/v0.1/spec/rkaf-core.md:21` ("rkaf:importedFromSource"). The hand-authored enum was missing this. |

Pre-release, no published crates.io consumer; the break is internal-only.

#### Gaps explicitly deferred (not blockers)

- **SHACL coverage of new vocab.** The 12 new CUE files do generate SHACL Turtle output (now in `compiled/shacl/core/`) — but the hand-authored `shapes/rkaf-shapes-*.ttl` files used by `tools/ci_validate.py` don't yet include the new classes. The CUE-source-of-truth SHACL is regenerated but not yet wired into the SHACL gate. This is intentional scope for a follow-up (the path is: switch `ci_validate.py` from hand-authored shapes to `compiled/shacl/` outputs).
- **Behavioral semantics (Layer 5).** The v0.1 `usageEligibility` reducer, `CascadeClosureV1` algorithm, and 10 bridge contract rules remain normative prose only (in `archive/v0.1/spec/rkaf-core.md`). They're not CUE-validatable shape; they're runtime contracts. A future `spec/rkaf-behavior.md` or `rkaf-runtime` crate would close this. Tracked in `spec/rkaf-vocabulary.md:94`.
- **`OneOrMany<T>` empty-array permissiveness.** The wrapper deserializes `[]` as `Many(vec![])`, bypassing `list.MinItems(N)` at the Rust layer. JSON Schema catches it on the validator side; the Rust layer trades type-strictness for round-trip parity. Documented in the lib.rs doc-comment.

#### Verified (post-fix)

- `cargo test --workspace`: **36 tests passing** (up from 20); zero failures.
- `tools/ci_validate.py` (SHACL): 20/20 pre-existing fixtures, 0 violations.
- `tools/validate_negatives.py`: 4/4 FAIL-AS-EXPECTED.
- `tools/constraints_parity.py`: 0 release blockers.
- `tools/projector_parity.py`: 7/7 round-trip OK.
- `tools/version_sync.py --check`: clean.
- `tools/rename_audit.py`: 0 findings.
- **All 10 new positive fixtures validate cleanly via `rkaf-validate`.**
- **All 10 new typed structs round-trip cleanly through `rkaf-core` serde.**

### Vocabulary backlog integration + CUE→Rust pipeline

**Closes the 17-term vocabulary backlog. The CUE source-of-truth is now the canonical generator for the Rust SDK as well as JSON Schema, SHACL, and TypeScript. Hand-authored Rust types are gone.**

#### Added

- **12 new CUE constraint files** under `constraints/core/`: `authority.cue`, `attestation.cue`, `local-adoption.cue`, `applicability-scope.cue`, `effective-period.cue`, `lifecycle-event.cue`, `concept.cue`, `concept-mapping.cue`, `concept-resolution-result.cue`, `bridge-validation-result.cue`, plus closed-enum lattices `usage-eligibility.cue` and `trust-and-safety.cue`.
- **24 generated Rust modules** under `crates/rkaf-core/src/generated/` — one per CUE source file. Drives the entire `rkaf-core` type surface from CUE.
- **10 new positive fixtures** under `fixtures/`: authority, attestation, localadoption, applicabilityscope, effectiveperiod, lifecycleevent, concept-registered, conceptmapping, conceptresolutionresult, bridgevalidationresult.
- **12 new embedded JSON Schemas** in `rkaf-validate` covering the new classes (`rkaf:Authority`, `rkaf:Attestation`, `rkaf:LocalAdoption`, …, `rkaf:BridgeValidationResult`).
- **`rkaf_core::OneOrMany<T>`** untagged-enum wrapper mirroring the JSON-LD wire shorthand (a property value may appear as either a single scalar or an array; the JSON Schema target emits `anyOf: [scalar, array]`, and this type accepts either).
- **22 new term declarations** in `context/rkaf-context.jsonld` for the new class IRIs + predicates (`hasApplicability`, `hasEffectivePeriod`, `derivesAuthorityFrom`, etc.).

#### Changed

- **`tools/constraints_compile.py` `--target rust`** rewritten. The output now matches the JSON-LD wire format: `@type` field with `default = "Class::default_type"`, `@id` as optional, properties renamed from `rkaf:foo` to idiomatic `foo` (no `rkaf_` prefix), `#[serde(flatten)] extra: BTreeMap<String, serde_json::Value>` catch-all for forward-compatibility, list types emitted as `crate::OneOrMany<T>` to handle the JSON-LD scalar-or-array shorthand. Cross-file enum references resolve to fully-qualified paths via the `_RUST_CROSS_FILE_ENUMS` registry (covers `UsageEligibility`, `AuthorityKind`, `TrustZone`, `SafetyLabel`).
- **`crates/rkaf-core/src/lib.rs`** is now a thin module index. The 8 hand-authored modules (`assertion.rs`, `warrant.rs`, `evidence.rs`, etc.) are deleted; their types now live in `generated/`. Top-level re-exports preserve the public API surface.
- **`spec/rkaf-vocabulary.md` §6** rewritten from "Vocabulary backlog — specified but not yet codified" to "Codified Vocabulary — additional terms," enumerating every codified class + enum + predicate with its CUE source, fixture, and purpose.

#### Removed

- `crates/rkaf-core/src/{access_scope,ai_lineage,artifact,assertion,confidence,evidence,source_fragment,warrant}.rs` — replaced wholesale by generated equivalents. No public API drift.

#### Verified

- `cargo test --workspace`: 20 `test result: ok` lines, zero failures.
- `tools/ci_validate.py` (SHACL): 20/20 fixtures pass, 0 violations, 114 triples.
- `tools/validate_negatives.py`: 4/4 FAIL-AS-EXPECTED.
- `tools/constraints_parity.py`: 0 CORE divergences (release blockers); 2 documented adversarial findings.
- `tools/projector_parity.py`: 7/7 round-trip fixtures pass.
- `tools/version_sync.py --check`: clean.
- `tools/rename_audit.py`: 0 findings.

#### Compatibility

Pre-release. The CUE source-of-truth pipeline is now end-to-end:

```
constraints/<class>.cue
  ↓ python3 tools/constraints_compile.py --target {json-schema, rust, typescript, shacl}
{compiled/json-schema/, crates/rkaf-core/src/generated/, compiled/typescript/, compiled/shacl/}
```

A future schema or vocab change should land as a CUE edit; all four targets regenerate. Hand-authoring Rust to match a CUE schema is now drift.

### Plan 6a: Rust SDK (Vocab + Validate + CLI)

**Three Rust crates land the first SDK surface: `rkaf-core` (typed Vocabulary primitives with serde round-trip), `rkaf-validate` (embedded v0.2 JSON Schema validator), and `rkaf-validate-cli` (the `rkaf-validate` binary).** This is the first time external code can pick up Rulespec without `git clone`-ing the repo or shelling out to the Python compiler.

#### Added

- `crates/rkaf-core/` — 8 typed primitives (Assertion, Warrant, EvidenceBinding, ConfidenceRecord, AccessScope, AILineage, Artifact, SourceFragment) with closed enums and JSON-LD-compatible serde derive. Each primitive carries a `#[serde(flatten)] extra` map preserving unknown properties through round-trip.
- `crates/rkaf-validate/` — `Validator` with all 8 v0.2 class schemas embedded via `include_str!` (no filesystem dependency at runtime). Exposes `validate(&node)` (single node) and `validate_document(&doc)` (walks `@graph` arrays). Unknown `@type` IRIs pass silently — outside our contract.
- `crates/rkaf-validate-cli/` — `rkaf-validate <file>` binary. Exit 0 on PASS, 1 on FAIL, 2 on setup error. `--json` emits a structured report.

#### Verified

- 16 v0.2 positive fixtures round-trip through their matching `rkaf-core` types byte-identically.
- **All 17 positive fixtures validate cleanly via `rkaf-validate`**. The two Appendix-C divergences surfaced during Plan 6a development were both closed in the same pass (see "Constraint compiler + fixture fixes" below).
- CLI integration tests cover PASS/FAIL/--json across positive and negative fixtures.
- Full workspace `cargo test --workspace` passes; `tools/ci_validate.py` (SHACL) passes 20/20; `tools/validate_negatives.py` passes 4/4 fail-as-expected.

#### Constraint compiler + fixture fixes

Plan 6a surfaced two real Layer 2/3 issues that previously produced JSON-Schema vs SHACL divergence on positive fixtures. Both are now fixed:

1. **`tools/constraints_compile.py` — bare `list.MinItems(N)` items.**
   The CUE → JSON Schema codegen treated a bare `list.MinItems(N)` (no item type constraint) as if the items were strings. The fix: leave `list_of_string` unset and emit `items: {}` (any) when neither an inner enum nor an explicit string item constraint is present. This affected `SourceFragment.hasSelector`, which on the wire is a structured OA selector object (`oa:TextQuoteSelector`, `oa:XPathSelector`, `rkaf:AktnEIdSelector`, `rkaf:USLMSectionSelector`).

2. **Cross-ref Assertion placeholders carry `assertionOrigin` now.**
   The `evidencebinding-{positive,no-evidence-reason-positive,missing-negative}` fixtures previously contained sparse `{"@type": "rkaf:Assertion", "@id": "…"}` nodes as cross-reference placeholders for the EvidenceBinding's `bindsAssertion`. SHACL targetClass validation didn't trip; JSON Schema `required` did. The fixtures now carry `"rkaf:assertionOrigin": "rkaf:humanAsserted"` on every Assertion node, matching the actual vocabulary contract.

After both fixes, every v0.2 positive fixture validates byte-identically across the JSON Schema (`rkaf-validate`) and SHACL (`tools/ci_validate.py`) gates. The `STRICT_POSITIVE` / `SHACL_ONLY_POSITIVE` split in the test source was retired.

#### Compatibility

Pre-release. The three new crates are versioned at workspace level (`0.2.0-pre.5`); their public API is small and stable enough for Plan 11 publication once the GitHub extraction lands.

## v0.2.0-pre.6 — Studio reference-consumer cutover (L2 + D3)

WOS Studio (Authoring) becomes the first Rulespec reference consumer at conformance level L2 (Shape) and adoption depth D3 (Derive). The L3 (Constraint) gate requires SHACL + Pattern-C validation and is disclosed as a path-to-close in the partner YAML.

### Added — Studio profile

- `profiles/studio/schema-source/` is the Rulespec-owned Studio profile in JSON Schema form (18 authoring + 6 api). `profiles/studio/schemas-derived/` is the projector output; `derive.sh` runs the projector. `profiles/studio/SHA256SUMS` pins the derived surface.
- The current cutover is conservative: `derive.sh` is an identity copy. The JSON Schema source-of-truth carries authoring prose, x-lm hints, examples, and $defs that the current Layer-4 CUE projector cannot yet reproduce. CUE-projection upgrade is documented as future work; the schema-source/ → schemas-derived/ projector-output discipline is what underpins the D3 declaration.

### Added — Cross-submodule overlay emission + lint

- `policy-studio/crates/wos-studio-compiler` (sibling submodule) now emits `x-rkaf-overlay` on every artifact (wos-workflow.json, compile-manifest.json, workspace-export.bundle.json). Each overlay carries a 4-node `@graph`: an Artifact node (`wos:Workflow` on the workflow — WOS canonical substrate type; `rkaf:Artifact` on the manifest + bundle) plus `rkaf:Assertion` + `rkaf:Warrant` + `rkaf:AccessScope`. Determinism is preserved — `rkaf:emittedAt` derives from the manifest hash, not wall clock — so byte-identical SNAP gate continues to hold.
- `policy-studio/crates/wos-studio-lint` gains the overlay-grounded rule tier, validating every emitted `rkaf:*` node against PKAF's compiled v0.2 vocabulary schemas via `rkaf-validate` (JSON Schema only). Non-`rkaf:*` nodes (e.g. the workflow's `wos:Workflow` root) are silently passed by design.

### Added — Conformance disclosure

- `conformance/partners/policy-studio.yaml` files Studio's L2 + D3 declaration with explicit provisional notes (L3 SHACL gate path, warrant chain, access scope default, JSON-Schema-vs-CUE source form, non-object carriers).
- Studio's conformance report lives at `policy-studio/conformance-reports/L2-report.json` in the partner submodule.

### Provisional — disclosed honestly

- **L3 (Constraint) path.** Studio's overlay-grounded gate is JSON-Schema-only via `rkaf-validate`. L3 per `spec/rkaf-conformance.md` additionally requires SHACL + Pattern-C cross-property invariants. Promote `conformance_level: "L2"` → `"L3"` when a SHACL gate lands and runs green against the SNAP slice.
- **Warrant chain.** All emitted `rkaf:Warrant` nodes carry `rkaf:provisionalUntilSourceAuthorityWired: true`. Wiring SourceAuthority records into overlay emission is Studio Stage-8 work.
- **AccessScope default.** All emitted `rkaf:AccessScope` nodes default to `rkaf:organizationVisible` scoped to workspace; per-assertion classification (HIPAA-PHI / GDPR-PII) flows from source-classification records in Stage-8.
- **CUE-projection upgrade.** Deferred until the Layer-4 CUE projector can round-trip authoring prose, x-lm hints, examples, and $defs without loss.
- **Non-object carriers.** scenarios.json + compile-events.jsonl have no root-object slot for `x-rkaf-overlay`; per-scenario provenance is carried indirectly via the workspace-export bundle's overlay.

### Future reference consumers

Per source spec §14.3, no framework-side requirement that future partners adopt at D3+. Studio's depth-D3 commitment is a Studio commitment, not a framework requirement.

## v0.2.0-pre.5 — Layer 4 Projectors (MVP triangle)

**Three bidirectional projectors landed: JSON Schema 2020-12, JSON-LD 1.1, OpenAPI 3.1. Each implements the source spec §8.1 contract (Attach, Extract, Validate, RoundTrip, Derive). Round-trip parity is the release gate.**

### Added

- `crates/Cargo.toml` — workspace root for the Layer 4 Rust crates.
- `crates/rkaf-projector-core/` — `Projector` trait per source spec §8.1.
- `crates/rkaf-projector-json-schema/` — JSON Schema 2020-12 projector. Carrier convention: root `x-rkaf` extension key (`{rkaf-version, rkaf-depth, "rkaf:overlay"}`). Validate uses `jsonschema` Rust crate against compiled v0.2 schemas. Derive shells out to `tools/constraints_compile.py --target json-schema`.
- `crates/rkaf-projector-json-ld/` — JSON-LD 1.1 projector. Carrier convention: `@graph` merge, type-namespace partition (`rkaf:` prefix → overlay) on Extract; context-array single-element collapse preserves byte-equality on common-shape inputs.
- `crates/rkaf-projector-openapi/` — OpenAPI 3.1 projector. Carrier convention: document-level `x-rkaf` extension. Derive wraps the JSON Schema target's `$defs` into a complete OpenAPI 3.1 document with populated `components.schemas`.
- `crates/projector-harness/` — CLI binary used by `tools/projector_parity.py` to exercise Attach/Extract/RoundTrip and Derive across all three targets.
- `spec/projectors/json-schema-v0.2.md` — JSON Schema carrier convention v0.2 (normative subordinate).
- `spec/projectors/json-ld-v0.2.md` — JSON-LD carrier convention v0.2 (normative subordinate).
- `spec/projectors/openapi-v0.2.md` — OpenAPI 3.1 carrier convention v0.2 (normative subordinate).
- `tools/projector_parity.py` — round-trip parity orchestrator (release gate).
- `fixtures/v0.2/projectors/{json-schema,json-ld,openapi}/round-trip-*.{jsonld,yaml}` — 7 round-trip fixtures covering SNAP redetermination, warrant chains, empty overlays, and OpenAPI source-authority API documents.

### Verified

- 9 projector unit tests pass (3 per projector: identity round-trip, attach-collision refusal, extract-collision refusal).
- 7/7 round-trip fixtures pass byte-identical Attach → Extract through the harness binary.
- Derive operation produces parseable JSON Schema, JSON-LD context fragment, and OpenAPI 3.1 documents end-to-end via subprocess to `tools/constraints_compile.py`.
- CI workflow `constraints-parity.yml` now builds the Layer 4 crates, runs `cargo test --workspace`, and exercises the projector parity orchestrator.

### Conformance

All three projectors implement the full §8.1 contract: Attach, Extract, Validate (delegated to JSON Schema in JSON-LD/OpenAPI for v0.2 MVP; per-node-validate loop deferred to Layer 5 SDKs), RoundTrip (default trait impl), Derive. Round-trip parity verified across the fixture set; the Studio-profile Derive output (Gate C of the master sequence) is the next gate to land in Plan 10 (Studio cutover), which depends on a published Studio profile.

### Compatibility

Pre-release. The reference Validate implementations in JSON-LD and OpenAPI projectors are stubs that return `Ok(())`; the production Validate composition (loop overlay nodes, validate each against compiled JSON Schema by `@type`) lands with the Layer 5 SDK harness in Plan 6. The MVP triangle's correctness contract is round-trip identity, asserted in CI.

## v0.2.0-pre.3 — Layer 2 Constraints

**CUE selected as constraint source language. JSON Schema 2020-12, Rust, TypeScript are MUST targets; SHACL, CUE-passthrough, Rego are MAY targets.**

### Added

- `docs/adr/2026-05-12-rkaf-constraint-source-cue.md` — selection rationale.
- `constraints/core/*.cue` — CUE source for every v0.2 vocabulary primitive (artifact, source-fragment, evidence-binding, warrant, confidence-record, access-scope, ai-lineage, retention-policy, workspace, mapping-state, assertion, concept-registry).
- `constraints/adversarial/*.cue` — 5 evaluator-class adversarial constraints (conditional-silent-pass, cross-property-coupling, enum-drift, access-scope-leakage, nested-noevidencereason) per spec §10.1.
- `constraints/ai-extraction/*.cue` — 3 LLM-systematic-misinterpretation adversarial constraints (warrant-family-confusion, consent-vs-warrant, confidence-score-without-method) per spec §10.1.
- `tools/constraints_compile.py` — CUE → {JSON Schema, Rust, TypeScript, SHACL, CUE, Rego} compiler. Recognizes Rulespec's regular CUE patterns (closed enums, enum-of-refs unions, shapes, conditionals, disjunctions, list cardinality).
- `tools/constraints_parity.py` — cross-target parity orchestrator (release gate). Asserts JSON Schema + SHACL classify every CORE fixture identically; documents adversarial-fixture divergences (which by design surface evaluator-class gaps).
- `tools/install-cue.sh` — pinned CUE 0.10.0 installer.
- `.tool-versions` — `cue 0.10.0`.
- `compiled/{json-schema,rust,typescript,shacl,cue,rego}/` — generated artifacts (gitignored; reproducible from CUE source).

### Changed

- SHACL is demoted from authoritative status (per source spec Appendix C). The hand-written shape files in `shapes/` (v0.1 and v0.2) remain in tree for transition; `compiled/shacl/` is the canonical SHACL output going forward, Pattern C only by construction.

### Verified

- 18/18 core Vocabulary fixtures pass parity across JSON Schema + SHACL targets, identical PASS/FAIL classification, all matching expected outcomes.
- 8 adversarial fixtures: 6/8 surface their designed evaluator-class divergence (SHACL accepts what JSON Schema rejects in cross-property / inline-enum cases — this is the documented gap, not a regression).
- 0 `sh:if` / `sh:then` constructs in `compiled/shacl/` — Pattern C lint passes.
- All v0.2 CUE source files vet successfully (`cue vet`).

### Compatibility

Pre-release. v0.1.x SHACL shape files do not interoperate with v0.2 compiled artifacts. No migration shim.

## v0.2.0-pre.2 — Vocabulary v0.2

**Vocabulary Layer 1 lands. Pre-release; CHANGELOG-driven; no compatibility with v0.1.x.**

### New first-class primitives (§§4.1-4.6 of `spec/rkaf-core-v0.2.md`)

- `rkaf:Artifact` with `artifactIdentifierScheme` closed enum (eli, eli-dl, eli-i, uslm, aknt-eId, doi, isbn, issn, cid, hash-sha256, urn-persistent, partner-defined).
- `rkaf:SourceFragment` composing the W3C Web Annotation (`oa:`) selector vocabulary plus domain-specific selectors (Akoma Ntoso eId, USLM section, ELI fragment, JSONPath, DOI fragment).
- `rkaf:EvidenceBinding` with the operational-validity invariant (≥1 source fragment OR a permitted `noEvidenceReason`).
- `rkaf:Warrant` as the universal grounding primitive; `rkaf:Authority` preserved as the legal-family specialization. Six warrant families: legal, scientific, editorial, cryptographic, social, source-class.
- `rkaf:ConfidenceRecord` with `calibrationStatus` + `confidenceBasis` + `generatedBy` required (rejects "score theater").
- `rkaf:AccessScope` with seven kinds plus DPV / ODRL alignment for regulatory and rights cases.

### Studio-derived promotions (§5)

- `rkaf:MappingState` (closed four-value enum: `mapsToWos`, `authoringOnly`, `requiresSpecExtension`, `unmappedButApproved`).
- `rkaf:RetentionPolicy` with `retentionTrigger` and `retentionPostExpiry` closed enums.
- `rkaf:AILineage` with mandatory `humanApprover`.
- `rkaf:llmHint` annotation property (carried through the JSON Schema projector as `x-rkaf-llmHint`).
- `rkaf:Workspace` scoping with `workspaceId` + `workspaceTrustList`.
- `rkaf:projectsTo` (generalizes Studio's `wosTarget`).

### Abstract anchoring contract (§7)

- `rkaf:anchoredBy` / `rkaf:anchorType` predicates; concrete bindings (Trellis, COSE, VC, Sigstore, IPFS) live outside Rulespec and depend on this contract.

### Public ontology composition (§9)

- Imports: PROV-O, OA, SKOS, DCTERMS, CiTO, DCAT, RDF/RDFS/XSD, SHACL.
- Alignments: ELI / ELI-DL / ELI-I, RRMV, Akoma Ntoso, USLM, LegalRuleML, ECO / SEPIO, Nanopublications, ODRL, DPV, Schema.org / Schema.org-Legislation, DCAT / VoID.
- Projections (carried by Layer 4 projectors, Plan 5): JSON Schema, JSON-LD, OpenAPI 3.1 (MVP).

### Shape files (compiled SHACL targets — not source of truth per Layer 2 plan)

- `shapes/rkaf-shapes-core-v0.2.ttl` (umbrella)
- `shapes/rkaf-shapes-warrant-v0.2.ttl`
- `shapes/rkaf-shapes-confidence-v0.2.ttl`
- `shapes/rkaf-shapes-accessscope-v0.2.ttl`
- `shapes/rkaf-shapes-studio-promotions-v0.2.ttl`
- `shapes/rkaf-shapes-conceptregistry-v0.2.ttl`

Pattern C only (per Appendix C of source spec). Zero `sh:if` / `sh:then` constructs.

### Companion specs

- `spec/rkaf-core-v0.2.md` (normative).
- `spec/rkaf-concept-registry-v0.2.md` (SKOS-bound mapping predicates, workspace scoping, generalized warrant on mappings; supersedes v0.1.2).
- `spec/rkaf-vocabulary-v0.2.md` (full term reference; mechanically consumable).

### Fixtures (`fixtures/v0.2/`)

20 positive + 4 negative fixtures. Coverage requirement (`tools/vocab_audit.py`): every Vocabulary class exercised by ≥1 fixture.

### Tooling

- `tools/vocab_audit.py` — fails build if a v0.2 term has no fixture.
- `tools/validate_negatives.py` — asserts negative fixtures FAIL as designed.
- `tools/ci_validate.py --mode v02` — full v0.2 positive-fixture validation.

### Compatibility

None with v0.1.x. v0.2 supersedes wholesale.

## v0.2.0-pre.1 — Brand rename: PKAF → Rulespec

- The framework is renamed to **Rulespec** (acronym **RKAF**, "Rulespec Knowledge Assertion Framework").
- Vocabulary prefix `pkaf:` is renamed to `rkaf:` everywhere in shapes, JSON-LD contexts, fixtures, and spec bodies.
- IRI namespace `https://w3id.org/pkaf/` is renamed to `https://rulespec.org/`.
- Bridge contract identifier `pkaf-bridge/1.0` is renamed to `rkaf-bridge/1.0`.
- All `pkaf-*` artifact filenames are renamed to `rkaf-*` (`spec/pkaf-core-v0.1.md` → `spec/rkaf-core-v0.1.md` etc.).
- This is a wholesale rename. There is no compatibility shim and no `pkaf:` prefix is supported in v0.2 or later.

## [v0.1.1] — 2026-05-12 — Structural validation fix and consumer-justification shapes

### Added

- **Consumer artifact overlay shape vocabulary** (`shapes/rkaf-shapes-justification-v0.1.ttl`)
  - `GeneratedWorkProductJustificationShape` — validates the Rulespec overlay type
  - `ConsumerArtifactJustificationShape` — universal shape targeting subjects of `rkaf:justifiedByAssertion`
  - `DataCollectionArtifactJustificationShape` — universal shape targeting subjects of `rkaf:collectsEvidenceType`
  - `ProcessArtifactJustificationShape` — universal shape targeting subjects of `rkaf:requiresEvidenceType`
  - `FullBridgeValidationResultShape` — structured output requirement on non-accepted bridge results
  - `JustificationChainHopShape` — allows `rkaf:implements` predicate (distinct from `AuthorityChainHop`)
  - `FormspecFieldJustificationShape` — documented example specialization
  - `WOSStepJustificationShape` — documented example specialization

- **Multi-mode CI gate** (`tools/ci_validate.py --mode core | batch2 | batch3 | batch4`)
  - Four conformance modes selectable via flag
  - Per-fixture triple-count drift detection
  - JSON output mode for CI pipelines

- **Public framing as universal ontology**
  - README rewritten: Rulespec positioned as universal evidence-backed assertion / authority / concept / lifecycle / justification ontology
  - Consumer systems (search engines, wikis, form builders, workflow engines, case systems, content management, AI assistants, publication tools, auditing tools, knowledge graphs) framed as examples, not anchors
  - Fixtures explicitly labeled as stress tests for the consumer overlay pattern, not dependencies

### Fixed

- **pySHACL `sh:if`/`sh:then` evaluation bug.** Eight conditional shapes across Batches 1.1, 2, 3, and 4 were not actually firing as designed. All eight rewritten using Pattern C (`sh:or` with `sh:not`), which pySHACL evaluates reliably:
  - `BridgeValidationResultShape` (Batch 1.1) — rejected → remediation OR noRemediationReason
  - `OperationalAssertionEvidenceShape` (Batch 1.1) — R2/A3/P4 → hasEvidence required
  - `AuthorityAssertionShape` (Batch 1.1) — A3 → authorityKind + hasApplicability + qualified evidence
  - `MappingAssertionShape` (Batch 2) — closeMatch + operational → MappingApplicabilityContext
  - `ConceptLifecyclePacketShape` (Batch 2) — split/merge/replacedBy → successorConcepts
  - `MappingConflictShape` (Batch 2) — operational/publicationBlocking severity → artifact reference
  - `RevalidationClosureEventShape` (Batch 3) — revalidatedWithSuccessor → successor reference
  - `FullBridgeValidationResultShape` (Batch 4) — non-accepted → structured indicator

- **Six latent fixture defects** surfaced by the corrected constraints, all patched:
  - `amend-001` (local-operational): added `authorityKind = rkaf:organizational` and `ApplicabilityContext`
  - `rescission-001` (statutory): added `authorityKind = rkaf:statutory` and `ApplicabilityContext`
  - `delegation-derives-from-statute` (statutory): added `ApplicabilityContext`
  - `regulation-derives-from-delegation` (statutory): added `ApplicabilityContext`
  - `caa-42-2026-07-01-001` (mapping): added structured `warnings` entry
  - `case-4-unreachable` (registry-failure-conflict): added `noRemediationReason = rkaf:noActionableRemediation`

### Changed

- **Triple count:** 1,186 → 1,206 (+20 from fixture defect patches)
- **Shape implementation:** Pattern C rewrites change all eight conditional shape SHA-256 hashes (semantics unchanged)
- **JSON-LD context:** `_meta` block added to `rkaf-context-v0.2.jsonld` documenting it as a strict additive superset of v0.1

### Unchanged from v0.1-rc1

- **Specification text** (`spec/rkaf-core-v0.1.md`, `spec/rkaf-concept-registry-v0.1.2.md`) — semantically identical
- **Fixture narratives** — substantively identical
- **Vocabulary** — no new terms added; only the additive `rkaf:definedInScope` context typing carried forward from Batch 2

### Conformance signature

```
Mode:       batch4 (Core + ConceptRegistry + Lifecycle + Justification)
Shapes:     4 files
Fixtures:   4
Triples:    1,206
Violations: 0
Result:     PASS
```

### Coverage gaps accepted

Four shapes have no fixture target. They remain structurally correct and will activate when future fixtures instantiate the relevant entity type:

- `ConceptMintingAuthorityShape` — full mint-authority instances not exercised
- `SupersessionPacketShape` — full-document supersession not exercised
- `MaterialRevisionPacketShape` — material revision distinct from amendment not exercised
- `JustificationChainHopShape` — justification chains with `rkaf:implements` predicate not exercised

---

## [v0.1-rc1] — 2026-05-12 — Initial release candidate

### Added

- **Rulespec Core specification** (`spec/rkaf-core-v0.1.md`)
  - Assertions, evidence, attestations, adoption, authority chain
  - Bridge model and consumer artifact overlay
  - Lifecycle packets, revalidation, point-in-time exceptions
  - Cascade closure algorithm specification

- **ConceptRegistry specification** (`spec/rkaf-concept-registry-v0.1.2.md`)
  - Registered concepts, local concepts, mappings
  - Mapping applicability contexts
  - Concept resolution and usage ceiling
  - ConceptRegistry-Core / Lifecycle / Federated conformance levels

- **JSON-LD context** (`context/rkaf-context-v0.1.jsonld`)

- **Core SHACL shapes** (`shapes/rkaf-shapes-core-v0.1.ttl`)
  - 8 shape sets covering trust zones, assertions, evidence, attestations, adoption, authority, applicability, bridge validation

- **Four conformance fixtures**
  - `local-operational-v0.2.jsonld` — CSBG eligibility lifecycle
  - `mapping-v0.1.jsonld` — Concept registry mappings
  - `statutory-authority-v0.1.jsonld` — Statutory rescission with authority chain
  - `registry-failure-conflict-v0.1.jsonld` — Nine registry failure scenarios

- **Multi-pass validation arc:** 251 → 14 → 0 violations
- **1,183 triples, 0 violations** at v0.1-rc1 freeze

### Known issues at v0.1-rc1 (discovered and fixed in v0.1.1)

- Three conditional shapes (`BridgeValidationResultShape`, `OperationalAssertionEvidenceShape`, `AuthorityAssertionShape`) used the `sh:if`/`sh:then` SHACL Advanced Features pattern which pySHACL 0.31.0 does not evaluate reliably. The constraints existed in the TTL files and parsed correctly, but did not fire against fixture data. v0.1-rc1 fixtures *happened to* mostly satisfy these constraints but four latent defects were hidden by the broken evaluation. All addressed in v0.1.1.
