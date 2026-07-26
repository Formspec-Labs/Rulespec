package rkaf

import "list"

// Closed enum of artifact identifier schemes (§4.1).
#ArtifactIdentifierScheme: "rkaf:eli" | "rkaf:eli-dl" | "rkaf:eli-i" |
	"rkaf:uslm" | "rkaf:aknt-eId" | "rkaf:doi" | "rkaf:isbn" | "rkaf:issn" |
	"rkaf:cid" | "rkaf:hash-sha256" | "rkaf:urn-persistent" | "rkaf:partner-defined"

// The universal Artifact. Jurisdiction-specific citation identity — the US
// regulatory identifier pair and its per-scheme grammars — and the rulemaking
// `rkaf:publishedInProceeding` relation are NOT kernel concerns; they live in
// constraints/profiles/us-rulemaking/us-regulatory-artifact.cue, which composes
// this definition. The kernel MUST NOT reference a profile shape.
//
// Version and revision identity (§4.1) composes Dublin Core and PROV-O rather
// than minting a Rulespec Work / Expression / Manifestation hierarchy: an
// Artifact is ONE immutable state, `dcterms:isVersionOf` names the stable
// resource it is a version of, and `prov:wasRevisionOf` names the exact earlier
// Artifact. The stable resource keeps whatever public type owns it (ELI,
// BIBFRAME, Schema.org, a profile class), so `dcterms:isVersionOf` deliberately
// carries NO class range — declaring one would be the universal Work class
// §4.1 declines to mint.
//
// The three conditionals below are what stops a version graph from being
// invented. They chain:
//
//   a version or revision claim  ->  MUST cite the source regions stating it
//   cited lineage evidence       ->  MUST make this state digest-addressable
//
// so a producer cannot assert lineage from a shared title, topic, identifier
// fragment, embedding score, or retrieval rank: whatever it names as evidence
// is an addressable region of an actual source, and the state carrying the
// claim is pinned by content digest. Neither conditional says the lineage is
// TRUE — they say the claim is CHECKABLE, which is the property comparison
// evidence needs and a similarity score never has.
#Artifact: artifact={
	"@type":                         "rkaf:Artifact"
	"rkaf:hasArtifactIdentifier":    [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1)
	"rkaf:artifactIdentifierScheme": [...#ArtifactIdentifierScheme] & list.MinItems(1)
	"foaf:primaryTopic"?:            string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"dcterms:hasFormat"?:            [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1)
	"dcterms:isFormatOf"?:           [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1)
	"dcterms:isVersionOf"?:          [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1)
	"prov:wasRevisionOf"?:           [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1)

	// The content digest of the immutable state this Artifact names. Lowercase
	// `sha256:<64 hex>` — the same lexical contract every other Rulespec digest
	// uses. The kernel checks the FORM of a digest, never its preimage.
	"rkaf:hasContentDigest"?: string & =~"^sha256:[0-9a-f]{64}$"

	// The source regions that STATE the version or revision relation: a
	// masthead line, an amendment note, a registry supersession field. These
	// are SourceFragments, so "where did this lineage come from" resolves to
	// exact coordinates in an actual document rather than to a heuristic.
	"rkaf:versionLineageEvidence"?: [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1)

	if artifact["dcterms:isVersionOf"] != _|_ {
		"rkaf:versionLineageEvidence": [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1)
	}
	if artifact["prov:wasRevisionOf"] != _|_ {
		"rkaf:versionLineageEvidence": [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1)
	}
	if artifact["rkaf:versionLineageEvidence"] != _|_ {
		"rkaf:hasContentDigest": string & =~"^sha256:[0-9a-f]{64}$"
	}
}
