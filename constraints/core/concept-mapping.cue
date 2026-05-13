package rkaf

// ConceptMapping (ConceptRegistry v0.1.2 §4): a mapping between concepts that
// aligns with SKOS mapping predicates (exactMatch, closeMatch, broadMatch,
// narrowMatch, relatedMatch). Carries an optional MappingApplicabilityContext
// constraining the domain in which the mapping is valid.
#SkosMappingPredicate: "skos:exactMatch" | "skos:closeMatch" |
	"skos:broadMatch" | "skos:narrowMatch" | "skos:relatedMatch"

#ConceptMapping: {
	"@type":                     "rkaf:ConceptMapping"
	"rkaf:sourceConcept":        string // IRI of source Concept
	"rkaf:targetConcept":        string // IRI of target Concept
	"rkaf:mappingPredicate":     #SkosMappingPredicate
	"rkaf:hasApplicability"?:    string // IRI of rkaf:MappingApplicabilityContext or rkaf:ApplicabilityScope
	"rkaf:usageEligibility"?:    #UsageEligibility
}

// MappingApplicabilityContext (§4.4): scopes a mapping by application domain
// and evidence purpose.
#MappingApplicabilityContext: {
	"@type":                  "rkaf:MappingApplicabilityContext"
	"rkaf:applicationDomain": [...string]
	"rkaf:evidencePurpose"?:  [...string]
}
