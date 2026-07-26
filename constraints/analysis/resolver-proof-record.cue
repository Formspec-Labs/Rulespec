package rkaf

import "list"

// ResolverProofRecord and ResolverProofIssuer (Analysis §4).
//
// The comparison kernel owns deterministic orchestration and nothing else. It
// does not know how a predicate registry, a database, a document parser, a
// model provider, or a legal profile works. Each of those implements a narrow
// resolver protocol and answers ONE question with `pass`, `fail`, or
// `unknown`, a rationale, and a resolvable proof record.
//
// Three rules govern the vocabulary below, and each of them is the reason a
// field exists:
//
//   1. `fail` is a GATE RESULT, never a negative fact about a source. A failed
//      eligibility gate makes a comparison `rkaf:comparisonNotComparable`; it
//      never becomes a denied assertion.
//   2. `unknown` never becomes `fail`. Absence of a decision is its own value.
//   3. An opaque string is not proof. A proof identifier used in a published
//      result must resolve inside the same immutable generation or through a
//      pinned, reachable external record — which is what
//      `rkaf:proofRecordDigest` and `rkaf:proofInputDigest` make checkable.

// WHICH question a proof answers, one value per active resolver protocol.
//
//   rkaf:predicateCatalogProof  is this canonical relation valid, and do two
//                               assertions describe the same relation?
//   rkaf:assertionStateProof    is this assertion accepted for this consumer,
//                               scope, and evaluation time?
//   rkaf:evidenceBindingProof   does exact evidence in this artifact version
//                               support this assertion occurrence?
//   rkaf:baselineWarrantProof   may this assertion serve as the expected
//                               baseline under an active warrant?
//   rkaf:artifactPairingProof   may these artifact versions be compared for
//                               this purpose?
//   rkaf:scopeComparisonProof   are the temporal, jurisdictional, conditional,
//                               and applicability scopes comparable?
//
// The three LONGITUDINAL protocols — version lineage, expected coverage, and
// closure — are deliberately ABSENT. They exist only to support omission
// findings, omission is disabled (see closure-claim.cue), and a contract that
// can mint a closure proof is a contract in which closure is half-enabled.
// They enter this enum by the same deliberate contract change that enables
// `#ClosureClaim`, not before.
#ResolverProofType: "rkaf:predicateCatalogProof" |
	"rkaf:assertionStateProof" | "rkaf:evidenceBindingProof" |
	"rkaf:baselineWarrantProof" | "rkaf:artifactPairingProof" |
	"rkaf:scopeComparisonProof"

// The common decision envelope every gate resolver returns.
#GateStatus: "rkaf:gatePass" | "rkaf:gateFail" | "rkaf:gateUnknown"

// What a scope comparator returns instead. A scope relation is not a gate
// result: `overlaps` is neither a pass nor a failure, and collapsing the six
// relations onto pass/fail would throw away the direction of containment that
// decides whether an expectation applies to the observed version at all.
#ScopeRelation: "rkaf:scopeEquivalent" |
	"rkaf:scopeObservedSubsumesExpected" |
	"rkaf:scopeObservedNarrowsExpected" | "rkaf:scopeOverlaps" |
	"rkaf:scopeDisjoint" | "rkaf:scopeUnknown"

// The union both kinds of resolver write into one slot. Assembled from the two
// parts above rather than restated, so neither half can drift.
#ResolverProofOutcome: #GateStatus | #ScopeRelation

// ResolverProofIssuer — the versioned resolver and policy a proof was issued
// under.
//
// The carrier implementation denormalizes these four fields onto every proof
// record because its identity is a content digest over them. The contract
// keeps ONE issuer record and references it, for the same reason Rulespec keeps
// one `rkaf:ConfidenceRecord` rather than a score on every assertion: a
// resolver version that changes must change in one place, and two proofs that
// claim the same issuer must be comparable by IRI rather than by hoping four
// strings were copied identically.
#ResolverProofIssuer: {
	"@type": "rkaf:ResolverProofIssuer"
	// The resolver implementation and the policy it applies. Both are
	// producer-scoped IRIs; Rulespec neither mints nor parses them.
	"rkaf:proofResolver":        string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:proofResolverVersion": string
	"rkaf:proofPolicy":          string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:proofPolicyVersion":   string
}

#ResolverProofRecord: {
	"@type":           "rkaf:ResolverProofRecord"
	"rkaf:proofType":  #ResolverProofType
	// Class-ranged to `rkaf:ResolverProofIssuer`: "issued by version 3" has to
	// resolve to a record, not to a version string a reader must trust.
	"rkaf:proofIssuer": string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"

	// The comparison this proof was issued for, class-ranged to
	// `rkaf:RelationComparisonContext`. A proof that does not name its
	// comparison can be replayed against a different one, which is how a stale
	// pass gets reused.
	//
	// Requiring the property only makes the binding DECLARED. That the named
	// comparison is the one actually CITING the proof is a statement relating
	// two nodes, which per-property SHACL cannot reach, so it is enforced by
	// `rkaf:ResolverProofComparisonBindingShape` in
	// `shapes/rkaf-shapes-analysis.ttl`: a comparison whose
	// `rkaf:comparisonProofRecord` names a proof issued for some other
	// comparison fails validation. `rkaf:proofRecordDigest` does not catch that
	// case — the proof record is unedited; it is the citation that is false.
	"rkaf:proofComparisonContext": string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"

	"rkaf:proofOutcome": #ResolverProofOutcome

	// The explanation. Required and non-empty: a decision with no stated reason
	// is not reviewable, and every resolver protocol returns a rationale.
	"rkaf:proofRationale": string

	// WHAT the resolver read. At least one input identifier, plus optional
	// content digests binding those inputs to exact bytes. Identifiers alone
	// prove which records were named; digests prove which VERSION of them was
	// read.
	"rkaf:proofInput":       [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1)
	"rkaf:proofInputDigest"?: [...(string & =~"^sha256:[0-9a-f]{64}$")]

	// Evidence, warrant, attestation, or other records the decision leaned on.
	// Separate from `rkaf:proofInput` because these are the SUPPORT, not the
	// subject: an attestation that made an assertion accepted is not one of the
	// assertions being compared.
	"rkaf:proofSupportingRecord"?: [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")]

	// When it was evaluated and against which immutable snapshot. Both are
	// part of the answer: the same resolver over the same inputs at another
	// time or against another snapshot may decide differently, and a proof that
	// hides that is not replayable.
	"rkaf:proofEvaluatedAt": string // xsd:dateTime
	"rkaf:proofSnapshot":    string

	// The record's own content digest — what makes the proof CONTENT-BOUND
	// rather than merely named. A consumer that dereferences the proof
	// recomputes this over the record and rejects it when the value differs,
	// so a proof cannot be edited after the result that cites it was published.
	"rkaf:proofRecordDigest": string & =~"^sha256:[0-9a-f]{64}$"
}
