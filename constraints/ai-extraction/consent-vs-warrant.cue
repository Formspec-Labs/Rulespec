package rkaf

// LLM-systematic-misinterpretation: LLM extracts "rkaf:consent" as a
// warrantKind value because the source text mentioned "consent". "consent" is
// not in the closed warrantKind enum. Closed enum rejects.

#ConsentVsWarrantRejector: {
	"@type":            "rkaf:Warrant"
	"rkaf:warrantKind": "rkaf:legal" | "rkaf:statutory" | "rkaf:regulatory" |
		"rkaf:delegated" | "rkaf:organizational" | "rkaf:contractual" |
		"rkaf:localOperational" | "rkaf:publication" |
		"rkaf:methodological" | "rkaf:empirical" | "rkaf:replication" | "rkaf:peerReview" |
		"rkaf:editorial" | "rkaf:factCheck" | "rkaf:correction" |
		"rkaf:cryptographic" | "rkaf:commitment" |
		"rkaf:consensus" | "rkaf:expertOpinion" | "rkaf:communityEndorsement" |
		"rkaf:sourceReliability" | "rkaf:provenanceClass"
}
