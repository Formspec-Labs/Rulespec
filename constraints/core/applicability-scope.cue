package rkaf

// ApplicabilityScope: declares where, to whom, and under what conditions a
// Warrant or Assertion applies. Aligns with LegalRuleML applicability and
// ELI's jurisdiction model.
//
// `appliesInJurisdiction` accepts ISO 3166 codes, ELI jurisdiction IRIs, or
// partner-defined territorial IRIs (e.g., agency codes). `appliesToSubject`
// constrains the kind of subject the warrant binds.
#ApplicabilityScope: {
	"@type":                          "rkaf:ApplicabilityScope"
	"rkaf:appliesInJurisdiction":     [...string]
	"rkaf:appliesToSubject"?:         [...string]
	"rkaf:hasEffectivePeriod"?:       string // IRI of rkaf:EffectivePeriod
	"rkaf:applicabilityCondition"?:   string // free-form predicate (audited not validated)
}
