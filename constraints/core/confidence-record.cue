package rkaf

import "list"

// Closed enums (§4.5).
#ConfidenceMethod: "rkaf:model-inference" | "rkaf:human-estimation" |
	"rkaf:review-consensus" | "rkaf:source-class-inheritance" | "rkaf:rule-based"

#CalibrationStatus: "rkaf:uncalibrated" | "rkaf:calibratedAgainst" |
	"rkaf:humanEstimated" | "rkaf:consensus"

#ScoreCategorical: "rkaf:very-low" | "rkaf:low" | "rkaf:medium" | "rkaf:high" | "rkaf:very-high"

// ConfidenceRecord rejects "score theater" by requiring confidenceMethod,
// confidenceBasis, calibrationStatus, generatedBy on every record.
#ConfidenceRecord: {
	"@type":                  "rkaf:ConfidenceRecord"
	"rkaf:confidenceMethod":  #ConfidenceMethod
	"rkaf:calibrationStatus": #CalibrationStatus
	"rkaf:confidenceBasis":   [...string] & list.MinItems(1)
	"rkaf:generatedBy":       string // IRI
	// Score: numeric in [0,1] OR categorical (disjunction).
	{"rkaf:score": >=0.0 & <=1.0} | {"rkaf:scoreCategorical": #ScoreCategorical}
	// If calibrationStatus = calibratedAgainst, evaluatedAgainst MUST be present.
	if "rkaf:calibrationStatus" == "rkaf:calibratedAgainst" {
		"rkaf:evaluatedAgainst": string
	}
}
