package rkaf

// Closed enum (§2.4). How the SOURCE attributes the claim — not how confident
// the extractor is, and not whether anyone approved it.
//
// `rkaf:claimantNotStated` is a real, honest answer: many documents assert
// without naming an asserter. It is not a failure and not a low-confidence
// signal; it says the source did not attribute the claim.
#ClaimantAttribution: "rkaf:claimantNamedInSource" |
	"rkaf:claimantImpliedBySource" | "rkaf:claimantIsDocumentIssuer" |
	"rkaf:claimantNotStated"

// SourceClaimant: who the SOURCE says asserts the proposition (§2.4).
//
// This is the role the vision keeps separate from every other provenance
// record, and the confusion it exists to prevent is a specific one: "the FAA
// states X" is a fact about the DOCUMENT, while "run r-42 extracted X" is a
// fact about the PIPELINE. Collapsing them makes an extractor look like an
// authority. So:
//   - the claimant is the party the document attributes the claim to;
//   - the extractor is rkaf:ExtractionActivity;
//   - the model-derivation record is rkaf:AILineage;
//   - the approver is an rkaf:Attestation.
// A SourceClaimant carries no decision, no confidence, and no approval.
#SourceClaimant: claimant={
	"@type":                  "rkaf:SourceClaimant"
	"rkaf:claimsAssertion":   string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:claimantAttribution": #ClaimantAttribution

	// What the document says, and — when the workspace can resolve it — who
	// that is. The two are separate because a source may name a claimant no
	// registry knows; dropping the verbatim text in that case would lose the
	// only evidence of attribution the document actually offers.
	"rkaf:claimantText"?:     string
	"rkaf:claimantIdentity"?: string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"

	// The exact source regions carrying the attribution. Separate from the
	// assertion's own EvidenceBinding: the text that names the claimant is
	// not necessarily the text that supports the claim.
	"rkaf:attributedInFragment"?: [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")]

	// A claimant the source NAMES must carry the naming text. Without it the
	// record asserts an attribution it cannot show, which is exactly the
	// unsourced-attribution failure this contract exists to block.
	if claimant["rkaf:claimantAttribution"] == "rkaf:claimantNamedInSource" {
		"rkaf:claimantText": string
	}
}
