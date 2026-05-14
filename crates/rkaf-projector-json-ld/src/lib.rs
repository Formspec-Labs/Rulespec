//! Rulespec JSON-LD 1.1 projector.
//!
//! Carrier convention: `spec/projectors/json-ld.md`.

use async_trait::async_trait;
use rkaf_projector_core::{Projector, ProjectorError, TargetId};
use serde_json::{json, Map, Value};
use std::path::{Path, PathBuf};

/// The canonical Rulespec v0.2 JSON-LD context URL appended on Attach.
pub const RKAF_CONTEXT: &str = "https://rulespec.org/context/rkaf-context.jsonld";

pub struct JsonLdProjector {
    pub version: String,
    pub depth: String,
    pub constraints_compile_script: PathBuf,
}

impl JsonLdProjector {
    pub fn with_repo_root(repo_root: impl AsRef<Path>) -> Self {
        Self {
            version: env!("CARGO_PKG_VERSION").into(),
            depth: "D1".into(),
            constraints_compile_script: repo_root.as_ref().join("tools/constraints_compile.py"),
        }
    }
}

fn graph_nodes(v: &Value) -> Vec<Value> {
    match v.get("@graph").and_then(|g| g.as_array()) {
        Some(arr) => arr.clone(),
        None => Vec::new(),
    }
}

fn is_overlay_type(node: &Value) -> bool {
    match node.get("@type") {
        Some(Value::String(s)) => s.starts_with("rkaf:"),
        Some(Value::Array(arr)) => arr
            .iter()
            .any(|t| t.as_str().map(|s| s.starts_with("rkaf:")).unwrap_or(false)),
        _ => false,
    }
}

fn append_context(ctx_slot: Option<&Value>, addition: &str) -> Value {
    match ctx_slot {
        None => Value::String(addition.into()),
        Some(Value::String(s)) => json!([s.clone(), addition]),
        Some(Value::Array(arr)) => {
            let mut next = arr.clone();
            next.push(Value::String(addition.into()));
            Value::Array(next)
        }
        Some(other) => json!([other.clone(), addition]),
    }
}

fn strip_context(ctx: Value, target: &str) -> Value {
    match ctx {
        Value::Array(arr) => {
            let kept: Vec<Value> = arr
                .into_iter()
                .filter(|c| c.as_str() != Some(target))
                .collect();
            // Collapse single-element array back to string for byte-equality with common-shape inputs.
            if kept.len() == 1 {
                kept.into_iter().next().unwrap()
            } else {
                Value::Array(kept)
            }
        }
        other => other,
    }
}

#[async_trait]
impl Projector for JsonLdProjector {
    fn target_id(&self) -> TargetId {
        "json-ld"
    }
    fn carrier_convention_version(&self) -> &'static str {
        "0.2.0"
    }

    async fn attach(&self, native: Value, overlay: Value) -> Result<Value, ProjectorError> {
        let native_obj = native
            .as_object()
            .ok_or_else(|| ProjectorError::Attach("native must be an object".into()))?;
        let mut merged: Map<String, Value> = native_obj.clone();
        merged.insert(
            "@context".into(),
            append_context(native_obj.get("@context"), RKAF_CONTEXT),
        );
        let mut graph = graph_nodes(&native);
        for node in graph_nodes(&overlay) {
            graph.push(node);
        }
        merged.insert("@graph".into(), Value::Array(graph));
        Ok(Value::Object(merged))
    }

    async fn extract(&self, merged: Value) -> Result<(Value, Value), ProjectorError> {
        let merged_obj = merged
            .as_object()
            .ok_or_else(|| ProjectorError::Extract("merged must be an object".into()))?;

        let graph = graph_nodes(&merged);
        let (overlay_nodes, native_nodes): (Vec<Value>, Vec<Value>) =
            graph.into_iter().partition(is_overlay_type);

        let native_ctx = merged_obj
            .get("@context")
            .cloned()
            .map(|c| strip_context(c, RKAF_CONTEXT))
            .unwrap_or(Value::Null);

        let mut native_out = Map::new();
        if !native_ctx.is_null() {
            native_out.insert("@context".into(), native_ctx);
        }
        native_out.insert("@graph".into(), Value::Array(native_nodes));

        let overlay_out = json!({
            "@context": RKAF_CONTEXT,
            "@graph":   overlay_nodes,
        });

        Ok((Value::Object(native_out), overlay_out))
    }

    async fn validate(&self, _overlay: Value) -> Result<(), ProjectorError> {
        // Per-node validation (against per-class compiled JSON Schemas keyed by @type) lands with
        // the Layer 5 SDK harness; v0.2 MVP delegates Validate to the JSON Schema projector when
        // composed with a validator. See spec/projectors/json-ld.md §2.
        Ok(())
    }

    async fn derive(&self, profile_cue_path: &str) -> Result<Value, ProjectorError> {
        let out = std::process::Command::new("python3")
            .arg(&self.constraints_compile_script)
            .args(["--in", profile_cue_path, "--target", "cue"])
            .output()
            .map_err(|e| ProjectorError::Derive(format!("spawn constraints_compile: {e}")))?;
        if !out.status.success() {
            return Err(ProjectorError::Derive(
                String::from_utf8_lossy(&out.stderr).into_owned(),
            ));
        }
        // Emit a JSON-LD context fragment pointing at the canonical rkaf context.
        // Full derive (per-profile context narrowing) lands in Plan 10 Studio cutover.
        Ok(json!({
            "@context-derived-from": profile_cue_path,
            "@context":              RKAF_CONTEXT,
            "cue-source-length":     String::from_utf8_lossy(&out.stdout).len(),
        }))
    }
}
