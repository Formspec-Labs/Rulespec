use serde::{Deserialize, Serialize};

/// Closed enum: `rkaf:warrantFamily` values per v0.2 §5.5.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum WarrantFamily {
    #[serde(rename = "rkaf:legal")]
    Legal,
    #[serde(rename = "rkaf:scientific")]
    Scientific,
    #[serde(rename = "rkaf:editorial")]
    Editorial,
    #[serde(rename = "rkaf:cryptographic")]
    Cryptographic,
    #[serde(rename = "rkaf:social")]
    Social,
    #[serde(rename = "rkaf:sourceClass")]
    SourceClass,
}

/// Closed enum: `rkaf:warrantKind` values per v0.2 §5.5. The enum is the
/// disjoint union of every family's kind set; cross-family transitions and
/// family↔kind agreement are Layer 2 constraints (not Rust-encoded).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum WarrantKind {
    // legal
    #[serde(rename = "rkaf:legal")]
    Legal,
    #[serde(rename = "rkaf:statutory")]
    Statutory,
    #[serde(rename = "rkaf:regulatory")]
    Regulatory,
    #[serde(rename = "rkaf:delegated")]
    Delegated,
    #[serde(rename = "rkaf:organizational")]
    Organizational,
    // scientific
    #[serde(rename = "rkaf:methodological")]
    Methodological,
    #[serde(rename = "rkaf:empirical")]
    Empirical,
    #[serde(rename = "rkaf:replication")]
    Replication,
    #[serde(rename = "rkaf:peerReview")]
    PeerReview,
    // editorial
    #[serde(rename = "rkaf:editorial")]
    Editorial,
    #[serde(rename = "rkaf:factCheck")]
    FactCheck,
    #[serde(rename = "rkaf:correction")]
    Correction,
    // cryptographic
    #[serde(rename = "rkaf:cryptographic")]
    Cryptographic,
    #[serde(rename = "rkaf:commitment")]
    Commitment,
    // social
    #[serde(rename = "rkaf:consensus")]
    Consensus,
    #[serde(rename = "rkaf:expertOpinion")]
    ExpertOpinion,
    #[serde(rename = "rkaf:communityEndorsement")]
    CommunityEndorsement,
    // source-class
    #[serde(rename = "rkaf:sourceReliability")]
    SourceReliability,
    #[serde(rename = "rkaf:provenanceClass")]
    ProvenanceClass,
}

/// `rkaf:Warrant` — a justification source pointing at the *kind* of authority
/// backing an Assertion (legal, scientific, editorial, …).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Warrant {
    #[serde(rename = "@type", default = "Warrant::default_type")]
    pub type_: String,
    #[serde(rename = "@id", skip_serializing_if = "Option::is_none", default)]
    pub id: Option<String>,
    #[serde(rename = "rkaf:warrantKind")]
    pub warrant_kind: WarrantKind,
    #[serde(rename = "rkaf:warrantFamily")]
    pub warrant_family: WarrantFamily,
    #[serde(rename = "rkaf:hasPredecessor", skip_serializing_if = "Option::is_none", default)]
    pub has_predecessor: Option<String>,
    #[serde(rename = "rkaf:defeasible", skip_serializing_if = "Option::is_none", default)]
    pub defeasible: Option<bool>,
    #[serde(flatten)]
    pub extra: std::collections::BTreeMap<String, serde_json::Value>,
}

impl Warrant {
    fn default_type() -> String {
        "rkaf:Warrant".into()
    }

    pub fn new(kind: WarrantKind, family: WarrantFamily) -> Self {
        Self {
            type_: Self::default_type(),
            id: None,
            warrant_kind: kind,
            warrant_family: family,
            has_predecessor: None,
            defeasible: None,
            extra: Default::default(),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn round_trip_minimal() {
        let w = Warrant::new(WarrantKind::Statutory, WarrantFamily::Legal);
        let v = serde_json::to_value(&w).unwrap();
        let parsed: Warrant = serde_json::from_value(v.clone()).unwrap();
        assert_eq!(w, parsed);
        assert_eq!(v["@type"], "rkaf:Warrant");
        assert_eq!(v["rkaf:warrantKind"], "rkaf:statutory");
        assert_eq!(v["rkaf:warrantFamily"], "rkaf:legal");
    }

    #[test]
    fn deserialize_from_jsonld_payload() {
        let payload = json!({
            "@type": "rkaf:Warrant",
            "rkaf:warrantKind": "rkaf:regulatory",
            "rkaf:warrantFamily": "rkaf:legal"
        });
        let w: Warrant = serde_json::from_value(payload).unwrap();
        assert_eq!(w.warrant_kind, WarrantKind::Regulatory);
        assert_eq!(w.warrant_family, WarrantFamily::Legal);
    }
}
