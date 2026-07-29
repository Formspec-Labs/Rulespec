//! Concept resolution with conflict — spec/rkaf-behavior.md §6.

use chrono::{DateTime, FixedOffset};
use serde_json::{json, Value};

use crate::{
    errors::RuntimeError, graph::Graph, temporal::effective_attestations_at, verdict::Verdict,
};

const USAGE_LATTICE: &[&str] = &[
    "rkaf:notEligible",
    "rkaf:searchOnly",
    "rkaf:reviewQueueOnly",
    "rkaf:draftGenerationAllowed",
    "rkaf:localOperationalUse",
    "rkaf:publicationAllowed",
    "rkaf:officialUse",
];

struct ResolutionContext<'a> {
    cache_status: &'a str,
    registry_available: bool,
    requested_purposes: Vec<&'a str>,
    consumer_capability: &'a str,
}

pub fn evaluate(test_case: &Value, graph: &Graph) -> Result<Verdict, RuntimeError> {
    let source_id = test_case
        .get("rkaf:subjectConcept")
        .and_then(Value::as_str)
        .ok_or_else(|| {
            RuntimeError::MalformedTestCase(
                "ConceptResolutionWithConflict requires rkaf:subjectConcept".into(),
            )
        })?;
    let source = graph.require(source_id)?;
    if !has_type(source, "rkaf:LocalConcept") && !has_type(source, "rkaf:RegisteredConcept") {
        return Err(RuntimeError::MalformedTestCase(format!(
            "rkaf:subjectConcept {source_id:?} is not a LocalConcept or RegisteredConcept"
        )));
    }
    let resolved_at = test_case
        .get("rkaf:evaluationTime")
        .and_then(Value::as_str)
        .ok_or_else(|| {
            RuntimeError::MalformedTestCase(
                "ConceptResolutionWithConflict requires rkaf:evaluationTime".into(),
            )
        })?;
    let resolution_time = DateTime::parse_from_rfc3339(resolved_at).map_err(|e| {
        RuntimeError::MalformedTestCase(format!(
            "rkaf:evaluationTime value {resolved_at:?} is not valid RFC-3339: {e}"
        ))
    })?;
    let context = parse_resolution_context(test_case)?;
    let consumer = crate::consumer::select_consumer(test_case, graph)?;
    let effective_attestations = effective_attestations_at(graph, &resolution_time)?;

    // With neither live registry access nor cached evidence, no graph record
    // may silently authorize a result.
    if !context.registry_available && context.cache_status == "rkaf:notCached" {
        return Ok(failure_result(
            source_id,
            resolved_at,
            &context,
            "rkaf:registryUnavailable",
        ));
    }

    // Direct identity is usable only through exact, complete release
    // membership. Trust evidence changes the ceiling, never the identity.
    if has_type(source, "rkaf:RegisteredConcept") {
        if let Some(base_ceiling) = direct_resolution_ceiling(
            source,
            graph,
            consumer,
            &effective_attestations,
            &resolution_time,
        )? {
            let (status, method) = match context.cache_status {
                "rkaf:fresh" => ("rkaf:resolved", "rkaf:cacheServed"),
                "rkaf:stale" => ("rkaf:staleCacheFallback", "rkaf:staleCacheServed"),
                _ => ("rkaf:resolved", "rkaf:directRegistry"),
            };
            let ceiling = apply_context_ceiling(base_ceiling, &context);
            return Ok(Verdict::new(json!({
                "conceptResolutionResult": {
                    "inputConcept": source_id,
                    "resolutionStatus": status,
                    "resolutionMethod": method,
                    "resolvedConcept": source_id,
                    "cacheStatus": context.cache_status,
                    "usageCeiling": ceiling,
                    "resolvedAt": resolved_at,
                    "resolverId": "urn:rulespec:runtime:reference",
                },
            })));
        }
    }

    // Gather only mappings that carry exact endpoint release membership,
    // requested-purpose applicability, effective approval/lifecycle, and
    // evidence supporting the method's ceiling.
    let mut mappings = Vec::new();
    for mapping in graph.nodes_by_type("rkaf:ConceptMapping") {
        if mapping.get("rkaf:assertsSubject").and_then(Value::as_str) != Some(source_id) {
            continue;
        }
        if eligible_mapping(
            mapping,
            graph,
            &context,
            consumer,
            &effective_attestations,
            &resolution_time,
        )? {
            mappings.push(mapping);
        }
    }

    if mappings.is_empty() {
        let status = if context.registry_available {
            "rkaf:unresolved"
        } else {
            "rkaf:registryUnavailable"
        };
        return Ok(failure_result(source_id, resolved_at, &context, status));
    }

    // Collect unique target concepts.
    let mut targets: Vec<&str> = mappings
        .iter()
        .filter_map(|m| m.get("rkaf:assertsObject").and_then(Value::as_str))
        .collect();
    targets.sort();
    targets.dedup();

    if targets.len() == 1 {
        let selected = strongest_mapping(&mappings, graph, &resolution_time)?;
        let selected_id = mapping_id(selected)?;
        let (method, base_ceiling, discovery_only) =
            method_and_ceiling(selected, graph, consumer, &resolution_time)?;
        let ceiling = apply_context_ceiling(base_ceiling, &context);
        let status = if discovery_only {
            "rkaf:unresolved"
        } else if context.cache_status == "rkaf:stale" {
            "rkaf:staleCacheFallback"
        } else {
            "rkaf:resolved"
        };
        let mut result = json!({
            "inputConcept": source_id,
            "resolutionStatus": status,
            "resolutionMethod": method,
            "mappingAssertion": selected_id,
            "cacheStatus": context.cache_status,
            "usageCeiling": ceiling,
            "resolvedAt": resolved_at,
            "resolverId": "urn:rulespec:runtime:reference",
        });
        if !discovery_only {
            result
                .as_object_mut()
                .expect("resolution result is an object")
                .insert("resolvedConcept".into(), Value::String(targets[0].into()));
        }
        return Ok(Verdict::new(json!({
            "conceptResolutionResult": result,
        })));
    }

    // Conflict — multiple distinct targets. Severity per spec §6.1.
    let severity = compute_severity(&mappings, test_case, graph)?;

    let mut conflicting: Vec<Value> = mappings
        .iter()
        .filter_map(|m| {
            m.get("@id")
                .and_then(Value::as_str)
                .map(|s| Value::String(s.into()))
        })
        .collect();
    conflicting.sort_by(|a, b| a.as_str().cmp(&b.as_str()));
    let selected = strongest_mapping(&mappings, graph, &resolution_time)?;
    let selected_id = mapping_id(selected)?;
    let (method, _, _) = method_and_ceiling(selected, graph, consumer, &resolution_time)?;

    Ok(Verdict::new(json!({
        "conceptResolutionResult": {
            "inputConcept": source_id,
            "resolutionStatus": "rkaf:conflicting",
            "resolutionMethod": method,
            "mappingAssertion": selected_id,
            "cacheStatus": context.cache_status,
            "usageCeiling": "rkaf:notEligible",
            "resolvedAt": resolved_at,
            "resolverId": "urn:rulespec:runtime:reference",
        },
        "registryConflict": {
            "conflictingEntries": conflicting,
            "severity": severity,
        }
    })))
}

