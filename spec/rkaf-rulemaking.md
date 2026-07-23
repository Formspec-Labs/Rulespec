# Rulespec US Rulemaking-Process Module

**Status:** Experimental.
**Companion docs:** `spec/rkaf-core.md`, `spec/rkaf-vocabulary.md`, `spec/rkaf-conformance.md`.

> Instability warning: these terms ship under the normal release-bound closed-taxonomy rules, but their shapes may change between pre-1.0 releases. The module does not advance to pre-release normative status until a full-corpus consumer exercise and an independent consumer review satisfy §8.

## 0. Conformance language

RFC 2119 / RFC 8174 keywords are normative when uppercase.

## 1. Scope

This module models the proceeding that produces a US federal regulation: its identity, current stage, public-comment intervals, published documents, affected CFR units, lifecycle events, and authority chain. It composes the universal Rulespec primitives instead of creating a second document, authority, or lifecycle system.

The module does not model comment content, commenter identity, campaign detection, or descriptive topic tags.

## 2. Proceeding

`rkaf:Proceeding` represents one rulemaking proceeding. It is distinct from a regulations.gov docket: a proceeding may span several dockets, and a docket may contain activity from several proceedings.

Required properties:

- `rkaf:hasArtifactIdentifier` (1..*) — canonical `rkaf:us-rin` and/or `rkaf:us-regsgov` identifiers. A RIN is preferred when available because it identifies the proceeding directly.
- `rkaf:artifactIdentifierScheme` (1..*) — restricted on Proceeding to `rkaf:us-rin` and `rkaf:us-regsgov`.
- `rkaf:proceedingStage` (1) — one value from the closed enum `rkaf:prerule`, `rkaf:proposed`, `rkaf:supplemental`, `rkaf:final`, `rkaf:withdrawn`, `rkaf:longterm`.
- `rkaf:hasAuthority` (1..*) — IRI of the issuing or grounding `rkaf:Authority`.

Optional properties:

- `rkaf:proceedingAffects` (0..*) — IRI of a CFR-unit `rkaf:Artifact` that the proceeding amends or proposes to amend.

A producer MAY also model a regulations.gov docket as an `rkaf:Artifact` carrying its `rkaf:us-regsgov` identifier. Reuse of the agency-issued identifier does not turn the docket container into the proceeding; consumers distinguish the resources by `@type`.

## 3. Comment periods

`rkaf:CommentPeriod` represents one continuous interval during which the public may submit comments.

Required properties:

- `rkaf:commentPeriodFor` (1) — IRI of the `rkaf:Proceeding`.
- `rkaf:commentPeriodStart` (1) — `xsd:date`.
- `rkaf:commentPeriodEnd` (1) — `xsd:date`, on or after `rkaf:commentPeriodStart`.

A reopening is a new CommentPeriod node linked to the same Proceeding. Producers MUST NOT overwrite the earlier interval or stretch it across a closed gap.

## 4. Published documents

Federal Register documents remain ordinary `rkaf:Artifact` nodes identified with `rkaf:us-frdoc`. `rkaf:publishedInProceeding` links an Artifact to one or more Proceedings.

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

`rkaf:proceedingStage` records the current state. LifecycleEvent nodes preserve the event sequence that produced that state.

## 6. Targets and authority

`rkaf:proceedingAffects` links a Proceeding to CFR-unit Artifacts identified by `rkaf:us-cfr`.

Statutory grounding uses the existing authority chain:

```text
rkaf:Proceeding
  └─ rkaf:hasAuthority → rkaf:Authority
       └─ rkaf:derivesAuthorityFrom → rkaf:Artifact
            └─ rkaf:artifactIdentifierScheme → rkaf:us-usc
```

Public-law and Executive-order artifacts MAY appear in the same chain with `rkaf:us-pl` and `rkaf:us-eo`.

## 7. Composition

ELI-DL is the EU draft-legislation analog for pre-enactment lifecycle. This module cites ELI-DL as a mode-4 architectural pattern; it imports no ELI-DL predicate. Promotion to an alignment row requires an EU-corpus consumer with a tested binding.

## 8. Experimental stabilization gate

The module remains Experimental until both conditions hold:

1. A consumer runs `Proceeding`, `proceedingStage`, `CommentPeriod`, and `publishedInProceeding` across a full regulatory corpus and publishes a friction report covering multi-docket proceedings, reopened comment periods, and stage sequences.
2. A non-originating consumer reviews the terms and shapes.

The curated corpus under `reference-corpora/us-rulemaking/` exercises the module but does not satisfy the consumer condition. A fixture proves validation; it does not prove corpus-scale fitness.

## 9. Validation surface

- CUE source: `constraints/core/rulemaking.cue`
- Generated JSON Schema, Rust, TypeScript, and SHACL: produced by `tools/compile_all.sh`
- Hand-authored interval and IRI invariants: `shapes/rkaf-shapes-rulemaking.ttl`
- Identifier normalization: `shapes/rkaf-shapes-us-identifiers.ttl`
- Positive, negative, and edge fixtures: `fixtures/`
