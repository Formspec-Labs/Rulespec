package rkaf

import "list"

// RelationChangeEvent (Analysis §2) — a source-stated ADOPTION, REMOVAL,
// SUSPENSION, or REPLACEMENT of a relation.
//
// This is the third of the four cases the analysis module keeps apart, and the
// one most often collapsed into the other three:
//
//   the source affirms the relation      -> affirmed  #RelationshipAssertion
//   the source denies the relation       -> denied    #RelationshipAssertion
//   the source CHANGES the relation      -> #RelationChangeEvent  (here)
//   the source says nothing              -> unknown; no record at all
//
// A change event is NOT a denial. "The Secretary removes the designation"
// does not assert that the designation never held; it says a designation that
// held is being taken away, at some stage of some process, with some intended
// effect time. Recording that as a denied assertion destroys the distinction
// between "this was never true" and "this stopped being true", which is the
// distinction every later comparison depends on.
//
// Polarity is therefore structurally absent here. `#RelationChangeEvent`
// composes `#AssertionEnvelope` (provenance, grounding, consumer disposition)
// and deliberately NOT `#AssertionProposition` (subject, predicate, POLARITY):
// a proposal cannot carry assertion polarity. The compiled carriers are
// open-world, so absence alone is not enforcement; the hand-authored shape
// `rkaf:RelationChangeEventNoPolarityShape` in
// `shapes/rkaf-shapes-analysis.ttl` rejects a change event that carries
// `rkaf:assertionPolarity` anyway.
//
// It is also NOT an `rkaf:LifecycleEvent`. A LifecycleEvent records what
// happened to a RESOURCE — an Artifact, a Warrant, an Assertion — and seeds
// cascade closure over that resource. A change event records what a source
// says about a RELATION between two resources, may be merely proposed, and
// seeds nothing. Publishing one as the other would let a proposed removal
// cascade as if it had already taken effect.

// What the source does to the relation. Four operations, each a different
// evidence situation; they are not degrees of one negative signal.
//
//   rkaf:relationAdoption     the relation is created / recognized
//   rkaf:relationRemoval      the relation is taken away
//   rkaf:relationSuspension   the relation is held in abeyance, not ended
//   rkaf:relationReplacement  the relation's object is exchanged for another
//
// Carrier mapping (`spicy_regs.corpora.relation_exclusion_evaluation_v2`):
// `adopt`, `remove`, `suspend`, `supersede` respectively.
#RelationChangeOperation: "rkaf:relationAdoption" | "rkaf:relationRemoval" |
	"rkaf:relationSuspension" | "rkaf:relationReplacement"

// How far the change has got in whatever process governs it. The stage says
// nothing about legal operativeness — that reading belongs to a profile, per
// the domain-interpretation rule (Analysis §7).
//
// `rkaf:changeStageUnclear` is a first-class value, not a gap: a source that
// states a change without a decidable stage must be recordable as such.
// Dropping the record or guessing a stage both convert uncertainty into a
// claim.
#RelationChangeStage: "rkaf:changeProposed" | "rkaf:changeDecided" |
	"rkaf:changeEffective" | "rkaf:changeWithdrawn" |
	"rkaf:changeStageUnclear"

#RelationChangeEvent: event={
	#AssertionEnvelope
	"@type": "rkaf:RelationChangeEvent"

	// The relation the change acts on. Same three slots a
	// `#RelationshipAssertion` proposition carries, under different names,
	// because they are NOT the same proposition: these identify the relation
	// being changed, not a relation the source affirms or denies. Reusing
	// `rkaf:assertsSubject` would make a change event indexable as an
	// assertion by every consumer that reads the assertion predicates.
	"rkaf:changeSubject":   string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:changePredicate": string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:changeObject":    string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"

	"rkaf:relationChangeOperation": #RelationChangeOperation
	"rkaf:relationChangeStage":     #RelationChangeStage

	// Two DISTINCT times, neither of which is the envelope's `rkaf:assertedAt`
	// (when the record was made):
	//   rkaf:relationChangeTime          — the time the SOURCE attaches to the
	//                                      change event itself
	//   rkaf:changeIntendedEffectiveTime — when the source says the change is
	//                                      intended to take effect
	// Both optional at the top level: a source may state a removal with no
	// date at all, and requiring a date would make producers invent one.
	"rkaf:relationChangeTime"?:          string // xsd:dateTime
	"rkaf:changeIntendedEffectiveTime"?: string // xsd:dateTime

	// The exact source regions the event was read off. Required, ≥1, and
	// class-ranged to `rkaf:SourceFragment` by
	// `constraints/analysis/semantics/l0-ranges.cue`. "Code may approve a
	// change event for a named source-extraction output with exact event
	// evidence, time, operation, and stage" — without cited regions there is
	// nothing to re-read, and a change event with no evidence is a rumour.
	"rkaf:changeEvidence": [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1)

	// The object that takes the place of `rkaf:changeObject`. Present only for
	// a replacement, and REQUIRED there (below): a replacement that does not
	// name the successor is indistinguishable from a removal, so the operation
	// would carry no information the removal value does not already carry.
	"rkaf:replacementRelationObject"?: string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"

	// Derived-shape narrowings of the envelope's reference fields, matching the
	// narrowings `#RelationshipAssertion`, `#ValueAssertion`, and
	// `#ConceptAssignment` apply. The envelope types these as plain strings;
	// every proposition- or event-bearing form requires absolute IRIs.
	"rkaf:hasApplicability"?:        string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:hasJustification"?:        string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:hasWarrant"?:              string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:hasAccessScope"?:          string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:hasSourceClaimant"?:       string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:hasExtractionProvenance"?: string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:hasConfidence"?:           [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")]
	"rkaf:supersedesAssertion"?:     [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")]

	// A change the source says is ALREADY in effect must say from when.
	// Without an effective time an `rkaf:changeEffective` record cannot be
	// ordered against a baseline, so a comparison would have to guess whether
	// the change precedes or follows the state it is comparing.
	if event["rkaf:relationChangeStage"] == "rkaf:changeEffective" {
		"rkaf:changeIntendedEffectiveTime": string
	}

	// A replacement must name what replaces the object.
	if event["rkaf:relationChangeOperation"] == "rkaf:relationReplacement" {
		"rkaf:replacementRelationObject": string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	}
}
