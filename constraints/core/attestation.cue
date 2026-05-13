package rkaf

// Attestation (§3.1): a scoped, multi-target attestation by a named attestor
// over a Rulespec target (Assertion, work product, packet, concept, mapping,
// registry, bridge validation result, etc.). Decisions and scopes accept the
// closed v0.1 enums OR declared extension URIs (extension governance §8).
#AttestationDecision: "rkaf:approved" | "rkaf:approvedWithConditions" |
	"rkaf:rejected" | "rkaf:abstained" | "rkaf:advisory" |
	"rkaf:endorsedForReview" | "rkaf:flaggedForReview"

#AttestorKind: "rkaf:humanUser" | "rkaf:aiModel" | "rkaf:aiAgent" |
	"rkaf:automatedParser" | "rkaf:team" | "rkaf:organization" |
	"rkaf:community" | "rkaf:formalReviewer" | "rkaf:conceptMintingAuthority"

#Attestation: {
	"@type":                "rkaf:Attestation"
	"rkaf:attestor":        string // IRI of the attestor
	"rkaf:attestorKind":    #AttestorKind
	"rkaf:targets":         [...string] // ≥1 IRI of target object(s)
	"rkaf:decision":        #AttestationDecision
	"rkaf:attestationScope": string // free-form scope IRI or label
	"rkaf:attestedAt":      string // xsd:dateTime
	"rkaf:rationale"?:      string
}
