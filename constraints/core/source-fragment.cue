package rkaf

import "list"

// Closed enum: foundational OA selectors + domain-specific (§4.2).
#SelectorKind: "oa:FragmentSelector" | "oa:TextQuoteSelector" | "oa:TextPositionSelector" |
	"oa:RangeSelector" | "oa:XPathSelector" | "oa:CssSelector" |
	"rkaf:aknt-eId" | "rkaf:uslm-section" | "rkaf:eli-fragment" |
	"rkaf:jsonpath" | "rkaf:doi-fragment" | "rkaf:partner-defined"

// TextQuoteSelector — OA 1.0 payload predicates (§9.1 Cohort A import).
// oa:exact is required; oa:prefix and oa:suffix are optional context anchors.
// rkaf:SourceFragment rdfs:subClassOf oa:SpecificResource (§4.2 alignment).
#TextQuoteSelector: {
	"@type":    "oa:TextQuoteSelector"
	"oa:exact": string // required — the verbatim quoted text
	"oa:prefix"?: string // optional — text immediately before the quote
	"oa:suffix"?: string // optional — text immediately after the quote
}

#SourceFragment: {
	"@type":          "rkaf:SourceFragment"
	"oa:hasSource":   string // IRI of the parent Artifact (oa:SpecificResource pattern)
	"oa:hasSelector": list.MinItems(1)
	"rkaf:selectorKind":  [...#SelectorKind] & list.MinItems(1)
	// Plan 7d — freshness. Orthogonal to lifecycle: tracks WHEN the source
	// was last reconfirmed, not whether the rule it grounds is in force.
	"rkaf:lastVerifiedAt"?: string // xsd:dateTime
	"rkaf:verifiedBy"?:     string // IRI of verifier
}
