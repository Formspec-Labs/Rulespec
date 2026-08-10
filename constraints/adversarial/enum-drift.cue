package rkaf

// Adversarial: a Warrant payload appears legitimate but uses a warrantKind that
// is NOT in the closed v0.2 enum (e.g., "rkaf:provisional" — a sensible-sounding
// label outside the taxonomy). A lax JSON Schema generator that defaults to
// open-additionalProperties would silently accept; closed-enum discipline rejects.

// A reference, not a copy: constraints/core/warrant.cue:22 (`#WarrantKind`) is
// the single source of the 22-member taxonomy. An enum-drift detector that
// hardcoded its own copy of the taxonomy it polices would silently stop
// covering a new #WarrantKind member the day one is added.
#WarrantKindV02: #WarrantKind

#EnumDriftWarrant: {
	"@type":            "rkaf:Warrant"
	"rkaf:warrantKind": #WarrantKindV02
}
