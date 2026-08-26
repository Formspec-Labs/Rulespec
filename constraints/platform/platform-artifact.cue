package platform

import "list"

// Closed plain-data carriers for the product-neutral platform container.
// rulespec_artifacts applies canonical-byte, ordering, identity, membership,
// digest, and exactly-one-location invariants that shapes cannot express.

#PlatformArtifactInput: {
	"role":           string & =~"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$"
	"logicalId":      string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]*[0-9a-f]{64}$"
	"artifactDigest": string & =~"^sha256:[0-9a-f]{64}$"
}

#PlatformArtifactCounts: {
	"manifestCount":       int & >=0 & <=9007199254740991
	"memberCount":         int & >=0 & <=9007199254740991
	"totalMemberByteSize": int & >=0 & <=9007199254740991
	"totalRecordCount":    int & >=0 & <=9007199254740991
}

#PlatformProducer: {
	"product":                  string & =~"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$"
	"implementationId":         string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"verifierId":               string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"verifierVersion":          string
	"verifierImplementationId": string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
}

#PlatformKnownLimit: knownLimit={
	"code":            string & =~"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$"
	"scope":           string & =~"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$"
	"statement":       string
	"evidenceDigests": [...(string & =~"^sha256:[0-9a-f]{64}$")] & list.MinItems(1)
	if !list.UniqueItems(knownLimit["evidenceDigests"]) { _|_ }
}

#PlatformSupersedes: {
	"logicalId":     string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]*[0-9a-f]{64}$"
	"artifactDigest": string & =~"^sha256:[0-9a-f]{64}$"
	"reason":          string
}

#PlatformMemberDescriptor: {
	"objectKey"?:   string
	"sha256"?:      string & =~"^sha256:[0-9a-f]{64}$"
	"blobRef"?:     string & =~"^sha256:[0-9a-f]{64}$"
	"role":         string & =~"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$"
	"mediaType":    string
	"byteSize":     int & >=0 & <=9007199254740991
	"recordCount"?: int & >=0 & <=9007199254740991
	"schemaId"?:    string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
}

#PlatformMemberManifestReference: {
	"manifestId":          string
	"scopeKind":           "global" | "partition"
	"scopeId":             string
	"objectKey":           string
	"byteSize":            int & >=0 & <=9007199254740991
	"sha256":              string & =~"^sha256:[0-9a-f]{64}$"
	"memberCount":         int & >=0 & <=9007199254740991
	"totalMemberByteSize": int & >=0 & <=9007199254740991
	"totalRecordCount":    int & >=0 & <=9007199254740991
}

#PlatformManifestCounts: {
	"memberCount":         int & >=0 & <=9007199254740991
	"totalMemberByteSize": int & >=0 & <=9007199254740991
	"totalRecordCount":    int & >=0 & <=9007199254740991
}

#PlatformManifestScope: {
	"kind": "global" | "partition"
	"id":   string
}

#PlatformMemberManifest: {
	"format":        "spicy-artifact-members"
	"formatVersion": "1.0"
	"manifestId":    string
	"scope":         #PlatformManifestScope
	"members":       [...#PlatformMemberDescriptor]
	"counts":        #PlatformManifestCounts
}

#PlatformDerivationRelation: relation={
	"relationKind":        "derivation"
	"processorId":         string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"processorVersion":    string
	"processorDigest":     string & =~"^sha256:[0-9a-f]{64}$"
	"policyId":            string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"policyVersion":       string
	"policyDigest":        string & =~"^sha256:[0-9a-f]{64}$"
	"parametersDigest":    string & =~"^sha256:[0-9a-f]{64}$"
	"partitioningId":      string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"partitioningDigest":  string & =~"^sha256:[0-9a-f]{64}$"
	"expectedOutputRoles": [...(string & =~"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")] & list.MinItems(1)
	if !list.UniqueItems(relation["expectedOutputRoles"]) { _|_ }
}

#PlatformCompositionRelation: relation={
	"relationKind":       "composition"
	"mergePolicyId":      string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"mergePolicyVersion": string
	"mergePolicyDigest":  string & =~"^sha256:[0-9a-f]{64}$"
	"totalOrderKey":      [...string] & list.MinItems(1)
	if !list.UniqueItems(relation["totalOrderKey"]) { _|_ }
}

#PlatformArtifact: artifact={
	"format":          "spicy-artifact"
	"formatVersion":   "1.0"
	"kind":            string & =~"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$"
	"spec":            {...}
	"logicalId":       string & =~"^urn:[^\\s]*:[0-9a-f]{64}$"
	"artifactDigest":  string & =~"^sha256:[0-9a-f]{64}$"
	"inputs":          [...#PlatformArtifactInput]
	"memberManifests": [...#PlatformMemberManifestReference]
	"counts":          #PlatformArtifactCounts
	"producer":        #PlatformProducer
	"knownLimits"?:    [...#PlatformKnownLimit] & list.MinItems(1)
	"supersedes"?:     #PlatformSupersedes
	if !list.UniqueItems(artifact["inputs"]) { _|_ }
}
