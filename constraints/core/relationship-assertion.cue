package rkaf

// RelationshipAssertion restores the proposition-bearing specialization from
// Rulespec v0.1 without changing the backward-compatible generic Assertion
// envelope. Expected and observed are comparison roles, not stored modes.
#AssertionPolarity: "rkaf:affirmed" | "rkaf:denied"

// The shared envelope arrives by composition: #AssertionEnvelope
// (constraints/core/assertion.cue) is embedded, so the envelope properties and
// the AI-lineage conditionals have exactly one source and are projected here
// from it.
//
// The restatements below are NOT duplication. They are deliberate
// RelationshipAssertion-specific NARROWINGS of the shared envelope: the
// envelope types its reference fields as plain `string`, while a
// RelationshipAssertion additionally requires each of them to be an absolute
// IRI. Narrowing is exactly what CUE unification does with an embedded
// definition; the projector unifies these facet by facet, so the compiled
// JSON Schema / SHACL / Rust / TypeScript carry the envelope AND the stricter
// pattern. Deleting them would loosen every generated target relative to the
// CUE source.
#RelationshipAssertion: assertion={
	#AssertionEnvelope
	"@type":                  "rkaf:RelationshipAssertion"
	"rkaf:assertsSubject":    string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:assertsPredicate":  string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:assertsObject":     string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:assertionPolarity": #AssertionPolarity

	// Derived-shape narrowings of #AssertionEnvelope reference fields.
	"rkaf:hasApplicability"?: string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:hasJustification"?: string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:hasWarrant"?:       string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:hasAuthority"?:     string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"

	// Derived-shape narrowing of the envelope's AI-lineage conditionals: the
	// envelope requires hasAILineage for AI-touched origins, and here it must
	// additionally be an IRI. The guard conditions are the envelope's own
	// (§5.3); only the value shape is narrowed.
	if assertion["rkaf:assertionOrigin"] == "rkaf:aiSuggested" {
		"rkaf:hasAILineage": string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	}
	if assertion["rkaf:assertionOrigin"] == "rkaf:aiPromoted" {
		"rkaf:hasAILineage": string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	}
	if assertion["rkaf:assertionOrigin"] == "rkaf:humanQualified" {
		"rkaf:hasAILineage": string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	}
	if assertion["rkaf:assertionOrigin"] == "rkaf:humanRevalidation" {
		"rkaf:hasAILineage": string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	}
}
