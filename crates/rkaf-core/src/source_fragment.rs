use serde::{Deserialize, Serialize};

/// Closed enum: `rkaf:selectorKind` values per v0.2 §5.7. OA-aligned.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum SelectorKind {
    #[serde(rename = "oa:FragmentSelector")]
    Fragment,
    #[serde(rename = "oa:TextQuoteSelector")]
    TextQuote,
    #[serde(rename = "oa:TextPositionSelector")]
    TextPosition,
    #[serde(rename = "oa:RangeSelector")]
    Range,
    #[serde(rename = "oa:XPathSelector")]
    XPath,
    #[serde(rename = "rkaf:aknt-eId")]
    AkntEId,
    #[serde(rename = "rkaf:uslm-section")]
    UslmSection,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SourceFragment {
    #[serde(rename = "@type", default = "SourceFragment::default_type")]
    pub type_: String,
    #[serde(rename = "@id", skip_serializing_if = "Option::is_none", default)]
    pub id: Option<String>,
    #[serde(rename = "rkaf:bindsArtifact")]
    pub binds_artifact: String,
    #[serde(rename = "rkaf:hasSelector")]
    pub has_selector: serde_json::Value,
    #[serde(rename = "rkaf:selectorKind")]
    pub selector_kind: SelectorKind,
    #[serde(flatten)]
    pub extra: std::collections::BTreeMap<String, serde_json::Value>,
}

impl SourceFragment {
    fn default_type() -> String {
        "rkaf:SourceFragment".into()
    }
}
