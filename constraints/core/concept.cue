package rkaf

// Concept (ConceptRegistry v0.1.2 §2): a named term registered against a
// ConceptRegistry. Two flavors:
//   RegisteredConcept — minted by a ConceptMintingAuthority, lives in a
//     federation-shared registry.
//   LocalConcept — defined within a workspace scope; may later be promoted
//     to a RegisteredConcept after federation review.
//
// Both share `conceptScope` and `conceptStatus`. RegisteredConcept adds
// `managedByRegistry`; LocalConcept adds `definedInScope`.
#ConceptStatus: "rkaf:draft" | "rkaf:proposed" | "rkaf:active" |
	"rkaf:promoted" | "rkaf:deprecated" | "rkaf:retired" |
	"rkaf:rejected"

#RegisteredConcept: {
	"@type":                  "rkaf:RegisteredConcept"
	"rkaf:managedByRegistry": string // IRI of rkaf:ConceptRegistry
	"rkaf:conceptScope":      string // free-form scope IRI
	"rkaf:conceptStatus":     #ConceptStatus
}

#LocalConcept: {
	"@type":              "rkaf:LocalConcept"
	"rkaf:definedInScope": string // IRI of the defining workspace
	"rkaf:conceptScope":   string
	"rkaf:conceptStatus":  #ConceptStatus
}