fn parse_resolution_context(test_case: &Value) -> Result<ResolutionContext<'_>, RuntimeError> {
    let raw = test_case.get("resolutionContext");
    let cache_status = raw
        .and_then(|v| v.get("cacheStatus"))
        .and_then(Value::as_str)
        .unwrap_or("rkaf:notCached");
    if !matches!(cache_status, "rkaf:fresh" | "rkaf:stale" | "rkaf:notCached") {
        return Err(RuntimeError::MalformedTestCase(format!(
            "resolutionContext.cacheStatus has unregistered value {cache_status:?}"
        )));
    }
    let registry_available = raw
        .and_then(|v| v.get("registryAvailable"))
        .and_then(Value::as_bool)
        .unwrap_or(true);
    let requested_purposes = raw
        .and_then(|v| v.get("requestedPurposes"))
        .map(string_values)
        .unwrap_or_default();
    let consumer_capability = raw
        .and_then(|v| v.get("consumerCapability"))
        .and_then(Value::as_str)
        .unwrap_or("rkaf:officialUse");
    if usage_rank(consumer_capability).is_none() {
        return Err(RuntimeError::MalformedTestCase(format!(
            "resolutionContext.consumerCapability has unregistered value {consumer_capability:?}"
        )));
    }
    Ok(ResolutionContext {
        cache_status,
        registry_available,
        requested_purposes,
        consumer_capability,
    })
}

