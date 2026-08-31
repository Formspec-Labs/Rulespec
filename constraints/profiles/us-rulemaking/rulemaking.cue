package rkaf

import (
	"list"
	"time"
)

// Experimental US rulemaking-process module (spec/rkaf-rulemaking.md).
// A RIN identifies a durable RegulatoryAgendaItem. Proceedings, dockets, and
// published documents retain separate identities.
#AgendaItemIdentifierScheme: "rkaf:us-rin"
#AgendaObservationIdentifierScheme: "rkaf:urn-persistent"

#AgendaScopeStatus: "rkaf:agendaScopeRecurring" |
	"rkaf:agendaScopeSingleObserved" | "rkaf:agendaScopeUnresolved"

#AgendaStage: "rkaf:agendaPrerule" | "rkaf:agendaProposed" |
	"rkaf:agendaFinal" | "rkaf:agendaLongterm" | "rkaf:agendaCompleted"

#AgendaPriority: "rkaf:agendaPriorityEconomicallySignificant" |
	"rkaf:agendaPriorityOtherSignificant" |
	"rkaf:agendaPrioritySubstantiveNonsignificant" |
	"rkaf:agendaPriorityRoutineFrequent" |
	"rkaf:agendaPriorityInfoAdminOther"

#ProceedingIdentifierScheme: "rkaf:official-registry" | "rkaf:partner-defined"

#DocketIdentifierScheme: "rkaf:us-regsgov" | "rkaf:official-registry" |
	"rkaf:partner-defined"

#ProceedingStage: "rkaf:proceedingPrerule" | "rkaf:proceedingProposed" |
	"rkaf:proceedingSupplemental" | "rkaf:proceedingFinal" |
	"rkaf:proceedingWithdrawn" | "rkaf:proceedingLongterm" |
	"rkaf:proceedingConcluded"

#ProceedingTerminationCause: "rkaf:agencyWithdrawal" |
	"rkaf:judicialVacatur" | "rkaf:congressionalDisapproval" |
	"rkaf:administrativeConclusion"

#RegulatoryAgendaItem: {
	"@type":                           "rkaf:RegulatoryAgendaItem"
	"rkaf:hasAgendaItemIdentifier":    string & =~"^urn:rkaf:us:rin:[0-9]{4}-[A-Z]{2}[0-9]{2}$"
	"rkaf:agendaItemIdentifierScheme": #AgendaItemIdentifierScheme
	"rkaf:agendaScopeStatus"?:         #AgendaScopeStatus
	"dcat:qualifiedRelation"?:         [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1)
}

// One immutable record of an agenda item in one Unified Agenda edition.
// This class is a profile subclass of both rkaf:Artifact and
// dcat:CatalogRecord; its artifact identity is the edition-specific source URL.
#RegulatoryAgendaObservation: {
	"@type":                           "rkaf:RegulatoryAgendaObservation"
	"rkaf:hasArtifactIdentifier":      [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1)
	"rkaf:artifactIdentifierScheme":   [...#AgendaObservationIdentifierScheme] & list.MinItems(1)
	"foaf:primaryTopic":               string & =~"^urn:rkaf:us:rin:[0-9]{4}-[A-Z]{2}[0-9]{2}$"
	"rkaf:agendaStage"?:               #AgendaStage
	"rkaf:agendaPriority"?:            #AgendaPriority
	"rkaf:agendaAffectsCitation"?:     [...(string & =~"^urn:rkaf:us:cfr:[1-9][0-9]*:[0-9]+([a-z]|-[0-9]+)?(\\.[0-9]+[a-z]{0,3}(-[0-9a-z]+)*)?$")] & list.MinItems(1)
	"rkaf:agendaAuthorityCitation"?:   [...(string & =~"^urn:rkaf:us:(usc:[1-9][0-9]*:[1-9][0-9]*[a-z]*(-[0-9a-z]+)*|pl:[1-9][0-9]*-[1-9][0-9]*)$")] & list.MinItems(1)
}

