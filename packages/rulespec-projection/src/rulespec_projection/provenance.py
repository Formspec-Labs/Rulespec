"""Run provenance and the digests every projected identity is built from.

Copied at the name from spicy-regs ``ontology/common.py`` at ``8d9e7a2``; that
module imports pyarrow and loguru at the top, so it cannot come along. These
five names are the whole of what the projection reads from it.

``canonical_json`` stays a copy rather than a call into
``rulespec_artifacts.canonical_json_bytes``. The two encoders agree byte for
byte on strings, integers, booleans, nulls, lists, and objects (20,000 random
values compared 2026-09-05), so reuse would have been safe for today's inputs;
keeping the copy makes this package depend on nothing and keeps every digest
identical to the producer's by construction rather than by measurement.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone


def iso_now() -> str:
    """Return the current UTC instant in a stable ISO-8601 representation."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class RunContext:
    """Provenance values shared by all rows produced in one pipeline run."""

    run_id: str
    asserted_at: str

    @classmethod
    def resolve(
        cls,
        *,
        run_id: str | None = None,
        asserted_at: str | None = None,
        prefix: str = "ontology",
    ) -> RunContext:
        now = asserted_at or iso_now()
        configured = run_id or os.environ.get("ONTOLOGY_RUN_ID")
        if configured:
            return cls(run_id=configured, asserted_at=now)
        timestamp = now.replace("-", "").replace(":", "").replace("+", "").replace("Z", "Z")
        return cls(run_id=f"{prefix}-{timestamp}", asserted_at=now)

    def provenance(
        self,
        *,
        method: str,
        actor_id: str,
        supersedes_id: str | None = None,
    ) -> dict[str, str | None]:
        return {
            "method": method,
            "actor_id": actor_id,
            "run_id": self.run_id,
            "asserted_at": self.asserted_at,
            "supersedes_id": supersedes_id,
        }


def stable_id(prefix: str, *parts: object, length: int = 24) -> str:
    """Return a stable opaque id derived from the supplied identity parts."""
    encoded = "\x1f".join("" if part is None else str(part) for part in parts).encode("utf-8")
    digest = hashlib.sha256(encoded).hexdigest()[:length]
    return f"{prefix}_{digest}"


def text_digest(*parts: object) -> str:
    """SHA-256 digest used to detect changed source text between tagging runs."""
    encoded = "\x1f".join("" if part is None else str(part) for part in parts).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def canonical_json(value: object) -> str:
    """Serialize JSON deterministically for stable ids, comparisons, and Parquet.

    ``allow_nan=False`` because the default spells NaN and the infinities as
    ``NaN``/``Infinity``, which no JSON reader accepts: a digest taken over that
    text is stable and the artifact it describes is unparseable. Raising says so
    where the value enters, instead of in whatever reads the column back.
    """
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
