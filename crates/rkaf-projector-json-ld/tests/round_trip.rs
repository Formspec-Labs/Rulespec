use rkaf_projector_core::Projector;
use rkaf_projector_json_ld::JsonLdProjector;
use serde_json::json;

fn projector() -> JsonLdProjector {
    JsonLdProjector {
        version: env!("CARGO_PKG_VERSION").into(),
        depth: "D1".into(),
        constraints_compile_script: "tools/constraints_compile.py".into(),
    }
}

#[tokio::test]
async fn attach_then_extract_partitions_by_type_namespace() {
    let p = projector();
    let native = json!({
        "@context": "https://w3id.org/wos/ns/v1",
        "@graph": [{"@id": "wf-1", "@type": "wos:Workflow"}]
    });
    let overlay = json!({
        "@context": "https://rulespec.org/context/rkaf-context-v0.2.jsonld",
        "@graph": [{
            "@id": "a-1",
            "@type": "rkaf:Assertion",
            "rkaf:assertsSubject": "wf-1"
        }]
    });
    let merged = p.attach(native.clone(), overlay.clone()).await.unwrap();
    let (n2, o2) = p.extract(merged).await.unwrap();
    assert_eq!(n2["@graph"], native["@graph"]);
    assert_eq!(n2["@context"], native["@context"]);
    assert_eq!(o2["@graph"], overlay["@graph"]);
}

#[tokio::test]
async fn round_trip_returns_true_on_common_shape() {
    let p = projector();
    let native = json!({
        "@context": "https://w3id.org/wos/ns/v1",
        "@graph": [{"@id": "wf-1", "@type": "wos:Workflow"}]
    });
    let overlay = json!({
        "@context": "https://rulespec.org/context/rkaf-context-v0.2.jsonld",
        "@graph": [{"@id": "a-1", "@type": "rkaf:Assertion"}]
    });
    assert!(p.round_trip(native, overlay).await.unwrap());
}

#[tokio::test]
async fn extract_returns_empty_overlay_when_no_rkaf_node_present() {
    let p = projector();
    let merged = json!({
        "@context": "https://w3id.org/wos/ns/v1",
        "@graph":   [{"@id": "x-1", "@type": "wos:Workflow"}]
    });
    let (_n, o) = p.extract(merged).await.unwrap();
    assert_eq!(o["@graph"], json!([]));
}
