package semantics

// Class-valued ranges used by the L0 carrier-mapping audit. Property domains
// come directly from the CUE shapes in constraints/core/.
//
// This file carries the KERNEL ranges only. A profile declares the ranges of
// the properties it owns in its own `l0-ranges.cue` (see
// constraints/profiles/us-rulemaking/semantics/l0-ranges.cue); the audit and
// the SHACL emitter read the union of every `l0-ranges.cue` under constraints/.
#L0RangeRegistry: {
	"rkaf:hasAuthority":    "rkaf:Authority"
	"dcterms:hasFormat":    "rkaf:Artifact"
	"dcterms:isFormatOf":   "rkaf:Artifact"
	"prov:wasRevisionOf":   "rkaf:Artifact"
	"prov:wasDerivedFrom":  "prov:Entity"
}
