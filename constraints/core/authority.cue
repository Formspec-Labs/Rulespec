package rkaf

// Authority (§2): a specialization of Warrant carrying a closed-enum
// authority kind, optional applicability + effective period, and an optional
// chain predecessor. Authority is the legal-family Warrant; the generic
// `rkaf:Warrant` covers scientific / editorial / cryptographic / social /
// source-class families.
//
// `authorityKind` is hop-local (§2.2): a chain
// requirement → regulation → delegation → statute carries
// `regulatory → delegated → statutory` across hops. Each Authority node
// records the kind of authority conveyed at its own hop, not a global label.
#AuthorityKind: "rkaf:legal" | "rkaf:statutory" | "rkaf:regulatory" |
	"rkaf:delegated" | "rkaf:organizational" | "rkaf:contractual" |
	"rkaf:localOperational" | "rkaf:publication"

#Authority: {
	"@type":                      "rkaf:Authority"
	"rkaf:authorityKind":         #AuthorityKind
	"rkaf:hasApplicability"?:     string // IRI of rkaf:ApplicabilityScope
	"rkaf:hasEffectivePeriod"?:   string // IRI of rkaf:EffectivePeriod
	"rkaf:derivesAuthorityFrom"?: [...string] // chain hop(s)
}
