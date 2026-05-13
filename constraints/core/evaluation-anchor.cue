package rkaf

// EvaluationAnchor closed enum (v0.1 §4.7).
//
// A PointInTimeException MUST reference an EvaluationAnchor; consumers honor
// the exception only if they support the referenced anchor. Extensions via
// declared URIs in the EvaluationAnchorExtensionRegistry (Plan 4).
#EvaluationAnchor: "rkaf:applicationSubmissionTime" |
	"rkaf:eventOccurrenceTime" |
	"rkaf:eligibilityDeterminationTime" |
	"rkaf:noticeGenerationTime" |
	"rkaf:workflowStartTime" |
	"rkaf:workflowStepStartTime" |
	"rkaf:currentTime" |
	"rkaf:effectivePeriodStart" |
	"rkaf:publicationTime"
