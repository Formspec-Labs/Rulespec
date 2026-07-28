package rkaf

// ConceptMapping is a durable assertion that one concept maps to another
// across schemes. SKOS defines exactly five concrete mapping properties.
// `skos:broader`, `skos:narrower`, and `skos:related` are in-scheme semantic
// relations, not mapping properties. `skos:mappingRelation` is their abstract
// super-property and is too weak to state which mapping is claimed. Those four
// predicates therefore remain available on Concept nodes and are deliberately
// illegal here (SKOS Reference §10).
#SkosMappingPredicate: "skos:exactMatch" | "skos:closeMatch" |
	"skos:broadMatch" | "skos:narrowMatch" | "skos:relatedMatch"

// Both concept slots are IRIs on the wire — `context/rkaf-context.jsonld`
// coerces each with `@type: @id` — but NEITHER carries a class range in
// `constraints/semantics/l0-ranges.cue`, and that absence is deliberate for the
// reason that file already records for `skos:inScheme`: SKOS owns concept
// identity, and a mapping's endpoint
// may legally be an external `skos:Concept` in a thesaurus Rulespec does not
// model. Pinning a range here would reject exactly the cross-scheme alignment
// the `*Match` predicates exist for. The cardinality and the IRI coercion are
// what is enforced; the class is not.
#ConceptMapping: mapping={
	#DurableAssertionEnvelope
	#AssertionProposition
	"@type":                     "rkaf:ConceptMapping"
	// Canonical RelationshipAssertion proposition. There are no parallel
	// sourceConcept / targetConcept / mappingRelation slots: one mapping has
	// one proposition identity everywhere in the graph.
	"rkaf:assertsSubject":       string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:assertsPredicate":     #SkosMappingPredicate
	"rkaf:assertsObject":        string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:assertionPolarity":    "rkaf:affirmed"
	// A mapping may connect concepts from different registries, so each
	// endpoint carries its own immutable release pin.
	"rkaf:sourceConceptRelease": string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:targetConceptRelease": string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:hasApplicability"?:    string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	// Registry identity and trust input only. It is not approval, publication,
	// deployment, or usage authorization.
	"rkaf:managedByRegistry"?:   string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"

	// Narrow shared-envelope references to IRIs for this assertion form.
	"rkaf:hasJustification"?:        string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:hasWarrant"?:              string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:hasAuthority"?:            string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:hasAccessScope"?:          string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:hasRetentionPolicy"?:      string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:hasSourceClaimant"?:       string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:hasExtractionProvenance"?: string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:hasConfidence"?:           [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")]
	"rkaf:supersedesAssertion"?:     [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")]

	if mapping["rkaf:assertionOrigin"] == "rkaf:aiSuggested" {
		"rkaf:hasAILineage": string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	}
	if mapping["rkaf:assertionOrigin"] == "rkaf:deterministicExtraction" {
		"rkaf:hasExtractionProvenance": string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	}
}

// MappingApplicabilityContext (§4.4): scopes a mapping by application domain
// and evidence purpose.
#MappingApplicabilityContext: {
	"@type":                  "rkaf:MappingApplicabilityContext"
	"rkaf:applicationDomain": [...string]
	"rkaf:evidencePurpose"?:  [...string]
}
