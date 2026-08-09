package rkaf

// MachineAdjudicationProof (Analysis §4 extension) — a machine-produced
// verdict over a sealed comparison question, carried as ONE proof record.
//
// A model MAY answer a sealed, well-formed comparison question about two
// concepts, two labels, or two assertion occurrences: same, near-same, target
// broader, target narrower, or related. That answer is a PROOF, never a
// comparison OUTCOME — `rkaf:comparisonOutcome` (relation-comparison-context.cue
// §3.4) still only comes from the deterministic lattice folding two or more
// independent proofs. `#MachineAdjudicationProof` is how a model's answer
// becomes reviewable evidence for that lattice, not a shortcut around it.
//
// CONSTRAINT (reviewer, wave 4a): ONE shape, not two. There is no parallel
// `rkaf:Attestation` (or other) representation of the same fact, and — as
// explained in `#ResolverProofFields` (resolver-proof-record.cue) — not even
// a second `@type`. A machine-adjudication proof IS a plain
// `rkaf:ResolverProofRecord`, narrowed by its own `rkaf:proofType` literal and
// five conditionally required properties. `#MachineAdjudicationProof` below
// composes exactly those pieces; it exists to be named, documented, and
// referenced by consumers who want the fully-narrowed shape, not to mint a
// second wire representation. A conforming document never needs it: any
// `rkaf:ResolverProofRecord` whose `rkaf:proofType` is
// `rkaf:machineAdjudicationProof` already satisfies it by construction.
//
// THE INDEPENDENCE RULE IS NOT HERE. "At least one pair distinct on all four
// axes, equal sealed request digest across the pair, complete support
// retained" spans MULTIPLE proof records cited by one comparison or finding —
// exactly the cross-node shape `shapes/README.md` reserves for hand-authored
// SHACL. `rkaf:MachineAdjudicationIndependentPairShape` and
// `rkaf:MachineAdjudicationCompleteSupportShape` in
// `shapes/rkaf-shapes-analysis.ttl` carry it, finding these proofs by
// `rkaf:proofType` rather than by a second `rdf:type`. This file only shapes
// ONE proof record; CUE constrains one struct.
//
// THE FOUR INDEPENDENCE AXES, and where each one lives:
//
//   validator actor   `rkaf:proofIssuer` — the exact versioned resolver AND
//                      policy this proof was issued under (already required
//                      by `#ResolverProofFields`). Two proofs issued under two
//                      different `rkaf:ResolverProofIssuer` records were run
//                      by two different validating configurations, even if
//                      the underlying resolver software is the same build.
//   provider          `rkaf:proofIssuer -> rkaf:proofResolver` — the resolver
//                      IMPLEMENTATION alone, one hop coarser than the full
//                      issuer identity above. Two proofs whose issuers name
//                      the same `rkaf:proofResolver` came from the same
//                      provider even if a policy version differs between
//                      them, and same-provider correlation is exactly the
//                      failure mode independence exists to catch.
//   provider model ID `rkaf:hasAILineage -> rkaf:modelId` — which model
//                      answered.
//   independence group `rkaf:independenceGroup`, declared below — a
//                      producer-scoped tag for the sampling or deployment
//                      pool a validator was drawn from, orthogonal to the
//                      other three: two calls to the same model through the
//                      same resolver can still land in different
//                      independence pools, and two different providers can
//                      still share one if a producer's pooling was sloppy.
//
// This mapping is a rulespec-native rendering of four independence checks,
// reached through the two reference fields every proof already carries
// (`proofIssuer`, `hasAILineage`) rather than restated as bare literals on
// this struct, so a resolver upgrade or a model swap changes one referenced
// record instead of every proof that cites it.

// The five verdicts a machine adjudicator may return over one sealed
// question (rkaf: prefixed, closed). These name a RELATION between two
// things under comparison, not a gate result — collapsing them onto
// pass/fail would throw away exactly the distinction the lattice needs.
//
//   rkaf:verdictSame            the two are the same thing
//   rkaf:verdictNearSame         close enough to substitute, short of identity
//   rkaf:verdictTargetBroader    the target subsumes the source
//   rkaf:verdictTargetNarrower   the target is subsumed by the source
//   rkaf:verdictRelated          associated, neither same nor a containment
//
// Closed deliberately, matching every other outcome enum in this module: a
// sixth value is a new semantic case and enters by review, not by a producer
// inventing a string.
#MachineAdjudicationVerdict: "rkaf:verdictSame" | "rkaf:verdictNearSame" |
	"rkaf:verdictTargetBroader" | "rkaf:verdictTargetNarrower" |
	"rkaf:verdictRelated"

// The fully-narrowed reference shape: every `#ResolverProofFields` property
// plus the five a machine-adjudication proof always carries, all REQUIRED
// rather than conditional. Composes `#ResolverProofFields`, not
// `#ResolverProofRecord`, so it carries no `@type` of its own — exactly like
// `#DurableAssertionEnvelope` in assertion.cue, a shared shape a leaf record
// composes rather than one a document is ever typed as directly. The wire
// discriminator a real proof carries is `rkaf:proofType`, already narrowed to
// the literal below.
#MachineAdjudicationProof: {
	#ResolverProofFields
	"rkaf:proofType": "rkaf:machineAdjudicationProof"

	// The reviewed model-derivation record behind this adjudication call —
	// which model, which prompt contract, which sampling settings, over which
	// input context (`constraints/core/ai-lineage.cue`, Core §5.3). REQUIRED:
	// an adjudication with no lineage is exactly the opaque-string-is-not-proof
	// failure this whole module refuses (§4.3).
	"rkaf:hasAILineage": string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"

	// Producer-scoped identity of the independence pool this validator run
	// was drawn from. One of the four axes `rkaf:MachineAdjudicationIndependentPairShape`
	// (shapes/rkaf-shapes-analysis.ttl) reads to find an independent pair.
	"rkaf:independenceGroup": string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"

	// WHICH relation this adjudication found. This is the model's PROOF, not
	// a comparison outcome — see the file-level comment and
	// spec/rkaf-analysis.md §3.4.
	"rkaf:adjudicationVerdict": #MachineAdjudicationVerdict

	// The sealed request this proof answered, as a content digest rather than
	// a name: two proofs with an equal `rkaf:sealedRequestDigest` answered the
	// IDENTICAL question, which is what makes them a corroborating pair rather
	// than two answers to two different questions.
	"rkaf:sealedRequestDigest": string & =~"^sha256:[0-9a-f]{64}$"

	// The sealed response artifact this proof's verdict was read from. Kept
	// separate from `rkaf:proofRecordDigest` (which covers this record's OWN
	// bytes): the response artifact is the raw provider output the record
	// summarizes, resolvable independently so a reviewer can re-read exactly
	// what the model returned.
	"rkaf:sealedResponseArtifact": string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
}
