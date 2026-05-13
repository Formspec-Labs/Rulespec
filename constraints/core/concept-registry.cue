package rkaf

// SKOS-bound mapping predicates (concept-registry-v0.2 §2.2).
#SkosMappingPredicate: "skos:closeMatch" | "skos:exactMatch" | "skos:broader" |
	"skos:narrower" | "skos:related" | "skos:mappingRelation"

#ConceptMapping: {
	"@type":                "rkaf:ConceptMapping"
	"rkaf:mappingRelation": #SkosMappingPredicate
}
