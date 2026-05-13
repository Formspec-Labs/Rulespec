package rkaf

// Adversarial: an EvidenceBinding whose AccessScope is more permissive than the
// bound SourceFragment's. AccessScope MUST narrow, never broaden. This is the
// access-scope-preservation invariant (§4.6).

#NarrowerOrEqualScope: {
	"@type":                "rkaf:EvidenceBinding"
	"rkaf:hasAccessScope": {
		"rkaf:accessScopeKind": "rkaf:regulatoryRestricted" |
			"rkaf:roleRestricted" |
			"rkaf:personalRestricted" |
			"rkaf:embargoUntil" |
			"rkaf:organizationVisible" |
			"rkaf:partnerVisible"
	}
}
