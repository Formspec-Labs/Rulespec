# RS-P6: Add `rkaf:declared-hypothesis` to `noEvidenceReason`

- **Date:** 2026-07-27
- **Status:** **ACCEPTED and landed 2026-07-28 in `56df3df`**, with one
  acceptance criterion left open. See "Resolution" at the foot of this
  document.
- **Origin:** Formspec Needs Specification, Appendix C proposal RS-P6
  (`formspec-stack/formspec/specs/needs/needs-spec.md`)
- **Consumers:** Rulespec, Formspec
- **Touches:** `spec/rkaf-core.md` §4.3 (`rkaf:noEvidenceReason`), §10
  (validation contract), §3 (closed-taxonomy discipline)

## What Formspec is asking for

Add `rkaf:declared-hypothesis` to the closed `rkaf:noEvidenceReason` enum: the
assertion is a **deliberately held, not-yet-validated belief**.

It is distinct from both existing neighbours:

| Value | Means |
|---|---|
| `rkaf:axiomatic` | needs no evidence; evidence would be circular |
| `rkaf:consensus-without-citation` | has social grounding, just no citable source |
| **`rkaf:declared-hypothesis`** *(proposed)* | **has no grounding at all, and we know it, and we intend to validate it** |

**Proposed constraint:** an assertion carrying it SHOULD be capped at
`rkaf:usageEligibility: rkaf:searchOnly` or `rkaf:reviewQueueOnly` until an
EvidenceBinding-with-fragment replaces the reason.

## Acceptance criteria

*(Verbatim from the needs spec's Appendix C.)*

1. **Enum value** declared in `rkaf:noEvidenceReason`.
2. **Shape constraint** expressing the eligibility cap.
3. **Positive and negative fixtures** per the §10 validation contract.

## Why this exists

The Formspec Needs Document requires that every Need carry either evidence or
an explicit `ungroundedReason` — silent ungroundedness is unrepresentable by
construction. That rule is Rulespec's own `noEvidenceReason` move, borrowed and
credited. The needs spec's `ungroundedReason` enum has three values, and the
correspondence table is complete except in one cell:

| Formspec `ungroundedReason` | Rulespec `noEvidenceReason` |
|---|---|
| `team-consensus` | `rkaf:consensus-without-citation` |
| `self-evident` | `rkaf:axiomatic` |
| `hypothesis` | **nothing** |

So a *hypothesis* Need has no honest landing in Rulespec. If RS-P1's promotion
mapping lands without this value, promoting a hypothesis Need forces the author
to choose between fabricating evidence and claiming
`rkaf:consensus-without-citation`, which asserts social grounding the team does
not have. Both are worse than the gap.

## Cost to Rulespec's charter

**Low and charter-aligned.** Declared absence over silent absence is Rulespec's
own posture; the eligibility cap keeps hypothesis assertions out of operational
use, which is the anti-laundering position the framework already takes.

## Interaction the maintainer should decide

§4.3 as written couples `noEvidenceReason` to the safety label, not to
usage eligibility:

> `rkaf:noEvidenceReason` (1) — closed enum: … The Assertion's
> `rkaf:hasSafetyLabel` MUST permit the chosen reason.

The proposed cap is stated in `rkaf:usageEligibility` terms. Two coherent
readings, and this document does not choose between them:

1. **Safety-label route (consistent with §4.3).** `rkaf:declared-hypothesis` is
   permitted only under specific safety labels, the way the existing values
   are. The eligibility cap then falls out of the existing lattice rather than
   being a second, parallel rule.
2. **Eligibility route (as Formspec proposed it).** A new shape constraint
   caps eligibility directly, and the safety-label permission table gains the
   value alongside.

Route 1 adds no new constraint mechanism and is probably the smaller change.
Route 2 says the thing Formspec actually wants said. The maintainer owns the
call; the needs spec's requirement is only that a hypothesis cannot reach
operational use while it is still a hypothesis.

## What Formspec deletes or simplifies

Nothing now. It **completes RS-P1**: without this value, the promotion mapping
has a hole exactly where the most common discovery-weight record sits.

## Resolution — landed 2026-07-28 (`56df3df`), one criterion open

Accepted. `rkaf:declared-hypothesis` is the fifth value of the closed
`rkaf:noEvidenceReason` enum.

**The cap rides `rkaf:usageEligibility` (route 2).** The maintainer's reasoning,
recorded here so the choice is auditable: §4.3's safety-label rule GRANTS
operational validity — "an assertion lacking either an
EvidenceBinding-with-fragment OR an explicit `noEvidenceReason` permitted by
its safety level is not operationally valid" — and does not bound it. Route 1
could therefore produce a cap only by never permitting the value under any
label, which yields binary operational invisibility rather than the graded
`searchOnly` / `reviewQueueOnly` state a consumer actually needs. A hypothesis
nobody can find is worse than one nobody may act on, and honest declared
absence is the whole point of the value. The safety-label rule keeps applying
uniformly to all five members, so nothing is orphaned; the eligibility cap is
an ADDITIONAL rule, not a replacement.

**Acceptance criterion 2 is NOT met.** The eligibility cap is a producer
obligation stated normatively in §4.3, and no compiled target enforces it.
`rkaf:usageEligibility` is a property of the assertion envelope (§2.3),
`rkaf:noEvidenceReason` a property of the binding, and `rkaf:bindsAssertion` a
bare IRI. The conditional idiom every other conditional requirement in the
specification compiles from needs the guard and the requirement to be
properties of ONE shape, and the compiler flattens nested objects rather than
traversing them — `compiled/shacl/adversarial/nested-noevidencereason.ttl`
targets `rkaf:EvidenceBinding` instead of `rkaf:Assertion` for exactly this
reason. Raw SHACL could express the traversal with a sequence path, but no
shape in this repo uses one and a SHACL-only constraint would put the compiled
targets out of parity. Putting eligibility on the binding would create two
places to look for one consumer-scoped fact, which §2.3 forbids. Tracked as an
open follow-up in TODO.md.

**Drift.** This document's correspondence table assumes a three-value
`noEvidenceReason` enum. It has had four since v0.2 —
`rkaf:inferred-from-warrant-class` and `rkaf:permitted-by-safety-label` are the
two the table omits — and now five. The hole the table names is real; it was
one of four.

**Surfaced en route.** §4.3's "the Assertion's `rkaf:hasSafetyLabel` MUST
permit the chosen reason" has no per-reason permission table behind it.
`#SafetyLabel` holds seven lettered values plus one orphan,
`rkaf:permits-axiomatic`; the adversarial shapes require
`rkaf:permits-consensus-without-citation` and `rkaf:permits-all`, neither an
enum member; and the canonical positive fixture pairs a lettered label with
`rkaf:axiomatic` and passes. No `rkaf:permits-declared-hypothesis` was minted:
that would extend a v0.1-INHERITED closed enum and add a fourth partial member
to an already-incoherent family. Filed as its own TODO item.

Coverage: `fixtures/evidencebinding-declared-hypothesis-positive.jsonld`,
`fixtures/negatives/evidence-binding-unregistered-no-evidence-reason-negative.jsonld`,
one parity row, the `sh:in` closure in `shapes/rkaf-shapes-warrant.ttl`, and a
`rkaf:NoEvidenceReason` entry in the vocabulary's closed-enum list.
Contract digest moved `sha256:8166af8a…` -> `sha256:6e550600…`.
