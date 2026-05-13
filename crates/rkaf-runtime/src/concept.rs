//! Concept resolution with conflict — spec/rkaf-behavior.md §6.

use serde_json::{json, Value};

use crate::{errors::RuntimeError, graph::Graph, verdict::Verdict};

pub fn evaluate(_test_case: &Value, graph: &Graph) -> Result<Verdict, RuntimeError> {
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

    // Conflict — multiple distinct targets.
    let any_exact = mappings.iter().any(|m| {
        m.get("rkaf:mappingRelation").and_then(Value::as_str) == Some("skos:exactMatch")
    });
    let severity = if any_exact {
        "rkaf:operationalConflict"
    } else {
        "rkaf:informational"
    };

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
