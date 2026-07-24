//! Round-trip every v0.2 positive fixture through the matching typed primitive.
//! Asserts the JSON we serialize back equals the JSON we deserialized from
//! (modulo serde_json key ordering — we compare as serde_json::Value).

use rkaf_core::*;
use serde_json::Value;

fn fixture(slug: &str) -> Value {
    let path = format!(
        "{}/../../fixtures/{slug}.jsonld",
        env!("CARGO_MANIFEST_DIR")
    );
    let bytes = std::fs::read(&path).unwrap_or_else(|e| panic!("read fixture {path}: {e}"));
    serde_json::from_slice(&bytes).unwrap()
}

/// Locate the node of the requested `@type` inside the fixture. Single-node
/// fixtures return as-is; `@graph` fixtures find the first matching node.
fn extract(fixture: &Value, type_iri: &str) -> Value {
    if fixture.get("@type").and_then(|t| t.as_str()) == Some(type_iri) {
        return fixture.clone();
    }
    if let Some(graph) = fixture.get("@graph").and_then(|g| g.as_array()) {
        for node in graph {
            if node.get("@type").and_then(|t| t.as_str()) == Some(type_iri) {
                return node.clone();
            }
        }
    }
    panic!("no @type=`{type_iri}` node in fixture (root or in @graph)");
}

fn round_trip<T>(slug: &str, type_iri: &str)
where
    T: serde::de::DeserializeOwned + serde::Serialize,
{
    let doc = fixture(slug);
    let original_node = extract(&doc, type_iri);
    let typed: T = serde_json::from_value(original_node.clone())
        .unwrap_or_else(|e| panic!("deserialize {slug} ({type_iri}): {e}"));
    let reserialized = serde_json::to_value(&typed)
        .unwrap_or_else(|e| panic!("serialize {slug} ({type_iri}): {e}"));
    assert_eq!(
        original_node, reserialized,
        "round-trip diverged for fixture `{slug}` (@type={type_iri})"
    );
}

#[test]
fn round_trip_warrant_fixtures() {
    round_trip::<Warrant>("warrant-legal-positive", "rkaf:Warrant");
    round_trip::<Warrant>("warrant-scientific-positive", "rkaf:Warrant");
    round_trip::<Warrant>("warrant-cross-family-transition-positive", "rkaf:Warrant");
}

#[test]
fn round_trip_confidence_record_fixtures() {
    round_trip::<ConfidenceRecord>(
        "confidencerecord-calibrated-positive",
        "rkaf:ConfidenceRecord",
    );
    round_trip::<ConfidenceRecord>(
        "confidencerecord-uncalibrated-positive",
        "rkaf:ConfidenceRecord",
    );
}

#[test]
fn round_trip_access_scope_fixtures() {
    round_trip::<AccessScope>("accessscope-public-positive", "rkaf:AccessScope");
    round_trip::<AccessScope>(
        "accessscope-organizationVisible-positive",
        "rkaf:AccessScope",
    );
}

#[test]
fn round_trip_ai_lineage_fixture() {
    round_trip::<AILineage>("ailineage-positive", "rkaf:AILineage");
}

#[test]
fn round_trip_artifact_fixtures() {
    round_trip::<Artifact>("artifact-eli-positive", "rkaf:Artifact");
    round_trip::<Artifact>("artifact-doi-positive", "rkaf:Artifact");
    round_trip::<Artifact>("artifact-cid-positive", "rkaf:Artifact");
    round_trip::<Artifact>("artifact-us-cfr-positive", "rkaf:Artifact");
    round_trip::<Artifact>("artifact-us-usc-positive", "rkaf:Artifact");
    round_trip::<Artifact>("artifact-us-frdoc-positive", "rkaf:Artifact");
    round_trip::<Artifact>("artifact-us-regsgov-positive", "rkaf:Artifact");
    round_trip::<Artifact>("artifact-us-pl-positive", "rkaf:Artifact");
    round_trip::<Artifact>("artifact-us-eo-positive", "rkaf:Artifact");
    round_trip::<Artifact>("artifact-primary-topic-positive", "rkaf:Artifact");
}

#[test]
fn round_trip_source_fragment_fixtures() {
    round_trip::<SourceFragment>(
        "sourcefragment-oa-textquote-positive",
        "rkaf:SourceFragment",
    );
    round_trip::<SourceFragment>("sourcefragment-oa-xpath-positive", "rkaf:SourceFragment");
    round_trip::<SourceFragment>("sourcefragment-aknt-eid-positive", "rkaf:SourceFragment");
    round_trip::<SourceFragment>(
        "sourcefragment-uslm-section-positive",
        "rkaf:SourceFragment",
    );
}

#[test]
fn round_trip_evidence_binding_fixtures() {
    round_trip::<EvidenceBinding>("evidencebinding-positive", "rkaf:EvidenceBinding");
    round_trip::<EvidenceBinding>(
        "evidencebinding-no-evidence-reason-positive",
        "rkaf:EvidenceBinding",
    );
}

// === Vocabulary backlog round-trip coverage ===

