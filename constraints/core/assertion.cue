package rkaf

// Closed enum (preserved from v0.1, see Core v0.1 §3 assertionOrigin).
// v0.2 adds ONE value: `rkaf:deterministicExtraction`, for a record a
// deterministic parser or join produced. The v0.1 set had no such value, so a
// mechanically derived record had to claim `rkaf:imported` — which says only
// that the record came from somewhere else — while the method that actually
// produced it hung off an OPTIONAL edge nothing required. See Core §2.4,
// "Deterministic origin".
#AssertionOrigin: "rkaf:humanAsserted" | "rkaf:aiSuggested" | "rkaf:aiPromoted" |
	"rkaf:humanQualified" | "rkaf:humanRevalidation" | "rkaf:imported" |
	"rkaf:deterministicExtraction"

// AI-touched origins; assertions with these MUST carry hasAILineage (§5.3).
#AssertionOriginAITouched: "rkaf:aiSuggested" | "rkaf:aiPromoted" |
	"rkaf:humanQualified" | "rkaf:humanRevalidation"

// Whether the proposition is affirmed or denied. Part of the immutable
// proposition core, so it lives beside `#AssertionProposition` rather than in
// one form's file: `#RelationshipAssertion` and `#ValueAssertion` both close
// over the same two values. Predicates stay affirmative; polarity records
// whether the source-backed assertion affirms or denies that relationship.
#AssertionPolarity: "rkaf:affirmed" | "rkaf:denied"

// Immutable proposition content: WHAT is claimed, and whether the claim is
// affirmed or denied (§2.3). Every proposition-bearing assertion form composes
// this definition, so the two forms cannot drift on the shared half of the
// proposition.
//
// This definition deliberately carries NOTHING else. Acceptance, disposition,
// confidence, attestation, and consumer eligibility are separate records keyed
// to the assertion IRI — an assertion's identity never includes mutable state,
// so none of it may live here. `#ConsumerDisposition` below is the named
// counterpart holding the mutable half; keeping both named makes the boundary
// a structural fact of the source rather than a comment.
//
// The object slot is form-specific and therefore NOT declared here:
// `#RelationshipAssertion` supplies an IRI-valued `rkaf:assertsObject`,
// `#ValueAssertion` a typed-literal `rkaf:assertsValue`.
#AssertionProposition: {
	"rkaf:assertsSubject":    string
	"rkaf:assertsPredicate":  string
	"rkaf:assertionPolarity": #AssertionPolarity
}

// Mutable, consumer-scoped disposition (§2.3). These are the L4 reducer's
// inputs and outputs; they change as consumers, scopes, and reviews change,
// while the proposition above does not. They are named separately so that no
// reader — and no future edit — can mistake them for proposition content.
#ConsumerDisposition: {
	// L4 reducer inputs (rkaf-behavior.md §1.2). The reducer reads
	// these to compute effective usageEligibility per scope.
	"rkaf:usageEligibility"?:       #UsageEligibility
	"rkaf:consumerLifecycleState"?: #ConsumerLifecycleState
	"rkaf:hasAccessScope"?:         string // IRI of an AccessScope
}

// The generic Assertion envelope, minus the JSON-LD `@type` discriminator.
// Assertion specializations embed this definition rather than restating it, so
// the envelope has exactly one source and cannot drift between classes. The
// projector flattens the composition into every target.
//
// The envelope holds CONTEXT for a proposition — where it came from, what
// grounds it, who may use it — never the proposition itself. It composes
// `#ConsumerDisposition` for the mutable half; `#AssertionProposition` is
// composed by the proposition-bearing forms, not by the envelope, because the
// generic `#Assertion` is an envelope-only carrier retained for v0.2
// backward compatibility.
#AssertionEnvelope: envelope={
	#ConsumerDisposition
	"rkaf:assertionOrigin": #AssertionOrigin
	// AI-touched assertionOrigin REQUIRES hasAILineage (§5.3).
	if envelope["rkaf:assertionOrigin"] == "rkaf:aiSuggested" {
		"rkaf:hasAILineage": string
	}
	if envelope["rkaf:assertionOrigin"] == "rkaf:aiPromoted" {
		"rkaf:hasAILineage": string
	}
	if envelope["rkaf:assertionOrigin"] == "rkaf:humanQualified" {
		"rkaf:hasAILineage": string
	}
	if envelope["rkaf:assertionOrigin"] == "rkaf:humanRevalidation" {
		"rkaf:hasAILineage": string
	}
	// A deterministic origin REQUIRES hasExtractionProvenance (§2.4). The
	// value claims the record is mechanically reproducible, and a claim of
	// reproducibility that names no run is not one: without the edge the
	// method is droppable and no gate notices, which is exactly the seam that
	// forced a real consumer to demote its parse method to an optional edge
	// under `rkaf:imported`.
	if envelope["rkaf:assertionOrigin"] == "rkaf:deterministicExtraction" {
		"rkaf:hasExtractionProvenance": string
	}
	"rkaf:hasApplicability"?:   string // IRI of an ApplicabilityScope
	"rkaf:hasJustification"?:   string // IRI of a Justification
	"rkaf:hasWarrant"?:         string // IRI of the warrant grounding this assertion
	"rkaf:hasAuthority"?:       string // IRI; legal-family Warrant or Authority
	"prov:wasDerivedFrom"?:     [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")]
	// Provenance roles, each a SEPARATE record (§2.4). None of them is the
	// proposition, and none of them stands in for another:
	//   hasSourceClaimant      — who the SOURCE says asserts this
	//   hasExtractionProvenance — which run produced the candidate
	//   hasAILineage            — the reviewed model-derivation record (§5.3)
	//   prov:wasDerivedFrom     — the derivation chain
	// Human approval is none of these: it is an rkaf:Attestation targeting
	// this assertion.
	"rkaf:hasSourceClaimant"?:       string // IRI of a SourceClaimant
	"rkaf:hasExtractionProvenance"?: string // IRI of an ExtractionActivity
	// Confidence is a separate measured record, never a bare number on the
	// assertion (§4.5). Repeatable: different measurers, different methods.
	//
	// Typed as plain strings here for the same reason every other envelope
	// reference field is: the generic envelope states the EDGE, and each
	// proposition-bearing form narrows it to an absolute IRI. The L4 behavior
	// corpus addresses assertions by short graph-local labels, so an IRI
	// pattern on the generic envelope would reject documents the runtime
	// contract is defined over.
	"rkaf:hasConfidence"?: [...string]
	// Supersession appends history instead of rewriting it: the successor
	// names the assertions it replaces; the predecessors stay addressable.
	"rkaf:supersedesAssertion"?: [...string]
	// When the assertion was made. A temporal reference on the record, NOT
	// the applicability period of what it claims (that is hasApplicability).
	"rkaf:assertedAt"?: string // xsd:dateTime
}

#Assertion: {
	#AssertionEnvelope
	"@type": "rkaf:Assertion"
}
