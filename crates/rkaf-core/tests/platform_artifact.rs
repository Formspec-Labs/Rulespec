//! Generated platform artifact carrier checks.

// Rust guideline compliant 2026-02-21

use rkaf_core::generated::platform::platform_artifact::{
    PlatformCompositionArtifact, PlatformDerivationArtifact, PlatformSourceCatalogArtifact,
};
use serde_json::json;

fn source_catalog() -> serde_json::Value {
    json!({
        "artifactDigest": format!("sha256:{}", "0".repeat(64)),
        "counts": {
            "manifestCount": 1,
            "memberCount": 1,
            "totalMemberByteSize": 10,
            "totalRecordCount": 1
        },
        "coverage": {
            "accountedInputCount": 1,
            "complete": true,
            "unaccountedInputCount": 0
        },
        "format": "spicy-artifact",
        "formatVersion": "1.0",
        "inputs": [],
        "kind": "source-catalog",
        "logicalId": format!("urn:spicy:artifact:source-catalog:{}", "1".repeat(64)),
        "memberManifests": [{
            "byteSize": 100,
            "manifestId": "global:global",
            "memberCount": 1,
            "objectKey": "manifests/global.json",
            "scopeId": "global",
            "scopeKind": "global",
            "sha256": format!("sha256:{}", "2".repeat(64)),
            "totalMemberByteSize": 10,
            "totalRecordCount": 1
        }],
        "spec": {
            "catalogId": "urn:example:catalog",
            "requestedUniverseSetDigest": format!("sha256:{}", "3".repeat(64)),
            "selectedSourceSetDigest": format!("sha256:{}", "4".repeat(64)),
            "selectionPolicyDigest": format!("sha256:{}", "5".repeat(64)),
            "selectionPolicyId": "urn:example:policy",
            "selectionPolicyVersion": "1",
            "sourceSystemId": "urn:example:source",
            "sourceSystemVersion": "1"
        }
    })
}

#[test]
fn derivation_and_reference_only_composition_use_the_same_closed_root() {
    let input = json!({
        "artifactDigest": format!("sha256:{}", "6".repeat(64)),
        "logicalId": format!("urn:spicy:artifact:source-catalog:{}", "7".repeat(64)),
        "role": "source"
    });
    let mut derivation = source_catalog();
    derivation["kind"] = json!("derivation");
    derivation["logicalId"] = json!(format!("urn:spicy:artifact:derivation:{}", "8".repeat(64)));
    derivation["inputs"] = json!([input]);
    derivation["spec"] = json!({
        "expectedOutputRoles": ["records"],
        "parametersDigest": format!("sha256:{}", "9".repeat(64)),
        "partitioningDigest": format!("sha256:{}", "a".repeat(64)),
        "partitioningId": "urn:example:partitioning",
        "policyDigest": format!("sha256:{}", "b".repeat(64)),
        "policyId": "urn:example:policy",
        "policyVersion": "1",
        "processorDigest": format!("sha256:{}", "c".repeat(64)),
        "processorId": "urn:example:processor",
        "processorVersion": "1"
    });
    serde_json::from_value::<PlatformDerivationArtifact>(derivation)
        .expect("valid derivation carrier");

    let composition = json!({
        "artifactDigest": format!("sha256:{}", "d".repeat(64)),
        "counts": {
            "manifestCount": 0,
            "memberCount": 0,
            "totalMemberByteSize": 0,
            "totalRecordCount": 0
        },
        "coverage": {
            "accountedInputCount": 1,
            "complete": true,
            "unaccountedInputCount": 0
        },
        "format": "spicy-artifact",
        "formatVersion": "1.0",
        "inputs": [{
            "artifactDigest": format!("sha256:{}", "e".repeat(64)),
            "logicalId": format!("urn:spicy:artifact:derivation:{}", "f".repeat(64)),
            "role": "member"
        }],
        "kind": "composition",
        "logicalId": format!("urn:spicy:artifact:composition:{}", "0".repeat(64)),
        "memberManifests": [],
        "spec": {
            "mergePolicyDigest": format!("sha256:{}", "1".repeat(64)),
            "mergePolicyId": "urn:example:merge-policy",
            "mergePolicyVersion": "1",
            "totalOrderKey": ["score", "catalog", "subject"]
        }
    });
    serde_json::from_value::<PlatformCompositionArtifact>(composition)
        .expect("valid reference-only composition carrier");
}

#[test]
fn source_catalog_round_trips_without_scalar_list_coercion() {
    let value = source_catalog();
    let artifact: PlatformSourceCatalogArtifact =
        serde_json::from_value(value.clone()).expect("valid generated carrier");
    assert_eq!(
        serde_json::to_value(artifact).expect("serialize carrier"),
        value
    );
}

#[test]
fn source_catalog_rejects_unknown_root_members() {
    let mut value = source_catalog();
    value["unexpected"] = json!(true);
    assert!(serde_json::from_value::<PlatformSourceCatalogArtifact>(value).is_err());
}
