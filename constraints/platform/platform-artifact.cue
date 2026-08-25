package platform

import "list"

// Generated carriers for the byte-level platform artifact protocol. The
// normative rules and identity preimages live in spec/platform-artifacts.md;
// rulespec_conformance.platform_artifact applies ordering, canonical-byte,
// digest, and cross-file invariants that a shape cannot express by itself.

#PlatformArtifactKind: "source-catalog" | "derivation" | "composition"
#PlatformManifestScopeKind: "global" | "partition"

#PlatformArtifactInput: {
	"role":           string & =~"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$"
	"logicalId":      string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"artifactDigest": string & =~"^sha256:[0-9a-f]{64}$"
}

#PlatformCompositionInput: {
	"role":           "member"
	"logicalId":      string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"artifactDigest": string & =~"^sha256:[0-9a-f]{64}$"
}

#PlatformArtifactCounts: {
	"manifestCount":       int & >=0 & <=9007199254740991
	"memberCount":         int & >=0 & <=9007199254740991
	"totalMemberByteSize": int & >=0 & <=9007199254740991
	"totalRecordCount":    int & >=0 & <=9007199254740991
}

#PlatformArtifactCoverage: {
	"complete":              true
	"accountedInputCount":   int & >=0 & <=9007199254740991
	"unaccountedInputCount": 0
}

#PlatformMemberDescriptor: {
	"objectKey":    string
	"role":         string & =~"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$"
	"mediaType":    string
	"byteSize":     int & >=0 & <=9007199254740991
	"sha256":       string & =~"^sha256:[0-9a-f]{64}$"
	"recordCount"?: int & >=0 & <=9007199254740991
	"schemaId"?:    string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
}

#PlatformMemberManifestReference: {
	"manifestId":          string
	"scopeKind":           #PlatformManifestScopeKind
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
	"kind": #PlatformManifestScopeKind
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

#PlatformSourceCatalogSpec: {
	"catalogId":                  string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"sourceSystemId":             string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"sourceSystemVersion":        string
	"selectionPolicyId":          string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"selectionPolicyVersion":     string
	"selectionPolicyDigest":      string & =~"^sha256:[0-9a-f]{64}$"
	"requestedUniverseSetDigest": string & =~"^sha256:[0-9a-f]{64}$"
	"selectedSourceSetDigest":    string & =~"^sha256:[0-9a-f]{64}$"
}

#PlatformDerivationSpec: derivationSpec={
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
	if !list.UniqueItems(derivationSpec["expectedOutputRoles"]) { _|_ }
}

#PlatformCompositionSpec: compositionSpec={
	"mergePolicyId":      string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"mergePolicyVersion": string
	"mergePolicyDigest":  string & =~"^sha256:[0-9a-f]{64}$"
	"totalOrderKey": [...string] & list.MinItems(1)
	if !list.UniqueItems(compositionSpec["totalOrderKey"]) { _|_ }
}

#PlatformArtifactFields: {
	"format":          "spicy-artifact"
	"formatVersion":   "1.0"
	"kind":            #PlatformArtifactKind
	"spec":            _
	"logicalId":       string & =~"^urn:spicy:artifact:(?:source-catalog|derivation|composition):[0-9a-f]{64}$"
	"artifactDigest":  string & =~"^sha256:[0-9a-f]{64}$"
	"inputs":          [..._]
	"memberManifests": [...#PlatformMemberManifestReference]
	"counts":          #PlatformArtifactCounts
	"coverage":        #PlatformArtifactCoverage
}

#PlatformSourceCatalogArtifact: sourceCatalog=#PlatformArtifactFields & {
	"kind": "source-catalog"
	"spec": #PlatformSourceCatalogSpec
	"inputs": [...#PlatformArtifactInput]
	"memberManifests": [...#PlatformMemberManifestReference] & list.MinItems(1)
	if !list.UniqueItems(sourceCatalog["inputs"]) { _|_ }
}

#PlatformDerivationArtifact: derivation=#PlatformArtifactFields & {
	"kind": "derivation"
	"spec": #PlatformDerivationSpec
	"inputs": [...#PlatformArtifactInput] & list.MinItems(1)
	"memberManifests": [...#PlatformMemberManifestReference] & list.MinItems(1)
	if !list.UniqueItems(derivation["inputs"]) { _|_ }
}

#PlatformCompositionArtifact: composition=#PlatformArtifactFields & {
	"kind": "composition"
	"spec": #PlatformCompositionSpec
	"inputs": [...#PlatformCompositionInput] & list.MinItems(1)
	if !list.UniqueItems(composition["inputs"]) { _|_ }
}
