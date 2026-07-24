# Rulespec US Rulemaking-Process Module

**Status:** Experimental.
**Companion docs:** `spec/rkaf-core.md`, `spec/rkaf-vocabulary.md`, `spec/rkaf-conformance.md`.

> Instability warning: these terms ship under the normal release-bound closed-taxonomy rules, but their shapes may change between pre-1.0 releases. The full-corpus consumer exercise has completed. The 2026-07-24 maintainer-operated adversarial simulation found a required repair batch and did not satisfy the non-originating-consumer gate. The module does not advance to pre-release normative status until the §8 requirements hold.

## 0. Conformance language

RFC 2119 / RFC 8174 keywords are normative when uppercase.

## 1. Scope

This module models the proceeding that produces a US federal regulation: its identity, current stage when known, public-comment intervals, published documents, affected CFR units, lifecycle events, and authority chain. It composes the universal Rulespec primitives instead of creating a second document, authority, or lifecycle system.

The module does not model comment content, commenter identity, campaign detection, or descriptive topic tags.

## 2. Proceeding

`rkaf:Proceeding` represents one rulemaking proceeding. It is distinct from a regulations.gov docket: a proceeding may span several dockets, and a docket may contain activity from several proceedings.

Required properties:

- `rkaf:hasProceedingIdentifier` (1) — an IRI that identifies the proceeding,
  never a docket or published document.
- `rkaf:proceedingIdentifierScheme` (1) — `rkaf:us-rin` or
  `rkaf:official-registry` or `rkaf:partner-defined`. An
  `rkaf:official-registry` identifier also requires
  `rkaf:identifierRegistry` (1), the IRI of the issuing registry.

Optional properties:

- `rkaf:proceedingStage` (0..1) — one value from the closed enum
  `rkaf:proceedingPrerule`, `rkaf:proceedingProposed`,
  `rkaf:proceedingSupplemental`, `rkaf:proceedingFinal`,
  `rkaf:proceedingWithdrawn`, `rkaf:proceedingLongterm`, or
  `rkaf:proceedingConcluded`. Absence means the current stage is unknown.
  Producers MUST NOT infer a stage from missing evidence.
- `rkaf:proceedingTerminationCause` (0..1) — one of
  `rkaf:agencyWithdrawal`, `rkaf:judicialVacatur`,
  `rkaf:congressionalDisapproval`, or `rkaf:administrativeConclusion`.
  It is REQUIRED when the stage is `rkaf:proceedingConcluded`. A partial
  judicial action does not by itself conclude the whole proceeding.
- `rkaf:hasAuthority` (0..*) — IRI of an evidenced issuing or grounding
  `rkaf:Authority`. Absence means unknown. A producer MUST NOT mint an
  Authority from agency identity alone merely to satisfy this property. When a
  source supplies a legal citation, the producer SHOULD emit the edge and its
  authority chain.
- `rkaf:hasDocket` (0..*) — IRI of an associated `rkaf:Docket`. Docket
  membership never establishes proceeding identity.
- `rkaf:hasProceedingEvidenceIdentifier` (0..*) plus
  `rkaf:proceedingEvidenceIdentifierScheme` (0..1) — repeatable non-identity
  evidence, normally one or more `rkaf:us-rin` values, retained when the
  Proceeding itself needs a partner or official-registry identifier. All
  evidence values on one Proceeding use the declared common scheme; split
  mixed-scheme evidence into separately typed assertions.
- `rkaf:proceedingSupersedes` (0..*) — directional link to predecessor
  Proceedings after a merge, split, replacement, or identity repair. This
  relation preserves continuity and MUST NOT be replaced by listing predecessor
  and successor together in lifecycle `appliesTo`, which would corrupt cascade
  semantics.
- `rkaf:proceedingAffectsCitation` (0..*) — a normalized `rkaf:us-cfr`
  citation known to be targeted, even when the applicable edition has not been
  resolved.
- `rkaf:proceedingAffects` (0..*) — IRI of the edition-scoped CFR
  `rkaf:Artifact` in force immediately before the proposed or final amendment.
- `rkaf:proceedingProduces` (0..*) — IRI of an immutable resulting edition or
  publication Artifact produced by the proceeding.

The canonical RIN form is
`urn:rkaf:us:rin:<four-digits>-<two-uppercase-letters><two-digits>`, for example
`urn:rkaf:us:rin:2060-AV16`. A producer that splits an action family because a
RIN was reused MUST assign each resulting Proceeding a stable,
partner-scoped persistent identifier instead of treating the reused RIN as a
globally unique key. It MUST retain the RIN through
`rkaf:hasProceedingEvidenceIdentifier`; a split never discards the evidence
that motivated it.

