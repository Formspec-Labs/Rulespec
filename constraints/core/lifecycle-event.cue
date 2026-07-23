package rkaf

// LifecycleEvent (§4): a typed audit-trail entry recording transitions across
// an Artifact's, Warrant's, or Assertion's lifecycle. Concrete kinds include
// revalidation, amendment, supersession, rescission, material revision, and
// concept lifecycle. The event itself is a portable substrate concern; the
// workflow-state machine consuming events is the consumer's responsibility.
#LifecycleEventKind: "rkaf:revalidation" | "rkaf:revalidationClosure" |
	"rkaf:amendment" | "rkaf:supersession" | "rkaf:rescission" |
	"rkaf:materialRevision" | "rkaf:editorialRevision" |
	"rkaf:conceptLifecycle" | "rkaf:promotion" | "rkaf:demotion" |
	"rkaf:proceedingPrerule" | "rkaf:proceedingProposed" |
	"rkaf:proceedingSupplemental" | "rkaf:proceedingFinal" |
	"rkaf:proceedingWithdrawn" | "rkaf:proceedingLongterm"

#LifecycleEvent: {
	"@type":                          "rkaf:LifecycleEvent"
	"rkaf:lifecycleEventKind":        #LifecycleEventKind
	"rkaf:effectiveDate":             string // xsd:dateTime
	"rkaf:emittedBy":                 string // IRI of the actor / system
	"rkaf:appliesTo":                 [...string] // IRIs of affected resources (cascade-closure seed set)
	"rkaf:bridgeContractVersion"?:    string
	"rkaf:cascadeAlgorithm"?:         string // e.g. "rkaf:CascadeClosureV1"
	// L4 stale-transition input (rkaf-behavior.md §3.5 / §5). When the event
	// declares a safeAutomaticMigration kind that the consumer supports
	// (BridgeConsumerRegistration.supportedAutomaticMigrations), the affected
	// assertions skip the staleForCurrentUse transition.
	"rkaf:safeAutomaticMigration"?:   string // migration kind IRI
}
