//! Rulespec OpenAPI 3.1 projector.
//!
//! Carrier convention: `spec/projectors/openapi-v0.2.md`.

use async_trait::async_trait;
use rkaf_projector_core::{Projector, ProjectorError, TargetId};
use serde_json::{json, Map, Value};
use std::path::{Path, PathBuf};

pub struct OpenApiProjector {
    pub version: String,
    pub depth: String,
    pub constraints_compile_script: PathBuf,
}

impl OpenApiProjector {
    pub fn with_repo_root(repo_root: impl AsRef<Path>) -> Self {
        Self {
            version: "0.2.0-pre.5".into(),
            depth: "D1".into(),
            constraints_compile_script: repo_root
                .as_ref()
                .join("tools/constraints_compile.py"),
        }
    }
}

#[async_trait]
impl Projector for OpenApiProjector {
    fn target_id(&self) -> TargetId {
        "openapi"
    }
    fn carrier_convention_version(&self) -> &'static str {
        "0.2.0"
    }

    async fn attach(
        &self,
        native: Value,
        overlay: Value,
    ) -> Result<Value, ProjectorError> {
        let mut doc = native
            .as_object()
            .ok_or_else(|| ProjectorError::Attach("native must be an OpenAPI object".into()))?
            .clone();
        if let Some(existing) = doc.get("x-rkaf") {
            if !existing
                .get("rkaf-version")
                .map(|v| v.is_string())
                .unwrap_or(false)
            {
                return Err(ProjectorError::Attach(
                    "x-rkaf already present with non-Rulespec payload".into(),
                ));
            }
        }
        doc.insert(
            "x-rkaf".into(),
            json!({
                "rkaf-version": self.version,
                "rkaf-depth":   self.depth,
                "rkaf:overlay": overlay,
            }),
        );
        Ok(Value::Object(doc))
    }

    async fn extract(
        &self,
        merged: Value,
    ) -> Result<(Value, Value), ProjectorError> {
        let mut doc = merged
            .as_object()
            .ok_or_else(|| ProjectorError::Extract("merged must be an OpenAPI object".into()))?
            .clone();
        let xrkaf = doc
            .remove("x-rkaf")
            .ok_or_else(|| ProjectorError::Extract("no document-level x-rkaf".into()))?;
        let xrkaf_obj = xrkaf
            .as_object()
            .ok_or_else(|| ProjectorError::Extract("x-rkaf must be an object".into()))?;
        if !xrkaf_obj.contains_key("rkaf-version") {
            return Err(ProjectorError::Extract(
                "x-rkaf missing rkaf-version; refusing to interpret as Rulespec overlay".into(),
            ));
        }
        let overlay = xrkaf_obj
            .get("rkaf:overlay")
            .cloned()
            .ok_or_else(|| ProjectorError::Extract("x-rkaf missing rkaf:overlay".into()))?;
        Ok((Value::Object(doc), overlay))
    }

    async fn validate(&self, _overlay: Value) -> Result<(), ProjectorError> {
        // Delegated to the JSON Schema projector when composed (the overlay payload is identical).
        Ok(())
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
        let js: Value = serde_json::from_slice(&out.stdout)
            .map_err(|e| ProjectorError::Derive(format!("parse json-schema: {e}")))?;
        let defs = js.get("$defs").cloned().unwrap_or(json!({}));
        let title = js
            .get("title")
            .and_then(|v| v.as_str())
            .unwrap_or("derived")
            .to_string();

        let mut info = Map::new();
        info.insert("title".into(), Value::String(format!("Derived: {title}")));
        info.insert(
            "version".into(),
            Value::String(self.version.clone()),
        );
        info.insert(
            "description".into(),
            Value::String(format!(
                "OpenAPI 3.1 document derived from Rulespec profile `{profile_cue_path}` via tools/constraints_compile.py."
            )),
        );

        let mut doc = Map::new();
        doc.insert("openapi".into(), Value::String("3.1.0".into()));
        doc.insert("info".into(), Value::Object(info));
        doc.insert("paths".into(), json!({}));
        doc.insert(
            "components".into(),
            json!({ "schemas": defs }),
        );
        Ok(Value::Object(doc))
    }
}
