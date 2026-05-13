package rkaf

import "list"

// RegistryConflict (Appendix A; generalization of v0.1's MappingConflict per
// ConceptRegistry v0.1.2 §8): a record indicating two or more registry
// entries disagree on the same canonical claim. Severity governs whether the
// conflict is informational, blocks operational use, blocks publication, or
// breaks authority chains.
#ConflictSeverity: "rkaf:informational" | "rkaf:operationalConflict" |
	"rkaf:publicationBlocking" | "rkaf:authorityCritical"

#RegistryConflict: {
	"@type":                    "rkaf:RegistryConflict"
	"rkaf:conflictingEntries":  list.MinItems(2) // IRIs of registry entries that disagree (≥2)
	"rkaf:severity":            #ConflictSeverity
	"rkaf:conflictingScope"?:   string // optional IRI of the ApplicabilityScope where the conflict surfaces
	"rkaf:detectedAt":          string // xsd:dateTime
	"rkaf:detectedBy"?:         string // IRI of the actor / system that detected the conflict
}
