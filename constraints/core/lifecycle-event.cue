package rkaf

import "list"

// Kernel lifecycle kinds. Promotion and demotion are no longer standalone
// event kinds; both are operations of rkaf:conceptLifecycle.
#LifecycleEventKind: "rkaf:revalidation" | "rkaf:revalidationClosure" |
	"rkaf:amendment" | "rkaf:supersession" | "rkaf:rescission" |
	"rkaf:materialRevision" | "rkaf:editorialRevision" |
	"rkaf:conceptLifecycle"

#ConceptLifecycleOperation: "rkaf:deprecation" | "rkaf:withdrawal" |
	"rkaf:replacement" | "rkaf:split" | "rkaf:merge" |
	"rkaf:promotion" | "rkaf:demotion"

#LifecycleEvent: event={
	"@type":                       "rkaf:LifecycleEvent"
	// Extension point. A profile assembles and closes the whole-contract set.
	"rkaf:lifecycleEventKind":     string
	"rkaf:effectiveDate":          string // xsd:dateTime
	"rkaf:emittedBy":              string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:appliesTo":              [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1)
	"rkaf:bridgeContractVersion"?: string
	"rkaf:cascadeAlgorithm"?:      string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:safeAutomaticMigration"?: string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"

	// Concept-lifecycle fields stay absent on other event kinds.
	"rkaf:conceptLifecycleOperation"?:  #ConceptLifecycleOperation
	"rkaf:predecessorConcepts"?:        [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1) @rkafStrictList()
	"rkaf:successorConcepts"?:          [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1) @rkafStrictList()
	"rkaf:predecessorConceptRelease"?:  string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:successorConceptRelease"?:    string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"

	if !list.UniqueItems(event["rkaf:appliesTo"]) { _|_ }
	if event["rkaf:predecessorConcepts"] != _|_ { if !list.UniqueItems(event["rkaf:predecessorConcepts"]) { _|_ } }
	if event["rkaf:successorConcepts"] != _|_ { if !list.UniqueItems(event["rkaf:successorConcepts"]) { _|_ } }

	// Concept participants and pins are forbidden on every other event kind.
	if event["rkaf:lifecycleEventKind"] != "rkaf:conceptLifecycle" {
		"rkaf:conceptLifecycleOperation"?: _|_
		"rkaf:predecessorConcepts"?:       _|_
		"rkaf:successorConcepts"?:         _|_
		"rkaf:predecessorConceptRelease"?: _|_
		"rkaf:successorConceptRelease"?:   _|_
	}

	if event["rkaf:lifecycleEventKind"] == "rkaf:conceptLifecycle" {
		"rkaf:conceptLifecycleOperation": #ConceptLifecycleOperation
		"rkaf:predecessorConcepts":       [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1) @rkafStrictList()
		"rkaf:predecessorConceptRelease": string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	}

	if event["rkaf:conceptLifecycleOperation"] == "rkaf:deprecation" {
		"rkaf:predecessorConcepts":       [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1) & list.MaxItems(1) @rkafStrictList()
		"rkaf:successorConcepts"?:        _|_
		"rkaf:successorConceptRelease"?:  _|_
	}
	if event["rkaf:conceptLifecycleOperation"] == "rkaf:withdrawal" {
		"rkaf:predecessorConcepts":       [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1) & list.MaxItems(1) @rkafStrictList()
		"rkaf:successorConcepts"?:        _|_
		"rkaf:successorConceptRelease"?:  _|_
	}
	if event["rkaf:conceptLifecycleOperation"] == "rkaf:replacement" {
		"rkaf:predecessorConcepts":       [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1) & list.MaxItems(1) @rkafStrictList()
		"rkaf:successorConcepts":         [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1) & list.MaxItems(1) @rkafStrictList()
		"rkaf:successorConceptRelease":   string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	}
	if event["rkaf:conceptLifecycleOperation"] == "rkaf:split" {
		"rkaf:predecessorConcepts":       [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1) & list.MaxItems(1) @rkafStrictList()
		"rkaf:successorConcepts":         [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(2) @rkafStrictList()
		"rkaf:successorConceptRelease":   string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	}
	if event["rkaf:conceptLifecycleOperation"] == "rkaf:merge" {
		"rkaf:predecessorConcepts":       [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(2) @rkafStrictList()
		"rkaf:successorConcepts":         [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1) & list.MaxItems(1) @rkafStrictList()
		"rkaf:successorConceptRelease":   string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	}
	if event["rkaf:conceptLifecycleOperation"] == "rkaf:promotion" {
		"rkaf:predecessorConcepts":       [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1) & list.MaxItems(1) @rkafStrictList()
		"rkaf:successorConcepts":         [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1) & list.MaxItems(1) @rkafStrictList()
		"rkaf:successorConceptRelease":   string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	}
	if event["rkaf:conceptLifecycleOperation"] == "rkaf:demotion" {
		"rkaf:predecessorConcepts":       [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1) & list.MaxItems(1) @rkafStrictList()
		"rkaf:successorConcepts":         [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1) & list.MaxItems(1) @rkafStrictList()
		"rkaf:successorConceptRelease":   string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	}

	// One lifecycle transition must cross release states. A successor-less
	// operation has no right-hand pin; otherwise one release IRI cannot serve
	// as both the before and after state.
	if event["rkaf:successorConceptRelease"] != _|_ && event["rkaf:predecessorConceptRelease"] == event["rkaf:successorConceptRelease"] { _|_ }

	// Keep this graph-wide set check after every portable scalar/list
	// constraint. Its nested loop is deliberately last because the compiler
	// delegates the expanded-graph equivalent to SHACL.
	if event["rkaf:predecessorConcepts"] != _|_ && event["rkaf:successorConcepts"] != _|_ {
		for predecessor in event["rkaf:predecessorConcepts"] {
			if list.Contains(event["rkaf:successorConcepts"], predecessor) { _|_ }
		}
	}
}
