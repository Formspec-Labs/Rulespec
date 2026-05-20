package rkaf

// Concept (ConceptRegistry v0.2 §2): a named term registered against a
// ConceptRegistry. Two flavors:
//   RegisteredConcept — minted by a ConceptMintingAuthority, lives in a
//     federation-shared registry.
//   LocalConcept — defined within a workspace scope; may later be promoted
//     to a RegisteredConcept after federation review.
//
// Both share `conceptScope` and `conceptStatus`. RegisteredConcept adds
// `managedByRegistry`; LocalConcept adds `definedInScope`.
//
// SKOS predicate composition (§9.1, rkaf-concept-registry.md §3):
//   skos:prefLabel (1) — required on both flavors; the human-readable label.
//   skos:altLabel (0..*) — optional synonyms / alternate labels.
//   skos:broader (0..*) — optional IRI(s) of broader/parent concepts.
//   skos:narrower (0..*) — optional IRI(s) of narrower/child concepts.
//   skos:related (0..*) — optional IRI(s) of associatively related concepts.
// L1 does not constrain the range of skos:broader/narrower/related — partners
// conform to the SKOS ontology's own domain/range (ELI precedent).
#ConceptStatus: "rkaf:draft" | "rkaf:proposed" | "rkaf:active" |
	"rkaf:promoted" | "rkaf:deprecated" | "rkaf:retired" |
	"rkaf:rejected"

#RegisteredConcept: {
	"@type":                  "rkaf:RegisteredConcept"
	"rkaf:managedByRegistry": string // IRI of rkaf:ConceptRegistry
	"rkaf:conceptScope":      string // free-form scope IRI
	"rkaf:conceptStatus":     #ConceptStatus
	"skos:prefLabel":         string // human-readable label (REQUIRED, 1)
	"skos:altLabel"?:         [...string] // synonym labels (optional, 0..*)
	"skos:broader"?:          [...string] // IRI(s) of parent concept(s)
	"skos:narrower"?:         [...string] // IRI(s) of child concept(s)
	"skos:related"?:          [...string] // IRI(s) of related concepts
}

#LocalConcept: {
	"@type":               "rkaf:LocalConcept"
	"rkaf:definedInScope": string // IRI of the defining workspace
	"rkaf:conceptScope":   string
	"rkaf:conceptStatus":  #ConceptStatus
	"skos:prefLabel":      string // human-readable label (REQUIRED, 1)
	"skos:altLabel"?:      [...string] // synonym labels (optional, 0..*)
	"skos:broader"?:       [...string] // IRI(s) of parent concept(s)
	"skos:narrower"?:      [...string] // IRI(s) of child concept(s)
	"skos:related"?:       [...string] // IRI(s) of related concepts
}
