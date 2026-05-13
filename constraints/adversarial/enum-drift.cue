package rkaf

// Adversarial: a Warrant payload appears legitimate but uses a warrantKind that
// is NOT in the closed v0.2 enum (e.g., "rkaf:provisional" — a sensible-sounding
// label outside the taxonomy). A lax JSON Schema generator that defaults to
// open-additionalProperties would silently accept; closed-enum discipline rejects.

#WarrantKindV02: "rkaf:legal" | "rkaf:statutory" | "rkaf:regulatory" |
	"rkaf:delegated" | "rkaf:organizational" | "rkaf:contractual" |
	"rkaf:localOperational" | "rkaf:publication" |
	"rkaf:methodological" | "rkaf:empirical" | "rkaf:replication" | "rkaf:peerReview" |
	"rkaf:editorial" | "rkaf:factCheck" | "rkaf:correction" |
	"rkaf:cryptographic" | "rkaf:commitment" |
	"rkaf:consensus" | "rkaf:expertOpinion" | "rkaf:communityEndorsement" |
	"rkaf:sourceReliability" | "rkaf:provenanceClass"

#EnumDriftWarrant: {
	"@type":            "rkaf:Warrant"
	"rkaf:warrantKind": #WarrantKindV02
}
