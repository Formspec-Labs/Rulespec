//! UsageEligibility reducer — spec/rkaf-behavior.md §1.

use chrono::{DateTime, Duration, FixedOffset};
use serde_json::{json, Value};

use crate::{
    errors::RuntimeError, graph::Graph, temporal::effective_attestations_at, verdict::Verdict,
};

/// The 7-level UsageEligibility lattice, ordered low → high.
const LATTICE: &[&str] = &[
    "rkaf:notEligible",
    "rkaf:searchOnly",
    "rkaf:reviewQueueOnly",
    "rkaf:draftGenerationAllowed",
    "rkaf:localOperationalUse",
    "rkaf:publicationAllowed",
    "rkaf:officialUse",
];

fn rank(level: &str) -> Option<usize> {
    LATTICE.iter().position(|&l| l == level)
}

fn max_on_lattice(a: &str, b: &str) -> String {
    let ra = rank(a).unwrap_or(0);
    let rb = rank(b).unwrap_or(0);
    LATTICE[ra.max(rb)].to_string()
}

fn min_on_lattice(a: &str, b: &str) -> String {
    let ra = rank(a).unwrap_or(LATTICE.len() - 1);
    let rb = rank(b).unwrap_or(LATTICE.len() - 1);
    LATTICE[ra.min(rb)].to_string()
}

