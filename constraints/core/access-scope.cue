package rkaf

import "list"

#AccessScopeKind: "rkaf:public" | "rkaf:partnerVisible" | "rkaf:organizationVisible" |
	"rkaf:roleRestricted" | "rkaf:personalRestricted" |
	"rkaf:regulatoryRestricted" | "rkaf:embargoUntil"

#RegulatoryClass: "rkaf:HIPAA-PHI" | "rkaf:GDPR-PII" | "rkaf:FERPA" |
	"rkaf:CJIS" | "rkaf:classified" | "rkaf:legally-privileged" | "rkaf:partner-defined"

#AccessScope: {
	"@type":                "rkaf:AccessScope"
	"rkaf:accessScopeKind": #AccessScopeKind
	if "rkaf:accessScopeKind" == "rkaf:regulatoryRestricted" {
		"rkaf:regulatoryClass": [...#RegulatoryClass] & list.MinItems(1)
	}
	if "rkaf:accessScopeKind" == "rkaf:embargoUntil" {
		"rkaf:embargoUntil": string // xsd:dateTime
	}
	if "rkaf:accessScopeKind" == "rkaf:roleRestricted" {
		"rkaf:permittedRole": [...string] & list.MinItems(1)
	}
}
