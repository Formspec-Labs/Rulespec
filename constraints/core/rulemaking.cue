package rkaf

import "list"

// Experimental US rulemaking-process module (spec/rkaf-rulemaking.md).
// A Proceeding is distinct from its docket and published documents. It uses
// the shared identifier predicates with RIN and regulations.gov schemes.
#ProceedingIdentifierScheme: "rkaf:us-rin" | "rkaf:us-regsgov"

#ProceedingStage: "rkaf:prerule" | "rkaf:proposed" | "rkaf:supplemental" |
	"rkaf:final" | "rkaf:withdrawn" | "rkaf:longterm"

#Proceeding: {
	"@type":                         "rkaf:Proceeding"
	"rkaf:hasArtifactIdentifier":    [...string] & list.MinItems(1)
	"rkaf:artifactIdentifierScheme": [...#ProceedingIdentifierScheme] & list.MinItems(1)
	"rkaf:proceedingStage":          #ProceedingStage
	"rkaf:hasAuthority":             [...string] & list.MinItems(1)
	"rkaf:proceedingAffects"?:       [...string]
}

// One node represents one continuous public-comment interval. A reopening is
// a second CommentPeriod node linked to the same Proceeding.
#CommentPeriod: {
	"@type":                       "rkaf:CommentPeriod"
	"rkaf:commentPeriodFor":       string // IRI of rkaf:Proceeding
	"rkaf:commentPeriodStart":     string // xsd:date
	"rkaf:commentPeriodEnd":       string // xsd:date
}
