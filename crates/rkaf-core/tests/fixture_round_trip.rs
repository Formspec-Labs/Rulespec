//! Round-trip every v0.2 positive fixture through the matching typed primitive.
//! Asserts the JSON we serialize back equals the JSON we deserialized from
//! (modulo serde_json key ordering — we compare as serde_json::Value).

use rkaf_core::*;
use serde_json::Value;

fn fixture(slug: &str) -> Value {
    let path =
        format!("{}/../../fixtures/{slug}.jsonld", env!("CARGO_MANIFEST_DIR"));
    let bytes = std::fs::read(&path).unwrap_or_else(|e| {
        panic!("read fixture {path}: {e}")
    });
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
    round_trip::<ConfidenceRecord>("confidencerecord-calibrated-positive", "rkaf:ConfidenceRecord");
    round_trip::<ConfidenceRecord>("confidencerecord-uncalibrated-positive", "rkaf:ConfidenceRecord");
}

#[test]
fn round_trip_access_scope_fixtures() {
    round_trip::<AccessScope>("accessscope-public-positive", "rkaf:AccessScope");
    round_trip::<AccessScope>("accessscope-organizationVisible-positive", "rkaf:AccessScope");
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
}

#[test]
fn round_trip_source_fragment_fixtures() {
    round_trip::<SourceFragment>("sourcefragment-oa-textquote-positive", "rkaf:SourceFragment");
    round_trip::<SourceFragment>("sourcefragment-oa-xpath-positive", "rkaf:SourceFragment");
    round_trip::<SourceFragment>("sourcefragment-aknt-eid-positive", "rkaf:SourceFragment");
    round_trip::<SourceFragment>("sourcefragment-uslm-section-positive", "rkaf:SourceFragment");
}

#[test]
fn round_trip_evidence_binding_fixtures() {
    round_trip::<EvidenceBinding>("evidencebinding-positive", "rkaf:EvidenceBinding");
    round_trip::<EvidenceBinding>("evidencebinding-no-evidence-reason-positive", "rkaf:EvidenceBinding");
}
