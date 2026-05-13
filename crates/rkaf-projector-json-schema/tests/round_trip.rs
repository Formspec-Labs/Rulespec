use rkaf_projector_core::Projector;
use rkaf_projector_json_schema::JsonSchemaProjector;
use serde_json::json;

fn projector() -> JsonSchemaProjector {
    JsonSchemaProjector {
        depth: "D1".into(),
        version: env!("CARGO_PKG_VERSION").into(),
        overlay_validator_schema_path: None,
        constraints_compile_script: "tools/constraints_compile.py".into(),
    }
}

#[tokio::test]
async fn attach_then_extract_is_identity() {
    let p = projector();
    let native = json!({"@type": "wos:Workflow", "id": "wf-1"});
    let overlay = json!({"@type": "rkaf:Assertion", "rkaf:assertsSubject": "wf-1"});
    assert!(p.round_trip(native, overlay).await.unwrap());
}

#[tokio::test]
async fn attach_refuses_to_overwrite_existing_x_rkaf() {
    let p = projector();
    let native = json!({"x-rkaf": {"rkaf-version": "0.1.0", "rkaf:overlay": {}}});
    let overlay = json!({});
    let err = p.attach(native, overlay).await.unwrap_err();
    assert!(err.to_string().contains("refusing to overwrite"));
}

#[tokio::test]
async fn extract_refuses_non_rulespec_x_rkaf() {
    let p = projector();
    let merged = json!({"x-rkaf": {"some-other-vendor": true}});
    let err = p.extract(merged).await.unwrap_err();
    assert!(err.to_string().contains("rkaf-version"));
}
