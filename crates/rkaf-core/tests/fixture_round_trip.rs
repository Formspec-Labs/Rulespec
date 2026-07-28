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
    round_trip::<Artifact>("artifact-version-lineage-positive", "rkaf:Artifact");
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

#[test]
fn round_trip_relationship_assertion_fixtures() {
    round_trip::<RelationshipAssertion>(
        "relationshipassertion-affirmed-positive",
        "rkaf:RelationshipAssertion",
    );
    round_trip::<RelationshipAssertion>(
        "relationshipassertion-denied-positive",
        "rkaf:RelationshipAssertion",
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
    round_trip::<Attestation>("attestation-waiving-finding-positive", "rkaf:Attestation");
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

#[test]
fn round_trip_value_assertion_fixtures() {
    round_trip::<ValueAssertion>("valueassertion-date-positive", "rkaf:ValueAssertion");
    round_trip::<ValueAssertion>(
        "valueassertion-denied-integer-positive",
        "rkaf:ValueAssertion",
    );
    round_trip::<ValueAssertion>(
        "valueassertion-ai-suggested-positive",
        "rkaf:ValueAssertion",
    );
}

#[test]
fn round_trip_source_claimant_fixtures() {
    round_trip::<SourceClaimant>("sourceclaimant-named-positive", "rkaf:SourceClaimant");
    round_trip::<SourceClaimant>("sourceclaimant-issuer-positive", "rkaf:SourceClaimant");
}

#[test]
fn round_trip_extraction_activity_fixtures() {
    round_trip::<ExtractionActivity>(
        "extractionactivity-deterministic-positive",
        "rkaf:ExtractionActivity",
    );
    round_trip::<ExtractionActivity>(
        "extractionactivity-model-positive",
        "rkaf:ExtractionActivity",
    );
}

/// The value object is CLOSED in every other target, and it must be closed
/// here too.
///
/// `TypedLiteral<T>` is the one hand-written carrier in this change, and it is
/// the only one without the generated `#[serde(flatten)] extra` catch-all. Left
/// open, it would ACCEPT `@language` and drop it on re-serialize — a silent
/// round-trip divergence on the exact member that also destroys the RDF
/// datatype (a language-tagged literal expands with no datatype at all, which
/// is why SHACL rejects it). `deny_unknown_fields` makes Rust reject what the
/// compiled JSON Schema, SHACL, and `cue vet` reject.
#[test]
fn typed_literal_rejects_members_outside_value_and_type() {
    use rkaf_core::generated::value_assertion::ValueDatatype;

    let ok: TypedLiteral<ValueDatatype> =
        serde_json::from_value(serde_json::json!({"@value": "x", "@type": "xsd:string"}))
            .expect("a bare value object must deserialize");
    assert_eq!(ok.value, "x");

    for extra in [
        serde_json::json!({"@value": "x", "@type": "xsd:string", "@language": "en"}),
        serde_json::json!({"@value": "x", "@type": "xsd:string", "rkaf:bogus": "y"}),
    ] {
        assert!(
            serde_json::from_value::<TypedLiteral<ValueDatatype>>(extra.clone()).is_err(),
            "TypedLiteral must reject the extra member in {extra}"
        );
    }
}

#[test]
fn round_trip_concept_scheme_fixtures() {
    round_trip::<ConceptScheme>("conceptscheme-registry-positive", "rkaf:ConceptScheme");
    round_trip::<ConceptScheme>("conceptscheme-local-positive", "rkaf:ConceptScheme");
}

#[test]
fn round_trip_concept_assignment_fixtures() {
    round_trip::<ConceptAssignment>(
        "conceptassignment-fragment-direct-positive",
        "rkaf:ConceptAssignment",
    );
    round_trip::<ConceptAssignment>(
        "conceptassignment-document-derived-positive",
        "rkaf:ConceptAssignment",
    );
}

#[test]
fn round_trip_source_fragment_identity_fixtures() {
    round_trip::<SourceFragment>(
        "sourcefragment-position-selector-positive",
        "rkaf:SourceFragment",
    );
    round_trip::<Artifact>("artifact-content-digest-positive", "rkaf:Artifact");
    round_trip::<Artifact>("artifact-version-lineage-positive", "rkaf:Artifact");
}

// ── Semantic carrier coverage: the document-analysis module ────────────────
//
// Category: **identity** and **typed values**, through the Rust carrier.
// `spec/rkaf-analysis.md` shipped five contracts with compiled Rust structs and
// no round-trip test — the one gate that proves a generated carrier neither
// drops nor invents a field. Every analysis fixture below is a `@graph`
// document, so `extract` locates the node by `@type`.

#[test]
fn round_trip_relation_change_event_fixtures() {
    round_trip::<RelationChangeEvent>(
        "relationchangeevent-removal-positive",
        "rkaf:RelationChangeEvent",
    );
    round_trip::<RelationChangeEvent>(
        "relationchangeevent-replacement-positive",
        "rkaf:RelationChangeEvent",
    );
}

#[test]
fn round_trip_relation_comparison_context_fixture() {
    round_trip::<RelationComparisonContext>(
        "relationcomparisoncontext-satisfied-positive",
        "rkaf:RelationComparisonContext",
    );
}

#[test]
fn round_trip_resolver_proof_fixtures() {
    round_trip::<ResolverProofRecord>(
        "relationcomparisoncontext-satisfied-positive",
        "rkaf:ResolverProofRecord",
    );
    round_trip::<ResolverProofIssuer>(
        "relationcomparisoncontext-satisfied-positive",
        "rkaf:ResolverProofIssuer",
    );
}

#[test]
fn round_trip_relation_finding_fixture() {
    round_trip::<RelationFinding>(
        "relationfinding-discrepancy-positive",
        "rkaf:RelationFinding",
    );
}

/// The disabled contract still has to round-trip. A carrier that silently
/// dropped `rkaf:closureClaimStatus` would erase the one field whose closed
/// single value is what "disabled" MEANS (`spec/rkaf-analysis.md` §6).
#[test]
fn round_trip_closure_claim_fixture() {
    round_trip::<ClosureClaim>("closureclaim-disabled-positive", "rkaf:ClosureClaim");
    let doc = fixture("closureclaim-disabled-positive");
    let node = extract(&doc, "rkaf:ClosureClaim");
    let claim: ClosureClaim = serde_json::from_value(node).expect("deserialize ClosureClaim");
    assert_eq!(
        serde_json::to_value(claim.closure_claim_status).expect("serialize status"),
        Value::String("rkaf:closureClaimDisabled".into()),
        "the only representable closure-claim status is the disabled one"
    );
}

// ── Semantic carrier coverage: concepts and the US rulemaking profile ──────

#[test]
fn round_trip_concept_flavor_fixtures() {
    round_trip::<RegisteredConcept>("concept-registered-positive", "rkaf:RegisteredConcept");
    round_trip::<LocalConcept>("localconcept-positive", "rkaf:LocalConcept");
}

/// The profile overlay keeps the kernel `@type`, so the SAME document
/// deserializes as the kernel carrier and as the profile carrier. That is the
/// composition claim of `constraints/README.md` stated as a carrier fact: a
/// consumer that loads only the kernel reads a US-bearing Artifact without
/// error, and a consumer that loads the profile reads the same bytes with the
/// regulatory identifier typed.
#[test]
fn round_trip_profile_overlay_shares_the_kernel_type() {
    round_trip::<USRegulatoryArtifact>("artifact-us-cfr-positive", "rkaf:Artifact");
    round_trip::<Artifact>("artifact-us-cfr-positive", "rkaf:Artifact");
    round_trip::<USLifecycleEvent>(
        "lifecycleevent-composed-kind-positive",
        "rkaf:LifecycleEvent",
    );
}

// ── Semantic carrier coverage: provenance-role and disposition carriers ────

#[test]
fn round_trip_retention_policy_fixture() {
    round_trip::<RetentionPolicy>("retentionpolicy-positive", "rkaf:RetentionPolicy");
}

/// `MappingStateCarrier` is the one primitive with no `@type` of its own — it
/// is an annotation any mapping-bearing node may carry — so it cannot go
/// through `extract`. Round-tripping it from the fixture root is the same
/// invariant, applied where the carrier actually lives.
#[test]
fn round_trip_mapping_state_carrier() {
    let doc = fixture("mappingstate-positive");
    let carrier: MappingStateCarrier =
        serde_json::from_value(doc.clone()).expect("deserialize MappingStateCarrier");
    let reserialized = serde_json::to_value(&carrier).expect("serialize MappingStateCarrier");
    assert_eq!(
        reserialized
            .get("rkaf:mappingState")
            .expect("carrier keeps its mapping state"),
        doc.get("rkaf:mappingState").expect("fixture states one"),
        "the mapping-state annotation must survive the carrier round-trip"
    );
}
