package rkaf

// Closed enum (§2.2). The datatypes a ValueAssertion object may carry, drawn
// from XSD so that every RDF consumer already knows how to read them.
//
// The set is deliberately narrow: text and enumerated tokens, the three
// numeric kinds, the three calendar kinds, a duration, and an IRI-as-value.
// It covers the typed data a document pipeline must keep typed — dates,
// identifiers, authorities, and document states — without opening the door to
// arbitrary datatype IRIs, which would make "typed" mean nothing.
#ValueDatatype: "xsd:string" | "xsd:token" | "xsd:boolean" | "xsd:integer" |
	"xsd:decimal" | "xsd:double" | "xsd:date" | "xsd:dateTime" |
	"xsd:time" | "xsd:duration" | "xsd:anyURI"

// ValueAssertion is the second proposition-bearing Assertion specialization
// (§2.2). It differs from #RelationshipAssertion in exactly one place: the
// object slot. A relationship's object is an IRI naming a semantic resource; a
// value's object is a typed literal.
//
// Everything else is shared by composition, not by restatement:
//   #AssertionProposition — subject, predicate, polarity (immutable core)
//   #AssertionEnvelope    — origin, provenance, grounding, consumer
//                           disposition (context, some of it mutable)
// Both are declared in constraints/core/assertion.cue. The narrowings below
// are the same deliberate IRI tightenings #RelationshipAssertion applies; the
// projector unifies them facet by facet into every target.
#ValueAssertion: assertion={
	#AssertionEnvelope
	#AssertionProposition
	"@type": "rkaf:ValueAssertion"

	// Derived-shape narrowings of the shared proposition core.
	"rkaf:assertsSubject":   string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:assertsPredicate": string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"

	// The form-specific object slot: one JSON-LD value object, which expands
	// to exactly one typed RDF literal. `@value` is the LEXICAL form — kept a
	// string on the wire so `"42"^^xsd:integer` round-trips byte-for-byte —
	// and `@type` names the datatype from the closed set above.
	//
	// Carriage per target: JSON Schema validates the object and closes `@type`
	// over #ValueDatatype; SHACL closes the expanded literal over the same set
	// with one `sh:datatype` alternative per value; Rust receives
	// `crate::TypedLiteral<ValueDatatype>`; TypeScript receives the member
	// types plus a generated datatype-membership check.
	"rkaf:assertsValue": {
		"@value": string
		"@type":  #ValueDatatype
	}

	// Derived-shape narrowings of #AssertionEnvelope reference fields.
	"rkaf:hasApplicability"?:        string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:hasJustification"?:        string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:hasWarrant"?:              string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:hasAuthority"?:            string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:hasAccessScope"?:          string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:hasSourceClaimant"?:       string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:hasExtractionProvenance"?: string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:hasConfidence"?:           [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")]
	"rkaf:supersedesAssertion"?:     [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")]

	// Derived-shape narrowing of the envelope's AI-lineage conditionals
	// (§5.3): the guards are the envelope's own, only the value shape is
	// narrowed to an absolute IRI.
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

	// Same narrowing for the envelope's deterministic-origin conditional
	// (§2.4): the required ExtractionActivity must be named by an IRI.
	if assertion["rkaf:assertionOrigin"] == "rkaf:deterministicExtraction" {
		"rkaf:hasExtractionProvenance": string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	}
}
