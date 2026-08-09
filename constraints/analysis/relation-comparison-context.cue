package rkaf

import "list"

// RelationComparisonContext (Analysis §3) — the immutable record of ONE
// comparison: the frame it ran in and the outcome it reached.
//
// The comparison kernel is deterministic and evidence-gated. It reads accepted
// assertions and returns one of five outcomes. No AI model decides that
// outcome alone (Analysis §3.4, amended 2026-08-09): a model may propose
// assertions and change events upstream, and — since machine-adjudication.cue
// — a model may also produce a `#MachineAdjudicationProof` answering one
// sealed comparison question. Either way it never creates a comparison result
// by itself; the outcome comes only from folding two or more independent
// proofs through the deterministic lattice.
//
// Everything that could change the answer is bound HERE, so a result is
// reproducible and auditable without re-deriving it:
//
//   which two artifact versions were compared;
//   which baseline assertion the comparison was run FOR;
//   for which consumer and under which scope;
//   at what evaluation time;
//   under which policy, detector, and detector version; and
//   against which immutable source snapshot.
//
// Changing any of these produces a DIFFERENT comparison, not an update to this
// one. Nothing in this record is mutable; a re-run writes a new context.
//
// Why the outcome lives on the context rather than on the finding: all five
// outcomes are real results of a comparison, but only one of them (an
// affirmed/denied discrepancy) also produces a neutral `#RelationFinding`.
// Putting the outcome on the finding would make `satisfied`, `not_comparable`,
// `conflict`, and `unknown` unrepresentable — the system would have no way to
// record that it looked and found no discrepancy, which is exactly the record
// an auditor needs in order to distinguish "checked, nothing found" from
// "never checked".

// The five comparison results (Analysis §3.2). Closed, and closed
// deliberately: a sixth value is a new semantic case, and new semantic cases
// enter this contract by review, not by a producer inventing a string.
//
//   rkaf:comparisonSatisfied                    an accepted, equivalent,
//                                               affirmed observation exists
//   rkaf:comparisonAffirmedDeniedDiscrepancy    accepted assertions disagree
//                                               on the same relation
//   rkaf:comparisonConflict                     accepted assertions are
//                                               mutually inconsistent on one
//                                               side of the comparison
//   rkaf:comparisonNotComparable                an eligibility gate FAILED —
//                                               a gate result, never a
//                                               negative fact about a source
//   rkaf:comparisonUnknown                      a required gate returned
//                                               unknown; unknown never becomes
//                                               fail
//
// `expected_relation_not_observed` is NOT here, and is not a
// `#RelationFindingKind` either. Omission requires a proven closure boundary,
// and closure is disabled (see constraints/analysis/closure-claim.cue). Until
// it is enabled by a deliberate contract change, silence outside a proven
// boundary is `rkaf:comparisonUnknown`.
#RelationComparisonOutcome: "rkaf:comparisonSatisfied" |
	"rkaf:comparisonAffirmedDeniedDiscrepancy" |
	"rkaf:comparisonConflict" | "rkaf:comparisonNotComparable" |
	"rkaf:comparisonUnknown"

#RelationComparisonContext: comparison={
	"@type": "rkaf:RelationComparisonContext"

	// The artifact pair, at exact versions. Both class-ranged to
	// `rkaf:Artifact`; an `rkaf:Artifact` is already one immutable version, so
	// "exact version" needs no extra slot here.
	"rkaf:comparisonBaselineArtifact": string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:comparisonObservedArtifact": string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"

	// The baseline assertion the comparison was run for. One comparison
	// answers one question about one expected relation.
	"rkaf:comparisonExpectedAssertion": string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"

	// FOR WHOM and UNDER WHAT SCOPE. Acceptance is consumer-scoped
	// (`#ConsumerDisposition`), so a comparison that does not name its consumer
	// and scope has not said which acceptance it read.
	"rkaf:comparisonConsumer": string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:comparisonScope":    string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"

	// WHEN the comparison was evaluated. Acceptance and applicability are both
	// time-dependent, so the same inputs at a different evaluation time are a
	// different comparison.
	"rkaf:comparisonEvaluationTime": string // xsd:dateTime

	// The versioned rules and code that produced the result. `policyVersion`
	// is the comparison policy; `detector` / `detectorVersion` name the
	// implementation. Both are needed: the same policy under two detector
	// versions may diverge, and that divergence must be attributable.
	"rkaf:comparisonPolicyVersion":   string
	"rkaf:comparisonDetector":        string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:comparisonDetectorVersion": string

	// The immutable source snapshot the comparison read. Re-running against a
	// moved corpus is a different comparison even when everything else matches.
	"rkaf:comparisonSnapshot": string

	// The deterministic result.
	"rkaf:comparisonOutcome": #RelationComparisonOutcome

	// Every resolver decision the comparison rested on, class-ranged to
	// `rkaf:ResolverProofRecord`. Optional at the top level and REQUIRED for
	// every outcome except `rkaf:comparisonUnknown`: an unknown result may
	// arise before any resolver could be consulted (a missing input, an
	// unreachable snapshot), while a satisfied, discrepant, conflicting, or
	// not-comparable result is a CLAIM about evidence and must show the proofs
	// that back it. "An opaque string is not proof."
	//
	// Spelled as four positive branches rather than one negated branch because
	// the projector carries `if property == literal` and nothing else; a
	// negation the flat AST cannot express would be dropped from every
	// compiled target while the CUE kept enforcing it.
	"rkaf:comparisonProofRecord"?: [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1)

	if comparison["rkaf:comparisonOutcome"] == "rkaf:comparisonSatisfied" {
		"rkaf:comparisonProofRecord": [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1)
	}
	if comparison["rkaf:comparisonOutcome"] == "rkaf:comparisonAffirmedDeniedDiscrepancy" {
		"rkaf:comparisonProofRecord": [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1)
	}
	if comparison["rkaf:comparisonOutcome"] == "rkaf:comparisonConflict" {
		"rkaf:comparisonProofRecord": [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1)
	}
	if comparison["rkaf:comparisonOutcome"] == "rkaf:comparisonNotComparable" {
		"rkaf:comparisonProofRecord": [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1)
	}
}
