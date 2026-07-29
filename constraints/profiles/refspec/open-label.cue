package rkaf

// RefSpec profile overlay. It composes the universal ValueAssertion and only
// narrows assertions whose predicate is rkaf:openLabel; ordinary value
// assertions retain the kernel contract unchanged.
#RefSpecOpenLabelValueAssertion: assertion={
	#ValueAssertion
	"@type":                 "rkaf:ValueAssertion"
	"rkaf:openLabelFacet"?:  string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:openLabelRole"?:   #ConceptAssignmentPredicate

	if assertion["rkaf:assertsPredicate"] == "rkaf:openLabel" {
		"rkaf:assertionPolarity": "rkaf:affirmed"
		"rkaf:assertsValue": {
			"@value":    #NonEmptyVocabularyText
			"@language": #BCP47LanguageTag
		}
		"rkaf:openLabelFacet":          string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
		"rkaf:openLabelRole":           #ConceptAssignmentPredicate
		"rkaf:hasExtractionProvenance": string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
		"rkaf:assertedAt":              string // xsd:dateTime
	}
}
