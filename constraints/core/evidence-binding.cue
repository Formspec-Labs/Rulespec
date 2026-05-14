package rkaf

import "list"

// Closed enum (§4.3).
#NoEvidenceReason: "rkaf:axiomatic" | "rkaf:inferred-from-warrant-class" |
	"rkaf:consensus-without-citation" | "rkaf:permitted-by-safety-label"

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
