package rkaf

// Closed enum (preserved from v0.1, see Core v0.1 §3 assertionOrigin).
#AssertionOrigin: "rkaf:humanAsserted" | "rkaf:aiSuggested" | "rkaf:aiPromoted" |
	"rkaf:humanQualified" | "rkaf:humanRevalidation" | "rkaf:imported"

// AI-touched origins; assertions with these MUST carry hasAILineage (§5.3).
#AssertionOriginAITouched: "rkaf:aiSuggested" | "rkaf:aiPromoted" |
	"rkaf:humanQualified" | "rkaf:humanRevalidation"

#Assertion: {
	"@type":                "rkaf:Assertion"
	"rkaf:assertionOrigin": #AssertionOrigin
	// AI-touched assertionOrigin REQUIRES hasAILineage (§5.3).
	if "rkaf:assertionOrigin" == "rkaf:aiSuggested" {
		"rkaf:hasAILineage": string
	}
	if "rkaf:assertionOrigin" == "rkaf:aiPromoted" {
		"rkaf:hasAILineage": string
	}
	if "rkaf:assertionOrigin" == "rkaf:humanQualified" {
		"rkaf:hasAILineage": string
	}
	if "rkaf:assertionOrigin" == "rkaf:humanRevalidation" {
		"rkaf:hasAILineage": string
	}
	// L4 reducer inputs (rkaf-behavior.md §1.2). The reducer reads
	// these to compute effective usageEligibility per scope.
	"rkaf:usageEligibility"?:         #UsageEligibility
	"rkaf:hasApplicability"?:         string // IRI of an ApplicabilityScope
	"rkaf:hasJustification"?:         string // IRI of a Justification
	"rkaf:hasWarrant"?:               string // IRI of the warrant grounding this assertion
	"rkaf:hasAuthority"?:             string // IRI; legal-family Warrant or Authority
	"prov:wasDerivedFrom"?:           [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")]
	"rkaf:consumerLifecycleState"?:   #ConsumerLifecycleState
}
