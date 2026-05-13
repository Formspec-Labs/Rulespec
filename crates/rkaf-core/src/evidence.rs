use serde::{Deserialize, Serialize};

/// Closed enum: `rkaf:noEvidenceReason` values per v0.2 §5.4. Only meaningful
/// when `rkaf:bindsSourceFragment` is absent — i.e., the EvidenceBinding is
/// declaring *why* no source fragment is needed.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum NoEvidenceReason {
    #[serde(rename = "rkaf:axiomatic")]
    Axiomatic,
    #[serde(rename = "rkaf:inferred-from-warrant-class")]
    InferredFromWarrantClass,
    #[serde(rename = "rkaf:consensus-without-citation")]
    ConsensusWithoutCitation,
    #[serde(rename = "rkaf:permitted-by-safety-label")]
    PermittedBySafetyLabel,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct EvidenceBinding {
    #[serde(rename = "@type", default = "EvidenceBinding::default_type")]
    pub type_: String,
    #[serde(rename = "@id", skip_serializing_if = "Option::is_none", default)]
    pub id: Option<String>,
    #[serde(rename = "rkaf:bindsAssertion")]
    pub binds_assertion: String,
    #[serde(rename = "rkaf:bindsSourceFragment", skip_serializing_if = "Option::is_none", default)]
    pub binds_source_fragment: Option<String>,
    #[serde(rename = "rkaf:noEvidenceReason", skip_serializing_if = "Option::is_none", default)]
    pub no_evidence_reason: Option<NoEvidenceReason>,
    #[serde(flatten)]
    pub extra: std::collections::BTreeMap<String, serde_json::Value>,
}

impl EvidenceBinding {
    fn default_type() -> String {
        "rkaf:EvidenceBinding".into()
    }
}
