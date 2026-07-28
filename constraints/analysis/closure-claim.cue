package rkaf

import "list"

// ClosureClaim (Analysis §6) — EXPERIMENTAL AND DISABLED.
//
// A closure claim says that a named observation process COMPLETELY enumerated a
// bounded class of relations in a specific source region of a specific Artifact
// version, under a declared scope, profile version, and extraction run. It is a
// reviewable claim about a process, not a property of a document, and never a
// property of a corpus or of the world.
//
// It exists in the contract for one reason: bounded omission — "a closed later
// observation lacks an expected relation" — is the ONLY situation in which
// silence may be reported as anything other than unknown, and it is unusable
// without a closure boundary. Defining the shape now, disabled, is what keeps
// the eventual enabling a reviewed contract change instead of an ad-hoc field
// invented by whichever producer needs it first.
//
// ── DISABLED [Normative] ─────────────────────────────────────────────────────
//
// A `rkaf:ClosureClaim` MUST NOT be produced or consumed as evidence for any
// finding. No `rkaf:RelationFinding` may reference one, directly or through its
// comparison context or proof records. No omission finding kind exists, and
// none may be added while this record is disabled. A ClosureClaim in a
// conforming document is a SHAPE-VALIDITY artifact only: it records what the
// eventual claim looks like, and it carries no weight in any comparison.
//
// Four independent mechanisms enforce that, so no single edit can quietly
// enable it:
//
//   1. `rkaf:closureClaimStatus` is REQUIRED and closed over exactly one value,
//      `rkaf:closureClaimDisabled`. Every compiled target — JSON Schema `enum`,
//      SHACL `sh:in`, the Rust and TypeScript enums, the Rego value set —
//      rejects any other value. Enabling means editing this enum, which moves
//      the contract digest and forces every pinned consumer to re-accept.
//   2. `#ResolverProofType` (resolver-proof-record.cue) declares no closure
//      proof type, so a closure decision cannot be minted as a proof record and
//      cited by a comparison.
//   3. `rkaf:ClosureClaimNotFindingEvidenceShape` in
//      `shapes/rkaf-shapes-analysis.ttl` fails any graph in which a
//      `rkaf:RelationFinding` reaches a `rkaf:ClosureClaim` through its own
//      properties, or transitively — at ANY depth — through its comparison
//      context, the proof records it or its context cite, the assertions it
//      compared, and the records those in turn lean on. The depth is
//      unbounded on purpose: `rkaf:proofSupportingRecord` is unranged and a
//      proof record may cite another one, so a fixed hop count is walked
//      around by interposing one extra proof record.
//
//      Unlike mechanisms 1 and 2, this one lives on the SHACL path only. The
//      JSON Schema, Rust, TypeScript, and Rego sinks carry the closed status
//      enum and the closed proof-type enum, but none of them can express
//      reachability across nodes. A consumer validating through
//      `rkaf-validate` alone gets mechanisms 1, 2, and 4 — see
//      spec/rkaf-analysis.md §6.4.
//   4. `AnalysisModuleTests` in `tools/test_constraints_compile.py` fails the
//      build if the status enum grows a second value, if any property anywhere
//      in the contract is class-ranged to `rkaf:ClosureClaim`, if a closure
//      proof type appears, or if any fixture contains both a ClosureClaim node
//      and a RelationFinding node. Exactly one fixture is exempt and named in
//      the test: the negative that PROVES mechanism 3 fires. It is named
//      rather than pattern-matched so that deleting it — which would let the
//      shape be removed with no gate noticing — also fails the build.
//
// Closure stays disabled until a frozen real dataset measures closure precision
// and recall SEPARATELY from extraction. Until then, silence outside a proven
// boundary is `rkaf:comparisonUnknown`.

// One value, on purpose. This is the experimental flag that gates the record:
// a producer cannot author a ClosureClaim without declaring it disabled, and a
// consumer reading `rkaf:closureClaimDisabled` knows the claim carries no
// weight without consulting prose.
#ClosureClaimStatus: "rkaf:closureClaimDisabled"

#ClosureClaim: {
	// Composes the shared assertion envelope, so construction origin, model
	// derivation, extraction run, confidence, consumer disposition,
	// supersession, and assertion time have exactly one home each rather than a
	// parallel closure-shaped copy. `rkaf:hasExtractionProvenance` carries the
	// extraction run the omission design asks the claim to bind, and
	// `rkaf:hasApplicability` carries the applicability scope and temporal
	// anchor. Approval remains an `rkaf:Attestation` targeting this record;
	// nothing here restates it.
	//
	// `#AssertionProposition` is NOT composed: a closure claim's proposition is
	// "this bounded region was completely enumerated", not a subject-predicate-
	// object triple, and it must never carry assertion polarity.
	//
	// Absence from this shape is not enforcement — the compiled JSON Schema
	// emits no `additionalProperties: false` and RDF is open-world — so
	// `rkaf:ClosureClaimNoPolarityShape` in `shapes/rkaf-shapes-analysis.ttl`
	// closes it, exactly as `rkaf:RelationChangeEventNoPolarityShape` does for
	// change events. Without it a DISABLED record can be published as a denied
	// assertion about a triple, which is the §2 collapse wearing the one
	// `@type` that is supposed to carry no weight at all.
	#DurableAssertionEnvelope
	"@type": "rkaf:ClosureClaim"

	// The experimental gate. Required; exactly one legal value.
	"rkaf:closureClaimStatus": #ClosureClaimStatus

	// WHERE the claim applies. The Artifact version, class-ranged to
	// `rkaf:Artifact`, and the exact source regions enumerated, class-ranged to
	// `rkaf:SourceFragment`. Both required: "closure is always local", so a
	// claim that names no region is a claim about a whole document, which this
	// record must be incapable of expressing.
	"rkaf:closureArtifact": string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:closureRegion":   [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1)

	// WHAT was enumerated: the predicate family or collection shape covered.
	// A producer-scoped IRI — the kernel does not own predicate families, and
	// which relations a profile expects a boundary to address is a profile
	// question.
	"rkaf:closurePredicateFamily": string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"

	// UNDER WHICH RULES. The profile version whose normalization policy defined
	// the boundary; changing it invalidates the claim rather than updating it.
	"rkaf:closureProfileVersion": string

	// The digest over the accepted member assertions. This is what makes the
	// claim checkable at all: "these and only these" is only verifiable against
	// a content-bound set, and a recomputed digest that differs means the
	// enumeration is not the one that was reviewed.
	"rkaf:closureMemberDigest": string & =~"^sha256:[0-9a-f]{64}$"

	// When the claim was reviewed or takes effect. Optional; closure is
	// "local and revocable", and an unreviewed claim must be representable as
	// unreviewed rather than back-dated.
	"rkaf:closureReviewedAt"?: string // xsd:dateTime

	// Derived-shape narrowings of the envelope's reference fields, matching
	// every other envelope-composing form.
	"rkaf:hasApplicability"?:        string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:hasJustification"?:        string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:hasWarrant"?:              string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:hasAccessScope"?:          string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:hasRetentionPolicy"?:      string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:hasSourceClaimant"?:       string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:hasExtractionProvenance"?: string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:hasConfidence"?:           [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")]
	"rkaf:supersedesAssertion"?:     [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")]
}
