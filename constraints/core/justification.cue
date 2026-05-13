package rkaf

// Justification (spec/rkaf-concept-registry.md §2.5; §1 abstract list of
// primitives): a structured grounding record carried by a ConceptMapping or
// other rkaf:* node. Generalizes v0.1.2's authority-chain hop into a
// warrant-family-agnostic form. The `hasWarrant` field accepts any warrant
// family (legal / scientific / editorial / cryptographic / social /
// source-class); v0.1.2's `hasAuthority` predicate remains valid as the
// legal-family specialization.
//
// Used in:
//   - rkaf:ConceptMapping (rkaf:hasJustification)
//   - rkaf:JustificationChainHop (chain traversal in v0.1 §2.4 — runtime;
//     codification deferred to Plan 7)
#Justification: {
	"@type":               "rkaf:Justification"
	"rkaf:hasWarrant":     string // IRI of an rkaf:Warrant (or rkaf:Authority specialization)
	"rkaf:basedOnEvidence"?: [...string] // optional IRIs of rkaf:EvidenceBinding nodes
	"rkaf:asserted_by"?:   string // optional IRI of the actor / system asserting the justification
	"rkaf:assertedAt"?:    string // xsd:dateTime
}
