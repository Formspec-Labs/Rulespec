package rkaf

import "list"

// Closed enum: foundational OA selectors + domain-specific (§4.2).
#SelectorKind: "oa:FragmentSelector" | "oa:TextQuoteSelector" | "oa:TextPositionSelector" |
	"oa:RangeSelector" | "oa:XPathSelector" | "oa:CssSelector" |
	"rkaf:aknt-eId" | "rkaf:uslm-section" | "rkaf:eli-fragment" |
	"rkaf:jsonpath" | "rkaf:doi-fragment" | "rkaf:partner-defined"

// Closed enum: the unit an offset-bearing selector counts in (§4.2).
//
// An offset without a declared unit is not a coordinate. "start 118" names
// three different regions depending on whether the producer counted Unicode
// code points, UTF-8 bytes, or UTF-16 code units, and the three disagree the
// moment the source contains a non-ASCII character — which legal text, with its
// section symbols, dashes, and curly quotes, always does. Declaring the unit is
// what lets a second reader land on the same region.
#CoordinateSystem: "rkaf:unicode-codepoint" | "rkaf:utf8-byte" |
	"rkaf:utf16-code-unit" | "rkaf:xml-node-path" | "rkaf:page-region" |
	"rkaf:partner-defined"

// TextQuoteSelector — OA 1.0 payload predicates (§9.1 Cohort A import).
// oa:exact is required; oa:prefix and oa:suffix are optional context anchors.
// rkaf:SourceFragment rdfs:subClassOf oa:SpecificResource (§4.2 alignment).
#TextQuoteSelector: {
	"@type":    "oa:TextQuoteSelector"
	"oa:exact": string // required — the verbatim quoted text
	"oa:prefix"?: string // optional — text immediately before the quote
	"oa:suffix"?: string // optional — text immediately after the quote
}

// TextPositionSelector — OA 1.0's offset selector (§9.1 Cohort A import).
//
// `oa:start` and `oa:end` are the offsets of the region; the ordering branch
// makes an inverted pair bottom. `rkaf:coordinateSystem` is REQUIRED here
// rather than on the fragment because the unit belongs to whatever counts in
// it: a fragment carrying a quote selector AND a position selector has exactly
// one coordinate system, and it is the position selector's. A position selector
// with no declared unit is unreproducible, which is the instability §4.2 exists
// to remove.
#TextPositionSelector: selector={
	"@type":                 "oa:TextPositionSelector"
	"oa:start":              >=0
	"oa:end":                >=0
	"rkaf:coordinateSystem": #CoordinateSystem
	if selector["oa:start"] > selector["oa:end"] {
		_|_
	}
}

// SourceFragment — one addressable region of ONE Artifact (§4.2).
//
// Fragment identity is the three REQUIRED bindings below taken together. Drop
// any one and the fragment stops naming a region:
//
//   oa:hasSource               WHICH Artifact — an exact IRI, class-ranged to
//                              rkaf:Artifact by the range registry
//   oa:hasSelector             WHICH region — at least one selector object
//   rkaf:selectorKind          HOW to read the region — closed set
//
// A fourth binding is required by the SELECTOR rather than by the fragment:
// `rkaf:coordinateSystem`, above, on `#TextPositionSelector`. Requiring it
// there and not here is deliberate — see the comment on that definition — but
// it left the whole selector contract opt-in, because the selector shape fires
// only on a node the producer typed. `rkaf:SourceFragmentSelectorKindAgreement`
// in `shapes/rkaf-shapes-core.ttl` binds a declared
// `rkaf:selectorKind: oa:TextPositionSelector` to an actually-typed selector,
// which is a cross-node rule Layer 2 has no carrier for.
//
// `rkaf:sourceArtifactDigest` is a STATE binding, not an identity binding, and
// it is deliberately optional at L1/L3. An Artifact is immutable by definition,
// but nothing stops a producer pointing `oa:hasSource` at an identifier whose
// backing bytes were quietly replaced; recording the digest the coordinates
// were computed against makes that substitution detectable instead of
// invisible. §4.2 states normatively that a fragment cited as comparison
// evidence or as evidence for an accepted assertion MUST carry it — an
// obligation on the consumer profile, not a cardinality this shape enforces.
#SourceFragment: {
	"@type": "rkaf:SourceFragment"
	// The parent Artifact, as an absolute IRI. The range registry
	// (constraints/semantics/l0-ranges.cue) pins the class, so SHACL checks
	// that the referenced node really is an rkaf:Artifact and not any IRI.
	"oa:hasSource":   string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"oa:hasSelector": list.MinItems(1)
	"rkaf:selectorKind":  [...#SelectorKind] & list.MinItems(1)

	// Content-digest bindings. `sourceArtifactDigest` pins the Artifact STATE
	// the coordinates address; `fragmentContentDigest` pins the exact region
	// text those coordinates select. They answer different questions — "did the
	// document change under me" and "is this the text I quoted" — so a record
	// may carry either, both, or neither.
	"rkaf:sourceArtifactDigest"?:  string & =~"^sha256:[0-9a-f]{64}$"
	"rkaf:fragmentContentDigest"?: string & =~"^sha256:[0-9a-f]{64}$"

	// Plan 7d — freshness. Orthogonal to lifecycle: tracks WHEN the source
	// was last reconfirmed, not whether the rule it grounds is in force.
	"rkaf:lastVerifiedAt"?: string // xsd:dateTime
	"rkaf:verifiedBy"?:     string // IRI of verifier
}
