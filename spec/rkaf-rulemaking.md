# Rulespec US Rulemaking-Process Module

**Status:** Experimental.
**Companion docs:** `spec/rkaf-core.md`, `spec/rkaf-vocabulary.md`, `spec/rkaf-conformance.md`.

> Instability warning: these terms ship under the normal release-bound closed-taxonomy rules, but their shapes may change between pre-1.0 releases. The full-corpus consumer exercise has completed; the module does not advance to pre-release normative status until an independent consumer review satisfies the remaining gate in §8.

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
  `rkaf:partner-defined`.
- `rkaf:hasAuthority` (1..*) — IRI of the issuing or grounding `rkaf:Authority`.

Optional properties:

- `rkaf:proceedingStage` (0..1) — one value from the closed enum
  `rkaf:prerule`, `rkaf:proposed`, `rkaf:supplemental`, `rkaf:final`,
  `rkaf:withdrawn`, `rkaf:longterm`. Absence means the current stage is
  unknown. Producers MUST NOT infer `rkaf:prerule`, `rkaf:withdrawn`, or any
  other stage from missing evidence.
- `rkaf:hasDocket` (0..*) — IRI of an associated `rkaf:Docket`. Docket
  membership never establishes proceeding identity.
- `rkaf:proceedingAffects` (0..*) — IRI of a CFR-unit `rkaf:Artifact` that the proceeding amends or proposes to amend.

The canonical RIN form is
`urn:rkaf:us:rin:<four-digits>-<two-uppercase-letters><two-digits>`, for example
`urn:rkaf:us:rin:2060-AV16`. A producer that splits an action family because a
RIN was reused MUST assign each resulting Proceeding a stable,
partner-scoped persistent identifier instead of treating the reused RIN as a
globally unique key.

### 2.1 Docket

`rkaf:Docket` represents a mutable administrative container. It is neither an
immutable `rkaf:Artifact` nor a `rkaf:Proceeding`.

Required properties:

- `rkaf:hasDocketIdentifier` (1) — an IRI identifying the docket.
- `rkaf:docketIdentifierScheme` (1) — `rkaf:us-regsgov` or
  `rkaf:partner-defined`.

For a regulations.gov docket, the canonical identifier is
`urn:rkaf:us:regsgov:<agency-issued-id>`, for example
`urn:rkaf:us:regsgov:EPA-HQ-OAR-2021-0317`. Normalize ASCII letters to
uppercase and preserve the agency-issued hyphen-separated segments. A docket
may link to several Proceedings, and a Proceeding may link to several dockets.

## 3. Comment periods

`rkaf:CommentPeriod` represents one continuous interval during which the public may submit comments.

Required properties:

- `rkaf:commentPeriodFor` (1) — IRI of the `rkaf:Proceeding`.
- `rkaf:commentPeriodStart` (1) — `xsd:date`.
- `rkaf:commentPeriodEnd` (1) — `xsd:date`, on or after `rkaf:commentPeriodStart`.
- `prov:wasDerivedFrom` (1..*) — IRI of a `prov:Entity` that carries the
  source evidence for this interval.

A reopening is a new CommentPeriod node linked to the same Proceeding.
Producers MUST NOT overwrite the earlier interval or stretch it across a
closed gap. When sources disagree or one source supplies an invalid interval,
producers MUST preserve the qualified evidence separately and MUST NOT emit an
unsupported CommentPeriod.

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

## 5. Lifecycle events

Proceeding stage transitions use `rkaf:LifecycleEvent`; this module defines no parallel event class. `rkaf:appliesTo` points to the Proceeding, and `rkaf:effectiveDate` records the transition time.

The `rkaf:lifecycleEventKind` closed enum adds:

| Event kind | Meaning |
|---|---|
| `rkaf:proceedingPrerule` | The proceeding entered prerule development. |
| `rkaf:proceedingProposed` | The agency published or formally entered the proposed-rule stage. |
| `rkaf:proceedingSupplemental` | The agency published or entered a supplemental-proposal stage. |
| `rkaf:proceedingFinal` | The agency published or entered the final-rule stage. |
| `rkaf:proceedingWithdrawn` | The agency withdrew the proceeding. |
| `rkaf:proceedingLongterm` | The agency placed the proceeding on the long-term agenda. |

When known, `rkaf:proceedingStage` records the current state. LifecycleEvent
nodes preserve the event sequence that produced that state. No lifecycle
event means unknown, not prerule.

## 6. Targets and authority

`rkaf:proceedingAffects` links a Proceeding to CFR-unit Artifacts. Each target
MUST identify a specific immutable CFR edition or snapshot through
`rkaf:hasArtifactIdentifier`; its edition-independent citation may be carried
separately through `rkaf:hasRegulatoryIdentifier` with
`rkaf:regulatoryIdentifierScheme: rkaf:us-cfr`. An unversioned eCFR URL or
compact citation alone is not a conforming target.

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

## 7. Composition

ELI-DL is the EU draft-legislation analog for pre-enactment lifecycle. This module cites ELI-DL as a mode-4 architectural pattern; it imports no ELI-DL predicate. Promotion to an alignment row requires an EU-corpus consumer with a tested binding.

## 8. Experimental stabilization gate

The module remains Experimental until both conditions hold:

1. A consumer runs `Proceeding`, `proceedingStage`, `CommentPeriod`, and `publishedInProceeding` across a full regulatory corpus and publishes a friction report covering multi-docket proceedings, reopened comment periods, and stage sequences.
2. A non-originating consumer reviews the terms and shapes.

The Spicy Regs full-corpus report dated 2026-07-23 satisfies condition 1 and
produced the identity, provenance, identifier-fallback, and unknown-stage
rules above. Condition 2 remains open. The curated corpus under
`reference-corpora/us-rulemaking/` exercises the module but does not itself
satisfy either condition. A fixture proves validation; it does not prove
corpus-scale fitness.

## 9. Validation surface

- CUE source: `constraints/core/rulemaking.cue`
- Generated JSON Schema, Rust, TypeScript, and SHACL: produced by
  `tools/compile_all.sh`; these are the only validation authority for the
  module's shapes, identifier patterns, dates, and interval ordering.
- Positive, negative, and edge fixtures: `fixtures/`
