use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum ArtifactIdentifierScheme {
    #[serde(rename = "rkaf:eli")]
    Eli,
    #[serde(rename = "rkaf:eli-dl")]
    EliDl,
    #[serde(rename = "rkaf:eli-i")]
    EliI,
    #[serde(rename = "rkaf:uslm")]
    Uslm,
    #[serde(rename = "rkaf:aknt-eId")]
    AkntEId,
    #[serde(rename = "rkaf:doi")]
    Doi,
    #[serde(rename = "rkaf:isbn")]
    Isbn,
    #[serde(rename = "rkaf:issn")]
    Issn,
    #[serde(rename = "rkaf:cid")]
    Cid,
    #[serde(rename = "rkaf:hash-sha256")]
    HashSha256,
    #[serde(rename = "rkaf:urn-persistent")]
    UrnPersistent,
    #[serde(rename = "rkaf:partner-defined")]
    PartnerDefined,
}

/// A `rkaf:Artifact` — the document a Warrant or EvidenceBinding cites.
/// Either field MAY be a single value or an array (multiple identifiers for
/// the same artifact, e.g., DOI + URL).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Artifact {
    #[serde(rename = "@type", default = "Artifact::default_type")]
    pub type_: String,
    #[serde(rename = "@id", skip_serializing_if = "Option::is_none", default)]
    pub id: Option<String>,
    #[serde(rename = "rkaf:hasArtifactIdentifier")]
    pub has_artifact_identifier: StringOrArray,
    #[serde(rename = "rkaf:artifactIdentifierScheme")]
    pub artifact_identifier_scheme: SchemeOrArray,
    #[serde(flatten)]
    pub extra: std::collections::BTreeMap<String, serde_json::Value>,
}

impl Artifact {
    fn default_type() -> String {
        "rkaf:Artifact".into()
    }

    pub fn new(
        identifier: impl Into<String>,
        scheme: ArtifactIdentifierScheme,
    ) -> Self {
        Self {
            type_: Self::default_type(),
            id: None,
            has_artifact_identifier: StringOrArray::One(identifier.into()),
            artifact_identifier_scheme: SchemeOrArray::One(scheme),
            extra: Default::default(),
        }
    }
}

/// Allows `rkaf:hasArtifactIdentifier` to be either a single string or an array
/// of strings on the wire, per the compiled JSON Schema (`anyOf`).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(untagged)]
pub enum StringOrArray {
    One(String),
    Many(Vec<String>),
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(untagged)]
pub enum SchemeOrArray {
    One(ArtifactIdentifierScheme),
    Many(Vec<ArtifactIdentifierScheme>),
}
