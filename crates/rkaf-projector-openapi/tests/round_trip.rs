use rkaf_projector_core::Projector;
use rkaf_projector_openapi::OpenApiProjector;
use serde_json::json;

fn projector() -> OpenApiProjector {
    OpenApiProjector {
        version: env!("CARGO_PKG_VERSION").into(),
        depth: "D1".into(),
        constraints_compile_script: "tools/constraints_compile.py".into(),
    }
}

#[tokio::test]
async fn attach_then_extract_is_identity_at_doc_level() {
    let p = projector();
    let native = json!({
        "openapi": "3.1.0",
        "info": {"title": "T", "version": "1.0"},
        "paths": {}
    });
    let overlay = json!({"@type": "rkaf:Assertion"});
    assert!(p.round_trip(native, overlay).await.unwrap());
}

#[tokio::test]
async fn attach_refuses_existing_non_rulespec_x_rkaf() {
    let p = projector();
    let native = json!({"openapi": "3.1.0", "x-rkaf": {"other": true}});
    let err = p.attach(native, json!({})).await.unwrap_err();
    assert!(err.to_string().contains("non-Rulespec"));
}

#[tokio::test]
async fn extract_refuses_missing_rkaf_version() {
    let p = projector();
    let merged = json!({"openapi": "3.1.0", "x-rkaf": {"rkaf:overlay": {}}});
    let err = p.extract(merged).await.unwrap_err();
    assert!(err.to_string().contains("rkaf-version"));
}
