//! Concept resolution with conflict — spec/rkaf-behavior.md §6.

use serde_json::{json, Value};

use crate::{errors::RuntimeError, graph::Graph, verdict::Verdict};

pub fn evaluate(test_case: &Value, graph: &Graph) -> Result<Verdict, RuntimeError> {
    // Locate the LocalConcept being resolved.
    let local = graph
        .nodes_by_type("rkaf:LocalConcept")
        .next()
        .or_else(|| graph.nodes_by_type("rkaf:RegisteredConcept").next())
        .ok_or_else(|| {
            RuntimeError::MalformedTestCase(
                "ConceptResolutionWithConflict fixture missing a Concept node".into(),
            )
        })?;
    let source_id = local
        .get("@id")
        .and_then(Value::as_str)
        .ok_or_else(|| RuntimeError::MalformedTestCase("Concept missing @id".into()))?;

    // Gather all ConceptMappings whose canonical assertion subject is this
    // concept.
    let mappings: Vec<&Value> = graph
        .nodes_by_type("rkaf:ConceptMapping")
        .filter(|m| m.get("rkaf:assertsSubject").and_then(Value::as_str) == Some(source_id))
        .collect();

    if mappings.is_empty() {
        return Ok(Verdict::new(json!({
            "resolutionResult": "rkaf:unresolved",
        })));
    }

    // Collect unique target concepts.
    let mut targets: Vec<&str> = mappings
        .iter()
        .filter_map(|m| m.get("rkaf:assertsObject").and_then(Value::as_str))
        .collect();
    targets.sort();
    targets.dedup();

    if targets.len() == 1 {
        return Ok(Verdict::new(json!({
            "resolutionResult": "rkaf:resolved",
            "canonicalConcept": targets[0],
        })));
    }

    // Conflict — multiple distinct targets. Severity per spec §6.1.
    let severity = compute_severity(&mappings, test_case, graph)?;

    let conflicting: Vec<Value> = mappings
        .iter()
        .filter_map(|m| {
            m.get("@id")
                .and_then(Value::as_str)
                .map(|s| Value::String(s.into()))
        })
        .collect();

    Ok(Verdict::new(json!({
        "resolutionResult": "rkaf:conflict",
        "registryConflict": {
            "conflictingEntries": conflicting,
            "severity": severity,
        }
    })))
}

/// Severity ladder per spec §6.1:
///   informational         — no exactMatch; targets differ
///   operationalConflict   — exactMatch present; targets differ
///   publicationBlocking   — ≥2 mappings are members of a reference-resource
///                           release, have an unrevoked publication-scope
///                           approval Attestation, remain active, and target
///                           different concepts
///   authorityCritical     — publicationBlocking AND ≥1 of those mappings is
///                            managedByRegistry ∈
///                            consumer.trustedRegistries
///
/// Multi-BCR errors from the consumer resolver propagate — a malformed
/// graph MUST NOT silently degrade to a lower severity.
fn compute_severity(
    mappings: &[&Value],
    test_case: &Value,
    graph: &Graph,
) -> Result<&'static str, RuntimeError> {
    let publication_relevant: Vec<&&Value> = mappings
        .iter()
        .filter(|m| mapping_is_publication_relevant(m, graph))
        .collect();

    if publication_relevant.len() >= 2 {
        // Authority-critical upgrade requires the canonical consumer. Any
        // resolver error (multi-BCR without rkaf:evaluationConsumer, etc.)
        // propagates rather than degrading to publicationBlocking.
        if let Some(reg) = crate::consumer::select_consumer(test_case, graph)? {
            let trusted: Vec<&str> = reg
                .get("rkaf:trustedRegistries")
                .and_then(Value::as_array)
                .map(|arr| arr.iter().filter_map(Value::as_str).collect())
                .unwrap_or_default();
            let any_trusted = publication_relevant.iter().any(|m| {
                m.get("rkaf:managedByRegistry")
                    .and_then(Value::as_str)
                    .map(|r| trusted.contains(&r))
                    .unwrap_or(false)
            });
            if any_trusted {
                return Ok("rkaf:authorityCritical");
            }
        }
        return Ok("rkaf:publicationBlocking");
    }

    let any_exact = mappings
        .iter()
        .any(|m| m.get("rkaf:assertsPredicate").and_then(Value::as_str) == Some("skos:exactMatch"));
    Ok(if any_exact {
        "rkaf:operationalConflict"
    } else {
        "rkaf:informational"
    })
}

