package rkaf

import "list"

// Closed enum: foundational OA selectors + domain-specific (§4.2).
#SelectorKind: "oa:FragmentSelector" | "oa:TextQuoteSelector" | "oa:TextPositionSelector" |
	"oa:RangeSelector" | "oa:XPathSelector" | "oa:CssSelector" |
	"rkaf:aknt-eId" | "rkaf:uslm-section" | "rkaf:eli-fragment" |
	"rkaf:jsonpath" | "rkaf:doi-fragment" | "rkaf:partner-defined"

#SourceFragment: {
	"@type":              "rkaf:SourceFragment"
	"rkaf:bindsArtifact": string // IRI of an Artifact
	"rkaf:hasSelector":   list.MinItems(1)
	"rkaf:selectorKind":  [...#SelectorKind] & list.MinItems(1)
	// Plan 7d — freshness. Orthogonal to lifecycle: tracks WHEN the source
	// was last reconfirmed, not whether the rule it grounds is in force.
	"rkaf:lastVerifiedAt"?: string // xsd:dateTime
	"rkaf:verifiedBy"?:     string // IRI of verifier
}
