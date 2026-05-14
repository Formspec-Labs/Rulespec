package rkaf

// Finding (ADR-0093): a first-class, IRI-addressable record of a single
// validation/audit detection. Promoted from BridgeValidationResult's flat
// string arrays so that downstream primitives can REFERENCE a Finding by
// IRI — enabling waiver-shaped Attestations (rkaf:targetFinding), Trellis
// anchoring of validation outcomes, and Studio readiness-tier projection.
//
// Universal across legal, scientific, editorial, and AI-substrate domains.
// A Finding is the typed handle for "something the validator/auditor/lint
// rule noticed about a subject"; downstream systems decide what to DO with
// it (block, warn, waive, escalate, anchor).

// Closed taxonomy of detection categories. Open extension via partner URIs
// is intentionally NOT permitted at L1 (Vocabulary); partners that need a
// new finding kind file an RFC per §13.4.
#FindingKind: "rkaf:warning" | "rkaf:error" |
	"rkaf:staleDependency" | "rkaf:registryUnavailable" |
	"rkaf:registryVersionOutOfRange" | "rkaf:conceptConflict" |
	"rkaf:authorityBroken" | "rkaf:unsupportedAnchor" |
	"rkaf:other"

// Closed severity ladder. Aligns with the ConceptResolutionResult severity
// enum already in use (#RegistryConflictSeverity) so a Finding produced by
// a ConceptResolutionResult and one produced by a BVR speak the same
// vocabulary.
#FindingSeverity: "rkaf:informational" | "rkaf:operationalConflict" |
	"rkaf:publicationBlocking" | "rkaf:authorityCritical"

#Finding: {
	"@type":            "rkaf:Finding"
	"rkaf:findingKind": #FindingKind
	"rkaf:detectedAt":  string // xsd:dateTime — when the detection happened
	"rkaf:detectedBy":  string // IRI of the detector (BVR, lint rule, validator, attester)
	"rkaf:subject":     string // IRI of the object the finding concerns
	"rkaf:severity"?:   #FindingSeverity
	"rkaf:rationale"?:  string
	// Plan 7d freshness fields apply uniformly to first-class primitives.
	"rkaf:lastVerifiedAt"?: string // xsd:dateTime
	"rkaf:verifiedBy"?:     string // IRI of verifier
}
