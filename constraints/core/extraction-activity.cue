package rkaf

// Closed enum (§2.4). WHAT produced the candidate, at the level of method
// rather than vendor. `rkaf:modelExtraction` says a text model was involved;
// it does not say which vendor, which SDK, or which response shape — those are
// implementation facts that never define contract identity.
#ExtractionMethod: "rkaf:deterministicParse" | "rkaf:ruleBasedExtraction" |
	"rkaf:modelExtraction" | "rkaf:humanExtraction" | "rkaf:importedRecord"

// ExtractionActivity: which run produced an assertion candidate (§2.4).
//
// This is the record that lets the system represent an UNREVIEWED candidate
// honestly. It requires no approver, no reviewer, and no decision — an
// extraction happened, and that is all it claims. Human approval is an
// rkaf:Attestation targeting the assertion; a run that no one has reviewed
// simply has no such Attestation yet.
//
// Provider neutrality is structural, not aspirational. Every field is either
// a Rulespec-owned IRI, a version string, or an opaque lowercase SHA-256
// digest. No provider request object, response object, SDK type, billing
// record, or configuration blob appears here or is referenced by shape. A
// consumer can verify WHICH contract was sent without the kernel knowing what
// a "chat completion" is.
#ExtractionActivity: activity={
	"@type":                 "rkaf:ExtractionActivity"
	"rkaf:extractionMethod": #ExtractionMethod
	// The run, and the system that performed it. Both are producer-scoped
	// IRIs: the kernel neither mints nor parses them.
	"rkaf:extractionRun":    string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:extractedBy":      string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:extractorVersion": string

	// The secret-free digest of the COMPLETE request contract: instructions,
	// schema, model configuration, and input payload. One digest, because the
	// question a consumer asks is "was this produced by the contract I audited"
	// — and that question has one answer only if the whole contract is hashed
	// together. Schema descriptions and prose hints are part of the contract;
	// they are not a substitute for it.
	//
	// CONDITIONAL, not universal (see the guard below). The field presumes a
	// REQUEST-shaped extraction: a run that sent instructions, a schema, and a
	// configuration somewhere and got an answer back. A deterministic table
	// parse sends nothing and has no such contract, so requiring the digest of
	// one made the only conforming move to invent an envelope and hash it —
	// which yields a real digest naming a contract the run never published,
	// and that is worse than an absent field. When the field IS present it
	// MUST name a contract the run actually issued.
	"rkaf:requestContractDigest"?: string & =~"^sha256:[0-9a-f]{64}$"

	// Opaque references to the model and prompt contract, present only when a
	// model was involved. These are NOT a second AILineage: AILineage (§5.3)
	// records the REVIEWED derivation — model id, version, temperature, seed,
	// input-context hash, and the human approver that review implies. These
	// two fields name the model and prompt of a run that may never be
	// reviewed at all. Where both exist, hasAILineage below links them.
	"rkaf:extractionModelRef"?:  string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:extractionPromptRef"?: string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:hasAILineage"?:        string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"

	// Digests of the exact inputs the run consumed. Opaque by construction:
	// the kernel checks the lexical form of a digest, never its preimage.
	"rkaf:inputDigest"?: [...(string & =~"^sha256:[0-9a-f]{64}$")]

	// PROV-O activity timing, imported rather than re-minted (§9.1).
	"prov:startedAtTime"?: string // xsd:dateTime
	"prov:endedAtTime"?:   string // xsd:dateTime

	// Attempt ordinal. Retries are part of run lineage, not a quality signal.
	"rkaf:extractionAttempt"?: >=1

	// A model extraction must name the model it used, and must name the
	// contract it sent. Without the first the record says "a model did this"
	// while making the model unauditable; without the second a consumer cannot
	// answer "was this produced by the contract I audited", and those two
	// together are the provenance gap this contract exists to close.
	//
	// The digest is required HERE and not at the top level because a request
	// contract is what a model call has and a deterministic parse does not.
	// The other four methods may still carry the digest whenever the run
	// genuinely published a contract — `rkaf:ruleBasedExtraction` over a
	// versioned ruleset is the common case — but they are not made to
	// manufacture one.
	if activity["rkaf:extractionMethod"] == "rkaf:modelExtraction" {
		"rkaf:extractionModelRef":    string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
		"rkaf:requestContractDigest": string & =~"^sha256:[0-9a-f]{64}$"
	}
}
