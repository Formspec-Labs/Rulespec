package rkaf

import "list"

// Concept (ConceptRegistry v0.2 §2): a named term registered against a
// ConceptRegistry. Two flavors:
//   RegisteredConcept — minted by a ConceptMintingAuthority, lives in a
//     federation-shared registry.
//   LocalConcept — defined within a workspace scope; may later be promoted
//     to a RegisteredConcept after federation review.
//
// Both shapes require skos:prefLabel(1) and skos:inScheme(1) per
// spec/rkaf-concept-registry.md §2.1 and Core §4.7.2.
// Optional SKOS predicates: altLabel, definition, broader, narrower, related.
//
// L1 imposes no CLASS range constraints on SKOS predicates — SKOS owns its
// vocabulary, and the scheme a concept names may be an external
// `skos:ConceptScheme`. Two narrowings are deliberate and are NOT range
// constraints on the referent: `skos:inScheme` must be an absolute IRI rather
// than free text, and it is capped at exactly one. SKOS itself places no
// cardinality restriction there; Rulespec narrows it because one concept
// belongs to exactly one facet, and multi-facet membership is modelled as
// separate concepts joined by a SKOS mapping rather than as one term that
// answers two questions. Core §4.7.2 states the narrowing normatively.
#ConceptStatus: "rkaf:draft" | "rkaf:proposed" | "rkaf:active" |
	"rkaf:promoted" | "rkaf:deprecated" | "rkaf:retired" |
	"rkaf:rejected"

// ConceptScheme — one facet, one controlled category system (§4.7).
//
// SKOS owns what a concept scheme MEANS: `skos:inScheme` membership,
// `skos:hasTopConcept`, `skos:prefLabel`, `skos:definition`. This shape
// restates none of that. It adds the two things SKOS deliberately leaves open
// and Rulespec needs mechanically:
//
//   rkaf:schemeFacet   WHICH facet the scheme controls, as an IRI. Topic,
//                      industry, regulated entity, affected population, legal
//                      authority, place, organization, document role,
//                      obligation, outcome, and legal status are different
//                      questions; a scheme that never says which one it answers
//                      is how they merge. The facet is a producer- or
//                      profile-owned IRI, NOT a kernel enum: closing that set
//                      universally would be Rulespec minting a facet taxonomy
//                      it has no standing to own.
//   ownership          a scheme is governed by a registry OR defined in a
//                      workspace scope. That disjunction is the same seam
//                      `#RegisteredConcept` / `#LocalConcept` draw for
//                      concepts, applied to the container.
#ConceptScheme: {
	"@type":              "rkaf:ConceptScheme"
	"skos:prefLabel":     string
	"rkaf:schemeFacet":   string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:conceptStatus": #ConceptStatus
	"skos:definition"?:   string
	"skos:hasTopConcept"?: [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1)
	{
		"rkaf:managedByRegistry": string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	} | {
		"rkaf:definedInScope": string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	}
}

#RegisteredConcept: registered={
	"@type":                  "rkaf:RegisteredConcept"
	"skos:prefLabel":          string              // required (1); xsd:string
	// The facet this concept belongs to, named by its scheme. Required so no
	// concept floats facet-free: an unscheme'd concept is precisely the term
	// that later merges with a same-spelled term from another facet. The
	// referenced scheme MAY be an rkaf:ConceptScheme or an external
	// skos:ConceptScheme — SKOS owns the membership relation, so L1 declares no
	// class range over it.
	"skos:inScheme":          string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:managedByRegistry": string              // IRI of rkaf:ConceptRegistry
	"rkaf:conceptScope":      string              // free-form scope IRI
	"rkaf:conceptStatus":     #ConceptStatus
	// Optional SKOS composition (Cohort A, §9.2, PKA-2szi).
	"skos:altLabel"?:   [...string]              // 0..*; display synonyms
	"skos:definition"?: string                   // 0..1; the meaning, in words
	"skos:broader"?:   string                    // 0..1; IRI of broader concept
	"skos:narrower"?:  [...string]               // 0..*; IRIs of narrower concepts
	"skos:related"?:   [...string]               // 0..*; IRIs of related concepts

	// Promotion is rare and requires a written meaning (§4.7). A concept marked
	// promoted with no `skos:definition` records the OUTCOME of a review whose
	// central artifact — what the term means — was never written down.
	if registered["rkaf:conceptStatus"] == "rkaf:promoted" {
		"skos:definition": string
	}
}

#LocalConcept: local={
	"@type":               "rkaf:LocalConcept"
	"skos:prefLabel":       string              // required (1); xsd:string
	"skos:inScheme":       string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:definedInScope": string              // IRI of the defining workspace
	"rkaf:conceptScope":   string
	"rkaf:conceptStatus":  #ConceptStatus
	// Optional SKOS composition (Cohort A, §9.2, PKA-2szi).
	"skos:altLabel"?:   [...string]            // 0..*; display synonyms
	"skos:definition"?: string                 // 0..1; the meaning, in words
	"skos:broader"?:   string                  // 0..1; IRI of broader concept
	"skos:narrower"?:  [...string]             // 0..*; IRIs of narrower concepts
	"skos:related"?:   [...string]             // 0..*; IRIs of related concepts

	if local["rkaf:conceptStatus"] == "rkaf:promoted" {
		"skos:definition": string
	}
}
