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
