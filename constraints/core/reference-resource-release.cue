package rkaf

import "list"

// Whether the publisher supplies the release label or the producer derives it
// from immutable content. This describes version identity only; it is not an
// approval, activation, deployment, or use decision.
#ReferenceResourceVersionBasis: "rkaf:publisherAssigned" |
	"rkaf:contentDerived"

#ReferenceResourceMembershipMode: "rkaf:completeMembership" |
	"rkaf:partialMembership" | "rkaf:membershipNotEnumerated"

// One immutable release of any externally or locally governed reference
// resource, including an ontology, thesaurus, code list, identifier authority,
// classification, entity registry, mapping set, or schema. Profiles own the
// concrete dcterms:type IRIs; the kernel accepts any absolute IRI so it does
// not duplicate domain inventories.
//
// This node is the semantic manifest. Standard predicates carry stable-resource
// identity, publisher version, resource kind, members, distributions, and
// issue time. Every distribution is a content-digested Artifact. The one
// Rulespec digest is SHA-256 over RDFC-1.0 canonical N-Quads of the CLOSED
// manifest graph defined in Core §4.1.1: the allowed release triples except
// `referenceReleaseDigest`, plus each distribution Artifact's identifier,
// media type, and content digest. The digest therefore has no self-reference
// and is distinct from each distribution's byte digest.
//
// Import, activation, rollback, indexing, deployment, rights, and cache state
// remain application concerns.
#ReferenceResourceRelease: release={
	"@type":                        "rkaf:ReferenceResourceRelease"
	"dcterms:isVersionOf":          string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"dcat:version":                 string
	"dcterms:type":                 string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:membershipMode":          #ReferenceResourceMembershipMode
	"prov:hadMember"?:              [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1)
	"dcat:distribution":            [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1)
	"rkaf:referenceReleaseDigest":  string & =~"^sha256:[0-9a-f]{64}$"
	"rkaf:versionBasis"?:           #ReferenceResourceVersionBasis
	"dcterms:issued"?:              string // xsd:dateTime
	"rkaf:hasEffectivePeriod"?:     string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	if release["rkaf:membershipMode"] == "rkaf:completeMembership" {
		"prov:hadMember": [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1)
	}
	if release["rkaf:membershipMode"] == "rkaf:partialMembership" {
		"prov:hadMember": [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1)
	}
	if release["rkaf:membershipMode"] == "rkaf:membershipNotEnumerated" {
		// Optional bottom forbids the property while preserving the shared
		// carrier slot for the two enumerating modes.
		"prov:hadMember"?: _|_
	}
}