pub fn evaluate(test_case: &Value, graph: &Graph) -> Result<Verdict, RuntimeError> {
    let consumer = crate::consumer::select_consumer(test_case, graph)?;
    // Plan 7e.2 — optional evaluation time for the freshness gate. If absent,
    // the reducer skips the freshness check (Attestations of any age accepted).
    // Strictness: malformed RFC-3339 propagates as MalformedTestCase.
    let evaluation_time: Option<DateTime<FixedOffset>> =
        match test_case.get("rkaf:evaluationTime").and_then(Value::as_str) {
            Some(s) => Some(DateTime::parse_from_rfc3339(s).map_err(|e| {
                RuntimeError::MalformedTestCase(format!(
                    "rkaf:evaluationTime value {s:?} is not valid RFC-3339: {e}"
                ))
            })?),
            None => None,
        };
    // Locate the Assertion under evaluation. Per spec §1, the fixture MUST
    // declare `rkaf:subjectAssertion` — greenfield contract, no implicit
    // "pick the first Assertion" fallback. Graphs commonly carry multiple
    // Assertions (e.g., justification chain), so silent selection is unsafe.
    let assertion_id_field = test_case
        .get("rkaf:subjectAssertion")
        .and_then(Value::as_str)
        .ok_or_else(|| {
            RuntimeError::MalformedTestCase(
                "UsageEligibilityReducer fixture MUST declare rkaf:subjectAssertion (no implicit selection)".into(),
            )
        })?;
    let assertion = graph.require(assertion_id_field)?;
    let assertion_id = assertion
        .get("@id")
        .and_then(Value::as_str)
        .ok_or_else(|| RuntimeError::MalformedTestCase("Assertion has no @id".into()))?
        .to_string();

    let baseline = assertion
        .get("rkaf:usageEligibility")
        .and_then(Value::as_str)
        .unwrap_or("rkaf:notEligible")
        .to_string();

    let is_stale = assertion
        .get("rkaf:consumerLifecycleState")
        .and_then(Value::as_str)
        == Some("rkaf:staleForCurrentUse");

    // hasApplicability is a single IRI per CUE; runtime accepts a list too
    // (defensive for graphs where authors used an array). The applicability
    // set is the IRIs pointing at ApplicabilityScope nodes; we resolve each
    // to its `appliesInJurisdiction` list and union them.
    let applicability_iris: Vec<&str> = match assertion.get("rkaf:hasApplicability") {
        Some(Value::String(s)) => vec![s.as_str()],
        Some(Value::Array(arr)) => arr.iter().filter_map(Value::as_str).collect(),
        _ => Vec::new(),
    };
    let mut applicability_set: Vec<&str> = Vec::new();
    for app_iri in &applicability_iris {
        if let Some(app) = graph.find(app_iri) {
            if let Some(arr) = app
                .get("rkaf:appliesInJurisdiction")
                .and_then(Value::as_array)
            {
                for v in arr {
                    if let Some(s) = v.as_str() {
                        applicability_set.push(s);
                    }
                }
            }
            // Fall back: if appliesInJurisdiction missing, the applicability
            // IRI itself is the scope match key (a one-element set).
            if applicability_set.is_empty() {
                applicability_set.push(app_iri);
            }
        }
    }

    // Determine evaluation scopes.
    // Behavior fixtures MAY carry rkaf:evaluationScopes; otherwise derive from
    // LocalAdoptions targeting the assertion.
    let mut scopes: Vec<String> = Vec::new();
    if let Some(arr) = test_case
        .get("rkaf:evaluationScopes")
        .and_then(Value::as_array)
    {
        for v in arr {
            if let Some(s) = v.as_str() {
                scopes.push(s.into());
            }
        }
    } else {
        // Default: every LocalAdoption.adoptionScope targeting this assertion,
        // plus an out-of-scope sentinel for comparison. The
        // local-broadens-in-scope fixture expects both an in-scope and
        // an out-of-scope reading; we synthesize them from the fixture.
        for la in graph.nodes_by_type("rkaf:LocalAdoption") {
            if la.get("rkaf:targetAssertion").and_then(Value::as_str) == Some(&assertion_id) {
                if let Some(s) = la.get("rkaf:adoptionScope").and_then(Value::as_str) {
                    if !scopes.contains(&s.to_string()) {
                        scopes.push(s.to_string());
                    }
                }
            }
        }
        // For multi-scope reasoning the fixture must declare scopes
        // explicitly; we don't synthesize the "other scope" — too magical.
    }

    // No scopes declared → workspace-wide reduction (no LocalAdoption).
    if scopes.is_empty() {
        let ScopeResult {
            level,
            freshness_narrowed,
            level_before_freshness,
        } = reduce_for_scope_traced(
            &assertion_id,
            &baseline,
            is_stale,
            &applicability_set,
            None,
            consumer,
            evaluation_time.as_ref(),
            graph,
        )?;
        let max_days = consumer
            .and_then(|reg| {
                reg.get("rkaf:maxAttestationStalenessDays")
                    .and_then(Value::as_i64)
            })
            .unwrap_or(0);
        let rationale: String = if freshness_narrowed {
            format!(
                "freshness gate narrowed from {level_before_freshness} to {level} (maxAttestationStalenessDays={max_days})"
            )
        } else if is_stale {
            "lifecycle status (staleForCurrentUse) wins over baseline".into()
        } else {
            "baseline applied; no LocalAdoption broadening (workspace-wide reduction)".into()
        };
        return Ok(Verdict::new(json!({
            "effectiveUsageEligibility": level,
            "rationale": rationale,
        })));
    }

    let mut by_scope = serde_json::Map::new();
    for scope in scopes {
        let level = reduce_for_scope(
            &assertion_id,
            &baseline,
            is_stale,
            &applicability_set,
            Some(&scope),
            consumer,
            evaluation_time.as_ref(),
            graph,
        )?;
        by_scope.insert(scope, Value::String(level));
    }
    Ok(Verdict::new(json!({ "byScope": Value::Object(by_scope) })))
}

/// Internal trace of a single-scope reduction. Used by `evaluate` to
/// build a richer rationale when Step 5.5 fires; per-scope `byScope`
/// output discards the trace (the output shape carries only the level).
struct ScopeResult {
    level: String,
    freshness_narrowed: bool,
    level_before_freshness: String,
}