fn failure_result(
    source_id: &str,
    resolved_at: &str,
    context: &ResolutionContext<'_>,
    status: &str,
) -> Verdict {
    Verdict::new(json!({
        "conceptResolutionResult": {
            "inputConcept": source_id,
            "resolutionStatus": status,
            "resolutionMethod": "rkaf:directRegistry",
            "cacheStatus": context.cache_status,
            "usageCeiling": "rkaf:notEligible",
            "resolvedAt": resolved_at,
            "resolverId": "urn:rulespec:runtime:reference",
        },
    }))
}

fn has_type(node: &Value, expected: &str) -> bool {
    match node.get("@type") {
        Some(Value::String(actual)) => actual == expected,
        Some(Value::Array(actual)) => actual.iter().any(|value| value.as_str() == Some(expected)),
        _ => false,
    }
}

fn string_values(value: &Value) -> Vec<&str> {
    match value {
        Value::String(value) => vec![value],
        Value::Array(values) => values.iter().filter_map(Value::as_str).collect(),
        _ => Vec::new(),
    }
}

fn contains_iri(node: &Value, predicate: &str, expected: &str) -> bool {
    node.get(predicate)
        .map(string_values)
        .unwrap_or_default()
        .contains(&expected)
}

fn is_terminal(node: &Value) -> bool {
    matches!(
        node.get("rkaf:consumerLifecycleState")
            .and_then(Value::as_str),
        Some("rkaf:staleForCurrentUse" | "rkaf:retired" | "rkaf:withdrawn")
    )
}

fn release_is_exact_complete_member(
    release_id: &str,
    member_id: &str,
    graph: &Graph,
    time: &DateTime<FixedOffset>,
) -> Result<bool, RuntimeError> {
    let Some(release) = graph.find(release_id) else {
        return Ok(false);
    };
    if !has_type(release, "rkaf:ReferenceResourceRelease")
        || release.get("rkaf:membershipMode").and_then(Value::as_str)
            != Some("rkaf:completeMembership")
        || !contains_iri(release, "prov:hadMember", member_id)
        || is_terminal(release)
    {
        return Ok(false);
    }
    crate::temporal::effective_at(release, time, graph)
}

fn complete_releases_for_member<'a>(
    member_id: &str,
    graph: &'a Graph,
    time: &DateTime<FixedOffset>,
) -> Result<Vec<&'a Value>, RuntimeError> {
    let mut releases = Vec::new();
    for release in graph.incoming(member_id, "prov:hadMember") {
        let Some(release_id) = release.get("@id").and_then(Value::as_str) else {
            continue;
        };
        if release_is_exact_complete_member(release_id, member_id, graph, time)? {
            releases.push(release);
        }
    }
    Ok(releases)
}

fn publication_attestation_for(target_id: &str, effective_attestations: &[&Value]) -> bool {
    effective_attestations.iter().any(|attestation| {
        contains_iri(attestation, "rkaf:targets", target_id)
            && matches!(
                attestation.get("rkaf:decision").and_then(Value::as_str),
                Some("rkaf:approved" | "rkaf:approvedWithConditions")
            )
            && attestation
                .get("rkaf:attestationScope")
                .and_then(Value::as_str)
                == Some("rkaf:registryPublication")
    })
}

