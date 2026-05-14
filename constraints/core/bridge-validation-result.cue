package rkaf

// BridgeValidationResult (§5.2): the control-plane record emitted by every
// bridge consumer for every packet ingestion. Records the verdict, effective
// usage eligibility, concept resolution results, findings (per ADR-0093),
// and (when applicable) authority chain status.
#BridgeResult: "rkaf:accepted" | "rkaf:acceptedWithWarnings" | "rkaf:rejected"

#AuthorityChainStatus: "rkaf:valid" | "rkaf:broken" |
	"rkaf:staleForCurrentUse" | "rkaf:validForPointInTimeOnly" |
	"rkaf:brokenForNewCases" | "rkaf:missingAuthority" |
	"rkaf:unsupportedAuthorityKind"

#BridgeValidationResult: {
	"@type":                                 "rkaf:BridgeValidationResult"
	"rkaf:packetId":                         string
	"rkaf:consumer":                         string // IRI of the bridge consumer
	"rkaf:bridgeContractVersion":            string
	"rkaf:result":                           #BridgeResult
	"rkaf:effectiveUsageEligibility":        #UsageEligibility
	"rkaf:effectiveUsageEligibilityRationale": string
	"rkaf:validatedAt":                      string // xsd:dateTime
	"rkaf:conceptResolutionResults"?:        [...string] // IRIs of ConceptResolutionResult
	// ADR-0093 Phase C: a single typed, IRI-addressable list of findings
	// REPLACES the prior flat string arrays (warnings, errors,
	// staleDependencies, registryUnavailable, registryVersionOutOfRange).
	// Each entry is the @id of an rkaf:Finding node. Greenfield: no
	// installed base; the legacy fields are removed outright.
	//
	// Why typed: findings need to be addressable from Attestations
	// (waivers via rkaf:targetFinding), anchorable in Trellis ledgers,
	// and projectable into Studio's ValidationFinding shape — all
	// impossible against opaque string-list entries.
	//
	// The closed #FindingKind enum on rkaf:Finding subsumes the
	// previous flat-array semantic distinctions (warning vs error vs
	// staleDependency vs registryUnavailable vs registryVersionOutOfRange).
	"rkaf:findings"?:                        [...string] // IRIs of rkaf:Finding nodes
	"rkaf:authorityChainTraversal"?:         [...string] // IRIs of rkaf:AuthorityChainHop
	"rkaf:chainTerminus"?:                   string
	"rkaf:chainTerminusKind"?:               #AuthorityKind
	"rkaf:authorityChainStatus"?:            #AuthorityChainStatus
	"rkaf:suggestedRemediation"?:            string
	"rkaf:noRemediationReason"?:             string
	// IRIs that the BVR cites AS AUTHORITY for the validated artifact's
	// usage. Bridge rule #6 fires if any of these IRIs is a Concept /
	// ConceptResolutionResult (resolution is NOT authority per spec §7).
	"rkaf:usedAsAuthority"?:                 [...string]
	// Issue kinds the bridge has detected for the validated packet. Each
	// entry is one of #BridgeIssueKind (closed enum codified in
	// constraints/core/bridge-issue-attestation-contract.cue). Bridge rule #8
	// fires when an issue kind in a consumer's BridgeIssueAttestationContract
	// appears here without a matching rkaf:Attestation referencing this BVR.
	"rkaf:detectedIssues"?:                  [...#BridgeIssueKind]
	// Plan 7d — freshness. When was this validation last reconfirmed?
	// Distinct from `validatedAt` (the original event) — supports the
	// "is this BVR still trustworthy at evaluation time?" question.
	"rkaf:lastVerifiedAt"?:                  string // xsd:dateTime
	"rkaf:verifiedBy"?:                      string // IRI of verifier
}
