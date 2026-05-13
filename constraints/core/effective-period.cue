package rkaf

// EffectivePeriod (§2.3 + §4): the temporal window in which a Warrant /
// Authority / DelegationInstrument is in force. `effectivePeriodStart` is
// required; `effectivePeriodEnd` is optional (open-ended = still in force).
// Retroactive periods carry `retroactiveFrom`.
#EffectivePeriod: {
	"@type":                      "rkaf:EffectivePeriod"
	"rkaf:effectivePeriodStart":  string // xsd:dateTime
	"rkaf:effectivePeriodEnd"?:   string // xsd:dateTime (omitted = open-ended)
	"rkaf:retroactiveFrom"?:      string // xsd:dateTime
	"rkaf:sunsetAt"?:             string // xsd:dateTime (planned termination)
}
