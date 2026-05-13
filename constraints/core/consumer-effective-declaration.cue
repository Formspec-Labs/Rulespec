package rkaf

// ConsumerEffectiveDeclaration (Plan 7b §3 rule 2 support concept).
//
// A consumer declares the effective usageEligibility it has computed (or
// intends to apply) for an Assertion. Bridge rule #2 fires when this
// declared value is HIGHER on the lattice than the reducer would compute
// from the same inputs — i.e., the consumer is BROADENING beyond what
// LocalAdoption permits.
//
// This node is consumer-emitted output, not Rulespec-derived. The runtime
// uses it as the "what the consumer said" side of the comparison; the
// reducer produces the "what the spec permits" side.
#ConsumerEffectiveDeclaration: {
	"@type":                  "rkaf:ConsumerEffectiveDeclaration"
	"rkaf:consumer":          string // IRI of the consumer making the declaration
	"rkaf:forAssertion":      string // IRI of the Assertion the declaration applies to
	"rkaf:declaredEffective": #UsageEligibility
	"rkaf:declaredScope"?:    string // optional scope IRI; if absent, declaration is workspace-wide
	"rkaf:declaredAt":        string // xsd:dateTime
}
