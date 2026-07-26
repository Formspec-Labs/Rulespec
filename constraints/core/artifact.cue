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
#Artifact: {
	"@type":                         "rkaf:Artifact"
	"rkaf:hasArtifactIdentifier":    [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1)
	"rkaf:artifactIdentifierScheme": [...#ArtifactIdentifierScheme] & list.MinItems(1)
	"foaf:primaryTopic"?:            string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"dcterms:hasFormat"?:            [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1)
	"dcterms:isFormatOf"?:           [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1)
	"dcterms:isVersionOf"?:          [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1)
	"prov:wasRevisionOf"?:           [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1)
}