/// Compute effective UsageEligibility per spec/rkaf-behavior.md §1.2.
/// Public for cross-contract reuse (bridge.rs::rule_2 calls this to stay
/// in lock-step with the reducer's canonical algorithm).
///
/// `evaluation_time` powers the Plan 7e.2 freshness gate (Step 5.5). When
/// `Some`, and the consumer declares `rkaf:maxAttestationStalenessDays`,
/// the gate narrows the effective level one lattice step downward if any
/// Attestation targeting `assertion_id` has a `lastVerifiedAt` older than
/// `evaluation_time - max_staleness_days`. When `None` (or the consumer
/// has no `maxAttestationStalenessDays`), the gate is skipped.
///
/// Errors propagate from malformed RFC-3339 literals on Attestation
/// `lastVerifiedAt` — same loud-error posture as `cascade::is_active`.
#[allow(clippy::too_many_arguments)]
pub fn reduce_for_scope(
    assertion_id: &str,
    baseline: &str,
    is_stale: bool,
    applicability_set: &[&str],
    scope: Option<&str>,
    consumer: Option<&Value>,
    evaluation_time: Option<&DateTime<FixedOffset>>,
    graph: &Graph,
) -> Result<String, RuntimeError> {
    Ok(reduce_for_scope_traced(
        assertion_id,
        baseline,
        is_stale,
        applicability_set,
        scope,
        consumer,
        evaluation_time,
        graph,
    )?
    .level)
}

#[allow(clippy::too_many_arguments)]
fn reduce_for_scope_traced(
    assertion_id: &str,
    baseline: &str,
    is_stale: bool,
    applicability_set: &[&str],
    scope: Option<&str>,
    consumer: Option<&Value>,
    evaluation_time: Option<&DateTime<FixedOffset>>,
    graph: &Graph,
) -> Result<ScopeResult, RuntimeError> {
    // Step 1 — applicability gate. If eval scope is non-None AND the
    // assertion declares applicability AND eval scope is not in the
    // applicability set, return notEligible (§1.2 step 1).
    if let Some(scope_iri) = scope {
        if !applicability_set.is_empty() && !applicability_set.contains(&scope_iri) {
            return Ok(ScopeResult {
                level: "rkaf:notEligible".to_string(),
                freshness_narrowed: false,
                level_before_freshness: "rkaf:notEligible".to_string(),
            });
        }
    }

    // Step 2 — baseline.
    // Step 3 — lifecycle stale check (honored PITs restore baseline).
    let lifecycle_floor: String = if is_stale && !has_honored_pit(assertion_id, consumer, graph) {
        "rkaf:notEligible".to_string()
    } else {
        baseline.to_string()
    };

    // Step 4 — LocalAdoption broadening (only in-scope).
    let mut effective = lifecycle_floor;
    if let Some(scope_iri) = scope {
        for la in graph.nodes_by_type("rkaf:LocalAdoption") {
            if la.get("rkaf:targetAssertion").and_then(Value::as_str) == Some(assertion_id)
                && la.get("rkaf:adoptionScope").and_then(Value::as_str) == Some(scope_iri)
                && la.get("rkaf:adoptionStatus").and_then(Value::as_str) == Some("rkaf:active")
            {
                if let Some(eligibility) = la.get("rkaf:usageEligibility").and_then(Value::as_str) {
                    effective = max_on_lattice(&effective, eligibility);
                }
            }
        }
    }

    // Step 5.5 — freshness gate (Plan 7e.2; spec §1.2 step 5.5). Narrow one
    // lattice step downward if ANY relevant **effective** Attestation's
    // `lastVerifiedAt` is older than `evaluation_time - maxAttestationStalenessDays`.
    // Relevance signal: Attestation.targets contains `assertion_id`.
    // Effectiveness gate (Plan 7e review F1+F4): revoked or out-of-period
    // Attestations are silently excluded — they're not in the active
    // authority chain so they should not narrow freshness either.
    // Skipped when consumer omits the field OR no evaluation_time given.
    let level_before_freshness = effective.clone();
    let mut freshness_narrowed = false;
    if let (Some(reg), Some(eval_t)) = (consumer, evaluation_time) {
        if let Some(max_days) = reg
            .get("rkaf:maxAttestationStalenessDays")
            .and_then(Value::as_i64)
        {
            if narrow_for_freshness(assertion_id, graph, eval_t, max_days)? {
                effective = step_down_lattice(&effective);
                freshness_narrowed = effective != level_before_freshness;
            }
        }
    }

    // Step 5 — consumer capability cap. Reads from the resolved consumer
    // (passed in by the dispatcher, NOT picked via .next()).
    if let Some(reg) = consumer {
        if let Some(cap) = reg.get("rkaf:capabilityCap").and_then(Value::as_str) {
            effective = min_on_lattice(&effective, cap);
        }
    }

    Ok(ScopeResult {
        level: effective,
        freshness_narrowed,
        level_before_freshness,
    })
}

