//! Rulespec JSON Schema 2020-12 projector.
//!
//! Carrier convention: `spec/projectors/json-schema-v0.2.md`.

use async_trait::async_trait;
use rkaf_projector_core::{Projector, ProjectorError, TargetId};
use serde_json::{json, Value};
use std::path::{Path, PathBuf};

pub struct JsonSchemaProjector {
    pub depth: String,
    pub version: String,
    /// Optional path to a compiled JSON Schema 2020-12 document used by `validate`.
    /// `None` means `validate` returns `Ok(())` without checking — useful in fixture
    /// tests that exercise Attach/Extract/RoundTrip only.
    pub overlay_validator_schema_path: Option<PathBuf>,
    /// Path to the `tools/constraints_compile.py` script used by `derive`.
    pub constraints_compile_script: PathBuf,
}

impl JsonSchemaProjector {
    /// Construct with default paths anchored at the Rulespec repo root.
    pub fn with_repo_root(repo_root: impl AsRef<Path>) -> Self {
        let root = repo_root.as_ref();
        Self {
            depth: "D1".into(),
            version: env!("CARGO_PKG_VERSION").into(),
            overlay_validator_schema_path: None,
            constraints_compile_script: root.join("tools/constraints_compile.py"),
        }
    }
}

#[async_trait]
impl Projector for JsonSchemaProjector {
    fn target_id(&self) -> TargetId {
        "json-schema"
    }
    fn carrier_convention_version(&self) -> &'static str {
        "0.2.0"
    }

    async fn attach(
        &self,
        native: Value,
        overlay: Value,
    ) -> Result<Value, ProjectorError> {
        let mut merged = native
            .as_object()
            .ok_or_else(|| ProjectorError::Attach("native must be a JSON object".into()))?
            .clone();
        if merged.contains_key("x-rkaf") {
            return Err(ProjectorError::Attach(
                "native already carries x-rkaf; refusing to overwrite".into(),
            ));
        }
        merged.insert(
            "x-rkaf".into(),
            json!({
                "rkaf-version": self.version,
                "rkaf-depth":   self.depth,
                "rkaf:overlay": overlay,
            }),
        );
        Ok(Value::Object(merged))
    }

    async fn extract(
        &self,
        merged: Value,
    ) -> Result<(Value, Value), ProjectorError> {
        let mut obj = merged
            .as_object()
            .ok_or_else(|| ProjectorError::Extract("merged must be a JSON object".into()))?
            .clone();
        let xrkaf = obj
            .remove("x-rkaf")
            .ok_or_else(|| ProjectorError::Extract("no x-rkaf key".into()))?;
        let xrkaf_obj = xrkaf
            .as_object()
            .ok_or_else(|| ProjectorError::Extract("x-rkaf must be an object".into()))?;
        if !xrkaf_obj.contains_key("rkaf-version") {
            return Err(ProjectorError::Extract(
                "x-rkaf missing rkaf-version; refusing to interpret as Rulespec overlay"
                    .into(),
            ));
        }
        let overlay = xrkaf_obj
            .get("rkaf:overlay")
            .cloned()
            .ok_or_else(|| ProjectorError::Extract("x-rkaf missing rkaf:overlay".into()))?;
        Ok((Value::Object(obj), overlay))
    }

    async fn validate(&self, overlay: Value) -> Result<(), ProjectorError> {
        let Some(schema_path) = &self.overlay_validator_schema_path else {
            return Ok(());
        };
        let schema_bytes = std::fs::read(schema_path)
            .map_err(|e| ProjectorError::Validate(format!("read schema: {e}")))?;
        let schema: Value = serde_json::from_slice(&schema_bytes)
            .map_err(|e| ProjectorError::Validate(format!("parse schema: {e}")))?;
        let validator = jsonschema::JSONSchema::options()
            .with_draft(jsonschema::Draft::Draft202012)
            .compile(&schema)
            .map_err(|e| ProjectorError::Validate(format!("compile schema: {e}")))?;
        let errors: Vec<String> = validator
            .validate(&overlay)
            .err()
            .into_iter()
            .flatten()
            .map(|e| e.to_string())
            .collect();
        if errors.is_empty() {
            Ok(())
        } else {
            Err(ProjectorError::Validate(errors.join("; ")))
        }
    }

    async fn derive(&self, profile_cue_path: &str) -> Result<Value, ProjectorError> {
        let out = std::process::Command::new("python3")
            .arg(&self.constraints_compile_script)
            .args(["--in", profile_cue_path, "--target", "json-schema"])
            .output()
            .map_err(|e| ProjectorError::Derive(format!("spawn constraints_compile: {e}")))?;
        if !out.status.success() {
            return Err(ProjectorError::Derive(
                String::from_utf8_lossy(&out.stderr).into_owned(),
            ));
        }
        serde_json::from_slice(&out.stdout)
            .map_err(|e| ProjectorError::Derive(format!("parse derive output: {e}")))
    }
}
