package rkaf

import "list"

#AccessScopeKind: "rkaf:public" | "rkaf:partnerVisible" | "rkaf:organizationVisible" |
	"rkaf:roleRestricted" | "rkaf:personalRestricted" |
	"rkaf:regulatoryRestricted" | "rkaf:embargoUntil"

#RegulatoryClass: "rkaf:HIPAA-PHI" | "rkaf:GDPR-PII" | "rkaf:FERPA" |
	"rkaf:CJIS" | "rkaf:classified" | "rkaf:legally-privileged" | "rkaf:partner-defined"

#AccessScope: scope={
	"@type":                "rkaf:AccessScope"
	"rkaf:accessScopeKind": #AccessScopeKind
	if scope["rkaf:accessScopeKind"] == "rkaf:regulatoryRestricted" {
		"rkaf:regulatoryClass": [...#RegulatoryClass] & list.MinItems(1)
	}
	if scope["rkaf:accessScopeKind"] == "rkaf:embargoUntil" {
		"rkaf:embargoUntil": string // xsd:dateTime
	}
	if scope["rkaf:accessScopeKind"] == "rkaf:roleRestricted" {
		"rkaf:permittedRole": [...string] & list.MinItems(1)
	}
	// DPV 2.3 cross-namespace composition (Cohort A, §9.2). Optional. L1 imposes no
	// range constraints — partner producers conform to DPV's own taxonomy.
	"dpv:hasPersonalDataCategory"?: [...string]
	"dpv:hasLegalBasis"?:           string
	"dpv:hasPurpose"?:              string
}
