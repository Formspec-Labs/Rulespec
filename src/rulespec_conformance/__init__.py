"""Rulespec conformance validator, runnable without a checkout.

Carries the SHACL/schema discovery helpers, the reference-release digest rule,
and the CI gate that applies them (`rulespec-ci-validate`). The rest of
`tools/` is repository tooling and is deliberately not packaged.

`rulespec_conformance.contract` is the other half of the same data: the
compiled schemas, the SHACL, the JSON-LD context and the rkaf vocabulary,
exported for consumers that AUTHOR Rulespec data rather than validate
someone else's.
"""
