//! Rulespec Layer 4 — Projector trait per source spec §8.1.
//!
//! Every projector implements five operations: Attach, Extract, Validate,
//! RoundTrip (default), Derive. Round-trip parity (Attach → Extract is the
//! identity transform) is the release-gating invariant.

use async_trait::async_trait;
use serde_json::Value;
use std::path::{Path, PathBuf};

#[derive(Debug, thiserror::Error)]
pub enum ProjectorError {
    #[error("attach: {0}")]
    Attach(String),
    #[error("extract: {0}")]
    Extract(String),
    #[error("validate: {0}")]
    Validate(String),
    #[error("derive: {0}")]
    Derive(String),
}

pub type TargetId = &'static str;

/// Validate every Rulespec node in an overlay against every generated JSON
/// Schema that targets its `@type`. Projector carriers differ, but the overlay
/// payload and Layer 2 meaning do not; this is the shared executable path used
/// by JSON Schema, JSON-LD, and OpenAPI projectors.
pub fn validate_overlay_with_schema_root(
    overlay: &Value,
    schema_root: &Path,
) -> Result<(), ProjectorError> {
    let mut schema_paths = Vec::new();
    collect_schema_paths(schema_root, &mut schema_paths)?;
    schema_paths.sort();

    let mut schemas = Vec::new();
    for path in schema_paths {
        let bytes = std::fs::read(&path)
            .map_err(|e| ProjectorError::Validate(format!("read {}: {e}", path.display())))?;
        let schema: Value = serde_json::from_slice(&bytes)
            .map_err(|e| ProjectorError::Validate(format!("parse {}: {e}", path.display())))?;
        schemas.push((path, schema));
    }

    let nodes: Vec<&Value> = match overlay.get("@graph").and_then(Value::as_array) {
        Some(graph) => graph.iter().filter(|node| node.is_object()).collect(),
        None if overlay.is_object() && overlay.get("@type").is_some() => vec![overlay],
        None => {
            return Err(ProjectorError::Validate(
                "overlay must be a typed object or carry an @graph array".into(),
            ));
        }
    };

    let mut errors = Vec::new();
    for node in nodes {
        let node_id = node
            .get("@id")
            .and_then(Value::as_str)
            .unwrap_or("<anonymous>");
        let types: Vec<&str> = match node.get("@type") {
            Some(Value::String(value)) => vec![value],
            Some(Value::Array(values)) => values.iter().filter_map(Value::as_str).collect(),
            _ => {
                errors.push(format!("{node_id}: missing string @type"));
                continue;
            }
        };
        for type_iri in types.into_iter().filter(|value| value.starts_with("rkaf:")) {
            let mut matched = 0usize;
            for (path, schema) in &schemas {
                let Some(defs) = schema.get("$defs").and_then(Value::as_object) else {
                    continue;
                };
                for (name, definition) in defs {
                    let target_type = definition
                        .get("properties")
                        .and_then(|properties| properties.get("@type"))
                        .and_then(|type_schema| type_schema.get("const"))
                        .and_then(Value::as_str);
                    if target_type != Some(type_iri) {
                        continue;
                    }
                    matched += 1;
                    let wrapper = serde_json::json!({
                        "$schema": "https://json-schema.org/draft/2020-12/schema",
                        "$defs": defs,
                        "$ref": format!("#/$defs/{name}"),
                    });
                    let validator = jsonschema::JSONSchema::options()
                        .with_draft(jsonschema::Draft::Draft202012)
                        .compile(&wrapper)
                        .map_err(|e| {
                            ProjectorError::Validate(format!(
                                "compile {}#/$defs/{name}: {e}",
                                path.display()
                            ))
                        })?;
                    if let Err(validation) = validator.validate(node) {
                        for error in validation {
                            errors.push(format!(
                                "{node_id} ({type_iri}) via {}#/$defs/{name}: {error}",
                                path.display()
                            ));
                        }
                    };
                }
            }
            if matched == 0 {
                errors.push(format!("{node_id}: no generated schema targets {type_iri}"));
            }
        }
    }

    if errors.is_empty() {
        Ok(())
    } else {
        Err(ProjectorError::Validate(errors.join("; ")))
    }
}

fn collect_schema_paths(directory: &Path, paths: &mut Vec<PathBuf>) -> Result<(), ProjectorError> {
    let entries = std::fs::read_dir(directory).map_err(|e| {
        ProjectorError::Validate(format!(
            "read schema directory {}: {e}",
            directory.display()
        ))
    })?;
    for entry in entries {
        let entry = entry.map_err(|e| ProjectorError::Validate(e.to_string()))?;
        let path = entry.path();
        if path.is_dir() {
            collect_schema_paths(&path, paths)?;
        } else if path
            .file_name()
            .and_then(|name| name.to_str())
            .map(|name| name.ends_with(".schema.json"))
            .unwrap_or(false)
        {
            paths.push(path);
        }
    }
    Ok(())
}

#[async_trait]
pub trait Projector: Send + Sync {
    fn target_id(&self) -> TargetId;
    fn carrier_convention_version(&self) -> &'static str;

    /// Embed a Rulespec overlay into a native artifact per the target's carrier convention.
    async fn attach(&self, native: Value, overlay: Value) -> Result<Value, ProjectorError>;

    /// Recover `(native, overlay)` from a merged artifact, lossless within the contract.
    async fn extract(&self, merged: Value) -> Result<(Value, Value), ProjectorError>;

    /// Validate that the overlay is well-formed per Layer 2 constraints.
    async fn validate(&self, overlay: Value) -> Result<(), ProjectorError>;

    /// Round-trip parity: `attach → extract` MUST be the identity transform.
    async fn round_trip(&self, native: Value, overlay: Value) -> Result<bool, ProjectorError> {
        let merged = self.attach(native.clone(), overlay.clone()).await?;
        let (n2, o2) = self.extract(merged).await?;
        Ok(n2 == native && o2 == overlay)
    }

    /// Given a profile (Vocabulary subset expressed as CUE), generate a native schema
    /// in the target format that expresses the profile's content.
    async fn derive(&self, profile_cue_path: &str) -> Result<Value, ProjectorError>;
}
