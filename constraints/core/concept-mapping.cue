package rkaf

// ConceptMapping (ConceptRegistry v0.1.2 §4): a mapping between concepts that
// aligns with SKOS mapping predicates (exactMatch, closeMatch, broadMatch,
// narrowMatch, relatedMatch). Carries an optional MappingApplicabilityContext
// constraining the domain in which the mapping is valid.
// SKOS mapping predicates per ConceptRegistry v0.1.2 §2.2 — the closed set
// allowed on `rkaf:mappingRelation`. The hand-authored conceptregistry shape
// (`shapes/rkaf-shapes-conceptregistry.ttl`) is the canonical reference for
// this enum; CUE mirrors it.
//
// v0.2 ADDS SKOS's three remaining mapping properties — `skos:broadMatch`,
// `skos:narrowMatch`, `skos:relatedMatch` — which the original set omitted even
// though the comment above claimed them. SKOS draws a real line here:
// `skos:broader` / `skos:narrower` / `skos:related` are semantic relations
// WITHIN one scheme, while the `*Match` properties are the cross-scheme mapping
// properties (SKOS Reference §10). Alignment to an external thesaurus needs the
// `*Match` half, and without it a producer had to reach for the in-scheme
// relation and misstate the alignment. No value is removed: the three in-scheme
// relations stay legal on a mapping, and every existing mapping stays valid.
#SkosMappingPredicate: "skos:closeMatch" | "skos:exactMatch" |
	"skos:broadMatch" | "skos:narrowMatch" | "skos:relatedMatch" |
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
