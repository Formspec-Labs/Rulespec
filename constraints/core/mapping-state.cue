package rkaf

// Closed four-value enum (§5.1).
#MappingState: "rkaf:mapsToWos" | "rkaf:authoringOnly" |
	"rkaf:requiresSpecExtension" | "rkaf:unmappedButApproved"

#MappingStateCarrier: {
	"rkaf:mappingState": #MappingState
}
