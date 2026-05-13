//! Rulespec v0.2 schema validator with embedded compiled schemas.
//!
//! ```no_run
//! use rkaf_validate::Validator;
//! use serde_json::json;
//!
//! let v = Validator::new();
//! let doc = json!({
//!     "@type": "rkaf:Warrant",
//!     "rkaf:warrantKind": "rkaf:statutory",
//!     "rkaf:warrantFamily": "rkaf:legal"
//! });
//! assert!(v.validate(&doc).is_ok());
//! ```
//!
//! Validation operates on JSON-LD node-shaped values. To validate a multi-node
//! document (an `@graph` envelope), call [`Validator::validate_document`] which
//! walks every node and aggregates errors.

use jsonschema::{Draft, JSONSchema};
use serde_json::{json, Value};
use std::collections::HashMap;

/// Class identifier (`@type` IRI) → embedded JSON Schema source.
///
/// Each entry is the full schema file emitted by `tools/constraints_compile.py
/// --target json-schema`. We construct a top-level `$ref` wrapper at load time
/// to make each class independently validatable.
const EMBEDDED_SCHEMAS: &[(&str, &str, &str)] = &[
    (
        "rkaf:Assertion",
        "Assertion",
        include_str!("../../../compiled/json-schema/core/assertion.schema.json"),
    ),
    (
        "rkaf:Warrant",
        "Warrant",
        include_str!("../../../compiled/json-schema/core/warrant.schema.json"),
    ),
    (
        "rkaf:EvidenceBinding",
        "EvidenceBinding",
        include_str!("../../../compiled/json-schema/core/evidence-binding.schema.json"),
    ),
    (
        "rkaf:ConfidenceRecord",
        "ConfidenceRecord",
        include_str!("../../../compiled/json-schema/core/confidence-record.schema.json"),
    ),
    (
        "rkaf:AccessScope",
        "AccessScope",
        include_str!("../../../compiled/json-schema/core/access-scope.schema.json"),
    ),
    (
        "rkaf:AILineage",
        "AILineage",
        include_str!("../../../compiled/json-schema/core/ai-lineage.schema.json"),
    ),
    (
        "rkaf:Artifact",
        "Artifact",
        include_str!("../../../compiled/json-schema/core/artifact.schema.json"),
    ),
    (
        "rkaf:SourceFragment",
        "SourceFragment",
        include_str!("../../../compiled/json-schema/core/source-fragment.schema.json"),
    ),
    (
        "rkaf:Authority",
        "Authority",
        include_str!("../../../compiled/json-schema/core/authority.schema.json"),
    ),
    (
        "rkaf:Attestation",
        "Attestation",
        include_str!("../../../compiled/json-schema/core/attestation.schema.json"),
    ),
    (
        "rkaf:LocalAdoption",
        "LocalAdoption",
        include_str!("../../../compiled/json-schema/core/local-adoption.schema.json"),
    ),
    (
        "rkaf:ApplicabilityScope",
        "ApplicabilityScope",
        include_str!("../../../compiled/json-schema/core/applicability-scope.schema.json"),
    ),
    (
        "rkaf:EffectivePeriod",
        "EffectivePeriod",
        include_str!("../../../compiled/json-schema/core/effective-period.schema.json"),
    ),
    (
        "rkaf:LifecycleEvent",
        "LifecycleEvent",
        include_str!("../../../compiled/json-schema/core/lifecycle-event.schema.json"),
    ),
    (
        "rkaf:RegisteredConcept",
        "RegisteredConcept",
        include_str!("../../../compiled/json-schema/core/concept.schema.json"),
    ),
    (
        "rkaf:LocalConcept",
        "LocalConcept",
        include_str!("../../../compiled/json-schema/core/concept.schema.json"),
    ),
    (
        "rkaf:ConceptMapping",
        "ConceptMapping",
        include_str!("../../../compiled/json-schema/core/concept-mapping.schema.json"),
    ),
    (
        "rkaf:MappingApplicabilityContext",
        "MappingApplicabilityContext",
        include_str!("../../../compiled/json-schema/core/concept-mapping.schema.json"),
    ),
    (
        "rkaf:ConceptResolutionResult",
        "ConceptResolutionResult",
        include_str!(
            "../../../compiled/json-schema/core/concept-resolution-result.schema.json"
        ),
    ),
    (
        "rkaf:BridgeValidationResult",
        "BridgeValidationResult",
        include_str!(
            "../../../compiled/json-schema/core/bridge-validation-result.schema.json"
        ),
    ),
    (
        "rkaf:BridgeConsumerRegistration",
        "BridgeConsumerRegistration",
        include_str!(
            "../../../compiled/json-schema/core/bridge-consumer-registration.schema.json"
        ),
    ),
    (
        "rkaf:RegistryConflict",
        "RegistryConflict",
        include_str!("../../../compiled/json-schema/core/registry-conflict.schema.json"),
    ),
    (
        "rkaf:Justification",
        "Justification",
        include_str!("../../../compiled/json-schema/core/justification.schema.json"),
    ),
    // Plan 7b — primitives the behavior contracts depend on.
    (
        "rkaf:PointInTimeException",
        "PointInTimeException",
        include_str!("../../../compiled/json-schema/core/point-in-time-exception.schema.json"),
    ),
    (
        "rkaf:GeneratedWorkProduct",
        "GeneratedWorkProduct",
        include_str!("../../../compiled/json-schema/core/generated-work-product.schema.json"),
    ),
    (
        "rkaf:RevalidationEvent",
        "RevalidationEvent",
        include_str!("../../../compiled/json-schema/core/revalidation-event.schema.json"),
    ),
    (
        "rkaf:RevalidationClosureEvent",
        "RevalidationClosureEvent",
        include_str!("../../../compiled/json-schema/core/revalidation-event.schema.json"),
    ),
    (
        "rkaf:ConsumerEffectiveDeclaration",
        "ConsumerEffectiveDeclaration",
        include_str!("../../../compiled/json-schema/core/consumer-effective-declaration.schema.json"),
    ),
    (
        "rkaf:BridgeIssueAttestationContract",
        "BridgeIssueAttestationContract",
        include_str!("../../../compiled/json-schema/core/bridge-issue-attestation-contract.schema.json"),
    ),
];