fn registry_is_trusted(node: &Value, consumer: Option<&Value>) -> bool {
    let Some(registry) = node.get("rkaf:managedByRegistry").and_then(Value::as_str) else {
        return false;
    };
    consumer
        .map(|registration| contains_iri(registration, "rkaf:trustedRegistries", registry))
        .unwrap_or(false)
}

fn direct_resolution_ceiling(
    concept: &Value,
    graph: &Graph,
    consumer: Option<&Value>,
    effective_attestations: &[&Value],
    time: &DateTime<FixedOffset>,
) -> Result<Option<&'static str>, RuntimeError> {
    let concept_id = mapping_id(concept)?;
    let releases = complete_releases_for_member(concept_id, graph, time)?;
    if releases.is_empty() {
        return Ok(None);
    }
    if registry_is_trusted(concept, consumer) {
        return Ok(Some("rkaf:localOperationalUse"));
    }
    if publication_attestation_for(concept_id, effective_attestations)
        || releases.iter().any(|release| {
            release
                .get("@id")
                .and_then(Value::as_str)
                .map(|release_id| publication_attestation_for(release_id, effective_attestations))
                .unwrap_or(false)
        })
    {
        return Ok(Some("rkaf:draftGenerationAllowed"));
    }
    // Exact release membership proves identity, but no trust input may raise
    // it above discovery.
    Ok(Some("rkaf:searchOnly"))
}

fn mapping_lifecycle_is_active(
    mapping: &Value,
    graph: &Graph,
    time: &DateTime<FixedOffset>,
) -> Result<bool, RuntimeError> {
    if is_terminal(mapping) {
        return Ok(false);
    }
    let mapping_id = mapping_id(mapping)?;
    for event in graph.nodes_by_type("rkaf:LifecycleEvent") {
        if !contains_iri(event, "rkaf:appliesTo", mapping_id) {
            continue;
        }
        let Some(raw_date) = event.get("rkaf:effectiveDate").and_then(Value::as_str) else {
            return Err(RuntimeError::MalformedTestCase(format!(
                "LifecycleEvent affecting mapping {mapping_id:?} is missing rkaf:effectiveDate"
            )));
        };
        let effective_date = DateTime::parse_from_rfc3339(raw_date).map_err(|e| {
            RuntimeError::MalformedTestCase(format!(
                "LifecycleEvent rkaf:effectiveDate {raw_date:?} is not valid RFC-3339: {e}"
            ))
        })?;
        if effective_date <= *time
            && matches!(
                event.get("rkaf:lifecycleEventKind").and_then(Value::as_str),
                Some("rkaf:rescission" | "rkaf:supersession")
            )
        {
            return Ok(false);
        }
    }
    Ok(true)
}

fn mapping_is_applicable(mapping: &Value, graph: &Graph, requested: &[&str]) -> bool {
    if requested.is_empty() {
        return true;
    }
    let Some(applicability_id) = mapping.get("rkaf:hasApplicability").and_then(Value::as_str)
    else {
        return false;
    };
    let Some(applicability) = graph.find(applicability_id) else {
        return false;
    };
    let included = applicability
        .get("rkaf:evidencePurpose")
        .map(string_values)
        .unwrap_or_default();
    let excluded = applicability
        .get("rkaf:excludesPurposes")
        .map(string_values)
        .unwrap_or_default();
    requested.iter().all(|purpose| included.contains(purpose))
        && requested.iter().all(|purpose| !excluded.contains(purpose))
}

