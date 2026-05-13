use crate::ai_lineage::AiLineage;
use serde::{Deserialize, Serialize};

/// Closed enum: `rkaf:assertionOrigin` values per v0.2 §5.3. The "AI-touched"
/// subset (`aiSuggested`, `aiPromoted`, `humanQualified`, `humanRevalidation`)
/// triggers the Pattern-C constraint requiring `rkaf:hasAILineage`.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum AssertionOrigin {
    #[serde(rename = "rkaf:humanAuthored")]
    HumanAuthored,
    #[serde(rename = "rkaf:humanQualified")]
    HumanQualified,
    #[serde(rename = "rkaf:humanRevalidation")]
    HumanRevalidation,
    #[serde(rename = "rkaf:aiSuggested")]
    AiSuggested,
    #[serde(rename = "rkaf:aiPromoted")]
    AiPromoted,
}

impl AssertionOrigin {
    /// Whether this origin is in the "AI-touched" subset that requires an
    /// `rkaf:hasAILineage` record per the Pattern-C constraint.
    pub fn is_ai_touched(&self) -> bool {
        matches!(
            self,
            Self::AiSuggested | Self::AiPromoted | Self::HumanQualified | Self::HumanRevalidation
        )
    }
}

/// `rkaf:Assertion` — the central proposition: subject S has property P with
/// value V, justified by Warrant W, witnessed by Evidence E, with Confidence C.
///
/// The compiled JSON Schema declares only `@type`, `assertionOrigin`, and
/// `hasAILineage` as recognized properties — additional properties (like
/// `assertsSubject`, `hasWarrant`, etc.) are valid JSON-LD but are not
/// type-checked here. Use the `extra` field to carry them through round-trip.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Assertion {
    #[serde(rename = "@type", default = "Assertion::default_type")]
    pub type_: String,
    #[serde(rename = "@id", skip_serializing_if = "Option::is_none", default)]
    pub id: Option<String>,
    #[serde(rename = "rkaf:assertionOrigin")]
    pub assertion_origin: AssertionOrigin,
    #[serde(rename = "rkaf:hasAILineage", skip_serializing_if = "Option::is_none", default)]
    pub has_ai_lineage: Option<AiLineage>,
    /// Catch-all for additional rkaf:* properties (assertsSubject, hasWarrant,
    /// hasEvidence, hasConfidence, hasAccessScope, ...) preserved through
    /// round-trip but not type-checked.
    #[serde(flatten)]
    pub extra: std::collections::BTreeMap<String, serde_json::Value>,
}

impl Assertion {
    fn default_type() -> String {
        "rkaf:Assertion".into()
    }

    pub fn new(origin: AssertionOrigin) -> Self {
        Self {
            type_: Self::default_type(),
            id: None,
            assertion_origin: origin,
            has_ai_lineage: None,
            extra: Default::default(),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn round_trip_with_extras_preserves_asserts_subject() {
        let mut a = Assertion::new(AssertionOrigin::HumanAuthored);
        a.extra.insert(
            "rkaf:assertsSubject".into(),
            json!("snap-2026-04-redet-0001"),
        );
        let v = serde_json::to_value(&a).unwrap();
        assert_eq!(v["rkaf:assertsSubject"], "snap-2026-04-redet-0001");
        let parsed: Assertion = serde_json::from_value(v).unwrap();
        assert_eq!(parsed, a);
    }

    #[test]
    fn ai_touched_classification() {
        assert!(AssertionOrigin::AiSuggested.is_ai_touched());
        assert!(AssertionOrigin::AiPromoted.is_ai_touched());
        assert!(AssertionOrigin::HumanQualified.is_ai_touched());
        assert!(AssertionOrigin::HumanRevalidation.is_ai_touched());
        assert!(!AssertionOrigin::HumanAuthored.is_ai_touched());
    }
}
