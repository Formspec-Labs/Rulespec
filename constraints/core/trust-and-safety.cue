package rkaf

// Safety labels (§1.3): D0 (display-only) through P4 (production-permitted),
// plus the "permits-*" family that authorizes a specific evidence gap on the
// EvidenceBinding a labeled Assertion carries (see
// constraints/adversarial/conditional-silent-pass.cue and
// nested-noevidencereason.cue, and `rkaf:NoEvidenceReason` in
// spec/rkaf-core.md §2.4). Operational property of an artifact — what the
// consumer may do with it. The published lettered scheme is D0 / S1 / R2 /
// A3 / P4 plus advisory and authority-critical refinements. Bound below via
// `#SafetyLabelCarrier`; the two adversarial modules above use literal
// subsets of this same set, never their own vocabulary.
#SafetyLabel: "rkaf:D0DisplayOnly" | "rkaf:S1Suggestion" | "rkaf:R2Review" |
	"rkaf:A3Advisory" | "rkaf:A3AdvisoryAggregated" |
	"rkaf:A3AuthorityCritical" | "rkaf:P4Production" |
	"rkaf:permits-axiomatic" | "rkaf:permits-consensus-without-citation" |
	"rkaf:permits-all"

// Composed into the concrete assertion forms observed to carry
// `hasSafetyLabel` in live fixtures (the generic `#Assertion` and
// `#RelationshipAssertion`; see constraints/core/assertion.cue and
// relationship-assertion.cue) rather than into the shared
// `#ConsumerDisposition`/`#AssertionEnvelope` every durable assertion form
// composes. `#ConceptAssignment` and `#ConceptMapping` also compose that
// shared envelope, and one of their compiled schemas is byte-pinned in a
// release-record fixture (release-records/fixtures/rulespec-core-release-m2.json)
// that is itself pinned by digest from a vendored, external upstream
// document (release-records/fixtures/upstream/spicyregs-document-release-v1.json)
// through the whole self-certification chain. Adding this field there would
// change that pinned digest and cascade into re-stamping vendored content
// this repo does not own — out of scope here. If a future producer needs
// `hasSafetyLabel` on those forms too, promote this into the shared envelope
// AND re-stamp the release-record chain deliberately, as one decision.
#SafetyLabelCarrier: {
	"rkaf:hasSafetyLabel"?: #SafetyLabel
}
