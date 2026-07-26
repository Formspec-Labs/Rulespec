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

include!(concat!(env!("OUT_DIR"), "/schema_registry.rs"));

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
    orders: HashMap<String, Vec<OrderConstraint>>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
struct OrderConstraint {
    lower: String,
    upper: String,
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
        let mut orders = HashMap::new();
        for (type_iri, class_name, raw) in EMBEDDED_SCHEMAS {
            let parsed: Value =
                serde_json::from_str(raw).map_err(|source| ValidatorError::Parse {
                    class: (*class_name).into(),
                    source,
                })?;
            let class_schema = parsed.get("$defs").and_then(|defs| defs.get(*class_name));
            let class_orders = parse_order_constraints(class_schema).map_err(|message| {
                ValidatorError::Compile {
                    class: (*class_name).into(),
                    message,
                }
            })?;
            let defs = parsed.get("$defs").cloned().unwrap_or(json!({}));
            let wrapped = json!({
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "$ref":    format!("#/$defs/{class_name}"),
                "$defs":   defs,
            });
            let schema = JSONSchema::options()
                .with_draft(Draft::Draft202012)
                .should_validate_formats(true)
                .compile(&wrapped)
                .map_err(|e| ValidatorError::Compile {
                    class: (*class_name).into(),
                    message: e.to_string(),
                })?;
            compiled.insert((*type_iri).into(), schema);
            orders.insert((*type_iri).into(), class_orders);
        }
        Ok(Self { compiled, orders })
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
        let mut errors: Vec<ValidationError> = schema
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
        for order in self.orders.get(type_iri).into_iter().flatten() {
            if violates_order(node.get(&order.lower), node.get(&order.upper)) {
                errors.push(ValidationError {
                    type_iri: type_iri.to_string(),
                    pointer: format!("/{}", order.lower.replace('~', "~0").replace('/', "~1")),
                    message: format!(
                        "{} must be less than or equal to {}",
                        order.lower, order.upper
                    ),
                });
            }
        }
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

    /// Return the vocabulary type IRIs known to this validator.
    pub fn known_type_iris(&self) -> impl Iterator<Item = &str> {
        self.compiled.keys().map(String::as_str)
    }
}

/// True when a same-typed ordered pair is inverted.
///
/// `x-rkaf-order` carries a CUE ordering branch, and the branch is
/// type-agnostic: the same expression guards `rkaf:commentPeriodStart` (an ISO
/// date string) and `oa:start` (an integer offset). Comparing only strings
/// enforced the date intervals and silently skipped every numeric one, leaving
/// this validator weaker than the SHACL `sh:lessThanOrEquals` compiled from the
/// same source line.
///
/// Mixed types are NOT compared: two values of different JSON types have no
/// meaningful order here, and inventing one would produce a verdict the CUE
/// never stated.
fn violates_order(lower: Option<&Value>, upper: Option<&Value>) -> bool {
    match (lower, upper) {
        (Some(Value::String(low)), Some(Value::String(high))) => low > high,
        (Some(Value::Number(low)), Some(Value::Number(high))) => {
            match (low.as_f64(), high.as_f64()) {
                (Some(low), Some(high)) => low > high,
                _ => false,
            }
        }
        _ => false,
    }
}

fn parse_order_constraints(class_schema: Option<&Value>) -> Result<Vec<OrderConstraint>, String> {
    let Some(raw_orders) = class_schema.and_then(|schema| schema.get("x-rkaf-order")) else {
        return Ok(Vec::new());
    };
    let Some(entries) = raw_orders.as_array() else {
        return Err("x-rkaf-order must be an array".into());
    };
    entries
        .iter()
        .map(|entry| {
            let lower = entry
                .get("lower")
                .and_then(Value::as_str)
                .ok_or_else(|| "x-rkaf-order entry requires string lower".to_string())?;
            let upper = entry
                .get("upper")
                .and_then(Value::as_str)
                .ok_or_else(|| "x-rkaf-order entry requires string upper".to_string())?;
            Ok(OrderConstraint {
                lower: lower.into(),
                upper: upper.into(),
            })
        })
        .collect()
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
        assert_eq!(
            errs.iter().filter(|e| e.type_iri == "rkaf:Warrant").count(),
            1
        );
    }

    #[test]
    fn reversed_comment_period_fails() {
        let validator = Validator::new();
        let period = json!({
            "@type": "rkaf:CommentPeriod",
            "rkaf:commentPeriodFor": "urn:rkaf:fixture:proceeding:2060-AV16",
            "rkaf:commentPeriodStart": "2022-02-01",
            "rkaf:commentPeriodEnd": "2022-01-31",
            "prov:wasDerivedFrom": ["urn:rkaf:fixture:evidence:reversed"]
        });

        let errors = validator.validate(&period).unwrap_err();
        assert!(errors.iter().any(|error| {
            error
                .message
                .contains("commentPeriodStart must be less than or equal")
        }));
    }

    #[test]
    fn malformed_comment_period_date_fails() {
        let validator = Validator::new();
        let period = json!({
            "@type": "rkaf:CommentPeriod",
            "rkaf:commentPeriodFor": "urn:rkaf:fixture:proceeding:2060-AV16",
            "rkaf:commentPeriodStart": "2022-13-40",
            "rkaf:commentPeriodEnd": "2022-13-41",
            "prov:wasDerivedFrom": ["urn:rkaf:fixture:evidence:malformed-date"]
        });

        let errors = validator.validate(&period).unwrap_err();
        assert!(errors
            .iter()
            .any(|error| error.message.contains("is not a \"date\"")));
    }
}
