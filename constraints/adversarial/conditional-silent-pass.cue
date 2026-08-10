package rkaf

// Appendix-C class regression: a constraint that an sh:if/sh:then-based SHACL
// evaluator silently passes. Restated as CUE so it compiles cleanly to every
// target; fixtures exercise the failure mode.
//
// "When an EvidenceBinding has noEvidenceReason = consensus-without-citation,
// the parent Assertion's safetyLabel MUST permit it."
//
// A literal subset of `#SafetyLabel` (constraints/core/trust-and-safety.cue),
// never its own vocabulary: every member here MUST also be a member there.
// Narrower on purpose — a D0/S1/R2/A3/P4 label does not permit this
// evidence gap, only the `permits-*` family does.
#SafetyLabelPermitsConsensus: "rkaf:permits-consensus-without-citation" |
	"rkaf:permits-axiomatic" |
	"rkaf:permits-all"

#ConsensusEvidencePermissionShape: {
	"@type":               "rkaf:Assertion"
	"rkaf:hasSafetyLabel": #SafetyLabelPermitsConsensus
	"rkaf:hasEvidenceBinding": [...{
		"rkaf:noEvidenceReason"?: "rkaf:consensus-without-citation"
	}]
}