fn mapping_is_publication_relevant(mapping: &Value, graph: &Graph) -> bool {
    let Some(mapping_id) = mapping.get("@id").and_then(Value::as_str) else {
        return false;
    };
    if matches!(
        mapping
            .get("rkaf:consumerLifecycleState")
            .and_then(Value::as_str),
        Some("rkaf:staleForCurrentUse" | "rkaf:retired" | "rkaf:withdrawn")
    ) {
        return false;
    }
    let in_release = graph
        .incoming(mapping_id, "prov:hadMember")
        .iter()
        .any(|node| {
            node.get("@type").and_then(Value::as_str) == Some("rkaf:ReferenceResourceRelease")
        });
    if !in_release {
        return false;
    }
    graph
        .incoming(mapping_id, "rkaf:targets")
        .iter()
        .any(|node| {
            node.get("@type").and_then(Value::as_str) == Some("rkaf:Attestation")
                && matches!(
                    node.get("rkaf:decision").and_then(Value::as_str),
                    Some("rkaf:approved" | "rkaf:approvedWithConditions")
                )
                && node.get("rkaf:attestationScope").and_then(Value::as_str)
                    == Some("rkaf:registryPublication")
                && node.get("rkaf:revokedAt").is_none()
        })
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn multi_bcr_without_evaluation_consumer_propagates_error() {
        // Two publication-relevant mappings with different targets — normally
        // trigger the publicationBlocking/authorityCritical branch where
        // compute_severity reads the consumer. With 2 BCRs in the graph
        // and no rkaf:evaluationConsumer in the test_case, select_consumer
        // MUST return Err — and compute_severity MUST `?`-propagate, not
        // silently degrade to publicationBlocking.
        let test_case = json!({
            "@type": "rkaf:BehaviorTestCase",
            "rkaf:behaviorContract": "rkaf:ConceptResolutionWithConflict",
            "rkaf:input": {
                "@graph": [
                    {"@id": "c1", "@type": "rkaf:LocalConcept"},
                    {"@id": "c2", "@type": "rkaf:RegisteredConcept"},
                    {"@id": "c3", "@type": "rkaf:RegisteredConcept"},
                    {
                        "@id": "m1",
                        "@type": "rkaf:ConceptMapping",
                        "rkaf:assertsSubject": "c1",
                        "rkaf:assertsPredicate": "skos:exactMatch",
                        "rkaf:assertsObject": "c2",
                        "rkaf:managedByRegistry": "urn:reg:r1"
                    },
                    {
                        "@id": "m2",
                        "@type": "rkaf:ConceptMapping",
                        "rkaf:assertsSubject": "c1",
                        "rkaf:assertsPredicate": "skos:exactMatch",
                        "rkaf:assertsObject": "c3",
                        "rkaf:managedByRegistry": "urn:reg:r2"
                    },
                    {
                        "@id": "release",
                        "@type": "rkaf:ReferenceResourceRelease",
                        "prov:hadMember": ["m1", "m2"]
                    },
                    {
                        "@id": "att1",
                        "@type": "rkaf:Attestation",
                        "rkaf:targets": ["m1"],
                        "rkaf:decision": "rkaf:approved",
                        "rkaf:attestationScope": "rkaf:registryPublication"
                    },
                    {
                        "@id": "att2",
                        "@type": "rkaf:Attestation",
                        "rkaf:targets": ["m2"],
                        "rkaf:decision": "rkaf:approved",
                        "rkaf:attestationScope": "rkaf:registryPublication"
                    },
                    {
                        "@id": "bcr1",
                        "@type": "rkaf:BridgeConsumerRegistration",
                        "rkaf:consumer": "urn:consumer:one",
                        "rkaf:bridgeContractVersion": "rkaf-bridge/1.0",
                        "rkaf:registeredAt": "2026-04-15T00:00:00Z",
                        "rkaf:supportedEvaluationAnchors": ["rkaf:applicationSubmissionTime"],
                        "rkaf:supportsRegistryVersionRange": ["^1.0"],
                        "rkaf:supportedAutomaticMigrations": [],
                        "rkaf:supportedAuthorityKinds": ["rkaf:statutory"]
                    },
                    {
                        "@id": "bcr2",
                        "@type": "rkaf:BridgeConsumerRegistration",
                        "rkaf:consumer": "urn:consumer:two",
                        "rkaf:bridgeContractVersion": "rkaf-bridge/1.0",
                        "rkaf:registeredAt": "2026-04-15T00:00:00Z",
                        "rkaf:supportedEvaluationAnchors": ["rkaf:applicationSubmissionTime"],
                        "rkaf:supportsRegistryVersionRange": ["^1.0"],
                        "rkaf:supportedAutomaticMigrations": [],
                        "rkaf:supportedAuthorityKinds": ["rkaf:statutory"]
                    }
                ]
            }
        });

        let graph = Graph::from_payload(test_case.get("rkaf:input").unwrap()).expect("graph parse");
        let err = evaluate(&test_case, &graph).unwrap_err();
        match err {
            RuntimeError::MalformedTestCase(msg) => {
                assert!(
                    msg.contains("BridgeConsumerRegistration"),
                    "expected multi-BCR error, got: {msg}"
                );
            }
            other => {
                panic!("expected MalformedTestCase propagated from select_consumer, got: {other:?}")
            }
        }
    }
}
