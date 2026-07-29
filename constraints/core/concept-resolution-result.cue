package rkaf

#ConceptResolutionStatus: "rkaf:resolved" | "rkaf:unresolved" |
	"rkaf:ambiguous" | "rkaf:conflicting" | "rkaf:registryUnavailable" |
	"rkaf:staleCacheFallback"

#ConceptResolutionMethod: "rkaf:directRegistry" |
	"rkaf:exactMatchTrusted" | "rkaf:closeMatchLocallyAdopted" |
	"rkaf:closeMatchAwaitingAdoption" |
	"rkaf:broadOrNarrowMatchDiscoveryOnly" | "rkaf:cacheServed" |
	"rkaf:staleCacheServed"

#ConceptResolutionCacheStatus: "rkaf:fresh" | "rkaf:stale" |
	"rkaf:notCached"

#ConceptResolutionResult: result={
	"@type":                 "rkaf:ConceptResolutionResult"
	"rkaf:inputConcept":     string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:resolutionStatus": #ConceptResolutionStatus
	"rkaf:resolutionMethod": #ConceptResolutionMethod
	"rkaf:resolvedConcept"?: string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:mappingAssertion"?: string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:cacheStatus":      #ConceptResolutionCacheStatus
	"rkaf:usageCeiling":     #UsageEligibility
	"rkaf:resolvedAt":       string // xsd:dateTime
	"rkaf:resolverId"?:      string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"

	if result["rkaf:resolutionStatus"] == "rkaf:resolved" {
		"rkaf:resolvedConcept": string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	}
	if result["rkaf:resolutionStatus"] == "rkaf:staleCacheFallback" {
		"rkaf:resolvedConcept": string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	}
	if result["rkaf:resolutionStatus"] == "rkaf:unresolved" {
		"rkaf:resolvedConcept"?: _|_
	}
	if result["rkaf:resolutionStatus"] == "rkaf:ambiguous" {
		"rkaf:resolvedConcept"?: _|_
	}
	if result["rkaf:resolutionStatus"] == "rkaf:conflicting" {
		"rkaf:resolvedConcept"?: _|_
	}
	if result["rkaf:resolutionStatus"] == "rkaf:registryUnavailable" {
		"rkaf:resolvedConcept"?: _|_
		"rkaf:usageCeiling": "rkaf:notEligible"
	}
	if result["rkaf:resolutionStatus"] == "rkaf:conflicting" {
		"rkaf:usageCeiling": "rkaf:notEligible"
	}
	if result["rkaf:resolutionStatus"] == "rkaf:unresolved" {
		"rkaf:usageCeiling": "rkaf:notEligible" | "rkaf:searchOnly"
	}
	if result["rkaf:resolutionStatus"] == "rkaf:staleCacheFallback" {
		"rkaf:cacheStatus": "rkaf:stale"
	}

	if result["rkaf:resolutionMethod"] == "rkaf:exactMatchTrusted" {
		"rkaf:mappingAssertion": string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	}
	if result["rkaf:resolutionMethod"] == "rkaf:closeMatchLocallyAdopted" {
		"rkaf:mappingAssertion": string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
		"rkaf:usageCeiling": "rkaf:notEligible" | "rkaf:searchOnly" |
			"rkaf:reviewQueueOnly" | "rkaf:draftGenerationAllowed" |
			"rkaf:localOperationalUse"
	}
	if result["rkaf:resolutionMethod"] == "rkaf:closeMatchAwaitingAdoption" {
		"rkaf:mappingAssertion": string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
		"rkaf:usageCeiling": "rkaf:notEligible" | "rkaf:searchOnly" |
			"rkaf:reviewQueueOnly" | "rkaf:draftGenerationAllowed"
	}
	if result["rkaf:resolutionMethod"] == "rkaf:broadOrNarrowMatchDiscoveryOnly" {
		"rkaf:mappingAssertion": string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
		"rkaf:resolutionStatus": "rkaf:unresolved"
		"rkaf:usageCeiling": "rkaf:notEligible" | "rkaf:searchOnly"
	}
	if result["rkaf:resolutionMethod"] == "rkaf:directRegistry" {
		"rkaf:mappingAssertion"?: _|_
		"rkaf:cacheStatus": "rkaf:notCached"
	}
	if result["rkaf:resolutionMethod"] == "rkaf:cacheServed" {
		"rkaf:mappingAssertion"?: _|_
		"rkaf:resolutionStatus": "rkaf:resolved"
		"rkaf:cacheStatus": "rkaf:fresh"
	}
	if result["rkaf:resolutionMethod"] == "rkaf:staleCacheServed" {
		"rkaf:mappingAssertion"?: _|_
		"rkaf:resolutionStatus": "rkaf:staleCacheFallback"
		"rkaf:cacheStatus": "rkaf:stale"
		"rkaf:usageCeiling": "rkaf:notEligible" | "rkaf:searchOnly"
	}
}
