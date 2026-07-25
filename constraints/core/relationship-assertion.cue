package rkaf

// RelationshipAssertion restores the proposition-bearing specialization from
// Rulespec v0.1 without changing the backward-compatible generic Assertion
// envelope. Expected and observed are comparison roles, not stored modes.
#AssertionPolarity: "rkaf:affirmed" | "rkaf:denied"

#RelationshipAssertion: assertion={
	"@type":                  "rkaf:RelationshipAssertion"
	"rkaf:assertionOrigin":   #AssertionOrigin
	"rkaf:assertsSubject":    string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:assertsPredicate":  string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:assertsObject":     string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:assertionPolarity": #AssertionPolarity

	// Shared Assertion envelope fields are flattened because the current
	// projector does not preserve CUE shape composition.
	"rkaf:usageEligibility"?:       #UsageEligibility
	"rkaf:hasApplicability"?:       string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:hasJustification"?:       string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:hasWarrant"?:             string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:hasAuthority"?:           string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"prov:wasDerivedFrom"?:         [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")]
	"rkaf:consumerLifecycleState"?: #ConsumerLifecycleState

	// AI-touched origins retain the generic Assertion lineage invariant.
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
