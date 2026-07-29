package rkaf

// US rulemaking profile — proceeding lifecycle kinds, contributed to the
// SHARED `rkaf:LifecycleEvent` class.
//
// These twelve kinds are NOT universal: a prerule stage, a supplemental
// proposal, a judicial vacatur, a congressional disapproval are US rulemaking
// events. The kernel `#LifecycleEventKind`
// (constraints/core/lifecycle-event.cue) therefore no longer declares them;
// this profile does, and the dependency runs profile -> kernel, never the
// other way.
//
// Class binding: the overlay keeps `@type: "rkaf:LifecycleEvent"`. A
// proceeding stage transition IS a LifecycleEvent — the profile contributes
// values to the universal class rather than minting a parallel event class
// (spec/rkaf-rulemaking.md §6, "this module defines no parallel event class").
//
// Value-set assembly: `#ComposedLifecycleEventKind` is the closed
// whole-contract kind set — the kernel's eight universal kinds unioned with this
// profile's twelve. The compiler resolves the union across files at build time
// (tools/constraints_compile.py `_resolve_enum_values`), so every compiled
// target of THIS file carries all 20 values while every compiled kernel target
// carries only the eight the kernel owns.
#USProceedingLifecycleEventKind: "rkaf:proceedingPrerule" |
	"rkaf:proceedingProposed" | "rkaf:proceedingSupplemental" |
	"rkaf:proceedingFinal" | "rkaf:proceedingWithdrawn" |
	"rkaf:proceedingLongterm" | "rkaf:proceedingConcluded" |
	"rkaf:proceedingVacated" | "rkaf:proceedingStayed" |
	"rkaf:proceedingRemanded" | "rkaf:proceedingReinstated" |
	"rkaf:proceedingDisapproved"

#ComposedLifecycleEventKind: #LifecycleEventKind | #USProceedingLifecycleEventKind

#USLifecycleEvent: {
	#LifecycleEvent
	"@type":                   "rkaf:LifecycleEvent"
	"rkaf:lifecycleEventKind": #ComposedLifecycleEventKind
}
