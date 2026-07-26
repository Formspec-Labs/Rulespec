package rkaf

// AILineage records the MODEL DERIVATION: which model, at which version, under
// which prompt contract and sampling settings, over which input context (§5.3).
// AI-touched assertions carrying no lineage at all are still rejected — that
// cross-property invariant lives in assertion.cue and is unchanged.
//
// `rkaf:humanApprover` is OPTIONAL. An unreviewed model candidate must be
// representable exactly as it is: a model produced it, and nobody has looked at
// it yet. Requiring an approver here forced every `rkaf:aiSuggested` assertion
// — the origin value whose entire meaning is "unreviewed candidate" — to name a
// reviewer, so the only way to record an honest candidate was to invent one.
// Approval is a separate, scoped, temporal `rkaf:Attestation` targeting the
// assertion (§2.4, §3.1); a candidate nobody has reviewed simply has no such
// Attestation yet.
//
// What the shape still refuses is a lineage carrying the TRACES of a review
// without the reviewer. `rkaf:humanRationale` is a human's stated reason for
// accepting the output; a rationale with no `rkaf:humanApprover` is a review
// attributed to nobody, which is worse than an unreviewed candidate because it
// READS as approved. The conditional below rejects exactly that.
#AILineage: lineage={
	"@type":                  "rkaf:AILineage"
	"rkaf:modelId":           string
	"rkaf:modelVersion":      string
	"rkaf:promptTemplateRef": string // IRI
	"rkaf:temperature":       >=0.0 & <=2.0
	"rkaf:seed"?:             int
	// A digest, not a free string: lowercase `sha256:<64 hex>`, the lexical
	// contract `rkaf:requestContractDigest` and `rkaf:inputDigest` already use.
	// A hash field that accepts any string cannot be compared across runs,
	// which is the only thing an input-context hash exists to do.
	"rkaf:inputContextHash":  string & =~"^sha256:[0-9a-f]{64}$"
	"rkaf:humanApprover"?:    string // IRI — OPTIONAL; approval is an Attestation
	"rkaf:humanRationale"?:   string

	if lineage["rkaf:humanRationale"] != _|_ {
		"rkaf:humanApprover": string
	}
}
