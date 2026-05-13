package rkaf

// RevalidationEvent + RevalidationClosureEvent (v0.1 §4.8).
//
// RevalidationEvent is emitted on cascade ingest and remains open until a
// RevalidationClosureEvent references it with a closureDecision and successor
// assertion / work product. Closure events are explicit; prose
// `closesWhen` rules are NOT permitted.
#RevalidationEvent: {
	"@type":                   "rkaf:RevalidationEvent"
	"rkaf:revalidationFor":    string // IRI of the affected Assertion or WorkProduct
	"rkaf:triggeredBy":        string // IRI of the LifecycleEvent that triggered this
	"rkaf:openedAt":            string // xsd:dateTime
	"rkaf:bridgeContractVersion": string
}

#RevalidationClosureDecision: "rkaf:revalidated" |
	"rkaf:supersededBySuccessor" |
	"rkaf:retainedForPointInTime" |
	"rkaf:retired"

#RevalidationClosureEvent: {
	"@type":                       "rkaf:RevalidationClosureEvent"
	"rkaf:closesRevalidation":     string // IRI of the open RevalidationEvent
	"rkaf:closureDecision":        #RevalidationClosureDecision
	"rkaf:successorAssertion"?:    string // IRI of the successor Assertion when applicable
	"rkaf:successorWorkProduct"?:  string // IRI of the successor WorkProduct when applicable
	"rkaf:closedAt":               string // xsd:dateTime
	"rkaf:bridgeContractVersion":  string
}
