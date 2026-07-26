package rkaf

// LifecycleEvent (§4): a typed audit-trail entry recording transitions across
// an Artifact's, Warrant's, or Assertion's lifecycle. Concrete kinds include
// revalidation, amendment, supersession, rescission, material revision, and
// concept lifecycle. The event itself is a portable substrate concern; the
// workflow-state machine consuming events is the consumer's responsibility.
//
// `#LifecycleEventKind` is the kernel's CONTRIBUTION to the event-kind value
// set, not the whole of it: these ten kinds are the ones that happen to a
// governed assertion in ANY jurisdiction. A domain profile contributes its own
// kinds and declares the assembled closed union — see
// `constraints/profiles/us-rulemaking/us-lifecycle-event.cue`, which unions
// this definition with the twelve US proceeding kinds and binds the
// result to `rkaf:LifecycleEvent`. One class, one property, values owned by
// exactly one module each (audited by `LifecycleKindOwnershipTests` in
// tools/test_constraints_compile.py).
#LifecycleEventKind: "rkaf:revalidation" | "rkaf:revalidationClosure" |
	"rkaf:amendment" | "rkaf:supersession" | "rkaf:rescission" |
	"rkaf:materialRevision" | "rkaf:editorialRevision" |
	"rkaf:conceptLifecycle" | "rkaf:promotion" | "rkaf:demotion"

#LifecycleEvent: {
	"@type":                          "rkaf:LifecycleEvent"
	// Extension point. The kernel deliberately leaves this property OPEN at
	// the carrier level, exactly as the kernel #Artifact treats US identifier
	// terms: a profile-contributed kind is UNCONSTRAINED by the kernel
	// carriers rather than rejected by them, and the composed profile shape
	// carries the closed union of every declared kind.
	// Closing it here at the kernel's ten would make the kernel reject events
	// whose kinds a profile in this same contract declares.
	"rkaf:lifecycleEventKind":        string
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
