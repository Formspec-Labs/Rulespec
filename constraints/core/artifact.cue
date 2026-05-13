package rkaf

import "list"

// Closed enum of artifact identifier schemes (§4.1).
#ArtifactIdentifierScheme: "rkaf:eli" | "rkaf:eli-dl" | "rkaf:eli-i" |
	"rkaf:uslm" | "rkaf:aknt-eId" | "rkaf:doi" | "rkaf:isbn" | "rkaf:issn" |
	"rkaf:cid" | "rkaf:hash-sha256" | "rkaf:urn-persistent" | "rkaf:partner-defined"

#Artifact: {
	"@type":                         "rkaf:Artifact"
	"rkaf:hasArtifactIdentifier":    list.MinItems(1)
	"rkaf:artifactIdentifierScheme": [...#ArtifactIdentifierScheme] & list.MinItems(1)
}
