package rkaf

// Trust zones (§1.3): Z0 (untrusted) through Z8 (canonical authoritative).
// Structural property of an artifact — what kind of object it is.
#TrustZone: "rkaf:Z0" | "rkaf:Z1" | "rkaf:Z2" | "rkaf:Z3" | "rkaf:Z4" |
	"rkaf:Z5" | "rkaf:Z6" | "rkaf:Z7" | "rkaf:Z8"

// Safety labels (§1.3): D0 (display-only) through P4 (production-permitted).
// Operational property of an artifact — what the consumer may do with it.
// The published lettered scheme is D0 / S1 / R2 / A3 / P4 plus advisory and
// authority-critical refinements.
#SafetyLabel: "rkaf:D0DisplayOnly" | "rkaf:S1Suggestion" | "rkaf:R2Review" |
	"rkaf:A3Advisory" | "rkaf:A3AdvisoryAggregated" |
	"rkaf:A3AuthorityCritical" | "rkaf:P4Production" |
	"rkaf:permits-axiomatic"
