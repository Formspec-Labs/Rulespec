package semantics

// Class-valued ranges owned by the US rulemaking profile. Every term here is
// declared by a shape in this directory, never by the kernel. The L0 audit and
// the SHACL emitter read the union of every `l0-ranges.cue` under
// constraints/; a consumer that does not adopt this profile simply never sees
// these predicates.
#USRulemakingL0RangeRegistry: {
	"rkaf:publishedInProceeding":  "rkaf:Proceeding"
	"dcat:qualifiedRelation":      "rkaf:AgendaProceedingRelationship"
	"dcterms:relation":            "rkaf:Proceeding"
	"rkaf:hasDocket":              "rkaf:Docket"
	"rkaf:proceedingAffects":      "rkaf:Artifact"
	"rkaf:proceedingProduces":     "rkaf:Artifact"
	"rkaf:proceedingSupersedes":   "rkaf:Proceeding"
	"rkaf:commentPeriodFor":       "rkaf:Proceeding"
	"rkaf:commentPeriodDocket":    "rkaf:Docket"
	"rkaf:commentPeriodOpenedBy":  "rkaf:Artifact"
}