/// Step 5.5 helper — returns true iff a relevant **effective** Attestation
/// is stale per the BCR's `maxAttestationStalenessDays` window.
///
/// Plan 7e review F1+F4: the universe walked is
/// `effective_attestations_at(graph, evaluation_time)`, NOT every targeting
/// Attestation. Revoked or out-of-period Attestations are silently excluded
/// from the freshness narrowing (they're already excluded from the
/// underlying authority chain by `temporal::effective_at`). This is the
/// only production caller of the Plan 7e.1 helper.
///
/// "Relevant" means `Attestation.targets` contains the assertion IRI.
/// Malformed RFC-3339 on `lastVerifiedAt` propagates as `MalformedTestCase`.
/// Malformed timestamps on `revokedAt` / `effectivePeriod{Start,End}` also
/// propagate via `effective_attestations_at` (same strict posture).
fn narrow_for_freshness(
    assertion_id: &str,
    graph: &Graph,
    evaluation_time: &DateTime<FixedOffset>,
    max_days: i64,
) -> Result<bool, RuntimeError> {
    let cutoff = *evaluation_time - Duration::days(max_days);
    let effective = effective_attestations_at(graph, evaluation_time)?;
    for att in effective {
        let targets_match = att
            .get("rkaf:targets")
            .and_then(Value::as_array)
            .map(|arr| arr.iter().any(|v| v.as_str() == Some(assertion_id)))
            .unwrap_or(false);
        if !targets_match {
            continue;
        }
        let Some(raw) = att.get("rkaf:lastVerifiedAt").and_then(Value::as_str) else {
            // Effective Attestation with no freshness signal → does not
            // satisfy freshness, so it narrows. Author intent: a consumer
            // that declares maxAttestationStalenessDays wants every relevant
            // Attestation to carry lastVerifiedAt.
            return Ok(true);
        };
        let att_id = att
            .get("@id")
            .and_then(Value::as_str)
            .unwrap_or("<unknown>");
        let last = DateTime::parse_from_rfc3339(raw).map_err(|e| {
            RuntimeError::MalformedTestCase(format!(
                "Attestation {att_id} rkaf:lastVerifiedAt value {raw:?} is not valid RFC-3339: {e}"
            ))
        })?;
        if last < cutoff {
            return Ok(true);
        }
    }
    Ok(false)
}

fn step_down_lattice(level: &str) -> String {
    let r = rank(level).unwrap_or(0);
    if r == 0 {
        level.to_string()
    } else {
        LATTICE[r - 1].to_string()
    }
}

/// True iff a PointInTimeException retains this assertion AND its anchor
/// is in the (first) BridgeConsumerRegistration's supportedEvaluationAnchors.
/// Used by reducer step 3 (§1.2) — a stale assertion with a honored PIT
/// keeps its baseline rather than falling to notEligible.
fn has_honored_pit(assertion_id: &str, consumer: Option<&Value>, graph: &Graph) -> bool {
    let supported: Vec<&str> = consumer
        .and_then(|reg| {
            reg.get("rkaf:supportedEvaluationAnchors")
                .and_then(Value::as_array)
        })
        .map(|arr| arr.iter().filter_map(Value::as_str).collect())
        .unwrap_or_default();
    for pit in graph.nodes_by_type("rkaf:PointInTimeException") {
        let retains = pit.get("rkaf:retainsAssertion").and_then(Value::as_str);
        let anchor = pit.get("rkaf:evaluationAnchor").and_then(Value::as_str);
        if retains == Some(assertion_id) && anchor.map(|a| supported.contains(&a)).unwrap_or(false)
        {
            return true;
        }
    }
    false
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn lattice_ordering() {
        assert!(rank("rkaf:officialUse") > rank("rkaf:publicationAllowed"));
        assert!(rank("rkaf:notEligible") < rank("rkaf:searchOnly"));
        assert_eq!(
            max_on_lattice("rkaf:officialUse", "rkaf:searchOnly"),
            "rkaf:officialUse"
        );
        assert_eq!(
            min_on_lattice("rkaf:officialUse", "rkaf:searchOnly"),
            "rkaf:searchOnly"
        );
    }
}
