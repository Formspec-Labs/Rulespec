package rkaf

import "list"

// Which KIND of thing a concept was assigned to (§4.7). Exactly two subject
// kinds are taggable, and they are not interchangeable: an Artifact assignment
// says the document as a whole is materially associated with the concept, a
// SourceFragment assignment says THIS clause, paragraph, table row, or list
// item supports it. Recording the subject KIND alongside the subject IRI is
// what lets a consumer tell the two apart without dereferencing, and it is what
// the fragment-evidence conditional below keys on.
#AssignmentSubjectType: "rkaf:Artifact" | "rkaf:SourceFragment"

// How strongly the subject is associated with the concept (§4.7). Ordering is
// editorial, not computable: nothing in Rulespec compares two roles.
#ConceptAssignmentRole: "rkaf:assignmentPrimary" | "rkaf:assignmentSubstantive" |
	"rkaf:assignmentMention" | "rkaf:assignmentContextual"

// Where the assignment came from, as a matter of RECORD STRUCTURE (§4.7).
// Deliberately distinct from `rkaf:assertionOrigin`, which says whether a
// human, a model, a deterministic parser, or an import CONSTRUCTED the record.
// The two are orthogonal: a model may propose a direct assignment, and a
// deterministic rule may compute a derived one.
//
//   rkaf:directAssignment   read off the subject's own text — MUST cite the
//                           exact regions that support it
//   rkaf:derivedAssignment  computed from other, already-accepted assignments
//                           — MUST name them and the policy that combined them
#AssignmentDerivation: "rkaf:directAssignment" | "rkaf:derivedAssignment"

