package semantics

// Class-valued ranges used by the L0 carrier-mapping audit. Property domains
// come directly from the CUE shapes in constraints/core/.
//
// This file carries the KERNEL ranges only. A profile declares the ranges of
// the properties it owns in its own `l0-ranges.cue` (see
// constraints/profiles/us-rulemaking/semantics/l0-ranges.cue); the audit and
// the SHACL emitter read the union of every `l0-ranges.cue` under constraints/.
// `dcterms:isVersionOf` is deliberately ABSENT. Its object is the stable
// resource an Artifact is a version of, and that resource keeps whatever public
// type owns it — ELI, BIBFRAME, Schema.org, or a profile class. Declaring a
// class range here would be Rulespec minting the universal Work class
// `spec/rkaf-core.md` §4.1 declines to mint, and it would reject every producer
// composing a public model instead. `skos:inScheme` is absent for the same
// reason: SKOS owns scheme membership and a concept may be an external
// `skos:Concept`.
#L0RangeRegistry: {
	"rkaf:hasAuthority":    "rkaf:Authority"
	"dcterms:hasFormat":    "rkaf:Artifact"
	"dcterms:isFormatOf":   "rkaf:Artifact"
	"prov:wasRevisionOf":   "rkaf:Artifact"
	"prov:wasDerivedFrom":  "prov:Entity"
	// SourceFragment identity: the parent of a fragment is an Artifact, not any
	// IRI (§4.2).
	"oa:hasSource":         "rkaf:Artifact"
	// Version lineage must resolve to addressable source regions, never to a
	// bare label or a similarity score (§4.1).
	"rkaf:versionLineageEvidence": "rkaf:SourceFragment"
	// No class range on bindsAssertion: the object may be a core Assertion
	// specialization or an analysis assertion form that deliberately is not
	// an rkaf:Assertion subclass. The inverse target shapes enforce the
	// allowed durable forms without inventing a false common class.
	"rkaf:bindsSourceFragment":    "rkaf:SourceFragment"
	// Immutable reference-resource release pins (§4.7 / Concept Registry §2.2).
	"rkaf:assignedConceptRelease":   "rkaf:ReferenceResourceRelease"
	"rkaf:sourceConceptRelease":     "rkaf:ReferenceResourceRelease"
	"rkaf:targetConceptRelease":     "rkaf:ReferenceResourceRelease"
	"dcat:distribution":             "rkaf:Artifact"
	"rkaf:hasAccessScope":                  "rkaf:AccessScope"
	"rkaf:hasRetentionPolicy":              "rkaf:RetentionPolicy"
}