fn eligible_mapping(
    mapping: &Value,
    graph: &Graph,
    context: &ResolutionContext<'_>,
    consumer: Option<&Value>,
    effective_attestations: &[&Value],
    time: &DateTime<FixedOffset>,
) -> Result<bool, RuntimeError> {
    let predicate = mapping.get("rkaf:assertsPredicate").and_then(Value::as_str);
    if !matches!(
        predicate,
        Some("skos:exactMatch" | "skos:closeMatch" | "skos:broadMatch" | "skos:narrowMatch")
    ) {
        return Ok(false);
    }
    let Some(mapping_id) = mapping.get("@id").and_then(Value::as_str) else {
        return Err(RuntimeError::MalformedTestCase(
            "eligible ConceptMapping is missing @id".into(),
        ));
    };
    let Some(source_id) = mapping.get("rkaf:assertsSubject").and_then(Value::as_str) else {
        return Ok(false);
    };
    let Some(target_id) = mapping.get("rkaf:assertsObject").and_then(Value::as_str) else {
        return Ok(false);
    };
    let Some(source_release) = mapping
        .get("rkaf:sourceConceptRelease")
        .and_then(Value::as_str)
    else {
        return Ok(false);
    };
    let Some(target_release) = mapping
        .get("rkaf:targetConceptRelease")
        .and_then(Value::as_str)
    else {
        return Ok(false);
    };
    let method_supported = match predicate {
        Some("skos:exactMatch" | "skos:closeMatch") => {
            registry_is_trusted(mapping, consumer)
                || active_local_adoption(mapping, graph, time).is_some()
        }
        Some("skos:broadMatch" | "skos:narrowMatch") => true,
        _ => false,
    };
    if !release_is_exact_complete_member(source_release, source_id, graph, time)?
        || !release_is_exact_complete_member(target_release, target_id, graph, time)?
        || !mapping_is_applicable(mapping, graph, &context.requested_purposes)
        || !mapping_lifecycle_is_active(mapping, graph, time)?
        || !publication_attestation_for(mapping_id, effective_attestations)
        || !method_supported
    {
        return Ok(false);
    }
    Ok(true)
}

fn mapping_id(mapping: &Value) -> Result<&str, RuntimeError> {
    mapping.get("@id").and_then(Value::as_str).ok_or_else(|| {
        RuntimeError::MalformedTestCase(
            "ConceptMapping selected by the resolver is missing @id".into(),
        )
    })
}

fn mapping_rank(mapping: &Value, graph: &Graph, time: &DateTime<FixedOffset>) -> u8 {
    match mapping.get("rkaf:assertsPredicate").and_then(Value::as_str) {
        Some("skos:exactMatch") => 0,
        Some("skos:closeMatch") if active_local_adoption(mapping, graph, time).is_some() => 1,
        Some("skos:closeMatch") => 2,
        Some("skos:broadMatch" | "skos:narrowMatch") => 3,
        _ => 4,
    }
}

fn strongest_mapping<'a>(
    mappings: &[&'a Value],
    graph: &Graph,
    time: &DateTime<FixedOffset>,
) -> Result<&'a Value, RuntimeError> {
    mappings
        .iter()
        .copied()
        .min_by(|left, right| {
            mapping_rank(left, graph, time)
                .cmp(&mapping_rank(right, graph, time))
                .then_with(|| {
                    left.get("@id")
                        .and_then(Value::as_str)
                        .cmp(&right.get("@id").and_then(Value::as_str))
                })
        })
        .ok_or_else(|| {
            RuntimeError::MalformedTestCase("concept resolution has no eligible mapping".into())
        })
}

