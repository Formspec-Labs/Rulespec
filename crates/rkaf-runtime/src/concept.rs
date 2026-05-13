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

    // Gather all ConceptMappings with sourceConcept == this concept.
    let mappings: Vec<&Value> = graph
        .nodes_by_type("rkaf:ConceptMapping")
        .filter(|m| m.get("rkaf:sourceConcept").and_then(Value::as_str) == Some(source_id))
        .collect();

    if mappings.is_empty() {
        return Ok(Verdict::new(json!({
            "resolutionResult": "rkaf:unresolved",
        })));
    }

    // Collect unique target concepts.
    let mut targets: Vec<&str> = mappings
        .iter()
        .filter_map(|m| m.get("rkaf:targetConcept").and_then(Value::as_str))
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
    let severity = compute_severity(&mappings, test_case, graph);

    let conflicting: Vec<Value> = mappings
        .iter()
        .filter_map(|m| m.get("@id").and_then(Value::as_str).map(|s| Value::String(s.into())))
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
///   publicationBlocking   — ≥2 mappings carry lifecycleState=approved AND
///                            targets differ
///   authorityCritical     — publicationBlocking AND ≥1 of the approved
///                            mappings is managedByRegistry ∈
///                            consumer.trustedRegistries
fn compute_severity(mappings: &[&Value], test_case: &Value, graph: &Graph) -> &'static str {
    let approved: Vec<&&Value> = mappings
        .iter()
        .filter(|m| {
            m.get("rkaf:lifecycleState").and_then(Value::as_str) == Some("rkaf:approved")
        })
        .collect();

    if approved.len() >= 2 {
        // Check for authority-critical upgrade. Pick the consumer (if any)
        // via the same resolver the rest of the runtime uses.
        if let Ok(Some(reg)) = crate::consumer::select_consumer(test_case, graph) {
            let trusted: Vec<&str> = reg
                .get("rkaf:trustedRegistries")
                .and_then(Value::as_array)
                .map(|arr| arr.iter().filter_map(Value::as_str).collect())
                .unwrap_or_default();
            let any_trusted = approved.iter().any(|m| {
                m.get("rkaf:managedByRegistry")
                    .and_then(Value::as_str)
                    .map(|r| trusted.contains(&r))
                    .unwrap_or(false)
            });
            if any_trusted {
                return "rkaf:authorityCritical";
            }
        }
        return "rkaf:publicationBlocking";
    }

    let any_exact = mappings.iter().any(|m| {
        m.get("rkaf:mappingRelation").and_then(Value::as_str) == Some("skos:exactMatch")
    });
    if any_exact {
        "rkaf:operationalConflict"
    } else {
        "rkaf:informational"
    }
}
