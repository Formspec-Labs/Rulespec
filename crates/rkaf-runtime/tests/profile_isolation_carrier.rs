//! Profile-isolation semantic carrier test — the RUNTIME half.
//!
//! Category: **profile isolation** (`spec/rkaf-behavior.md` §2.1, the reshape
//! note after the cascade-edge table). The contract half — kernel-only versus
//! composed validation differing exactly where documented — lives in
//! `tools/test_semantic_carriers.py::ProfileIsolationCarrierTests`. This file
//! covers the half that only the runtime can answer: whether a
//! profile-contributed lifecycle kind still reaches the kernel's behavioral
//! paths.
//!
//! `constraints/profiles/us-rulemaking/us-lifecycle-event.cue` contributes
//! twelve `rkaf:proceeding*` kinds to the SHARED `rkaf:LifecycleEvent` class
//! rather than minting a parallel event class
//! (`spec/rkaf-rulemaking.md` §6). `stale::should_be_stale` finds events by
//! `graph.nodes_by_type("rkaf:LifecycleEvent")`, so that decision is what keeps
//! a `rkaf:proceedingFinal` event visible to the stale transition.
//!
//! **What this file proves, and what it does not.** Every payload below states
//! `"@type": "rkaf:LifecycleEvent"` as a literal, so what is under test here is
//! the CONSEQUENT: given an event that arrives under the kernel's `@type`, a
//! profile-contributed `rkaf:lifecycleEventKind` reaches the kernel's stale
//! path, gets the same `appliesTo` scoping, and gets the same
//! safe-migration exemption. It cannot see the ANTECEDENT failing: were the
//! profile to mint `rkaf:USLifecycleEvent` as its own `@type` tomorrow, these
//! four tests would keep passing against a hand-written `rkaf:LifecycleEvent`
//! payload no producer would ever emit. That half is guarded on the contract
//! side, by
//! `tools/test_semantic_carriers.py::ProfileIsolationCarrierTests::test_the_profile_overlay_keeps_the_kernel_class`,
//! which reads the profile's own binding and shape targets. Both halves are
//! needed; neither subsumes the other.
//!
//! One more scope note: `stale::should_be_stale` never reads
//! `rkaf:lifecycleEventKind` at all — it keys on the `@type` and on
//! `rkaf:appliesTo`. The three profile kinds below are therefore a sample of
//! the profile's value set, not three independent facts about the runtime.

// Rust guideline compliant 2026-07-26

use rkaf_runtime::{graph::Graph, stale};
use serde_json::{json, Value};

/// A one-event graph whose `rkaf:lifecycleEventKind` is the caller's value.
/// Everything else is held constant so the kind is the only variable.
fn graph_payload(kind: &str) -> Value {
    json!({
        "@graph": [
            {
                "@id": "urn:rkaf:test:lifecycle:profile-kind",
                "@type": "rkaf:LifecycleEvent",
                "rkaf:lifecycleEventKind": kind,
                "rkaf:effectiveDate": "2026-03-11T00:00:00Z",
                "rkaf:emittedBy": "urn:rkaf:test:actor:agency",
                "rkaf:appliesTo": ["urn:rkaf:test:assertion:target"]
            },
            {
                "@id": "urn:rkaf:test:assertion:target",
                "@type": "rkaf:RelationshipAssertion",
                "rkaf:assertionOrigin": "rkaf:humanAsserted",
                "rkaf:assertsSubject": "urn:rkaf:test:subject",
                "rkaf:assertsPredicate": "urn:rkaf:test:predicate",
                "rkaf:assertsObject": "urn:rkaf:test:object",
                "rkaf:assertionPolarity": "rkaf:affirmed"
            }
        ]
    })
}

fn stale_for(kind: &str) -> bool {
    let payload = graph_payload(kind);
    let graph = Graph::from_payload(&payload).expect("build graph");
    stale::should_be_stale("urn:rkaf:test:assertion:target", None, &graph)
}

/// A kernel-owned kind drives the stale transition. This is the control: if it
/// ever fails, the profile assertions below prove nothing.
#[test]
fn a_kernel_lifecycle_kind_drives_the_stale_transition() {
    assert!(
        stale_for("rkaf:amendment"),
        "a kernel `rkaf:amendment` event applying to an assertion must make it \
         staleForCurrentUse (spec/rkaf-behavior.md §5)"
    );
}

/// The load-bearing assertion: an event carrying a profile-contributed kind
/// under the kernel's `@type` reaches the SAME path a kernel kind does.
///
/// The `@type` in the payload is the kernel's because `#USLifecycleEvent`
/// composes `#LifecycleEvent` and keeps it. That THIS is still the profile's
/// `@type` is asserted where it can be read off the profile —
/// `ProfileIsolationCarrierTests::test_the_profile_overlay_keeps_the_kernel_class`
/// — not here, where it is a constant in the fixture.
#[test]
fn a_profile_lifecycle_kind_drives_the_same_stale_transition() {
    for kind in [
        "rkaf:proceedingFinal",
        "rkaf:proceedingWithdrawn",
        "rkaf:proceedingVacated",
    ] {
        assert!(
            stale_for(kind),
            "a `rkaf:LifecycleEvent` carrying profile-contributed kind \
             `{kind}` must reach the kernel stale path exactly as a kernel \
             kind does — the runtime keys on `@type` and `rkaf:appliesTo`, so \
             nothing about a profile VALUE may change the transition. The \
             separate question of whether the profile still emits this `@type` \
             is guarded by \
             `tools/test_semantic_carriers.py::ProfileIsolationCarrierTests::\
             test_the_profile_overlay_keeps_the_kernel_class`."
        );
    }
}

/// Direction still matters at the runtime layer: `appliesTo` names the affected
/// node, and an event that applies to something else does not make this
/// assertion stale. Without this, the assertion above would also pass on a
/// runtime that returned `true` unconditionally.
#[test]
fn an_event_applying_elsewhere_leaves_the_assertion_fresh() {
    let payload = graph_payload("rkaf:proceedingFinal");
    let graph = Graph::from_payload(&payload).expect("build graph");
    assert!(
        !stale::should_be_stale("urn:rkaf:test:assertion:unrelated", None, &graph),
        "a lifecycle event must only stale the nodes its `rkaf:appliesTo` names"
    );
}

/// The consumer's declared automatic migrations still exempt the assertion when
/// the profile kind carries one — the profile contributes a VALUE, and no value
/// gets its own escape from the §5 rule.
#[test]
fn a_supported_migration_exempts_a_profile_kind_event_too() {
    let mut payload = graph_payload("rkaf:proceedingFinal");
    payload["@graph"][0]["rkaf:safeAutomaticMigration"] = json!("rkaf:scheme-rename");
    let graph = Graph::from_payload(&payload).expect("build graph");
    let consumer = json!({
        "@id": "urn:rkaf:test:consumer",
        "@type": "rkaf:BridgeConsumerRegistration",
        "rkaf:supportedAutomaticMigrations": ["rkaf:scheme-rename"]
    });
    assert!(
        !stale::should_be_stale("urn:rkaf:test:assertion:target", Some(&consumer), &graph),
        "a declared, consumer-supported safe automatic migration exempts the \
         affected assertion regardless of which module declared the kind"
    );
}