fn active_local_adoption<'a>(
    mapping: &Value,
    graph: &'a Graph,
    time: &DateTime<FixedOffset>,
) -> Option<&'a Value> {
    let mapping_id = mapping.get("@id").and_then(Value::as_str)?;
    graph
        .nodes_by_type("rkaf:LocalAdoption")
        .filter(|adoption| {
            adoption.get("rkaf:targetAssertion").and_then(Value::as_str) == Some(mapping_id)
                && adoption.get("rkaf:adoptionStatus").and_then(Value::as_str)
                    == Some("rkaf:active")
                && adoption
                    .get("rkaf:adoptedAt")
                    .and_then(Value::as_str)
                    .and_then(|raw| DateTime::parse_from_rfc3339(raw).ok())
                    .map(|adopted| adopted <= *time)
                    .unwrap_or(false)
        })
        .max_by_key(|adoption| {
            adoption
                .get("rkaf:usageEligibility")
                .and_then(Value::as_str)
                .and_then(usage_rank)
                .unwrap_or(0)
        })
}

fn method_and_ceiling(
    mapping: &Value,
    graph: &Graph,
    consumer: Option<&Value>,
    time: &DateTime<FixedOffset>,
) -> Result<(&'static str, &'static str, bool), RuntimeError> {
    match mapping.get("rkaf:assertsPredicate").and_then(Value::as_str) {
        Some("skos:exactMatch") => {
            let ceiling = if registry_is_trusted(mapping, consumer) {
                "rkaf:localOperationalUse"
            } else if let Some(adoption) = active_local_adoption(mapping, graph, time) {
                let adopted_ceiling = adoption
                    .get("rkaf:usageEligibility")
                    .and_then(Value::as_str)
                    .unwrap_or("rkaf:notEligible");
                usage_static(min_usage(adopted_ceiling, "rkaf:localOperationalUse"))?
            } else {
                return Err(RuntimeError::MalformedTestCase(
                    "exactMatch reached selection without trust or local adoption".into(),
                ));
            };
            Ok(("rkaf:exactMatchTrusted", ceiling, false))
        }
        Some("skos:closeMatch") => {
            if let Some(adoption) = active_local_adoption(mapping, graph, time) {
                let adopted_ceiling = adoption
                    .get("rkaf:usageEligibility")
                    .and_then(Value::as_str)
                    .unwrap_or("rkaf:notEligible");
                let ceiling = min_usage(adopted_ceiling, "rkaf:localOperationalUse");
                Ok((
                    "rkaf:closeMatchLocallyAdopted",
                    usage_static(ceiling)?,
                    false,
                ))
            } else {
                Ok((
                    "rkaf:closeMatchAwaitingAdoption",
                    "rkaf:draftGenerationAllowed",
                    false,
                ))
            }
        }
        Some("skos:broadMatch" | "skos:narrowMatch") => Ok((
            "rkaf:broadOrNarrowMatchDiscoveryOnly",
            "rkaf:searchOnly",
            true,
        )),
        _ => Err(RuntimeError::MalformedTestCase(
            "selected mapping uses no resolution predicate".into(),
        )),
    }
}

fn usage_rank(level: &str) -> Option<usize> {
    USAGE_LATTICE
        .iter()
        .position(|candidate| *candidate == level)
}

fn min_usage<'a>(left: &'a str, right: &'a str) -> &'a str {
    match (usage_rank(left), usage_rank(right)) {
        (Some(left_rank), Some(right_rank)) if left_rank <= right_rank => left,
        (Some(_), Some(_)) => right,
        _ => "rkaf:notEligible",
    }
}

fn usage_static(level: &str) -> Result<&'static str, RuntimeError> {
    USAGE_LATTICE
        .iter()
        .copied()
        .find(|candidate| *candidate == level)
        .ok_or_else(|| {
            RuntimeError::MalformedTestCase(format!(
                "LocalAdoption has unregistered rkaf:usageEligibility {level:?}"
            ))
        })
}

fn apply_context_ceiling<'a>(base: &'a str, context: &'a ResolutionContext<'_>) -> &'a str {
    let mut ceiling = min_usage(base, context.consumer_capability);
    if context.cache_status == "rkaf:stale" {
        ceiling = min_usage(ceiling, "rkaf:searchOnly");
    }
    ceiling
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
            "rkaf:evaluationTime": "2026-07-29T12:00:00Z",
            "rkaf:subjectConcept": "c1",
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
