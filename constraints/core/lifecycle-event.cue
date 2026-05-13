package rkaf

// LifecycleEvent (§4): a typed audit-trail entry recording transitions across
// an Artifact's, Warrant's, or Assertion's lifecycle. Concrete kinds include
// revalidation, amendment, supersession, rescission, material revision, and
// concept lifecycle. The event itself is a portable substrate concern; the
// workflow-state machine consuming events is the consumer's responsibility.
#LifecycleEventKind: "rkaf:revalidation" | "rkaf:revalidationClosure" |
	"rkaf:amendment" | "rkaf:supersession" | "rkaf:rescission" |
	"rkaf:materialRevision" | "rkaf:editorialRevision" |
	"rkaf:conceptLifecycle" | "rkaf:promotion" | "rkaf:demotion"

#LifecycleEvent: {
	"@type":                       "rkaf:LifecycleEvent"
	"rkaf:lifecycleEventKind":     #LifecycleEventKind
	"rkaf:effectiveDate":          string // xsd:dateTime
	"rkaf:emittedBy":              string // IRI of the actor / system
	"rkaf:appliesTo":              [...string] // IRIs of affected resources
	"rkaf:bridgeContractVersion"?: string
	"rkaf:cascadeAlgorithm"?:      string // e.g. "rkaf:CascadeClosureV1"
}
