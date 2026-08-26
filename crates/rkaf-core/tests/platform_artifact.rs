//! Generated platform artifact carrier checks.

// Rust guideline compliant 2026-02-21

use rkaf_core::generated::platform::platform_artifact::PlatformArtifact;
use serde_json::json;

fn platform_artifact() -> serde_json::Value {
    json!({
        "artifactDigest": format!("sha256:{}", "0".repeat(64)),
        "counts": {
            "manifestCount": 1,
            "memberCount": 1,
            "totalMemberByteSize": 10,
            "totalRecordCount": 1
        },
        "format": "spicy-artifact",
        "formatVersion": "1.0",
        "inputs": [],
        "kind": "test-artifact",
        "logicalId": format!("urn:spicy:artifact:test-artifact:{}", "1".repeat(64)),
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
        "producer": {
            "implementationId": format!("git:https://example.test/product@{}", "3".repeat(40)),
            "product": "test-product",
            "verifierId": "urn:example:verifier",
            "verifierImplementationId": format!("pkg:pypi/rulespec-artifacts@1.0.0?sha256:{}", "4".repeat(64)),
            "verifierVersion": "1.0.0"
        },
        "spec": {
            "nested": {"accepted": true},
            "profile": "test/1"
        }
    })
}

#[test]
fn product_neutral_artifact_round_trips_with_an_opaque_spec() {
    let value = platform_artifact();
    let artifact: PlatformArtifact =
        serde_json::from_value(value.clone()).expect("valid generated carrier");
    assert_eq!(
        serde_json::to_value(artifact).expect("serialize carrier"),
        value
    );
}

#[test]
fn artifact_rejects_unknown_root_members() {
    let mut value = platform_artifact();
    value["unexpected"] = json!(true);
    assert!(serde_json::from_value::<PlatformArtifact>(value).is_err());
}
