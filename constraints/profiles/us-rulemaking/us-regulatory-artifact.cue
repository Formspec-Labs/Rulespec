package rkaf

import "list"

// US rulemaking profile — regulatory citation identity on an Artifact.
//
// These terms are NOT universal. `rkaf:hasRegulatoryIdentifier`,
// `rkaf:regulatoryIdentifierScheme`, their seven per-scheme grammars, and
// `rkaf:publishedInProceeding` are jurisdiction-specific, so the kernel
// `#Artifact` (constraints/core/artifact.cue) no longer declares them. This
// profile shape composes the kernel definition and overlays them; the
// dependency runs profile -> kernel and never the other way.
//
// Class binding: the overlay keeps `@type: "rkaf:Artifact"`. A US regulatory
// document IS an Artifact — the profile constrains the universal class rather
// than minting a parallel one (spec/rkaf-rulemaking.md §5, "Federal Register
// documents need no source-specific subclass"). Every overlaid property is
// optional and every grammar sits behind a scheme guard, so a consumer loading
// kernel + profile sees the union of both shapes and a kernel-only consumer
// sees no US term at all.
#USRegulatoryIdentifierScheme: "rkaf:us-cfr" | "rkaf:us-usc" |
	"rkaf:us-frdoc" | "rkaf:us-frdoc-legacy" | "rkaf:us-regsgov" |
	"rkaf:us-pl" | "rkaf:us-eo"

#USRegulatoryArtifact: A={
	#Artifact
	"@type":                            "rkaf:Artifact"
	"rkaf:hasRegulatoryIdentifier"?:    string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:regulatoryIdentifierScheme"?: #USRegulatoryIdentifierScheme
	"rkaf:publishedInProceeding"?:      [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1)
	// Document -> Docket, direct. Federal Register metadata natively says
	// which docket a document belongs to, and until this term existed the only
	// docket edge in the profile was `rkaf:hasDocket` on `#Proceeding` — so a
	// producer holding dockets and documents but modelling no proceedings
	// could not state a fact its source states outright. The two edges are
	// independent, not substitutes: see spec/rkaf-rulemaking.md §5.3.
	"rkaf:publishedInDocket"?:          [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1)

	if A["rkaf:hasRegulatoryIdentifier"] != _|_ {
		"rkaf:regulatoryIdentifierScheme": #USRegulatoryIdentifierScheme
	}
	if A["rkaf:regulatoryIdentifierScheme"] == "rkaf:us-cfr" {
		"rkaf:hasRegulatoryIdentifier": string & =~"^urn:rkaf:us:cfr:[1-9][0-9]*:[0-9]+([a-z]|-[0-9]+)?(\\.[0-9]+[a-z]{0,3}(-[0-9a-z]+)*)?$"
	}
	if A["rkaf:regulatoryIdentifierScheme"] == "rkaf:us-usc" {
		"rkaf:hasRegulatoryIdentifier": string & =~"^urn:rkaf:us:usc:[1-9][0-9]*:[1-9][0-9]*[a-z]*(-[0-9a-z]+)*$"
	}
	if A["rkaf:regulatoryIdentifierScheme"] == "rkaf:us-frdoc" {
		"rkaf:hasRegulatoryIdentifier": string & =~"^urn:rkaf:us:frdoc:[0-9]{4}-[0-9]{3,5}$"
	}
	if A["rkaf:regulatoryIdentifierScheme"] == "rkaf:us-frdoc-legacy" {
		"rkaf:hasRegulatoryIdentifier": string & =~"^urn:rkaf:us:frdoc-legacy:[0-9]{2}-[0-9]{1,6}:[0-9]{4}-[0-9]{2}-[0-9]{2}$"
	}
	if A["rkaf:regulatoryIdentifierScheme"] == "rkaf:us-regsgov" {
		"rkaf:hasRegulatoryIdentifier": string & =~"^urn:rkaf:us:regsgov:[A-Z0-9]+([-_][A-Z0-9]+)*$"
	}
	if A["rkaf:regulatoryIdentifierScheme"] == "rkaf:us-pl" {
		"rkaf:hasRegulatoryIdentifier": string & =~"^urn:rkaf:us:pl:[1-9][0-9]*-[1-9][0-9]*$"
	}
	if A["rkaf:regulatoryIdentifierScheme"] == "rkaf:us-eo" {
		"rkaf:hasRegulatoryIdentifier": string & =~"^urn:rkaf:us:eo:[1-9][0-9]*$"
	}
}