#[test]
fn round_trip_authority_fixture() {
    round_trip::<Authority>("authority-positive", "rkaf:Authority");
}

#[test]
fn round_trip_attestation_fixture() {
    round_trip::<Attestation>("attestation-positive", "rkaf:Attestation");
}

// Plan 7d: temporal-bounds + freshness on existing primitives.
// These tests exercise serde round-trip on the new optional fields so a
// regression on `Option<String>` field handling or serde-rename keys
// surfaces at the codegen layer, not just at SHACL.
#[test]
fn round_trip_attestation_with_effective_period_fixture() {
    round_trip::<Attestation>(
        "attestation-with-effective-period-positive",
        "rkaf:Attestation",
    );
}

#[test]
fn round_trip_attestation_revoked_fixture() {
    round_trip::<Attestation>("attestation-revoked-positive", "rkaf:Attestation");
}

#[test]
fn round_trip_attestation_revoked_within_period_fixture() {
    round_trip::<Attestation>(
        "attestation-revoked-within-period-positive",
        "rkaf:Attestation",
    );
}

// ADR-0093 Phase B: targetFinding round-trip.
#[test]
fn round_trip_attestation_waiving_finding_fixture() {
    round_trip::<Attestation>(
        "attestation-waiving-finding-positive",
        "rkaf:Attestation",
    );
}

#[test]
fn round_trip_sourcefragment_with_freshness_fixture() {
    round_trip::<SourceFragment>(
        "sourcefragment-with-freshness-positive",
        "rkaf:SourceFragment",
    );
}

// ADR-0093 Phase A: round-trip the new Finding primitive itself.
#[test]
fn round_trip_finding_fixture() {
    round_trip::<Finding>("finding-positive", "rkaf:Finding");
}

#[test]
fn round_trip_evidencebinding_with_freshness_fixture() {
    round_trip::<EvidenceBinding>(
        "evidencebinding-with-freshness-positive",
        "rkaf:EvidenceBinding",
    );
}

#[test]
fn round_trip_bridgevalidationresult_with_freshness_fixture() {
    round_trip::<BridgeValidationResult>(
        "bridgevalidationresult-with-freshness-positive",
        "rkaf:BridgeValidationResult",
    );
}

#[test]
fn round_trip_local_adoption_fixture() {
    round_trip::<LocalAdoption>("localadoption-positive", "rkaf:LocalAdoption");
}

#[test]
fn round_trip_applicability_scope_fixture() {
    round_trip::<ApplicabilityScope>("applicabilityscope-positive", "rkaf:ApplicabilityScope");
}

#[test]
fn round_trip_effective_period_fixture() {
    round_trip::<EffectivePeriod>("effectiveperiod-positive", "rkaf:EffectivePeriod");
}

#[test]
fn round_trip_lifecycle_event_fixture() {
    round_trip::<LifecycleEvent>("lifecycleevent-positive", "rkaf:LifecycleEvent");
    round_trip::<LifecycleEvent>(
        "lifecycleevent-proceeding-stages-positive",
        "rkaf:LifecycleEvent",
    );
}

#[test]
fn round_trip_rulemaking_fixtures() {
    round_trip::<RegulatoryAgendaItem>(
        "agenda-item-ordinary-positive",
        "rkaf:RegulatoryAgendaItem",
    );
    round_trip::<RegulatoryAgendaObservation>(
        "agenda-observations-multiple-editions-positive",
        "rkaf:RegulatoryAgendaObservation",
    );
    round_trip::<AgendaProceedingRelationship>(
        "agenda-item-ordinary-positive",
        "rkaf:AgendaProceedingRelationship",
    );
    round_trip::<Proceeding>("proceeding-partner-positive", "rkaf:Proceeding");
    round_trip::<Docket>("docket-us-regsgov-positive", "rkaf:Docket");
    round_trip::<CommentPeriod>("commentperiod-positive", "rkaf:CommentPeriod");
}

#[test]
fn round_trip_concept_mapping_fixture() {
    round_trip::<ConceptMapping>("conceptmapping-positive", "rkaf:ConceptMapping");
}

#[test]
fn round_trip_concept_resolution_result_fixture() {
    round_trip::<ConceptResolutionResult>(
        "conceptresolutionresult-positive",
        "rkaf:ConceptResolutionResult",
    );
}

#[test]
fn round_trip_bridge_validation_result_fixture() {
    round_trip::<BridgeValidationResult>(
        "bridgevalidationresult-positive",
        "rkaf:BridgeValidationResult",
    );
}

#[test]
fn round_trip_bridge_consumer_registration_fixture() {
    round_trip::<BridgeConsumerRegistration>(
        "bridgeconsumerregistration-positive",
        "rkaf:BridgeConsumerRegistration",
    );
}

#[test]
fn round_trip_registry_conflict_fixture() {
    round_trip::<RegistryConflict>("registryconflict-positive", "rkaf:RegistryConflict");
}

#[test]
fn round_trip_justification_fixture() {
    round_trip::<Justification>("justification-positive", "rkaf:Justification");
}