/// A single validation error, paired with the validating class's `@type` IRI
/// and the JSON pointer at which the error was discovered.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize)]
pub struct ValidationError {
    pub type_iri: String,
    pub pointer: String,
    pub message: String,
}

#[derive(Debug, thiserror::Error)]
pub enum ValidatorError {
    #[error("validator init: parse embedded schema for `{class}`: {source}")]
    Parse {
        class: String,
        source: serde_json::Error,
    },
    #[error("validator init: compile embedded schema for `{class}`: {message}")]
    Compile { class: String, message: String },
}

pub struct Validator {
    compiled: HashMap<String, JSONSchema>,
}

impl Validator {
    /// Build a validator with every v0.2 class loaded. Panics if an embedded
    /// schema fails to parse or compile — this is a programmer error in the
    /// crate, not a runtime error in the caller.
    pub fn new() -> Self {
        Self::try_new().expect("rkaf-validate: embedded schemas must compile")
    }

    /// Fallible constructor used by tests and by callers that want explicit
    /// failure handling.
    pub fn try_new() -> Result<Self, ValidatorError> {
        let mut compiled = HashMap::new();
        for (type_iri, class_name, raw) in EMBEDDED_SCHEMAS {
            let parsed: Value =
                serde_json::from_str(raw).map_err(|source| ValidatorError::Parse {
                    class: (*class_name).into(),
                    source,
                })?;
            let defs = parsed.get("$defs").cloned().unwrap_or(json!({}));
            let wrapped = json!({
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "$ref":    format!("#/$defs/{class_name}"),
                "$defs":   defs,
            });
            let schema = JSONSchema::options()
                .with_draft(Draft::Draft202012)
                .compile(&wrapped)
                .map_err(|e| ValidatorError::Compile {
                    class: (*class_name).into(),
                    message: e.to_string(),
                })?;
            compiled.insert((*type_iri).into(), schema);
        }
        Ok(Self { compiled })
    }

    /// Validate a single JSON-LD node against the schema for its `@type` IRI.
    /// Returns `Ok(())` on a match with no violations, or a non-empty error
    /// list otherwise. Nodes carrying a `@type` outside the v0.2 vocabulary
    /// pass silently — they're outside this validator's contract.
    pub fn validate(&self, node: &Value) -> Result<(), Vec<ValidationError>> {
        let Some(type_iri) = node.get("@type").and_then(|t| t.as_str()) else {
            return Ok(()); // no @type — outside our contract (e.g., a literal map)
        };
        let Some(schema) = self.compiled.get(type_iri) else {
            return Ok(()); // @type is not a v0.2 rkaf:* class — pass silently
        };
        let errors: Vec<ValidationError> = schema
            .validate(node)
            .err()
            .into_iter()
            .flatten()
            .map(|e| ValidationError {
                type_iri: type_iri.to_string(),
                pointer: e.instance_path.to_string(),
                message: e.to_string(),
            })
            .collect();
        if errors.is_empty() {
            Ok(())
        } else {
            Err(errors)
        }
    }

    /// Validate every node in a document. If the document carries a `@graph`
    /// array, every node is validated and errors are aggregated. Otherwise the
    /// document is treated as a single node.
    pub fn validate_document(&self, doc: &Value) -> Result<(), Vec<ValidationError>> {
        let mut all_errors = Vec::new();
        if let Some(graph) = doc.get("@graph").and_then(|g| g.as_array()) {
            for node in graph {
                if let Err(errs) = self.validate(node) {
                    all_errors.extend(errs);
                }
            }
        } else if let Err(errs) = self.validate(doc) {
            all_errors.extend(errs);
        }
        if all_errors.is_empty() {
            Ok(())
        } else {
            Err(all_errors)
        }
    }
}

impl Default for Validator {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn warrant_minimal_passes() {
        let v = Validator::new();
        let w = json!({
            "@type": "rkaf:Warrant",
            "rkaf:warrantKind": "rkaf:statutory",
            "rkaf:warrantFamily": "rkaf:legal"
        });
        v.validate(&w).expect("minimal warrant should validate");
    }

    #[test]
    fn warrant_missing_kind_fails() {
        let v = Validator::new();
        let w = json!({
            "@type": "rkaf:Warrant",
            "rkaf:warrantFamily": "rkaf:legal"
        });
        let errs = v.validate(&w).unwrap_err();
        assert!(!errs.is_empty());
        assert!(errs.iter().any(|e| e.message.contains("warrantKind")));
    }

    #[test]
    fn unknown_type_passes() {
        let v = Validator::new();
        let doc = json!({"@type": "wos:Workflow", "id": "wf-1"});
        v.validate(&doc).unwrap();
    }

    #[test]
    fn graph_envelope_aggregates_errors() {
        let v = Validator::new();
        let doc = json!({
            "@graph": [
                {"@type": "rkaf:Warrant", "rkaf:warrantKind": "rkaf:statutory", "rkaf:warrantFamily": "rkaf:legal"},
                {"@type": "rkaf:Warrant", "rkaf:warrantFamily": "rkaf:legal"}
            ]
        });
        let errs = v.validate_document(&doc).unwrap_err();
        assert_eq!(errs.iter().filter(|e| e.type_iri == "rkaf:Warrant").count(), 1);
    }
}
