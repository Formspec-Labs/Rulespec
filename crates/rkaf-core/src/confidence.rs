use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum ConfidenceMethod {
    #[serde(rename = "rkaf:model-inference")]
    ModelInference,
    #[serde(rename = "rkaf:human-estimation")]
    HumanEstimation,
    #[serde(rename = "rkaf:review-consensus")]
    ReviewConsensus,
    #[serde(rename = "rkaf:source-class-inheritance")]
    SourceClassInheritance,
    #[serde(rename = "rkaf:rule-based")]
    RuleBased,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum CalibrationStatus {
    #[serde(rename = "rkaf:uncalibrated")]
    Uncalibrated,
    #[serde(rename = "rkaf:calibratedAgainst")]
    CalibratedAgainst,
    #[serde(rename = "rkaf:humanEstimated")]
    HumanEstimated,
    #[serde(rename = "rkaf:consensus")]
    Consensus,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum ScoreCategorical {
    #[serde(rename = "rkaf:very-low")]
    VeryLow,
    #[serde(rename = "rkaf:low")]
    Low,
    #[serde(rename = "rkaf:medium")]
    Medium,
    #[serde(rename = "rkaf:high")]
    High,
    #[serde(rename = "rkaf:very-high")]
    VeryHigh,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ConfidenceRecord {
    #[serde(rename = "@type", default = "ConfidenceRecord::default_type")]
    pub type_: String,
    #[serde(rename = "@id", skip_serializing_if = "Option::is_none", default)]
    pub id: Option<String>,
    #[serde(rename = "rkaf:confidenceMethod")]
    pub confidence_method: ConfidenceMethod,
    #[serde(rename = "rkaf:calibrationStatus")]
    pub calibration_status: CalibrationStatus,
    #[serde(rename = "rkaf:confidenceBasis")]
    pub confidence_basis: String,
    #[serde(rename = "rkaf:generatedBy")]
    pub generated_by: String,
    #[serde(rename = "rkaf:evaluatedAgainst", skip_serializing_if = "Option::is_none", default)]
    pub evaluated_against: Option<String>,
    #[serde(flatten)]
    pub extra: std::collections::BTreeMap<String, serde_json::Value>,
}

impl ConfidenceRecord {
    fn default_type() -> String {
        "rkaf:ConfidenceRecord".into()
    }
}
