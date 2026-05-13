package rkaf

// BridgeIssueAttestationContract (Plan 7b §3 rule 8 support concept).
//
// Bridge rule #8 says: "Bridge-emitted attestations for consumer-detected
// issues." v0.1 doesn't enumerate WHICH issues require an Attestation;
// this contract closes that gap by declaring the issue types that MUST
// yield a corresponding rkaf:Attestation node referencing the BVR.
//
// Closed enum: a Rulespec-conformant bridge MUST emit an Attestation for
// every issue of one of these kinds that it surfaces in a
// BridgeValidationResult.
#BridgeIssueKind: "rkaf:staleDep" |
	"rkaf:unresolvedConcept" |
	"rkaf:brokenAuthority" |
	"rkaf:unsupportedAnchor"

// A BridgeIssueAttestationContract is the consumer's published declaration
// of which issue kinds it commits to attesting. Bridge rule #8 fires when a
// BVR surfaces an issue of a contracted kind but no Attestation references
// the BVR + issue pair.
#BridgeIssueAttestationContract: {
	"@type":                    "rkaf:BridgeIssueAttestationContract"
	"rkaf:consumer":            string // IRI of the consumer
	"rkaf:attestedIssueKinds":  [...#BridgeIssueKind]
	"rkaf:contractVersion":     string // semver
}
