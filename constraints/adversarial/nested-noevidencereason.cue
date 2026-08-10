package rkaf

// Adversarial: an Assertion inlines an EvidenceBinding via a forward predicate.
// The EB has noEvidenceReason = "rkaf:axiomatic". The parent Assertion's
// safetyLabel MUST permit axiomatic evidence. SHACL evaluators that miss the
// nested traversal silent-pass; closed-form constraint catches it.
//
// The inline value set below is a literal subset of `#SafetyLabel`
// (constraints/core/trust-and-safety.cue), never its own vocabulary.

#NestedNoEvidenceReasonShape: {
	"@type":               "rkaf:Assertion"
	"rkaf:hasSafetyLabel": "rkaf:permits-axiomatic" | "rkaf:permits-all"
	"rkaf:hasEvidenceBinding": [...{
		"@type":                  "rkaf:EvidenceBinding"
		"rkaf:noEvidenceReason"?: "rkaf:axiomatic"
	}]
}
