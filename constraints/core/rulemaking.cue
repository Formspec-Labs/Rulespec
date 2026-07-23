package rkaf

import (
	"list"
	"time"
)

// Experimental US rulemaking-process module (spec/rkaf-rulemaking.md).
// A Proceeding is distinct from its dockets and published documents. A RIN or
// partner-scoped persistent identifier establishes proceeding identity.
#ProceedingIdentifierScheme: "rkaf:us-rin" | "rkaf:partner-defined"

#DocketIdentifierScheme: "rkaf:us-regsgov" | "rkaf:partner-defined"

#ProceedingStage: "rkaf:prerule" | "rkaf:proposed" | "rkaf:supplemental" |
	"rkaf:final" | "rkaf:withdrawn" | "rkaf:longterm"

// A Docket is a mutable administrative container, not an immutable Artifact.
#Docket: D={
	"@type":                       "rkaf:Docket"
	"rkaf:hasDocketIdentifier":    string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:docketIdentifierScheme": #DocketIdentifierScheme

	if D["rkaf:docketIdentifierScheme"] == "rkaf:us-regsgov" {
		"rkaf:hasDocketIdentifier": string & =~"^urn:rkaf:us:regsgov:[A-Z0-9]+(-[A-Z0-9]+)+$"
	}
}

#Proceeding: P={
	"@type":                         "rkaf:Proceeding"
	"rkaf:hasProceedingIdentifier":  string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:proceedingIdentifierScheme": #ProceedingIdentifierScheme
	"rkaf:proceedingStage"?:         #ProceedingStage
	"rkaf:hasAuthority":             [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1)
	"rkaf:hasDocket"?:               [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")]
	"rkaf:proceedingAffects"?:       [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")]

	if P["rkaf:proceedingIdentifierScheme"] == "rkaf:us-rin" {
		"rkaf:hasProceedingIdentifier": string & =~"^urn:rkaf:us:rin:[0-9]{4}-[A-Z]{2}[0-9]{2}$"
	}
}

// One node represents one continuous public-comment interval. A reopening is
// a second CommentPeriod node linked to the same Proceeding.
#CommentPeriod: C={
	"@type":                       "rkaf:CommentPeriod"
	"rkaf:commentPeriodFor":       string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:commentPeriodStart":     time.Format("2006-01-02")
	"rkaf:commentPeriodEnd":       time.Format("2006-01-02")
	"prov:wasDerivedFrom":         [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1)
	if C["rkaf:commentPeriodStart"] > C["rkaf:commentPeriodEnd"] {
		_|_
	}
}
