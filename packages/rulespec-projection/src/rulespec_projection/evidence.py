"""Exact-quote evidence resolution against a stored text field.

``resolve_exact_evidence_offsets`` and its result type, copied from spicy-regs
``ontology/llm.py`` at ``8d9e7a2`` (54 lines of a module that otherwise
imports loguru and, lazily, openai). A quote resolves only when it occurs
exactly once; the projection never guesses which occurrence a claim meant.
"""

from __future__ import annotations

from dataclasses import dataclass


EVIDENCE_ALIGNMENT_PROVIDED = "provided-offsets"


EVIDENCE_ALIGNMENT_UNIQUE_EXACT = "unique-exact-match"


EVIDENCE_OFFSET_UNIT = "unicode-codepoints"


EVIDENCE_OFFSET_INTERVAL = "half-open"


@dataclass(frozen=True)
class EvidenceOffsetResolution:
    """An exact, deterministic alignment of quoted evidence to one field.

    ``start`` and ``end`` index ``field_text`` in :data:`EVIDENCE_OFFSET_UNIT`
    over the :data:`EVIDENCE_OFFSET_INTERVAL` interval — the same units the
    ``str`` they came from uses, so ``field_text[start:end]`` is the evidence
    by construction. They are not UTF-8 byte offsets and must not be written
    into a field that holds those.
    """

    start: int
    end: int
    method: str
    unit: str = EVIDENCE_OFFSET_UNIT
    interval: str = EVIDENCE_OFFSET_INTERVAL


def resolve_exact_evidence_offsets(
    field_text: str,
    evidence_text: str,
    start: int | None,
    end: int | None,
) -> EvidenceOffsetResolution | None:
    """Verify provider offsets or repair one unambiguous verbatim match.

    Offsets in and out are :data:`EVIDENCE_OFFSET_UNIT` into ``field_text``.
    """
    if not evidence_text:
        return None
    if (
        isinstance(start, int)
        and not isinstance(start, bool)
        and isinstance(end, int)
        and not isinstance(end, bool)
        and start >= 0
        and end > start
        and end <= len(field_text)
        and field_text[start:end] == evidence_text
    ):
        return EvidenceOffsetResolution(
            start=start,
            end=end,
            method=EVIDENCE_ALIGNMENT_PROVIDED,
        )
    first = field_text.find(evidence_text)
    if first < 0 or field_text.find(evidence_text, first + 1) >= 0:
        return None
    return EvidenceOffsetResolution(
        start=first,
        end=first + len(evidence_text),
        method=EVIDENCE_ALIGNMENT_UNIQUE_EXACT,
    )
