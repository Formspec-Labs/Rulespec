package rkaf

// BridgeConsumerRegistration (Core §5.1 — Bridge model): every bridge
// consumer publishes a registration declaring its capabilities. The
// registration is published once and referenced by every
// rkaf:BridgeValidationResult the consumer emits.
//
// `supportedAuthorityKinds` is the list of authorityKind values this
// consumer can validate. Unsupported kinds in incoming packets are refused
// with structured errors per bridge contract rule #3 (spec/rkaf-behavior.md
// §3).
#BridgeConsumerRegistration: {
	"@type":                                "rkaf:BridgeConsumerRegistration"
	"rkaf:consumer":                        string // IRI of the bridge consumer
	"rkaf:bridgeContractVersion":           string
	"rkaf:registeredAt":                    string // xsd:dateTime
	"rkaf:supportedEvaluationAnchors":      [...string] // IRIs of supported EvaluationAnchor values
	"rkaf:supportsRegistryVersionRange":    [...string] // SemVer range strings, one per registry
	"rkaf:supportedAutomaticMigrations":    [...string] // migration kind IRIs
	"rkaf:supportedAuthorityKinds":         [...#AuthorityKind] // cross-file enum (codified in constraints/core/authority.cue)
}
