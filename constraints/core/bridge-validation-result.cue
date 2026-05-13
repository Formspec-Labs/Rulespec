package rkaf

// BridgeValidationResult (§5.2): the control-plane record emitted by every
// bridge consumer for every packet ingestion. Records the verdict, effective
// usage eligibility, concept resolution results, warnings, errors, stale
// dependencies, registry availability, and (when applicable) authority chain
// status.
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
	"rkaf:warnings"?:                        [...string]
	"rkaf:errors"?:                          [...string]
	"rkaf:staleDependencies"?:               [...string]
	"rkaf:registryUnavailable"?:             [...string]
	"rkaf:registryVersionOutOfRange"?:       [...string]
	"rkaf:authorityChainTraversal"?:         [...string] // IRIs of rkaf:AuthorityChainHop
	"rkaf:chainTerminus"?:                   string
	"rkaf:chainTerminusKind"?:               #AuthorityKind
	"rkaf:authorityChainStatus"?:            #AuthorityChainStatus
	"rkaf:suggestedRemediation"?:            string
	"rkaf:noRemediationReason"?:             string
}
