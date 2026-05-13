package rkaf

// ConceptResolutionResult (ConceptRegistry v0.1.2 §5.4): emitted by the
// resolver when matching a local concept reference against the federation
// registry. Records the input, the matched concept (or its absence), the
// status, and a usage ceiling derived from the resolution.
#ConceptResolutionStatus: "rkaf:resolved" | "rkaf:unresolved" |
	"rkaf:ambiguous" | "rkaf:conflicting" | "rkaf:registryUnavailable" |
	"rkaf:staleCacheFallback"

#ConceptResolutionResult: {
	"@type":                  "rkaf:ConceptResolutionResult"
	"rkaf:inputConcept":      string // IRI of the input concept reference
	"rkaf:resolutionStatus":  #ConceptResolutionStatus
	"rkaf:resolvedConcept"?:  string // IRI of matched RegisteredConcept (if resolved)
	"rkaf:usageCeiling"?:     #UsageEligibility
	"rkaf:resolvedAt":        string // xsd:dateTime
	"rkaf:resolverId"?:       string // IRI of the resolver
}
