package rkaf

import "list"

// Closed enum (§4.3).
//
// `rkaf:declared-hypothesis` is the v0.2 addition: a deliberately held,
// not-yet-validated belief. It is distinct from both neighbours —
// `rkaf:axiomatic` needs no evidence, `rkaf:consensus-without-citation` has
// social grounding and no citable source, and this one has NO grounding at
// all, says so, and intends to be validated.
//
// §4.3 caps it at `rkaf:searchOnly` or `rkaf:reviewQueueOnly` until an
// EvidenceBinding-with-fragment replaces the reason. That cap is NOT
// expressible here and is not compiled to any target: `rkaf:usageEligibility`
// is a property of the assertion envelope (`#ConsumerDisposition`), this is a
// property of the binding, and `rkaf:bindsAssertion` is a bare IRI. The
// conditional idiom requires both the guard and the requirement to be
// properties of ONE shape, and the compiler flattens nested objects rather
// than traversing them. The cap is therefore a producer obligation; see the
// note in Core §4.3 and TODO.md.
#NoEvidenceReason: "rkaf:axiomatic" | "rkaf:inferred-from-warrant-class" |
	"rkaf:consensus-without-citation" | "rkaf:permitted-by-safety-label" |
	"rkaf:declared-hypothesis"

// EvidenceBinding MUST either bind ≥1 SourceFragment OR carry a permitted
// noEvidenceReason. CUE's disjunction expresses this directly; no Pattern C
// dance needed (the SHACL target compiles this disjunction to Pattern C).
#EvidenceBinding: {
	"@type":               "rkaf:EvidenceBinding"
	"rkaf:bindsAssertion": string // IRI
	// Plan 7d — freshness. Orthogonal to lifecycle.
	"rkaf:lastVerifiedAt"?: string // xsd:dateTime
	"rkaf:verifiedBy"?:     string // IRI of verifier
	{
		"rkaf:bindsSourceFragment": [...string] & list.MinItems(1)
	} | {
		"rkaf:noEvidenceReason": #NoEvidenceReason
	}
}
