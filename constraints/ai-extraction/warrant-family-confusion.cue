package rkaf

// LLM-systematic-misinterpretation pattern (§10.1):
// The LLM picks a legal-family warrantKind ("rkaf:statutory") but assigns the
// scientific family because the surrounding source text mentions "studies".
// Closed family/kind agreement (defined in constraints/core/warrant.cue
// #WarrantFamilyKindAgreement) rejects this; the AI-extraction adversarial
// payload below is expected to FAIL on every target.

#WarrantFamilyConfusionRejector: {
	"@type":              "rkaf:Warrant"
	"rkaf:warrantKind":   "rkaf:statutory"
	"rkaf:warrantFamily": "rkaf:legal" // ONLY value permitted for kind=statutory
}
