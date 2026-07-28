package rkaf

// ConceptAssignment is a strict RelationshipAssertion specialization. The
// predicate records the assignment role; the subject is the Artifact or
// SourceFragment being tagged; the object is the concept. There are no parallel
// assignmentSubject/assignedConcept/assignmentRole fields.
#ConceptAssignmentPredicate: "rkaf:assignmentPrimary" |
	"rkaf:assignmentSubstantive" | "rkaf:assignmentMention" |
	"rkaf:assignmentContextual"

#ConceptAssignment: assignment={
	#DurableAssertionEnvelope
	#AssertionProposition
	"@type":                  "rkaf:ConceptAssignment"
	"rkaf:assertsSubject":    string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:assertsPredicate":  #ConceptAssignmentPredicate
	"rkaf:assertsObject":     string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:assertionPolarity": "rkaf:affirmed"

	// Exact release whose semantic manifest contains assertsObject. The concept
	// IRI stays stable; this pin preserves the definition used by this record.
	"rkaf:assignedConceptRelease": string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"

	// Narrow shared-envelope references to absolute IRIs.
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

	if assignment["rkaf:assertionOrigin"] == "rkaf:aiSuggested" {
		"rkaf:hasAILineage": string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	}
	if assignment["rkaf:assertionOrigin"] == "rkaf:deterministicExtraction" {
		"rkaf:hasExtractionProvenance": string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	}
}
