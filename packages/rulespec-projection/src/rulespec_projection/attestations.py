"""Contract-shaped ``rkaf:Attestation`` rows for the model layer's production claim.

The closure of ``attestation_row`` and ``ATTESTOR_KIND_AI_MODEL`` from
spicy-regs ``ontology/attestations.py`` at ``8d9e7a2`` (146 lines of a
544-line module whose remainder reads and writes Parquet), plus the one
exception class it raises from ``ontology/invariants.py``.

The rule these rows follow is rulespec ``spec/rkaf-core.md`` §3.1/§4.7.3 and
the "attestation as a table" pattern in ``spec/rkaf-conformance.md``: one row
is one Attestation node, the row's own identifier is its identity, the attested
record appears only in the target column, and the decision and attestor kind
are drawn from the closed enums below.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence

from .provenance import RunContext, canonical_json, stable_id


class OntologyInvariantError(ValueError):
    """Raised when an ontology table would violate a published invariant."""


DECISION_APPROVED = "rkaf:approved"


DECISION_APPROVED_WITH_CONDITIONS = "rkaf:approvedWithConditions"


DECISION_REJECTED = "rkaf:rejected"


DECISION_ABSTAINED = "rkaf:abstained"


DECISION_ADVISORY = "rkaf:advisory"


DECISION_ENDORSED_FOR_REVIEW = "rkaf:endorsedForReview"


DECISION_FLAGGED_FOR_REVIEW = "rkaf:flaggedForReview"


DECISIONS: tuple[str, ...] = (
    DECISION_APPROVED,
    DECISION_APPROVED_WITH_CONDITIONS,
    DECISION_REJECTED,
    DECISION_ABSTAINED,
    DECISION_ADVISORY,
    DECISION_ENDORSED_FOR_REVIEW,
    DECISION_FLAGGED_FOR_REVIEW,
)


ATTESTOR_KIND_HUMAN_USER = "rkaf:humanUser"


ATTESTOR_KIND_AI_MODEL = "rkaf:aiModel"


ATTESTOR_KIND_AI_AGENT = "rkaf:aiAgent"


ATTESTOR_KIND_AUTOMATED_PARSER = "rkaf:automatedParser"


ATTESTOR_KIND_TEAM = "rkaf:team"


ATTESTOR_KIND_ORGANIZATION = "rkaf:organization"


ATTESTOR_KIND_COMMUNITY = "rkaf:community"


ATTESTOR_KIND_FORMAL_REVIEWER = "rkaf:formalReviewer"


ATTESTOR_KIND_CONCEPT_MINTING_AUTHORITY = "rkaf:conceptMintingAuthority"


ATTESTOR_KINDS: tuple[str, ...] = (
    ATTESTOR_KIND_HUMAN_USER,
    ATTESTOR_KIND_AI_MODEL,
    ATTESTOR_KIND_AI_AGENT,
    ATTESTOR_KIND_AUTOMATED_PARSER,
    ATTESTOR_KIND_TEAM,
    ATTESTOR_KIND_ORGANIZATION,
    ATTESTOR_KIND_COMMUNITY,
    ATTESTOR_KIND_FORMAL_REVIEWER,
    ATTESTOR_KIND_CONCEPT_MINTING_AUTHORITY,
)


_METHOD_BY_ATTESTOR_KIND: dict[str, str] = {
    ATTESTOR_KIND_HUMAN_USER: "human",
    ATTESTOR_KIND_AI_MODEL: "llm",
    ATTESTOR_KIND_AI_AGENT: "llm",
    ATTESTOR_KIND_AUTOMATED_PARSER: "deterministic",
    ATTESTOR_KIND_TEAM: "human",
    ATTESTOR_KIND_ORGANIZATION: "human",
    ATTESTOR_KIND_COMMUNITY: "human",
    ATTESTOR_KIND_FORMAL_REVIEWER: "human",
    ATTESTOR_KIND_CONCEPT_MINTING_AUTHORITY: "human",
}


class AttestationError(OntologyInvariantError):
    """Raised when a row would break the tabular attestation pattern."""


def _text(value: object) -> str:
    return "" if value is None else str(value).strip()


def parse_targets(value: object) -> list[str]:
    """Parse ``target_ids_json`` into its target identities.

    Raises :class:`AttestationError` unless the value is a JSON array of at
    least one distinct, non-blank identity (rule 4: targets is the join, and it
    is many — never zero).
    """
    if isinstance(value, (list, tuple)):
        parsed: object = list(value)
    else:
        text = _text(value)
        if not text:
            raise AttestationError("attestation targets are empty; rkaf:targets requires at least one target")
        try:
            parsed = json.loads(text)
        except (TypeError, json.JSONDecodeError) as exc:
            raise AttestationError(f"attestation targets are not valid JSON: {value!r}") from exc
    if not isinstance(parsed, list):
        raise AttestationError(f"attestation targets must be a JSON array, got {type(parsed).__name__}")
    targets = [_text(item) for item in parsed]
    if not targets:
        raise AttestationError("attestation targets are empty; rkaf:targets requires at least one target")
    if any(not target for target in targets):
        raise AttestationError(f"attestation targets contain a blank identity: {parsed!r}")
    if len(set(targets)) != len(targets):
        raise AttestationError(f"attestation targets contain duplicates: {parsed!r}")
    return targets


def canonical_targets(targets: object) -> str:
    """Serialize target identities deterministically for storage and identity."""
    return canonical_json(sorted(parse_targets(targets)))


def attestation_identity(row: Mapping[str, object]) -> str:
    """Derive the stable attestation id from the decision the row records.

    ``revoked_at`` is excluded on purpose: revoking an attestation must not
    change which attestation it is.
    """
    return stable_id(
        "attestation",
        _text(row.get("attestor_id")),
        _text(row.get("attestor_kind")),
        _text(row.get("decision")),
        _text(row.get("attestation_scope")),
        _text(row.get("attested_at")),
        canonical_targets(row.get("target_ids_json") or ""),
        _text(row.get("supersedes_id")) or None,
    )


def attestation_row(
    *,
    attestor_id: str,
    attestor_kind: str,
    targets: Sequence[str],
    decision: str,
    attestation_scope: str,
    context: RunContext,
    attested_at: str | None = None,
    rationale: str | None = None,
    supersedes_id: str | None = None,
    method: str | None = None,
    actor_id: str | None = None,
) -> dict:
    """Build one validated ``rkaf:Attestation`` row.

    ``attestor_id`` is the party that decided; ``actor_id`` (provenance) is the
    process that wrote the row and defaults to the attestor.  ``method``
    defaults to the honest method for the attestor kind (``llm`` for a model or
    agent, ``human`` for a person or body, ``deterministic`` for a parser).
    """
    if decision not in DECISIONS:
        raise AttestationError(f"decision {decision!r} is outside the closed rkaf:AttestationDecision enum {DECISIONS}")
    if attestor_kind not in ATTESTOR_KINDS:
        raise AttestationError(
            f"attestor_kind {attestor_kind!r} is outside the closed rkaf:AttestorKind enum {ATTESTOR_KINDS}"
        )
    if not _text(attestor_id):
        raise AttestationError("attestation requires an attestor identity")
    if not _text(attestation_scope):
        raise AttestationError("attestation requires a scope naming what the decision covers")
    target_ids_json = canonical_targets(targets)
    decided_at = _text(attested_at) or context.asserted_at
    row = {
        "attestor_id": _text(attestor_id),
        "attestor_kind": attestor_kind,
        "target_ids_json": target_ids_json,
        "decision": decision,
        "attestation_scope": _text(attestation_scope),
        "attested_at": decided_at,
        "revoked_at": None,
        "rationale": rationale,
        **context.provenance(
            method=method or _METHOD_BY_ATTESTOR_KIND[attestor_kind],
            actor_id=_text(actor_id) or _text(attestor_id),
            supersedes_id=supersedes_id,
        ),
    }
    return {"attestation_id": attestation_identity(row), **row}
