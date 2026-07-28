# RS-P6: Add `rkaf:declared-hypothesis` to `noEvidenceReason`

- **Date:** 2026-07-27
- **Status:** Proposed — awaiting Rulespec maintainer decision
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