// ConceptAssignment — an evidence-bearing, versioned record that one Artifact
// or one SourceFragment is associated with one concept (§4.7).
//
// It composes `#AssertionEnvelope` rather than restating it. Everything the
// vision asks an assignment to record about its own trustworthiness already has
// exactly one home there, and duplicating any of it would create a second place
// to look for the same fact:
//
//   construction origin   rkaf:assertionOrigin        (envelope)
//   model derivation      rkaf:hasAILineage           (envelope, AI-touched)
//   extraction run        rkaf:hasExtractionProvenance (envelope)
//   source claimant       rkaf:hasSourceClaimant      (envelope)
//   confidence            rkaf:hasConfidence          (envelope, 0..*)
//   approval / rejection  rkaf:Attestation targeting this record — NOT a field
//   consumer state        #ConsumerDisposition        (envelope)
//   supersession          rkaf:supersedesAssertion    (envelope)
//   time of assertion     rkaf:assertedAt             (envelope)
//
// What is NOT inherited is the proposition core. An assignment's proposition is
// the subject-concept pair below, not a subject/predicate/object triple, so
// `#AssertionProposition` is deliberately absent: composing it would demand an
// `rkaf:assertsPredicate` that every assignment would have to fill with the
// same placeholder.
//
// The two conditionals that carry the directional rule from the carrier
// evidence are `rkaf:assignmentSubjectType` and `rkaf:assignmentDerivation`.
// Together they say: a segment tag needs its own cited evidence, and a document
// tag aggregated from segment tags must name the segment tags and the
// documented rule that combined them. A document tag may shortlist candidate
// concepts for a segment; it can never prove one, because the segment
// assignment cannot be recorded without its own local evidence.
#ConceptAssignment: assignment={
	#AssertionEnvelope
	"@type": "rkaf:ConceptAssignment"

	// The tagged thing, and what kind of thing it is.
	"rkaf:assignmentSubject":     string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:assignmentSubjectType": #AssignmentSubjectType

	// The concept, and the facet it belongs to. Both are IRIs with no class
	// range: the concept may be an rkaf:RegisteredConcept, an rkaf:LocalConcept,
	// or an external skos:Concept, and SKOS owns `skos:inScheme`. Naming the
	// scheme ON THE ASSIGNMENT is what keeps facets legible at the point of use
	// — a consumer reading assignments alone can still tell an industry tag from
	// a topic tag without resolving the concept.
	"rkaf:assignedConcept": string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"skos:inScheme":        string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"

	"rkaf:assignmentRole":       #ConceptAssignmentRole
	"rkaf:assignmentDerivation": #AssignmentDerivation

	// The exact source regions supporting this assignment. Class-ranged to
	// rkaf:SourceFragment by the range registry, so "evidence" resolves to real
	// coordinates in a real Artifact rather than to any IRI at all.
	"rkaf:assignmentEvidence"?: [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1)

	// WHICH identity form those cited regions use — `#FragmentIdentityScheme`
	// in constraints/core/source-fragment.cue. Required whenever evidence is
	// present, exactly as `rkaf:regulatoryIdentifierScheme` is required
	// whenever `rkaf:hasRegulatoryIdentifier` is present: the grammar a value
	// must satisfy is not recoverable from the value, so the record declares
	// which one applies and the declaration is what turns a minted identifier
	// into a CHECKED claim instead of an assumed one.
	//
	// The class range stays `rkaf:SourceFragment`. A carrier-local URN does not
	// escape it — it SATISFIES it by construction, because the artifact,
	// the offsets, the coordinate system, the selector kind, and the region
	// digest are all recoverable by parsing. What changes is where the bindings
	// live, not whether they exist.
	"rkaf:assignmentEvidenceScheme"?: #FragmentIdentityScheme

	if assignment["rkaf:assignmentEvidence"] != _|_ {
		"rkaf:assignmentEvidenceScheme": #FragmentIdentityScheme
	}

	// A declared carrier-local scheme binds every cited value to the derived
	// grammar. Without this narrowing the declaration would be a label rather
	// than a constraint, which is the unchecked semantic claim the scheme
	// exists to prevent.
	if assignment["rkaf:assignmentEvidenceScheme"] == "rkaf:carrier-local-fragment" {
		"rkaf:assignmentEvidence": [...(string & =~"^urn:rkaf:fragment:([A-Za-z0-9._~-]|%[0-9A-F]{2})+:(0|[1-9][0-9]*):(0|[1-9][0-9]*):sha256-[0-9a-f]{64}$")] & list.MinItems(1)
	}

	// The already-accepted assignments a derived assignment was computed from,
	// and the version of the documented rule that combined them. Aggregation
	// without both is an unexplainable tag.
	"rkaf:supportingAssignment"?:   [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1)
	"rkaf:assignmentPolicyVersion"?: string

	// Derived-shape narrowings of the envelope's reference fields, matching the
	// narrowings `#RelationshipAssertion` and `#ValueAssertion` apply.
	"rkaf:hasApplicability"?:        string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:hasJustification"?:        string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:hasWarrant"?:              string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:hasAccessScope"?:          string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:hasSourceClaimant"?:       string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:hasExtractionProvenance"?: string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:hasConfidence"?:           [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")]
	"rkaf:supersedesAssertion"?:     [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")]

	// A segment tag needs local evidence. Inherited document context stays
	// non-evidentiary: it may suggest which concepts to look for, and it never
	// stands in for local support. Without this rule one mistaken document tag
	// propagates to every segment and then confirms itself.
	//
	// This branch keys on the self-declared `rkaf:assignmentSubjectType`
	// literal, so it catches an HONEST record and nothing else. Two
	// hand-authored shapes in `shapes/rkaf-shapes-core.ttl` close what a
	// per-property target cannot reach:
	// `rkaf:ConceptAssignmentFragmentSubjectEvidenceShape` re-keys the same
	// obligation on the subject node's own `rdf:type`, so relabelling a segment
	// assignment `rkaf:Artifact` buys nothing; and
	// `rkaf:ConceptAssignmentEvidenceSameArtifactShape` requires the cited
	// fragment to name the same `oa:hasSource` Artifact as the subject
	// fragment. That the cited region is the subject's OWN region stays a
	// producer obligation — Core §4.7.3 states it as one rather than claiming
	// it is checked.
	if assignment["rkaf:assignmentSubjectType"] == "rkaf:SourceFragment" {
		"rkaf:assignmentEvidence": [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1)
	}

	// A direct assignment is by definition read off the subject's own text.
	if assignment["rkaf:assignmentDerivation"] == "rkaf:directAssignment" {
		"rkaf:assignmentEvidence": [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1)
	}

	// A derived assignment must name what it was derived FROM.
	if assignment["rkaf:assignmentDerivation"] == "rkaf:derivedAssignment" {
		"rkaf:supportingAssignment": [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1)
	}

	// …and the version of the documented rule that combined them, so the same
	// inputs can be replayed against the same policy. "A documented rule may
	// combine approved section tags into a document tag" is only checkable if
	// the record says WHICH documented rule.
	if assignment["rkaf:supportingAssignment"] != _|_ {
		"rkaf:assignmentPolicyVersion": string
	}
}
