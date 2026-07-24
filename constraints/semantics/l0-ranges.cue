package semantics

// Class-valued ranges used by the L0 carrier-mapping audit. Property domains
// come directly from the CUE shapes in constraints/core/.
#L0RangeRegistry: {
	"rkaf:publishedInProceeding": "rkaf:Proceeding"
	"rkaf:hasAuthority":           "rkaf:Authority"
	"rkaf:hasDocket":              "rkaf:Docket"
	"rkaf:proceedingAffects":      "rkaf:Artifact"
	"rkaf:proceedingProduces":     "rkaf:Artifact"
	"rkaf:proceedingSupersedes":   "rkaf:Proceeding"
	"rkaf:commentPeriodFor":       "rkaf:Proceeding"
	"rkaf:commentPeriodDocket":    "rkaf:Docket"
	"rkaf:commentPeriodOpenedBy":  "rkaf:Artifact"
	"dcterms:hasFormat":            "rkaf:Artifact"
	"dcterms:isFormatOf":           "rkaf:Artifact"
	"prov:wasDerivedFrom":         "prov:Entity"
}
