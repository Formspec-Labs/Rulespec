package rkaf

// LocalAdoption (§2.5 + §3.2): authorizes local operational use of an
// Assertion within a declared scope. CRITICAL invariant (§2.5): MUST NOT
// substitute for a broken/expired/rescinded `hasAuthority` /
// `derivesAuthorityFrom` chain when the adopted assertion requires external
// legal, regulatory, or delegated authority.
//
// Enforced via the closed enum on `adoptionAuthorityKind` — only
// organizational / localOperational / contractual / publication may be
// declared. (`legal` / `statutory` / `regulatory` / `delegated` are
// structurally excluded.)
#LocalAdoptionAuthorityKind: "rkaf:organizational" | "rkaf:localOperational" |
	"rkaf:contractual" | "rkaf:publication"

#LocalAdoption: {
	"@type":                       "rkaf:LocalAdoption"
	"rkaf:organization":           string // IRI of adopting organization
	"rkaf:targetAssertion":        string // IRI of the Assertion being adopted
	"rkaf:adoptionStatus":         "rkaf:active" | "rkaf:revoked" | "rkaf:expired" | "rkaf:proposed"
	"rkaf:usageEligibility":       #UsageEligibility
	"rkaf:adoptionAuthorityKind":  #LocalAdoptionAuthorityKind
	"rkaf:adoptionScope":          string // free-form scope IRI or label
	"rkaf:authorizedBy":           string // IRI of authorizing actor
	"rkaf:adoptedAt":              string // xsd:dateTime
	"rkaf:adoptsApplicability"?:   string // optional IRI of an ApplicabilityScope
	"rkaf:basedOnAttestation"?:    string // optional IRI of an Attestation
}
