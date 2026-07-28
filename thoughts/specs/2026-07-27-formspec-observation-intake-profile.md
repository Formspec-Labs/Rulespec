# RS-P1: Observation intake profile — a documented Observation→Assertion mapping

- **Date:** 2026-07-27
- **Status:** Proposed — awaiting Rulespec maintainer decision. Its dependency
  is satisfied: RS-P6 landed 2026-07-28 in `56df3df`, so the promotion mapping
  no longer has a hole where a hypothesis Need would sit. RS-P3 landed in
  `c283d94`. This one is deliberately still open.
- **Origin:** Formspec Needs Specification, Appendix C proposal RS-P1
  (`formspec-stack/formspec/specs/needs/needs-spec.md`)
- **Consumers:** Rulespec, Formspec
- **Layer:** 4 (projectors / companions). Adds no vocabulary.

## What Formspec is asking for

The Formspec Needs Document (landed 2026-07-27) records why a piece of
software should exist. Each Need carries at least one **Grounding**, in one of
two channels:

- **Assertion Grounding** — an IRI into a Rulespec corpus. Rulespec owns
  everything behind it; Formspec restates none of it.
- **Observation Grounding** — a product-local research record at discovery
  weight: an interview moment, a usability session, an analytics signal, a
  support pattern, a field report. Carries `method` (closed enum), `uri`,
  an optional OA-shaped `excerpt`, `observedAt`, and an optional `observer`.

The needs spec states a **promotion path** (S5.5): when an Observation becomes
load-bearing — cited in a procurement claim, contested by a stakeholder,
feeding a compliance argument — it should be re-minted as a Rulespec assertion
and the Grounding upgraded in place from `kind: "observation"` to
`kind: "assertion"`. Today that promotion is prose. This proposal asks
Rulespec to make it mechanical.

**Proposed home:** a new informative companion, `spec/rkaf-observation-intake.md`.

## The mapping

| Observation field | Rulespec target |
|---|---|
| `uri` | `rkaf:Artifact` with `rkaf:artifactIdentifierScheme: rkaf:partner-defined` |
| `excerpt` (`exact` / `prefix` / `suffix`) | `oa:TextQuoteSelector` on an `rkaf:SourceFragment` (§4.2 already composes OA this way) |
| `method: interview` | `rkaf:warrantKind: rkaf:empirical` |
| `method: usability-session` | `rkaf:warrantKind: rkaf:empirical` |
| `method: field-report` | `rkaf:warrantKind: rkaf:empirical` |
| `method: analytics` | `rkaf:warrantKind: rkaf:methodological` |
| `method: support-signal` | `rkaf:warrantKind: rkaf:sourceReliability` |
| `observer` | `prov:wasAttributedTo` |
| *(landing state)* | `rkaf:usageEligibility: rkaf:searchOnly` until independently revalidated |

The `searchOnly` landing is the load-bearing part and is deliberately
conservative: a promoted interview quote enters **below** operational validity.
Nothing about the promotion should let a research quote start acting like a
statutory obligation.

## Acceptance criteria

*(Verbatim from the needs spec's Appendix C, plus the repo-local shape the
CONTRIBUTING shape-batch method implies.)*

1. One **positive fixture pair** in `fixtures/`: an Observation JSON input and
   the conformant assertion JSON-LD output it maps to.
2. The pair is **exercised by the vocab audit** (`tools/vocab_audit.py`), so
   the mapping is a tested artifact rather than a table in prose.
3. Every constraint the companion states is anchored on a specific `rkaf-core`
   section, per CONTRIBUTING step 1 ("no constraint exists without a textual
   basis").

## What Formspec deletes or simplifies

Nothing is deleted. S5.5's promotion path stops being manual prose and becomes
a cited, testable mapping; future promotion tooling **implements** the mapping
instead of designing one. That is the whole benefit: two independent
implementations of an undocumented mapping would diverge, and the divergence
would be invisible until a procurement reviewer found it.

## Cost to Rulespec's charter

**Low.** It is a projector-pattern companion (Layer 4 posture), adds no
vocabulary, and the `searchOnly` landing eligibility preserves the
anti-score-theater discipline.

## Why the record itself stays in Formspec

The needs spec's own verdict is **PROPOSE-TO-RULESPEC** (the mapping) /
**KEEP-LOCAL** (the Observation record). Two reasons, both structural:

1. **Discovery tempo.** Forcing every interview quote through Artifact +
   SourceFragment + Warrant + ConfidenceRecord + L2 enforcement would kill the
   velocity the record exists to serve. Rulespec's own conformance ladder
   exists precisely so consumers adopt depth incrementally.
2. **Stack topology.** The stack's topological build order places PKAF/Rulespec
   *downstream* of Formspec (`… → formspec → … → PKAF`, stack `Makefile`).
   Formspec schemas and processors cannot consume Rulespec vocabulary, tooling,
   or validation without inverting the build order. Citation by opaque IRI is
   dependency-free; anything more is not.

The mapping makes escalation mechanical without moving the record.

## Open questions for the maintainer

- **Warrant family for `support-signal`.** The proposal maps it to
  `rkaf:sourceReliability`, which sits in the source-class family rather than
  the scientific one. A support queue is a reliability claim about a channel,
  not an empirical observation of a person — but this is a judgment call and the
  companion should state its reasoning either way.
- **Does the companion need a negative fixture?** The acceptance criteria above
  name only a positive pair. A negative — e.g. an Observation promoted straight
  to an eligibility above `searchOnly` — would make the cap enforceable rather
  than advisory.
