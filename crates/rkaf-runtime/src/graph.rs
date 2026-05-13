//! Graph view over a JSON-LD `@graph` payload.
//!
//! Builds a per-`@id` index at construction time and exposes the traversal
//! helpers every contract module needs: lookup by `@id`, iterate nodes by
//! `@type` (supports multi-typed nodes), inverse-edge traversal (find every
//! node `M` where `M.<predicate> == target_id`).

use serde_json::Value;
use std::collections::HashMap;

use crate::errors::RuntimeError;

/// Indexed view of a JSON-LD `@graph` array.
///
/// Construction parses every node into a per-`@id` map and a per-`@type`
/// secondary index for `O(1)` lookup. Single-node "documents" (no top-level
/// `@graph`) are accepted with the root treated as the sole node.
pub struct Graph<'a> {
    /// All nodes by `@id`. Nodes without an `@id` are excluded — they cannot
    /// be addressed and therefore cannot participate in inverse-edge
    /// traversal anyway.
    by_id: HashMap<String, &'a Value>,
    /// Secondary index: every node owning each `@type` IRI. Multi-typed nodes
    /// appear under each of their types.
    by_type: HashMap<String, Vec<&'a Value>>,
}

impl<'a> Graph<'a> {
    /// Build a graph view from a JSON-LD payload.
    ///
    /// Accepts either:
    /// - A document with a top-level `@graph` array of objects.
    /// - A single object (treated as a one-node graph).
    pub fn from_payload(doc: &'a Value) -> Result<Self, RuntimeError> {
        let mut by_id: HashMap<String, &Value> = HashMap::new();
        let mut by_type: HashMap<String, Vec<&Value>> = HashMap::new();

        let nodes: Vec<&Value> = if let Some(graph) = doc.get("@graph").and_then(Value::as_array) {
            graph.iter().filter(|n| n.is_object()).collect()
        } else if doc.is_object() {
            vec![doc]
        } else {
            return Err(RuntimeError::Parse(
                "input is neither @graph array nor object".into(),
            ));
        };

        for node in nodes {
            if let Some(id) = node.get("@id").and_then(Value::as_str) {
                by_id.insert(id.to_string(), node);
            }
            // @type may be a string or an array of strings (multi-typed).
            match node.get("@type") {
                Some(Value::String(t)) => by_type.entry(t.clone()).or_default().push(node),
                Some(Value::Array(arr)) => {
                    for v in arr {
                        if let Some(t) = v.as_str() {
                            by_type.entry(t.to_string()).or_default().push(node);
                        }
                    }
                }
                _ => {}
            }
        }

        Ok(Graph { by_id, by_type })
    }

    /// Look up a node by its `@id`. Returns `None` if absent.
    pub fn find(&self, id: &str) -> Option<&'a Value> {
        self.by_id.get(id).copied()
    }

    /// Look up a node by `@id` or error with `MissingNode`.
    pub fn require(&self, id: &str) -> Result<&'a Value, RuntimeError> {
        self.find(id)
            .ok_or_else(|| RuntimeError::MissingNode(id.to_string()))
    }

    /// Iterate every node whose `@type` includes the given IRI.
    pub fn nodes_by_type(&self, type_iri: &str) -> impl Iterator<Item = &'a Value> + '_ {
        self.by_type
            .get(type_iri)
            .into_iter()
            .flat_map(|v| v.iter().copied())
    }

    /// Inverse-edge traversal: find every node where `node.<predicate>`
    /// references `target_id` (either as a single string or as a member of
    /// an array). The reverse of "outgoing edges from `target_id`."
    ///
    /// This is the core primitive used by `CascadeClosureV1`, Rule 8's
    /// "Attestation references this BVR", and similar lookups.
    pub fn incoming(&self, target_id: &str, predicate: &str) -> Vec<&'a Value> {
        let mut out = Vec::new();
        for node in self.by_id.values() {
            match node.get(predicate) {
                Some(Value::String(s)) if s == target_id => out.push(*node),
                Some(Value::Array(arr)) => {
                    for v in arr {
                        if v.as_str() == Some(target_id) {
                            out.push(*node);
                            break;
                        }
                    }
                }
                _ => {}
            }
        }
        out
    }

    /// Count of distinct nodes in the graph.
    pub fn len(&self) -> usize {
        self.by_id.len()
    }

    /// True iff the graph has no addressable nodes.
    pub fn is_empty(&self) -> bool {
        self.by_id.is_empty()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn fixture() -> Value {
        json!({
            "@graph": [
                {"@id": "A", "@type": "rkaf:Assertion"},
                {"@id": "B", "@type": "rkaf:Assertion", "rkaf:supersedesAssertion": "A"},
                {"@id": "W1", "@type": "rkaf:GeneratedWorkProduct", "rkaf:justifiedByAssertion": "A"},
                {"@id": "W2", "@type": "rkaf:GeneratedWorkProduct", "rkaf:justifiedByAssertion": "A"},
                {"@id": "C", "@type": ["rkaf:Authority", "rkaf:Warrant"], "rkaf:authorityKind": "rkaf:statutory"}
            ]
        })
    }

    #[test]
    fn parses_graph_and_indexes_by_id() {
        let payload = fixture();
        let g = Graph::from_payload(&payload).unwrap();
        assert_eq!(g.len(), 5);
        assert!(g.find("A").is_some());
        assert!(g.find("nonexistent").is_none());
    }

    #[test]
    fn multi_typed_node_appears_under_each_type() {
        let payload = fixture();
        let g = Graph::from_payload(&payload).unwrap();
        // C is BOTH Authority and Warrant.
        let auth_nodes: Vec<_> = g.nodes_by_type("rkaf:Authority").collect();
        let warrant_nodes: Vec<_> = g.nodes_by_type("rkaf:Warrant").collect();
        assert_eq!(auth_nodes.len(), 1);
        assert_eq!(warrant_nodes.len(), 1);
        assert_eq!(auth_nodes[0].get("@id").and_then(Value::as_str), Some("C"));
    }

    #[test]
    fn incoming_finds_inverse_edges() {
        let payload = fixture();
        let g = Graph::from_payload(&payload).unwrap();
        // Inverse of justifiedByAssertion from A → W1 and W2.
        let dependents = g.incoming("A", "rkaf:justifiedByAssertion");
        assert_eq!(dependents.len(), 2);
        let ids: Vec<&str> = dependents
            .iter()
            .filter_map(|n| n.get("@id").and_then(Value::as_str))
            .collect();
        assert!(ids.contains(&"W1"));
        assert!(ids.contains(&"W2"));
    }

    #[test]
    fn incoming_handles_array_valued_predicates() {
        let payload = json!({
            "@graph": [
                {"@id": "ev", "@type": "rkaf:LifecycleEvent", "rkaf:appliesTo": ["X", "Y"]}
            ]
        });
        let g = Graph::from_payload(&payload).unwrap();
        let inbound_x = g.incoming("X", "rkaf:appliesTo");
        let inbound_y = g.incoming("Y", "rkaf:appliesTo");
        assert_eq!(inbound_x.len(), 1);
        assert_eq!(inbound_y.len(), 1);
    }

    #[test]
    fn single_object_treated_as_one_node_graph() {
        let payload = json!({"@id": "solo", "@type": "rkaf:Assertion"});
        let g = Graph::from_payload(&payload).unwrap();
        assert_eq!(g.len(), 1);
        assert!(g.find("solo").is_some());
    }
}
