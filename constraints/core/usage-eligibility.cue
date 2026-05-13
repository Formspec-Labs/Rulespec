package rkaf

// Closed lattice (§1.4): usage eligibility ascends from notEligible (lowest
// ceiling) to officialUse (highest). The lattice ORDER is normative — consumers
// MAY narrow (move down), MUST NOT broaden (move up). Only LocalAdoption MAY
// broaden within its declared scope.
//
// Effective `usageEligibility` for an artifact is computed by a reducer that
// combines: assertion baseline, scoped LocalAdoption grants, lifecycle status,
// applicability constraints, consumer capabilities. The reducer is runtime
// behavior; CUE only validates the closed enum membership.
#UsageEligibility: "rkaf:notEligible" | "rkaf:searchOnly" | "rkaf:reviewQueueOnly" |
	"rkaf:draftGenerationAllowed" | "rkaf:localOperationalUse" |
	"rkaf:publicationAllowed" | "rkaf:officialUse"
