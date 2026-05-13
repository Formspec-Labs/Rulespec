package rkaf

// Appendix-C class regression: a constraint that an sh:if/sh:then-based SHACL
// evaluator silently passes. Restated as CUE so it compiles cleanly to every
// target; fixtures exercise the failure mode.
//
// "When an EvidenceBinding has noEvidenceReason = consensus-without-citation,
// the parent Assertion's safetyLabel MUST permit it."

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
