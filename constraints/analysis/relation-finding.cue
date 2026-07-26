package rkaf

import "list"

// RelationFinding (Analysis §5) — a NEUTRAL analytical observation about a
// completed comparison.
//
// A finding says exactly one thing: under the named comparison, accepted
// assertions disagreed about the same relation. It is not a denial, not a
// legal effect, not a policy exclusion, not a rescission, and not a
// recommendation. "The generic layer emits neutral findings"; a regulatory,
// scientific, judicial, legislative, contractual, procurement, or oversight
// profile may interpret one of these — differently from each other, or not at
// all — only after its own authority, applicability, deontic, source, and
// closure rules pass. That interpretation belongs to the profile's vocabulary,
// never to this record.
//
// The module therefore declares no legal-effect terms at all. There is no
// `rkaf:policyExclusion`, no `rkaf:rescinds`, no `rkaf:legalEffect`, and no
// severity ladder that a consumer could read as one. `AnalysisModuleTests` in
// `tools/test_constraints_compile.py` fails the build if such a term appears.
//
// ── Not the kernel's `#Finding` (ADR-0093) ───────────────────────────────────
//
// `constraints/core/finding.cue` already declares a generic `rkaf:Finding`.
// `#RelationFinding` neither composes nor subclasses it. That is a decision,
// not an oversight, and it rests on four incompatibilities:
//
//   1. SEVERITY. `#FindingSeverity` is a closed, deliberately ACTIONABLE
//      ladder — `rkaf:publicationBlocking`, `rkaf:authorityCritical`.
//      Composing it would put exactly the readable-as-legal-effect ladder this
//      shape forbids onto a record whose entire purpose is neutrality.
//   2. SUBJECT. `rkaf:subject` is ONE IRI, "the object the finding concerns".
//      A relation finding is about a COMPARISON between two artifact versions
//      over at least two assertions; there is no single subject, and forcing
//      one would make producers choose arbitrarily and consumers index on the
//      choice.
//   3. WAIVABILITY, as a READING. `rkaf:targetFinding` on `#Attestation` is
//      what the kernel's waiver path is spelled with, and §7 reserves waiving
//      a discrepancy — "we accept this" — to profiles.
//
//      Note precisely what this argument does and does not carry.
//      `rkaf:targetFinding` is a plain string with `sh:maxCount 1` and NO
//      class range anywhere (constraints/core/attestation.cue), so any IRI is
//      already nameable there, including a `#RelationFinding`'s. Subclassing
//      would therefore not be what first opens the path — it would make the
//      waiver READ as a kernel-sanctioned one, which is the part §7 reserves.
//      Arguments 1, 2, and 4 are the mechanically enforced ones and are what
//      the decision rests on; this one is about what a consumer would be
//      entitled to infer, and it is deliberately not claimed as a gate.
//   4. KERNEL PURITY. `#FindingKind` is a closed KERNEL enum with the kernel's
//      own RFC path. Adding `rkaf:affirmedDeniedDiscrepancy` to it would put
//      an analysis-owned value in a kernel enum — the exact dependency this
//      module exists to avoid.
//
// The two coexist: a validator that notices a malformed comparison record
// emits an `rkaf:Finding` about it, and the comparison itself yields a
// `rkaf:RelationFinding`. Different producers, different subjects, different
// consequences.

// The kinds of neutral finding this contract can express. ONE value today, and
// the single value is the point: every other evidence situation has its own
// representation, so a finding kind exists only where none of the others fit.
//
//   affirmed / denied disagreement -> rkaf:affirmedDeniedDiscrepancy (here)
//   source affirms                 -> affirmed #RelationshipAssertion
//   source denies                  -> denied   #RelationshipAssertion
//   source changes the relation    -> #RelationChangeEvent
//   gate failed                    -> rkaf:comparisonNotComparable outcome
//   gate undecided                 -> rkaf:comparisonUnknown outcome
//   source silent                  -> no record; unknown
//
// `expected_relation_not_observed` is deliberately NOT a value and MUST NOT
// become one while `#ClosureClaim` is disabled. An omission finding is only
// meaningful inside a proven closure boundary; without one it converts silence
// into a claim, which is the single failure mode this whole module exists to
// prevent. `AnalysisModuleTests` asserts the absence mechanically so it cannot
// be reintroduced as a "small" enum addition.
#RelationFindingKind: "rkaf:affirmedDeniedDiscrepancy"

#RelationFinding: {
	"@type":                  "rkaf:RelationFinding"
	"rkaf:relationFindingKind": #RelationFindingKind

	// The comparison this finding reports, class-ranged to
	// `rkaf:RelationComparisonContext`. The context carries the artifact pair,
	// versions, consumer, scope, evaluation time, policy and detector versions,
	// snapshot, and outcome — so the finding does not restate any of them and
	// cannot disagree with them.
	//
	// The bound context's outcome must be
	// `rkaf:comparisonAffirmedDeniedDiscrepancy`. That is a cross-node
	// agreement rule, which per-property SHACL cannot reach, so it is enforced
	// by `rkaf:RelationFindingContextOutcomeAgreementShape` in
	// `shapes/rkaf-shapes-analysis.ttl`. Without it a producer could attach a
	// discrepancy finding to a comparison that came back `satisfied`.
	"rkaf:findingComparisonContext": string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"

	// The accepted assertions that disagreed. At least two: one assertion
	// cannot disagree with itself, and a "discrepancy" naming a single record
	// is a mislabelled unilateral claim.
	"rkaf:findingComparedAssertion": [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(2)

	// Every proof record backing the finding, class-ranged to
	// `rkaf:ResolverProofRecord`. Required: a neutral finding is only as
	// reviewable as the gate decisions under it, and "complete proof records
	// for every emitted finding" is an acceptance threshold, not a nicety.
	"rkaf:findingProofRecord": [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1)

	// When the detector produced this occurrence, and why.
	"rkaf:findingDetectedAt": string // xsd:dateTime
	"rkaf:findingRationale": string

	// A stable correlation key grouping repeated observations of the same
	// conceptual gap. Optional and deliberately separate from the finding's
	// identity: changing any comparison input creates a NEW detector
	// occurrence, and the fingerprint is what lets a consumer see that two
	// occurrences are about the same thing without merging them into one.
	"rkaf:findingFingerprint"?: string
}
