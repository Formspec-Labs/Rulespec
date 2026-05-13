package rkaf

// PointInTimeException (v0.1 §4.6).
//
// A lifecycle packet MAY include `pointInTimeExceptions[]`, each declaring an
// `evaluationAnchor` (from the EvaluationAnchor vocabulary), a scope
// description, and `retainsAssertion` / `retainsWorkProduct`. Consumers
// honor the exception only if they support the referenced anchor;
// otherwise they MUST refuse the packet rather than ignore the anchor.
#PointInTimeException: {
	"@type":                  "rkaf:PointInTimeException"
	"rkaf:evaluationAnchor":  #EvaluationAnchor
	// A PIT exception MUST retain at least one of: an Assertion or a
	// WorkProduct. The disjunction lives in the hand-authored Pattern-C
	// shape `shapes/rkaf-shapes-pattern-c.ttl::PointInTimeExceptionRetainsShape`.
	// The CUE source uses optional fields because CUE cannot express an
	// "exactly-one-of-these-two" cardinality constraint that compiles
	// straight to a per-property JSON Schema; the invariant is L3 SHACL.
	"rkaf:retainsAssertion"?:   string // IRI of the retained Assertion
	"rkaf:retainsWorkProduct"?: string // IRI of the retained GeneratedWorkProduct
	"rkaf:exceptionScope"?:     string // human-readable scope description
}
