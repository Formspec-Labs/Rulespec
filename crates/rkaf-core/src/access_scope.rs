use serde::{Deserialize, Serialize};

/// Closed enum: `rkaf:accessScopeKind` values per v0.2 §5.6.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum AccessScopeKind {
    #[serde(rename = "rkaf:public")]
    Public,
    #[serde(rename = "rkaf:partnerVisible")]
    PartnerVisible,
    #[serde(rename = "rkaf:organizationVisible")]
    OrganizationVisible,
    #[serde(rename = "rkaf:roleRestricted")]
    RoleRestricted,
    #[serde(rename = "rkaf:personalRestricted")]
    PersonalRestricted,
    #[serde(rename = "rkaf:regulatoryRestricted")]
    RegulatoryRestricted,
    #[serde(rename = "rkaf:embargoed")]
    Embargoed,
}

/// Closed enum: `rkaf:regulatoryClass` values per v0.2 §5.6 (only meaningful
/// when `accessScopeKind` is `rkaf:regulatoryRestricted`).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum RegulatoryClass {
    #[serde(rename = "rkaf:HIPAA-PHI")]
    HipaaPhi,
    #[serde(rename = "rkaf:GDPR-PII")]
    GdprPii,
    #[serde(rename = "rkaf:FERPA")]
    Ferpa,
    #[serde(rename = "rkaf:CJIS")]
    Cjis,
    #[serde(rename = "rkaf:classified")]
    Classified,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct AccessScope {
    #[serde(rename = "@type", default = "AccessScope::default_type")]
    pub type_: String,
    #[serde(rename = "@id", skip_serializing_if = "Option::is_none", default)]
    pub id: Option<String>,
    #[serde(rename = "rkaf:accessScopeKind")]
    pub access_scope_kind: AccessScopeKind,
    #[serde(rename = "rkaf:regulatoryClass", skip_serializing_if = "Option::is_none", default)]
    pub regulatory_class: Option<RegulatoryClass>,
    #[serde(rename = "rkaf:embargoUntil", skip_serializing_if = "Option::is_none", default)]
    pub embargo_until: Option<String>,
    #[serde(rename = "rkaf:permittedRole", skip_serializing_if = "Option::is_none", default)]
    pub permitted_role: Option<Vec<String>>,
    #[serde(flatten)]
    pub extra: std::collections::BTreeMap<String, serde_json::Value>,
}

impl AccessScope {
    fn default_type() -> String {
        "rkaf:AccessScope".into()
    }

    pub fn new(kind: AccessScopeKind) -> Self {
        Self {
            type_: Self::default_type(),
            id: None,
            access_scope_kind: kind,
            regulatory_class: None,
            embargo_until: None,
            permitted_role: None,
            extra: Default::default(),
        }
    }
}