`rkaf:hasProceedingIdentifier` MUST NOT contain a
`urn:rkaf:us:regsgov:*` value under any scheme. That value identifies a docket,
document, or comment, never a Proceeding.

### 2.1 Docket

`rkaf:Docket` represents a mutable administrative container. It is neither an
immutable `rkaf:Artifact` nor a `rkaf:Proceeding`.

Required properties:

- `rkaf:hasDocketIdentifier` (1) — an IRI identifying the docket.
- `rkaf:docketIdentifierScheme` (1) — `rkaf:us-regsgov` or
  `rkaf:official-registry` or `rkaf:partner-defined`. The official-registry
  form also requires `rkaf:identifierRegistry` (1).

For a regulations.gov docket, the canonical identifier is
`urn:rkaf:us:regsgov:<agency-issued-id>`, for example
`urn:rkaf:us:regsgov:EPA-HQ-OAR-2021-0317`. Normalize ASCII letters to
uppercase and preserve agency-issued hyphen or underscore separators. The
grammar includes source-owned identifiers such as
`urn:rkaf:us:regsgov:EPA_FRDOC_0001`. A docket may link to several Proceedings,
and a Proceeding may link to several dockets.

`rkaf:official-registry` distinguishes an official identifier for systems such
as FCC ECFS, FERC eLibrary, or SEC rulemaking from a partner-minted surrogate.
It does not assert a universal grammar; `rkaf:identifierRegistry` names the
issuer and the producer preserves the issuer's identifier exactly.

## 3. Comment periods

`rkaf:CommentPeriod` represents one continuous interval during which the public may submit comments.

Required properties:

- at least one anchor: `rkaf:commentPeriodFor` (0..*) naming Proceedings or
  `rkaf:commentPeriodDocket` (0..*) naming Dockets. A period may carry both and
  may name multiple Proceedings for a joint action.
- `rkaf:commentPeriodStart` (1) — `xsd:date`.
- `rkaf:commentPeriodEnd` (1) — `xsd:date`, on or after `rkaf:commentPeriodStart`.
- `prov:wasDerivedFrom` (1..*) — IRI of a `prov:Entity` that carries the
  source evidence for this interval.

`rkaf:commentPeriodOpenedBy` (0..*) names the notice or other Artifact that
solicited comment. It is distinct from `prov:wasDerivedFrom`: the former names
the subject-opening document, while the latter records the evidence used to
construct the interval.

A reopening is a new CommentPeriod node linked to the same Proceeding.
Producers MUST NOT overwrite the earlier interval or stretch it across a
closed gap. When sources disagree or one source supplies an invalid interval,
producers MUST preserve the qualified evidence separately and MUST NOT emit an
unsupported CommentPeriod.

Start and end are inclusive calendar days in the deadline's governing
timezone. For Regulations.gov and Federal Register deadlines, the governing
timezone is US Eastern unless the source expressly specifies another one. A
producer deriving a date from an instant MUST convert the instant into the
governing timezone before truncating it to `xsd:date`; UTC truncation is
non-conforming when it changes the source's calendar day.

## 4. Published documents

Federal Register documents remain ordinary `rkaf:Artifact` nodes.
`rkaf:hasArtifactIdentifier` identifies the immutable publication, normally
with its permanent federalregister.gov document URL, while
`rkaf:hasRegulatoryIdentifier` may carry the normalized `rkaf:us-frdoc`
identifier. `rkaf:publishedInProceeding` links an Artifact to one or more
Proceedings.

The `rkaf:us-frdoc` grammar is deliberately strict. If an official source
document number does not match `YYYY-NNNNN`, the Artifact MUST still use its
permanent federalregister.gov document URL as
`rkaf:hasArtifactIdentifier` with `rkaf:artifactIdentifierScheme:
rkaf:urn-persistent`, and the producer MUST NOT label the source value
`rkaf:us-frdoc`. This is the normative fallback for legacy, correction, and
other source-preserved forms.

The relation also applies to a Unified Agenda entry represented as an Artifact. Rulespec defines no Federal Register subclass and no Unified Agenda subclass.

### 4.1 Cross-posted documents

A rulemaking document routinely appears in more than one registry: the same
proposed rule is a Federal Register document and a regulations.gov docket
document. Each posting is a distinct immutable publication, so each posting is
its own `rkaf:Artifact` (core §4.1):

- The Federal Register posting uses its permanent federalregister.gov URL as
  Artifact identity and MAY carry the `rkaf:us-frdoc` citation.
