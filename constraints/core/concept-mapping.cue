package rkaf

// ConceptMapping (ConceptRegistry v0.1.2 §4): a mapping between concepts that
// aligns with SKOS mapping predicates (exactMatch, closeMatch, broadMatch,
// narrowMatch, relatedMatch). Carries an optional MappingApplicabilityContext
// constraining the domain in which the mapping is valid.
// SKOS mapping predicates per ConceptRegistry v0.1.2 §2.2 — the closed set
// allowed on `rkaf:mappingRelation`. The hand-authored conceptregistry shape
// (`shapes/rkaf-shapes-conceptregistry.ttl`) is the canonical reference for
// this enum; CUE mirrors it.
#SkosMappingPredicate: "skos:closeMatch" | "skos:exactMatch" |
	"skos:broader" | "skos:narrower" | "skos:related" | "skos:mappingRelation"

#ConceptMappingLifecycleState: "rkaf:proposed" | "rkaf:underReview" |
	"rkaf:approved" | "rkaf:deprecated" | "rkaf:retired"

#ConceptMapping: {
	"@type":                     "rkaf:ConceptMapping"
	"rkaf:sourceConcept":        string // IRI of source Concept
	"rkaf:targetConcept":        string // IRI of target Concept
	"rkaf:mappingRelation":      #SkosMappingPredicate
	"rkaf:hasApplicability"?:    string // IRI of rkaf:MappingApplicabilityContext or rkaf:ApplicabilityScope
	"rkaf:usageEligibility"?:    #UsageEligibility
	// L4 severity input (rkaf-behavior.md §6.1). Two `approved` mappings
	// pointing at different targets upgrade severity from operationalConflict
	// to publicationBlocking; a mapping in a trusted registry further
	// upgrades to authorityCritical.
	"rkaf:lifecycleState"?:      #ConceptMappingLifecycleState
	"rkaf:managedByRegistry"?:   string // IRI of the ConceptRegistry that owns this mapping
}

// MappingApplicabilityContext (§4.4): scopes a mapping by application domain
// and evidence purpose.
#MappingApplicabilityContext: {
	"@type":                  "rkaf:MappingApplicabilityContext"
	"rkaf:applicationDomain": [...string]
	"rkaf:evidencePurpose"?:  [...string]
}
