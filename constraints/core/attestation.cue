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
	// Plan 7d (rkaf-behavior.md §4.6 / §5) — temporal bounds + freshness.
	// All optional, additive. `hasEffectivePeriod` reuses the same predicate
	// already on Authority + ApplicabilityScope (cascade::is_active reads
	// this edge); domain expansion, not parallel predicate.
	"rkaf:hasEffectivePeriod"?: string // IRI to rkaf:EffectivePeriod
	"rkaf:revokedAt"?:          string // xsd:dateTime — retraction marker; supersedes effective period if before period end
	"rkaf:lastVerifiedAt"?:     string // xsd:dateTime — when last reconfirmed against source; ORTHOGONAL to lifecycle state
	"rkaf:verifiedBy"?:         string // IRI of verifier (attestor or other party)
}
