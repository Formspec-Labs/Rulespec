"""Rulespec conformance validator, runnable without a checkout.

Carries the SHACL/schema discovery helpers, the reference-release digest rule,
and the CI gate that applies them (`rulespec-ci-validate`). The rest of
`tools/` is repository tooling and is deliberately not packaged.
"""
