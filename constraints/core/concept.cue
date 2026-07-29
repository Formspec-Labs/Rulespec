package rkaf

// Native SKOS concept carriage. Language maps and typed notation come from
// vocabulary-text.cue so every resource uses one BCP 47 grammar.
#ConceptScheme: {
	#SkosAuthoredText
	"@type":                    "rkaf:ConceptScheme"
	"rkaf:schemeFacet":         string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"skos:hasTopConcept"?:      [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")]
	{
		"rkaf:managedByRegistry": string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	} | {
		"rkaf:definedInScope": string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	}
}

#RegisteredConcept: {
	#SkosConceptAuthoredText
	"@type":                  "rkaf:RegisteredConcept"
	"skos:inScheme":          string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:managedByRegistry": string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:conceptScope":      string
	"rkaf:registeredAt":      string // xsd:dateTime
	"skos:broader"?:          [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")]
	"skos:narrower"?:         [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")]
	"skos:related"?:          [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")]
}

#LocalConcept: {
	#SkosConceptAuthoredText
	"@type":               "rkaf:LocalConcept"
	"skos:inScheme":       string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:definedInScope": string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:conceptScope":   string
	"skos:broader"?:       [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")]
	"skos:narrower"?:      [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")]
	"skos:related"?:       [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")]
}
