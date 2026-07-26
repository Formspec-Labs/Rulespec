package semantics

// Class-valued ranges owned by the document-analysis module. Every term here is
// declared by a shape in `constraints/analysis/`, never by the kernel and never
// by a profile. The L0 audit and the SHACL emitter read the union of every
// `l0-ranges.cue` under `constraints/`, so these ranges reach the compiled
// artifacts exactly as the kernel's and the profiles' do.
//
// Deliberately ABSENT: any range naming `rkaf:ClosureClaim`. Declaring one
// would give some property a class-ranged edge INTO a disabled record, which is
// the first half of consuming it as evidence. `AnalysisModuleTests` in
// `tools/test_constraints_compile.py` asserts the absence across every range
// registry in the repository, so it cannot be reintroduced silently.
//
// Also absent: `rkaf:comparisonConsumer`, `rkaf:comparisonScope`,
// `rkaf:comparisonDetector`, `rkaf:proofResolver`, `rkaf:proofPolicy`,
// `rkaf:closurePredicateFamily`, `rkaf:changeSubject`, `rkaf:changePredicate`,
// `rkaf:changeObject`, and `rkaf:replacementRelationObject`. Each of those
// names a producer- or profile-owned resource — a consumer identity, a policy,
// a detector, a predicate family, or an arbitrary semantic resource — and
// pinning a Rulespec class to it would reject every producer that composes a
// public model or its own vocabulary instead.
//
// Absent for the OTHER reason — the range is real but not expressible as one
// class — are `rkaf:proofInput`, `rkaf:proofSupportingRecord`, and
// `rkaf:comparisonExpectedAssertion`, alongside `rkaf:findingComparedAssertion`
// below:
//
//   * `rkaf:proofInput` names WHAT a resolver read, which is an assertion, an
//     artifact version, a fragment, a warrant, or an attestation depending on
//     the protocol; `rkaf:comparisonExpectedAssertion` and
//     `rkaf:findingComparedAssertion` may each be a `rkaf:RelationshipAssertion`
//     or a `rkaf:ValueAssertion`; and `rkaf:proofSupportingRecord` is the open
//     SUPPORT slot — evidence, warrant, attestation, or another proof record.
//     SHACL `sh:class` names exactly one class, so a range here would reject
//     conforming documents rather than describe them.
//
// That `rkaf:proofSupportingRecord` is unranged is LOAD-BEARING, not
// incidental: a `rkaf:ResolverProofRecord` may name another one, so a proof
// citation chain has no natural depth limit. It is why
// `rkaf:ClosureClaimNotFindingEvidenceShape` traverses these edges
// TRANSITIVELY instead of enumerating a fixed number of hops — an earlier
// one-hop form of that shape was walked around by interposing one extra proof
// record (spec/rkaf-analysis.md §6.4).
#AnalysisL0RangeRegistry: {
	// Change events resolve to exact source regions, never to a bare label.
	"rkaf:changeEvidence": "rkaf:SourceFragment"

	// A comparison names two immutable Artifact versions and the proofs it
	// rested on.
	"rkaf:comparisonBaselineArtifact": "rkaf:Artifact"
	"rkaf:comparisonObservedArtifact": "rkaf:Artifact"
	"rkaf:comparisonProofRecord":      "rkaf:ResolverProofRecord"

	// A proof names the versioned issuer that produced it and the comparison it
	// was issued for. Without both, a proof can be replayed against a different
	// comparison or attributed to a resolver version that never ran.
	"rkaf:proofIssuer":            "rkaf:ResolverProofIssuer"
	"rkaf:proofComparisonContext": "rkaf:RelationComparisonContext"

	// A finding binds its comparison and its proof records. `findingComparedAssertion`
	// is deliberately unranged: the compared records may be
	// `rkaf:RelationshipAssertion` or `rkaf:ValueAssertion`, and SHACL
	// `sh:class` names one class.
	"rkaf:findingComparisonContext": "rkaf:RelationComparisonContext"
	"rkaf:findingProofRecord":       "rkaf:ResolverProofRecord"

	// A closure claim is bounded by one Artifact version and named regions of
	// it. These are the ranges that make "closure is always local" checkable.
	"rkaf:closureArtifact": "rkaf:Artifact"
	"rkaf:closureRegion":   "rkaf:SourceFragment"
}
