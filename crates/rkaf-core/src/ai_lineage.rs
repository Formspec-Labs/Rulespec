use serde::{Deserialize, Serialize};

/// `rkaf:AILineage` — the provenance record for an AI-touched Assertion. All
/// fields except `seed` and `humanRationale` are required (per the compiled
/// JSON Schema). Pattern-C cross-property invariant: any Assertion whose
/// `assertionOrigin` is in the AI-touched set MUST carry an AILineage.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct AiLineage {
    #[serde(rename = "@type", default = "AiLineage::default_type")]
    pub type_: String,
    #[serde(rename = "@id", skip_serializing_if = "Option::is_none", default)]
    pub id: Option<String>,
    #[serde(rename = "rkaf:modelId")]
    pub model_id: String,
    #[serde(rename = "rkaf:modelVersion")]
    pub model_version: String,
    #[serde(rename = "rkaf:promptTemplateRef")]
    pub prompt_template_ref: String,
    #[serde(rename = "rkaf:temperature")]
    pub temperature: f64,
    #[serde(rename = "rkaf:seed", skip_serializing_if = "Option::is_none", default)]
    pub seed: Option<i64>,
    #[serde(rename = "rkaf:inputContextHash")]
    pub input_context_hash: String,
    #[serde(rename = "rkaf:humanApprover")]
    pub human_approver: String,
    #[serde(rename = "rkaf:humanRationale", skip_serializing_if = "Option::is_none", default)]
    pub human_rationale: Option<String>,
    #[serde(flatten)]
    pub extra: std::collections::BTreeMap<String, serde_json::Value>,
}

impl AiLineage {
    fn default_type() -> String {
        "rkaf:AILineage".into()
    }
}
