package rkaf

// AILineage requires humanApprover; AI-touched assertions without lineage are
// rejected (§5.3). Cross-property invariant enforced in assertion.cue.
#AILineage: {
	"@type":                  "rkaf:AILineage"
	"rkaf:modelId":           string
	"rkaf:modelVersion":      string
	"rkaf:promptTemplateRef": string // IRI
	"rkaf:temperature":       >=0.0 & <=2.0
	"rkaf:seed"?:             int
	"rkaf:inputContextHash":  string
	"rkaf:humanApprover":     string // IRI — REQUIRED
	"rkaf:humanRationale"?:   string
}
