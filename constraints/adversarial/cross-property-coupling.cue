package rkaf

// Adversarial pattern: when a ConfidenceRecord's confidenceMethod is "model-inference",
// the generatedBy actor MUST be a model IRI (urn:rkaf:actor:model:*), not a human or
// community actor. This couples two properties on the same node — JSON Schema's
// allOf/oneOf composition can silently accept the violation if the schema doesn't
// realize cross-property coupling.

#ModelInferenceCoupling: {
	"@type":                  "rkaf:ConfidenceRecord"
	"rkaf:confidenceMethod":  "rkaf:model-inference"
	"rkaf:generatedBy":       =~"^urn:rkaf:actor:model:"
}
