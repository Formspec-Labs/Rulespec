package rkaf

// GeneratedWorkProduct (v0.1 §6.1).
//
// An OVERLAY type on existing consumer types (`formspec:Field`,
// `wos:WorkflowStep`, others). Preexisting artifacts not created by Rulespec
// tooling MAY carry `justifiedByAssertion` without being typed as
// GeneratedWorkProduct. Only Rulespec-generated artifacts receive this type.
//
// `consumerLifecycleState` is a DENORMALIZED consumer-side cache — not
// authoritative; authoritative state is computed by the reducer (§1.4 of
// rkaf-behavior) plus lifecycle events.
#GeneratedWorkProduct: {
	"@type":                          "rkaf:GeneratedWorkProduct"
	"rkaf:justifiedByAssertion":      string // IRI of the justifying Assertion (required per bridge rule #10)
	"rkaf:consumerLifecycleState"?:   #ConsumerLifecycleState
	"rkaf:proposedUsageEligibility"?: string // IRI of the rkaf:UsageEligibility lattice value being requested (§6.3)
}

// Cached lifecycle state on a generated work product. Closed enum.
#ConsumerLifecycleState: "rkaf:draft" |
	"rkaf:proposedForOperational" |
	"rkaf:operational" |
	"rkaf:staleForCurrentUse" |
	"rkaf:published"
