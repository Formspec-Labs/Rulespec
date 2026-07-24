package rkaf

import "list"

// Closed enum of artifact identifier schemes (§4.1).
#ArtifactIdentifierScheme: "rkaf:eli" | "rkaf:eli-dl" | "rkaf:eli-i" |
	"rkaf:uslm" | "rkaf:aknt-eId" | "rkaf:doi" | "rkaf:isbn" | "rkaf:issn" |
	"rkaf:cid" | "rkaf:hash-sha256" | "rkaf:urn-persistent" | "rkaf:partner-defined"

#USRegulatoryIdentifierScheme: "rkaf:us-cfr" | "rkaf:us-usc" |
	"rkaf:us-frdoc" | "rkaf:us-regsgov" | "rkaf:us-pl" | "rkaf:us-eo"

#Artifact: A={
	"@type":                         "rkaf:Artifact"
	"rkaf:hasArtifactIdentifier":    [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1)
	"rkaf:artifactIdentifierScheme": [...#ArtifactIdentifierScheme] & list.MinItems(1)
	"rkaf:hasRegulatoryIdentifier"?: string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:regulatoryIdentifierScheme"?: #USRegulatoryIdentifierScheme
	"foaf:primaryTopic"?:            string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:publishedInProceeding"?:   [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1)
	"dcterms:hasFormat"?:            [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1)
	"dcterms:isFormatOf"?:           [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1)

	if A["rkaf:hasRegulatoryIdentifier"] != _|_ {
		"rkaf:regulatoryIdentifierScheme": #USRegulatoryIdentifierScheme
	}
	if A["rkaf:regulatoryIdentifierScheme"] == "rkaf:us-cfr" {
		"rkaf:hasRegulatoryIdentifier": string & =~"^urn:rkaf:us:cfr:[1-9][0-9]*:[0-9]+(\\.[0-9]+[a-z]{0,3}(-[0-9a-z]+)*)?$"
	}
	if A["rkaf:regulatoryIdentifierScheme"] == "rkaf:us-usc" {
		"rkaf:hasRegulatoryIdentifier": string & =~"^urn:rkaf:us:usc:[1-9][0-9]*:[1-9][0-9]*[a-z]*(-[0-9a-z]+)*$"
	}
	if A["rkaf:regulatoryIdentifierScheme"] == "rkaf:us-frdoc" {
		"rkaf:hasRegulatoryIdentifier": string & =~"^urn:rkaf:us:frdoc:[0-9]{4}-[0-9]{5}$"
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
