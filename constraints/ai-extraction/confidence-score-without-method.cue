package rkaf

// LLM-systematic-misinterpretation: LLM emits a bare {score: 0.9}
// ConfidenceRecord, omitting confidenceMethod, confidenceBasis,
// calibrationStatus, and generatedBy. ConfidenceRecord shape (in
// constraints/core/confidence-record.cue) requires all four; rejects.

#ConfidenceScoreWithoutMethodRejector: {
	"@type":                  "rkaf:ConfidenceRecord"
	"rkaf:confidenceMethod":  "rkaf:model-inference" | "rkaf:human-estimation" |
		"rkaf:review-consensus" | "rkaf:source-class-inheritance" | "rkaf:rule-based"
	"rkaf:calibrationStatus": "rkaf:uncalibrated" | "rkaf:calibratedAgainst" |
		"rkaf:humanEstimated" | "rkaf:consensus"
	"rkaf:confidenceBasis":   [...string]
	"rkaf:generatedBy":       string
}
