package rkaf

#RetentionTrigger: "rkaf:creation" | "rkaf:lastAccess" | "rkaf:lastModification" | "rkaf:lifecycleEvent"

#RetentionPostExpiry: "rkaf:delete" | "rkaf:anonymize" | "rkaf:archive" | "rkaf:legal-hold-on-trigger"

#RetentionPolicy: {
	"@type":                      "rkaf:RetentionPolicy"
	"rkaf:retentionDurationDays": >=0
	"rkaf:retentionTrigger":      #RetentionTrigger
	"rkaf:retentionPostExpiry":   #RetentionPostExpiry
}
