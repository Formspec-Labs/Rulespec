package rkaf

// RelationshipAssertion restores the proposition-bearing specialization from
// Rulespec v0.1 without changing the backward-compatible generic Assertion
// envelope. Expected and observed are comparison roles, not stored modes.
//
// `#AssertionPolarity` is declared in constraints/core/assertion.cue: polarity
// belongs to the shared proposition core that `#ValueAssertion` closes over
// too, not to this one form.
//
// Two definitions arrive by composition, and each carries a different half of
// the contract:
//   #AssertionProposition — the immutable proposition core (subject,
//     predicate, polarity), shared with #ValueAssertion.
//   #DurableAssertionEnvelope — provenance, epistemic basis, grounding, and
//                               consumer disposition.
// Both live in constraints/core/assertion.cue, so their properties and the
// AI-lineage conditionals have exactly one source and are projected here from
// it.
//
// The restatements below are NOT duplication. They are deliberate
// RelationshipAssertion-specific NARROWINGS of the composed definitions: the
// shared definitions type their reference fields as plain `string`, while a
// RelationshipAssertion additionally requires each of them to be an absolute
// IRI. Narrowing is exactly what CUE unification does with an embedded
// definition; the projector unifies these facet by facet, so the compiled
// JSON Schema / SHACL / Rust / TypeScript carry the composed definition AND
// the stricter pattern. Deleting them would loosen every generated target
// relative to the CUE source.
#RelationshipAssertion: assertion={
	#DurableAssertionEnvelope
	#AssertionProposition
	"@type": "rkaf:RelationshipAssertion"

	// Derived-shape narrowings of the shared proposition core, plus the
	// form-specific object slot: a RelationshipAssertion's object is an IRI
	// naming an entity, concept, Artifact, SourceFragment, or other semantic
	// resource. A typed literal object is a #ValueAssertion instead.
	"rkaf:assertsSubject":   string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:assertsPredicate": string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:assertsObject":    string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"

	// Derived-shape narrowings of #AssertionEnvelope reference fields.
	"rkaf:hasApplicability"?:        string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:hasJustification"?:        string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:hasWarrant"?:              string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:hasAuthority"?:            string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:hasAccessScope"?:          string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:hasRetentionPolicy"?:      string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:hasSourceClaimant"?:       string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:hasExtractionProvenance"?: string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:hasConfidence"?:           [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")]
	"rkaf:supersedesAssertion"?:     [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")]

	// Derived-shape narrowing of the envelope's AI-lineage conditionals: the
	// envelope requires hasAILineage for AI-touched origins, and here it must
	// additionally be an IRI. The guard conditions are the envelope's own
	// (§5.3); only the value shape is narrowed.
	if assertion["rkaf:assertionOrigin"] == "rkaf:aiSuggested" {
		"rkaf:hasAILineage": string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	}
	// Same narrowing for the envelope's deterministic-origin conditional
	// (§2.4): the required ExtractionActivity must be named by an IRI.
	if assertion["rkaf:assertionOrigin"] == "rkaf:deterministicExtraction" {
		"rkaf:hasExtractionProvenance": string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	}
}