// A provenance-bearing, action-specific association. The DCAT qualified
// relation pattern is general; this subclass fixes the target and role used by
// the US rulemaking profile.
#AgendaProceedingRelationship: {
	"@type":                  "rkaf:AgendaProceedingRelationship"
	"dcterms:relation":       string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"dcat:hadRole":           "rkaf:agendaTracksProceeding"
	"prov:wasDerivedFrom":    [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1)
	"prov:wasGeneratedBy":    string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"prov:wasAttributedTo":   string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"prov:generatedAtTime":   string // xsd:dateTime
}

// A Docket is a mutable administrative container, not an immutable Artifact.
#Docket: D={
	"@type":                       "rkaf:Docket"
	"rkaf:hasDocketIdentifier":    string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:docketIdentifierScheme": #DocketIdentifierScheme
	"rkaf:identifierRegistry"?:    string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"

	if D["rkaf:docketIdentifierScheme"] == "rkaf:us-regsgov" {
		"rkaf:hasDocketIdentifier": string & =~"^urn:rkaf:us:regsgov:[A-Z0-9]+([-_][A-Z0-9]+)*$"
	}
	if D["rkaf:docketIdentifierScheme"] == "rkaf:official-registry" {
		"rkaf:identifierRegistry": string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	}
}

#Proceeding: P={
	"@type":                           "rkaf:Proceeding"
	"rkaf:hasProceedingIdentifier":    string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$" & !~"^urn:rkaf:us:(rin|regsgov):"
	"rkaf:proceedingIdentifierScheme": #ProceedingIdentifierScheme
	"rkaf:identifierRegistry"?:        string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	"rkaf:proceedingStage"?:           #ProceedingStage
	"rkaf:proceedingTerminationCause"?: #ProceedingTerminationCause
	"rkaf:hasAuthority"?:              [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1)
	"rkaf:hasDocket"?:                 [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1)
	"rkaf:proceedingAffects"?:         [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1)
	"rkaf:proceedingAffectsCitation"?: [...(string & =~"^urn:rkaf:us:cfr:[1-9][0-9]*:[0-9]+([a-z]|-[0-9]+)?(\\.[0-9]+[a-z]{0,3}(-[0-9a-z]+)*)?$")] & list.MinItems(1)
	"rkaf:proceedingProduces"?:        [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1)
	"rkaf:proceedingSupersedes"?:      [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1)

	if P["rkaf:proceedingIdentifierScheme"] == "rkaf:official-registry" {
		"rkaf:identifierRegistry": string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
	}
	if P["rkaf:proceedingStage"] == "rkaf:proceedingConcluded" {
		"rkaf:proceedingTerminationCause": #ProceedingTerminationCause
	}
}

// One node represents one continuous public-comment interval. A reopening is
// a second CommentPeriod node. It has at least one Proceeding or Docket anchor.
// The disjunction projects the requirement into CUE, JSON Schema, generated
// SHACL, and the generated SDK validators; the hand-authored Pattern-C shape
// remains a graph-level defense in depth.
#CommentPeriod: C={
	"@type":                         "rkaf:CommentPeriod"
	"rkaf:commentPeriodFor"?:        [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1)
	"rkaf:commentPeriodDocket"?:     [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1)
	"rkaf:commentPeriodOpenedBy"?:   [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1)
	"rkaf:commentPeriodStart":       time.Format("2006-01-02")
	"rkaf:commentPeriodEnd":         time.Format("2006-01-02")
	"prov:wasDerivedFrom":           [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1)
	{
		"rkaf:commentPeriodFor": [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1)
	} | {
		"rkaf:commentPeriodDocket": [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")] & list.MinItems(1)
	}
	if C["rkaf:commentPeriodStart"] > C["rkaf:commentPeriodEnd"] {
		_|_
	}
}