- The regulations.gov posting uses its permanent
  `https://www.regulations.gov/document/<id>` URL as Artifact identity and MAY
  carry the `rkaf:us-regsgov` citation.

A producer MUST NOT collapse the postings into one Artifact carrying two
regulatory-identifier pairs. Two nodes represent the same posting if they
share a `rkaf:hasArtifactIdentifier` value; producers SHOULD use the permanent
publication URL as `@id` so that identity converges without a merge heuristic.
When one producer emits both postings, it MUST link the Federal Register
posting to the Regulations.gov posting with `dcterms:hasFormat`; it SHOULD
also emit the inverse `dcterms:isFormatOf`. Both are mode-1 imported predicates
with Artifact domain and range. Every posting Artifact MAY assert
`rkaf:publishedInProceeding`; consumers that need one node per underlying work
unify through the format links, never merely because the postings share a
Proceeding. Relations whose range is a specific edition — such as
`rkaf:proceedingAffects` and `rkaf:derivesAuthorityFrom` — target whichever
posting Artifact carries the edition being cited, not "the document" in the
abstract.

## 5. Lifecycle events

Proceeding stage transitions use `rkaf:LifecycleEvent`; this module defines no
parallel event class. For the stage-family kinds, every `rkaf:appliesTo` value
MUST be a Proceeding, and `rkaf:effectiveDate` records the transition time.

The `rkaf:lifecycleEventKind` closed enum adds:

| Event kind | Meaning |
|---|---|
| `rkaf:proceedingPrerule` | The proceeding entered prerule development. |
| `rkaf:proceedingProposed` | The agency published or formally entered the proposed-rule stage. |
| `rkaf:proceedingSupplemental` | The agency published or entered a supplemental-proposal stage. |
| `rkaf:proceedingFinal` | The agency published or entered the final-rule stage. |
| `rkaf:proceedingWithdrawn` | The agency withdrew the proceeding. |
| `rkaf:proceedingLongterm` | The agency placed the proceeding on the long-term agenda. |
| `rkaf:proceedingConcluded` | Evidence establishes that the proceeding ended without another stage value accurately describing the terminal state. |

External legal events use these additional closed values:

| Event kind | Meaning |
|---|---|
| `rkaf:proceedingVacated` | A court vacated all or part of a produced rule. |
| `rkaf:proceedingStayed` | A court stayed operation of all or part of a produced rule. |
| `rkaf:proceedingRemanded` | A court remanded all or part of the action. |
| `rkaf:proceedingReinstated` | A later legal event restored a previously displaced action. |
| `rkaf:proceedingDisapproved` | Congress disapproved all or part of the action. |

An external legal event MUST name at least one Proceeding in `rkaf:appliesTo`.
It MAY additionally enumerate affected CFR-unit Artifacts from the
Proceeding's target/produced set, allowing partial vacatur, stay, remand,
reinstatement, or disapproval to preserve severability. An Artifact target
does not imply that every other target shares the legal effect.

`rkaf:proceedingStage` records agency procedural progress or an evidenced
conclusion. It does not assert that a rule is legally effective, operative,
valid, or enforceable; external legal events carry those facts. LifecycleEvent
nodes preserve the event sequence that produced the stage. When stage-family
events exist, `rkaf:proceedingStage` MUST equal the
`rkaf:lifecycleEventKind` of the latest such event. Equal latest timestamps
with different kinds are conflicting evidence and MUST NOT yield a current
stage. No lifecycle event means unknown, not prerule. A final-stage proceeding
SHOULD carry the corresponding `rkaf:proceedingFinal` event.

## 6. Targets and authority

`rkaf:proceedingAffectsCitation` is the producible citation-level relation for
bulk sources. Its values use the `rkaf:us-cfr` grammar, including
letter-suffixed sections such as
`urn:rkaf:us:cfr:40:60.5375a`. The relation records a known target without
pretending that an edition has been resolved.

`rkaf:proceedingAffects` is the stronger relation to the CFR-unit Artifact in
force immediately before the amendment. Each target MUST identify a specific
immutable CFR edition or snapshot through `rkaf:hasArtifactIdentifier`; its
edition-independent citation may be carried separately through
`rkaf:hasRegulatoryIdentifier`. `rkaf:proceedingProduces` names the immutable
post-action edition or publication. A compact citation alone supports
`proceedingAffectsCitation`, not `proceedingAffects`. Producers SHOULD upgrade a
citation edge after resolution without deleting the citation evidence.

Statutory grounding uses the existing authority chain:

