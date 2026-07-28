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
//   #DurableAssertionEnvelope — origin, epistemic basis, provenance,
//                               grounding, and consumer disposition
// Both are declared in constraints/core/assertion.cue. The narrowings below
// are the same deliberate IRI tightenings #RelationshipAssertion applies; the
// projector unifies them facet by facet into every target.
#ValueAssertion: assertion={
	#DurableAssertionEnvelope
	#AssertionProposition
	"@type": "rkaf:ValueAssertion"

	// Derived-shape narrowings of the shared proposition core.
	"rkaf:assertsSubject":   string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:assertsPredicate": string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"

	// The form-specific object slot: one closed JSON-LD value object. The two
	// mutually exclusive RDF 1.1 branches are a typed literal and a
	// language-tagged string. A BCP 47 script subtag (for example `Hant` in
	// `zh-Hant`) preserves script without a parallel property.
	//
	// Carriage per target: JSON Schema validates the object and closes `@type`
	// over #ValueDatatype; SHACL closes the expanded literal over the same set
	// with one `sh:datatype` alternative per value; Rust receives
	// `crate::TypedLiteral<ValueDatatype>`; TypeScript receives the member
	// types plus a generated datatype-membership check.
	"rkaf:assertsValue": {
		"@value": string
		{
			"@type": #ValueDatatype
		} | {
			"@language": string & =~"^(?:(?:[A-Za-z]{2,3}(?:-[A-Za-z]{3}){0,3}|[A-Za-z]{4}|[A-Za-z]{5,8})(?:-[A-Za-z]{4})?(?:-(?:[A-Za-z]{2}|[0-9]{3}))?(?:-(?:[A-Za-z0-9]{5,8}|[0-9][A-Za-z0-9]{3}))*(?:-[0-9A-WY-Za-wy-z](?:-[A-Za-z0-9]{2,8})+)*(?:-[xX](?:-[A-Za-z0-9]{1,8})+)?|[xX](?:-[A-Za-z0-9]{1,8})+|[eE][nN]-[gG][bB]-[oO][eE][dD]|[iI]-(?:[aA][mM][iI]|[bB][nN][nN]|[dD][eE][fF][aA][uU][lL][tT]|[eE][nN][oO][cC][hH][iI][aA][nN]|[hH][aA][kK]|[kK][lL][iI][nN][gG][oO][nN]|[lL][uU][xX]|[mM][iI][nN][gG][oO]|[nN][aA][vV][aA][jJ][oO]|[pP][wW][nN]|[tT][aA][oO]|[tT][aA][yY]|[tT][sS][uU])|[sS][gG][nN]-(?:[bB][eE]-[fF][rR]|[bB][eE]-[nN][lL]|[cC][hH]-[dD][eE])|[aA][rR][tT]-[lL][oO][jJ][bB][aA][nN]|[cC][eE][lL]-[gG][aA][uU][lL][iI][sS][hH]|[nN][oO]-(?:[bB][oO][kK]|[nN][yY][nN])|[zZ][hH]-(?:[gG][uU][oO][yY][uU]|[hH][aA][kK][kK][aA]|[mM][iI][nN]|[mM][iI][nN]-[nN][aA][nN]|[xX][iI][aA][nN][gG]))$"
		}
	}

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

	// Derived-shape narrowing of the envelope's AI-lineage conditionals
	// (§5.3): the guards are the envelope's own, only the value shape is
	// narrowed to an absolute IRI.
	if assertion["rkaf:assertionOrigin"] == "rkaf:aiSuggested" {
		"rkaf:hasAILineage": string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	}
	// Same narrowing for the envelope's deterministic-origin conditional
	// (§2.4): the required ExtractionActivity must be named by an IRI.
	if assertion["rkaf:assertionOrigin"] == "rkaf:deterministicExtraction" {
		"rkaf:hasExtractionProvenance": string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	}
}
