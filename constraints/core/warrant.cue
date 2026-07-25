package rkaf

// Closed taxonomy (§4.4).
#WarrantFamily: "rkaf:legal" | "rkaf:scientific" | "rkaf:editorial" |
	"rkaf:cryptographic" | "rkaf:social" | "rkaf:source-class"

#WarrantKindLegal: "rkaf:legal" | "rkaf:statutory" | "rkaf:regulatory" |
	"rkaf:delegated" | "rkaf:organizational" | "rkaf:contractual" |
	"rkaf:localOperational" | "rkaf:publication"

#WarrantKindScientific: "rkaf:methodological" | "rkaf:empirical" |
	"rkaf:replication" | "rkaf:peerReview"

#WarrantKindEditorial: "rkaf:editorial" | "rkaf:factCheck" | "rkaf:correction"

#WarrantKindCryptographic: "rkaf:cryptographic" | "rkaf:commitment"

#WarrantKindSocial: "rkaf:consensus" | "rkaf:expertOpinion" | "rkaf:communityEndorsement"

#WarrantKindSourceClass: "rkaf:sourceReliability" | "rkaf:provenanceClass"

#WarrantKind: #WarrantKindLegal | #WarrantKindScientific | #WarrantKindEditorial |
	#WarrantKindCryptographic | #WarrantKindSocial | #WarrantKindSourceClass

#Warrant: {
	"@type":              "rkaf:Warrant"
	"rkaf:warrantKind":   #WarrantKind
	"rkaf:warrantFamily": #WarrantFamily
	// Optional cross-warrant chain link.
	"rkaf:hasPredecessor"?: [...string]
	// Annotation: defeasible (LegalRuleML interop).
	"rkaf:defeasible"?: bool
}

// Family/kind agreement (§4.4): a warrant's family MUST agree with its kind's family.
// The chain-level cross-family transition warning is runtime-enforced
// in rkaf-constraints-runtime (not at compile time).
//
// PROJECTION NOTE — what the generated carriers do and do not enforce:
//   - JSON Schema is the ONLY generated target that checks the agreement. It
//     emits the disjunction as `allOf: [{anyOf: [...]}]`.
//   - The generated Rust struct and TypeScript interface are inert CARRIERS.
//     They reproduce the composed #Warrant fields so the shape round-trips;
//     they carry NO family/kind agreement enforcement whatsoever. Constructing
//     a `WarrantFamilyKindAgreement` with `warrantKind: rkaf:legal` and
//     `warrantFamily: rkaf:scientific` compiles and serializes cleanly.
//   - No SHACL NodeShape is generated for this definition. It declares no
//     `@type` of its own, and the projector deliberately does not inherit
//     #Warrant's `@type` — doing so would emit a second NodeShape targeting
//     rkaf:Warrant that collides with the hand-authored normative shape in
//     shapes/rkaf-shapes-pattern-c.ttl. That hand-authored shape is the SHACL
//     enforcement for §4.4.
#WarrantFamilyKindAgreement: (#Warrant & {
	"rkaf:warrantKind":   #WarrantKindLegal
	"rkaf:warrantFamily": "rkaf:legal"
}) | (#Warrant & {
	"rkaf:warrantKind":   #WarrantKindScientific
	"rkaf:warrantFamily": "rkaf:scientific"
}) | (#Warrant & {
	"rkaf:warrantKind":   #WarrantKindEditorial
	"rkaf:warrantFamily": "rkaf:editorial"
}) | (#Warrant & {
	"rkaf:warrantKind":   #WarrantKindCryptographic
	"rkaf:warrantFamily": "rkaf:cryptographic"
}) | (#Warrant & {
	"rkaf:warrantKind":   #WarrantKindSocial
	"rkaf:warrantFamily": "rkaf:social"
}) | (#Warrant & {
	"rkaf:warrantKind":   #WarrantKindSourceClass
	"rkaf:warrantFamily": "rkaf:source-class"
})
