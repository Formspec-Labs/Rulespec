package rkaf

// Concept (ConceptRegistry v0.2 §2): a named term registered against a
// ConceptRegistry. Two flavors:
//   RegisteredConcept — minted by a ConceptMintingAuthority, lives in a
//     federation-shared registry.
//   LocalConcept — defined within a workspace scope; may later be promoted
//     to a RegisteredConcept after federation review.
//
// Both shapes require skos:prefLabel(1) per spec/rkaf-concept-registry.md §2.1.
// Optional SKOS predicates: altLabel, broader, narrower, related.
// L1 imposes no range constraints on SKOS predicates — SKOS owns its vocabulary.
#ConceptStatus: "rkaf:draft" | "rkaf:proposed" | "rkaf:active" |
	"rkaf:promoted" | "rkaf:deprecated" | "rkaf:retired" |
	"rkaf:rejected"

#RegisteredConcept: {
	"@type":                  "rkaf:RegisteredConcept"
	"skos:prefLabel":          string              // required (1); xsd:string
	"rkaf:managedByRegistry": string              // IRI of rkaf:ConceptRegistry
	"rkaf:conceptScope":      string              // free-form scope IRI
	"rkaf:conceptStatus":     #ConceptStatus
	// Optional SKOS composition (Cohort A, §9.2, PKA-2szi).
	"skos:altLabel"?:  [...string]               // 0..*; display synonyms
	"skos:broader"?:   string                    // 0..1; IRI of broader concept
	"skos:narrower"?:  [...string]               // 0..*; IRIs of narrower concepts
	"skos:related"?:   [...string]               // 0..*; IRIs of related concepts
}

#LocalConcept: {
	"@type":               "rkaf:LocalConcept"
	"skos:prefLabel":       string              // required (1); xsd:string
	"rkaf:definedInScope": string              // IRI of the defining workspace
	"rkaf:conceptScope":   string
	"rkaf:conceptStatus":  #ConceptStatus
	// Optional SKOS composition (Cohort A, §9.2, PKA-2szi).
	"skos:altLabel"?:  [...string]             // 0..*; display synonyms
	"skos:broader"?:   string                  // 0..1; IRI of broader concept
	"skos:narrower"?:  [...string]             // 0..*; IRIs of narrower concepts
	"skos:related"?:   [...string]             // 0..*; IRIs of related concepts
}