```text
rkaf:Proceeding
  └─ rkaf:hasAuthority → rkaf:Authority
       └─ rkaf:derivesAuthorityFrom → rkaf:Artifact
            ├─ rkaf:hasArtifactIdentifier → edition-scoped GovInfo URI
            ├─ rkaf:hasRegulatoryIdentifier → urn:rkaf:us:usc:42:7411
            └─ rkaf:regulatoryIdentifierScheme → rkaf:us-usc
```

Public-law and Executive-order artifacts MAY appear in the same chain with `rkaf:us-pl` and `rkaf:us-eo`.

The general module permits unknown authority. A decision-grade consumption
profile MUST require `rkaf:hasAuthority` and MUST verify that every required
chain resolves through edition-scoped Artifacts before relying on the
Proceeding for a legal or eligibility decision.

## 7. Composition

ELI-DL is the EU draft-legislation analog for pre-enactment lifecycle. This
module cites ELI-DL as a mode-4 architectural pattern; it imports no ELI-DL
predicate. Promotion to an alignment row requires an EU-corpus consumer with a
tested binding.

`dcterms:hasFormat` and `dcterms:isFormatOf` are mode-1 predicate imports for
Artifact-to-Artifact cross-posting links. Rulespec does not redefine their
meaning.

## 8. Experimental stabilization gate

The module remains Experimental until both conditions hold:

1. A consumer runs `Proceeding`, `proceedingStage`, `CommentPeriod`, and `publishedInProceeding` across a full regulatory corpus and publishes a friction report covering multi-docket proceedings, reopened comment periods, and stage sequences.
2. A non-originating consumer reviews the terms and shapes.

The Spicy Regs full-corpus report dated 2026-07-23 satisfied condition 1 for
the earlier contract and produced the identity, provenance,
identifier-fallback, and unknown-stage rules above. The repaired contract
repeated that exercise on 2026-07-24. Its paired receipt binds Rulespec commit
`d81fb29e5673fd9459723fe36fdde4f16358c19c`, Spicy Regs commit
`3a032d26138c0d99d518e1dbfca20fa1a6e4c0b2`, contract digest
`sha256:ea9b899ba92955b83638ece811d7a4b744dd912f72e19290e32c97508674de1c`,
and candidate snapshot `snapshot_04ebfb14969691c54af2c3cc31a28be4`.
The paired build, corpus validation, and full repository gates passed, so
condition 1 is satisfied for the repaired contract.

A maintainer-operated adversarial simulated-consumer review dated 2026-07-24 is
recorded in
`thoughts/reviews/2026-07-24-rulemaking-condition2-adversarial-review.md`. It is
not an external organization's review: no non-originating consumer operated or
ratified it. Condition 2 therefore remains open. The review also found that the
module must not graduate as-is. Graduation requires the review's §5
preconditions to land and a non-originating consumer to review the repaired
contract or ratify the review against it.

The simulation resolved the three agenda questions for the next Experimental
revision:

1. Keep one Artifact per posting and the 0..1 regulatory-identifier pair, then
   harden cross-posting identity, format links, and cardinality enforcement.
2. Change `rkaf:hasAuthority` on Proceeding to 0..* with
   absent-means-unknown, prohibit placeholder Authority nodes, and enforce
   decision-grade authority completeness in a consumption profile.
3. Replace the six bare stage-value IRIs before release. Prefer the existing
   `proceeding-*` IRIs shared with stage-family lifecycle events; distinct
   `proceedingStage*` IRIs remain the documented fallback if state and
   transition IRIs must stay separate.

These are design decisions for the repair batch, not evidence that the module
is stable. The curated corpus under `reference-corpora/us-rulemaking/`
exercises the module but does not itself satisfy either gate condition. A
fixture proves validation; it does not prove corpus-scale fitness.

## 9. Validation surface

- CUE source: `constraints/core/rulemaking.cue`
- Generated JSON Schema, Rust, TypeScript, and SHACL: produced by
  `tools/compile_all.sh`.
- JSON Schema is an intentionally partial validation projection for calendar
  dates and cross-field ordering. It emits a lexical date pattern, `format:
  date`, and the `x-rkaf-order` annotation, but Draft 2020-12 processors may
  ignore `format` and unknown annotations. Calendar validity and interval
  ordering are normative only through Rulespec's `x-rkaf-order`-aware
  validator or the SHACL projection. A JSON-Schema-only consumer MUST NOT claim
  those checks unless its validator explicitly asserts both capabilities.
- Positive, negative, and edge fixtures: `fixtures/`
