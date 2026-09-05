"""Project one source document into a gate-valid Rulespec (RKAF) JSON-LD object.

This is the deterministic layer of the spicy-regs document producer
(``docpipeline/rkaf_projection.py`` at ``8d9e7a2``), moved here so the format
owner ships the reference producer beside its verifier. The split it enforces
is the whole point, and it is not negotiable:

**The deterministic layer mints every identity.** Artifact identity and digests
arrive on the :class:`SourceArtifact` the caller supplies and are never
re-derived here. Fragment coordinates are the stored source field's own
``[start, end)`` code-point offsets, and every one of them is proven by
re-slicing the stored text and comparing the SHA-256 of the slice against the
digest baked into the carrier-local URN. Canonical CFR/USC/RIN/FR-doc/regs.gov
IRIs come from :mod:`rulespec_projection.citations`. Relationship assertions
are re-serialized rows of published tables reached through
:class:`PublishedTables`; nothing is re-parsed out of prose to rediscover an
edge a transform already produced.

**The model layer supplies judgments only, and it lives with the caller.** What
crosses into this module is a :class:`ModelLayer` of already-grounded candidate
rows. :func:`verify_candidate_rows` re-slices every offset against the stored
text one more time and turns the survivors into ``rkaf:ConceptAssignment``
nodes. A model-supplied value that cannot be verified against source text or a
supplied vocabulary row is dropped with a recorded reason; it is never repaired.

Text-state convention (load-bearing, and the one place this projection has to
choose): an RKAF ``rkaf:Artifact`` names ONE immutable state, while a source
artifact spans several stored fields with independent digests. Each profile
therefore declares one *projected evidence field*. ``rkaf:hasContentDigest``
and every fragment coordinate in the emitted document are taken over that field
alone, offsets in Unicode code points, half-open ``[start, end)``, matching
rulespec Core §4.2. Evidence landing in any other field is refused rather than
silently re-based, and the count of such refusals is reported.

Two seams are declared rather than implemented, because the producer's own
implementations read Parquet: :class:`SourceArtifact` names the six attributes
the projection reads from a source artifact, and :class:`PublishedTables` names
the one query it makes of the published tables. spicy-regs' own
``SourceArtifact`` and ``PublishedTables`` satisfy both unchanged;
:class:`InMemoryTables` serves callers that already hold rows.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from .attestations import ATTESTOR_KIND_AI_MODEL, DECISION_ENDORSED_FOR_REVIEW, attestation_row
from .citations import (
    canonical_cfr_iri,
    canonical_pl_iri,
    canonical_regsgov_iri,
    canonical_rin_iri,
    canonical_usc_iri,
    docket_reference_as_stated,
    federal_register_identifier,
    normalize_docket_reference,
    parse_authority_citation,
    parse_cfr_citation,
)
from .evidence import resolve_exact_evidence_offsets
from .provenance import RunContext, canonical_json, stable_id, text_digest


@runtime_checkable
class SourceArtifact(Protocol):
    """One exact, immutable source state, as far as the projection reads it.

    These six attributes are the whole of what the deterministic layer takes
    from a source artifact (measured over the moved functions at ``8d9e7a2``).
    ``raw_fields`` maps a field name such as ``federal_register.body_html`` to
    its stored text; ``field_sha256`` maps the same names to the SHA-256 of that
    text as UTF-8; ``content_sha256`` is the producer-scoped digest of the whole
    state, recorded but never used as ``rkaf:hasContentDigest``.
    """

    @property
    def artifact_id(self) -> str: ...

    @property
    def content_sha256(self) -> str: ...

    @property
    def subject_id(self) -> str: ...

    @property
    def profile_id(self) -> str: ...

    @property
    def raw_fields(self) -> Mapping[str, str]: ...

    @property
    def field_sha256(self) -> Mapping[str, str]: ...


class PublishedTables(Protocol):
    """Read-only equality lookup over the published relationship tables.

    ``rows("proceedings")`` returns every row; ``rows("dockets", docket_id=x)``
    returns the rows whose columns equal every keyword after the same
    whitespace-and-sentinel cleaning the projection applies to its own values
    (see :func:`_clean`). A table that does not exist reads as empty.
    """

    def rows(self, table: str, **equals: Any) -> list[dict[str, Any]]: ...


ASSERTION_ORIGIN_DETERMINISTIC = "rkaf:deterministicExtraction"


ASSERTION_ORIGIN_MODEL = "rkaf:aiSuggested"


REQUEST_CONTRACT_DIGEST_REQUIRED_FOR = frozenset({"rkaf:modelExtraction"})


EMIT_DOCUMENT_DOCKET_EDGE = True


DOCUMENT_DOCKET_PREDICATE = "rkaf:publishedInDocket"


EMIT_PROFILE_EDGE_PROJECTIONS = True


MODEL_ATTESTATION_DECISION = DECISION_ENDORSED_FOR_REVIEW


MODEL_USAGE_ELIGIBILITY = "rkaf:reviewQueueOnly"


DETERMINISTIC_USAGE_ELIGIBILITY = "rkaf:localOperationalUse"


PROJECTION_SCHEMA_VERSION = "rkaf-document-projection-v2"


CANDIDATE_SELECTION_STATE = "notConfigured"


CANDIDATE_OUTPUT_MODE = "diagnosticReviewQueue"


_RULESPEC_VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$")


_RULESPEC_REVISION_PATTERN = re.compile(r"^[0-9a-f]{40}$")


_CONSTRAINT_DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")


FRAGMENT_URN_PATTERN = re.compile(
    r"^urn:rkaf:fragment:([A-Za-z0-9._~-]|%[0-9A-F]{2})+:(0|[1-9][0-9]*):(0|[1-9][0-9]*):sha256-[0-9a-f]{64}$"
)


SOURCE_EXACT_EVIDENCE_GRADE = "source-exact"


_SELECTOR_KIND = "oa:TextPositionSelector"


_COORDINATE_SYSTEM = "rkaf:unicode-codepoint"


_EVIDENCE_SCHEME = "rkaf:carrier-local-fragment"


class ProjectionError(RuntimeError):
    """The projection cannot be assembled from the inputs it was given."""


class OffsetVerificationError(ProjectionError):
    """A fragment's stored offsets do not slice the text they claim to.

    This aborts. It is never repaired and never downgraded to a rejection row:
    a fragment whose coordinates lie is not a weaker fragment, it is a false
    statement about a document, and every digest downstream of it is worthless.
    """


def encode_for_uri(value: str) -> str:
    """Percent-encode outside the RFC 3986 unreserved set, uppercase hex.

    This is SPARQL's ``ENCODE_FOR_URI``, which is the encoding Core §4.2 names
    for the artifact component and the encoding
    ``CarrierLocalFragmentUrnSourceAgreementShape`` compares against.
    """
    out: list[str] = []
    for character in value:
        if (character.isascii() and character.isalnum()) or character in "-._~":
            out.append(character)
        else:
            out.extend(f"%{byte:02X}" for byte in character.encode("utf-8"))
    return "".join(out)


def fragment_urn(artifact_iri: str, start: int, end: int, region_sha256: str) -> str:
    """Mint the carrier-local fragment URN for one verified region."""
    return f"urn:rkaf:fragment:{encode_for_uri(artifact_iri)}:{start}:{end}:sha256-{region_sha256}"


@dataclass(frozen=True)
class ProjectedFragment:
    """One region of the projected evidence field, proven by re-slicing."""

    key: str
    source_field: str
    start: int
    end: int
    text: str
    text_sha256: str
    urn: str

    @property
    def selector_iri(self) -> str:
        return f"{self.urn}#selector"


def verify_fragment(
    artifact: SourceArtifact,
    *,
    key: str,
    source_field: str,
    start: int,
    end: int,
    artifact_iri: str,
    expected_text: str | None = None,
) -> ProjectedFragment:
    """Re-slice the stored field and mint the URN, or abort.

    Every value in the returned fragment is recomputed from
    ``artifact.raw_fields[source_field]``. Nothing is trusted: not the caller's
    offsets, not a model's quote, not a gold row's stored digest.
    """
    text = artifact.raw_fields.get(source_field)
    if text is None:
        raise OffsetVerificationError(f"{key}: the artifact carries no field {source_field!r}")
    if not (0 <= start <= end <= len(text)):
        raise OffsetVerificationError(
            f"{key}: [{start},{end}) is outside {source_field} (length {len(text)} code points)"
        )
    region = text[start:end]
    if expected_text is not None and region != expected_text:
        raise OffsetVerificationError(
            f"{key}: {source_field}[{start}:{end}] is {region!r}, not the expected {expected_text!r}"
        )
    digest = text_digest(region)
    urn = fragment_urn(artifact_iri, start, end, digest)
    if not FRAGMENT_URN_PATTERN.match(urn):
        raise OffsetVerificationError(f"{key}: minted URN violates the Core §4.2 grammar: {urn}")
    return ProjectedFragment(
        key=key,
        source_field=source_field,
        start=start,
        end=end,
        text=region,
        text_sha256=digest,
        urn=urn,
    )


def ground_literal(
    artifact: SourceArtifact,
    *,
    key: str,
    source_field: str,
    artifact_iri: str,
    surface_forms: Sequence[str],
) -> ProjectedFragment | None:
    """Locate a citation's own words in the projected field, or give up.

    Grounding reuses :func:`resolve_exact_evidence_offsets`, so a surface form
    that appears zero times or more than once is not grounded. An assertion
    whose evidence cannot be pinned to one unambiguous region simply gets no
    ``rkaf:EvidenceBinding``; it keeps its extraction provenance and says
    nothing it cannot show.
    """
    text = artifact.raw_fields.get(source_field)
    if not text:
        return None
    for form in surface_forms:
        if not form:
            continue
        resolution = resolve_exact_evidence_offsets(text, form, None, None)
        if resolution is None:
            continue
        return verify_fragment(
            artifact,
            key=key,
            source_field=source_field,
            start=resolution.start,
            end=resolution.end,
            artifact_iri=artifact_iri,
            expected_text=form,
        )
    return None


@dataclass(frozen=True)
class ExtractionActivitySpec:
    """One ``rkaf:ExtractionActivity``: which run produced which candidates."""

    key: str
    method: str
    run_id: str
    actor_id: str
    version: str
    instructions: str
    input_row: Mapping[str, Any]
    model_ref: str | None = None
    prompt_ref: str | None = None


@dataclass(frozen=True)
class DeterministicEdge:
    """One relationship a published table already asserts."""

    key: str
    subject: str
    predicate: str
    object: str
    table: str
    record_key: str
    activity_key: str
    asserted_at: str
    surface_forms: tuple[str, ...] = ()
    claimant_identity: str | None = None
    profile_edge: tuple[str, str, str] | None = None
    """``(node IRI, predicate, object IRI)`` — the plain profile edge this
    assertion reifies, emitted alongside it while :data:`EMIT_PROFILE_EDGE_PROJECTIONS`
    holds (finding G5)."""


@dataclass(frozen=True)
class ProfileFacts:
    """Everything a profile contributes that is not the model's business."""

    profile_id: str
    artifact_iri: str
    evidence_field: str
    artifact_identifiers: tuple[str, ...]
    artifact_schemes: tuple[str, ...]
    regulatory_identifier: str | None = None
    regulatory_scheme: str | None = None
    published_in_proceeding: tuple[str, ...] = ()
    published_in_docket: tuple[str, ...] = ()
    """Docket IRIs this document was filed under (rulemaking §5.3). Every one is
    a Docket whose identity another published row establishes — never one minted
    from the document alone."""
    extra_nodes: tuple[Mapping[str, Any], ...] = ()
    edges: tuple[DeterministicEdge, ...] = ()
    activities: tuple[ExtractionActivitySpec, ...] = ()
    claimant_identity: str | None = None
    notes: tuple[str, ...] = ()


def request_contract_digest(spec: ExtractionActivitySpec) -> tuple[str, str]:
    """Digest the request contract and the input row for one extraction activity.

    Recipe: SHA-256 over the canonical JSON of
    ``{instructions, actor_id, run_id, input_row}`` with every input value
    stringified. Returns ``(contract digest, input-row digest)``.

    Since finding G4 landed only the contract digest of a genuinely
    request-shaped run is emitted (see
    :data:`REQUEST_CONTRACT_DIGEST_REQUIRED_FOR`); the input-row digest is
    unconditional, because every activity really does have inputs.
    """
    clean = {str(key): (None if value is None else str(value)) for key, value in spec.input_row.items()}
    contract = {
        "instructions": spec.instructions,
        "actor_id": spec.actor_id,
        "run_id": spec.run_id,
        "input_row": clean,
    }
    return text_digest(canonical_json(contract)), text_digest(canonical_json(clean))


def _json_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value]
    text = str(value).strip()
    if not text or text in {"None", "null"}:
        return []
    try:
        parsed = json.loads(text)
    except (TypeError, ValueError):
        return [text]
    if isinstance(parsed, list):
        return [str(item) for item in parsed]
    return [str(parsed)]


def _clean(value: object) -> str:
    text = "" if value is None else str(value).strip()
    return "" if text in {"None", "nan", "null"} else text


_FR_AGENCY_IRI = "https://www.federalregister.gov/agencies/"


_AGENDA_STAGE_BY_RULE_STAGE = {
    "prerule stage": "rkaf:agendaPrerule",
    "proposed rule stage": "rkaf:agendaProposed",
    "final rule stage": "rkaf:agendaFinal",
    "long-term actions": "rkaf:agendaLongterm",
    "completed actions": "rkaf:agendaCompleted",
}


_AGENDA_PRIORITY_BY_CATEGORY = {
    "economically significant": "rkaf:agendaPriorityEconomicallySignificant",
    "other significant": "rkaf:agendaPriorityOtherSignificant",
    "substantive, nonsignificant": "rkaf:agendaPrioritySubstantiveNonsignificant",
    "routine and frequent": "rkaf:agendaPriorityRoutineFrequent",
    "info./admin./other": "rkaf:agendaPriorityInfoAdminOther",
}


_PROCEEDING_STAGE_BY_CURRENT = {
    "prerule": "rkaf:proceedingPrerule",
    "proposed": "rkaf:proceedingProposed",
    "supplemental": "rkaf:proceedingSupplemental",
    "final": "rkaf:proceedingFinal",
    "withdrawn": "rkaf:proceedingWithdrawn",
    "longterm": "rkaf:proceedingLongterm",
    "long-term": "rkaf:proceedingLongterm",
    "concluded": "rkaf:proceedingConcluded",
}


def _cfr_iri(row: Mapping[str, Any]) -> str | None:
    title, part = _clean(row.get("cfr_title")), _clean(row.get("cfr_part"))
    if not title or not part:
        return None
    try:
        return canonical_cfr_iri(title, part, _clean(row.get("cfr_section")) or None)
    except ValueError:
        return None


def _authority_iri(row: Mapping[str, Any]) -> str | None:
    try:
        if _clean(row.get("authority_type")) == "usc":
            return canonical_usc_iri(_clean(row.get("usc_title")), _clean(row.get("usc_section")))
        if _clean(row.get("pl_number")):
            return canonical_pl_iri(_clean(row.get("pl_number")))
    except ValueError:
        return None
    return None


def _document_docket_iris(
    row: Mapping[str, Any],
    *,
    tables: PublishedTables,
    known_docket_iris: Sequence[str],
) -> tuple[list[str], list[dict[str, Any]], list[str]]:
    """Resolve ``federal_register.docket_ids_json`` into Docket IRIs (§5.3).

    Returns ``(iris, docket nodes to add, notes)``.

    Two refusals, both because §5.3 forbids minting the Docket node from the
    document alone — an edge to a container with no ``rkaf:hasDocketIdentifier``
    names nothing. A value whose label-stripped remainder is not a syntactically
    valid regulations.gov identifier is refused, and so is one that no OTHER
    published row establishes: a docket the proceedings path already
    materialized, or a ``dockets.parquet`` row carrying that id. The document's
    own say-so is never enough to bring a Docket into existence.
    """
    iris: list[str] = []
    nodes: list[dict[str, Any]] = []
    notes: list[str] = []
    already = set(known_docket_iris)
    for raw in _json_list(row.get("docket_ids_json")):
        # The docket-aware cleaning, shared with the fr_docket_links transform
        # so the two readers of this column agree byte for byte on what states
        # nothing: it removes the same sentinels _clean does, plus a bare label.
        stated = docket_reference_as_stated(raw)
        if not stated:
            continue
        identifier = normalize_docket_reference(stated)
        if identifier is None:
            notes.append(f"document docket identifier {stated!r} is not expressible in rkaf:us-regsgov")
            continue
        docket_iri = canonical_regsgov_iri(identifier)
        if docket_iri in iris:
            continue
        if docket_iri in already:
            iris.append(docket_iri)
            continue
        docket_id = docket_iri.rsplit(":", 1)[-1]
        if not tables.rows("dockets", docket_id=docket_id):
            notes.append(
                f"document docket {docket_id} is stated by the document but no published dockets row "
                "carries it, so rulemaking §5.3 forbids minting the Docket node and the edge is dropped"
            )
            continue
        iris.append(docket_iri)
        nodes.append(
            {
                "@id": docket_iri,
                "@type": "rkaf:Docket",
                "rkaf:hasDocketIdentifier": docket_iri,
                "rkaf:docketIdentifierScheme": "rkaf:us-regsgov",
            }
        )
    return iris, nodes, notes


def _authority_edge(
    tables: PublishedTables,
    *,
    rin: str,
    rin_iri: str,
) -> DeterministicEdge | None:
    rows = tables.rows("authority_edges", rin=rin) if rin else []
    if not rows:
        return None
    row = rows[0]
    target = _authority_iri(row)
    if target is None:
        return None
    raw = _clean(row.get("authority_raw"))
    forms = [raw]
    usc_title, usc_section = _clean(row.get("usc_title")), _clean(row.get("usc_section"))
    if usc_title and usc_section:
        forms.extend([f"{usc_title} U.S.C. {usc_section}", f"{usc_title} USC {usc_section}"])
    return DeterministicEdge(
        key="authority",
        subject=rin_iri,
        # J3 (hand-authored): authority_edges is RIN + agenda-edition keyed with
        # parse_status often partial, so this asserts the agenda item's cited
        # authority rather than minting the stronger rkaf:hasAuthority chain.
        predicate="rkaf:agendaAuthorityCitation",
        object=target,
        table="authority_edges",
        record_key=f"{rin}:{_clean(row.get('agenda_edition'))}",
        activity_key="authority-parser",
        asserted_at=_clean(row.get("asserted_at")),
        surface_forms=tuple(dict.fromkeys(form for form in forms if form)),
    )


def _authority_activity(tables: PublishedTables, *, rin: str) -> ExtractionActivitySpec | None:
    rows = tables.rows("authority_edges", rin=rin) if rin else []
    if not rows:
        return None
    row = rows[0]
    return ExtractionActivitySpec(
        key="authority-parser",
        method="rkaf:deterministicParse",
        run_id=_clean(row.get("run_id")),
        actor_id=_clean(row.get("actor_id")),
        version="v1",
        instructions=("spicy-regs deterministic Unified Agenda authority-citation parse (authority_edges.parquet row)"),
        input_row=row,
    )


def federal_register_facts(
    artifact: SourceArtifact,
    row: Mapping[str, Any],
    *,
    tables: PublishedTables,
    partner: str,
) -> ProfileFacts:
    """Everything a Federal Register document row and the published tables state about it.

    The proceedings table is the join: it is the only published row that names
    this document, and the RIN, the dockets, and the CFR targets hang off it.
    Nothing is re-parsed out of the document to find any of them.
    """
    document_number = _clean(row.get("document_number"))
    artifact_iri = f"https://www.federalregister.gov/d/{document_number}"
    scheme, regulatory_iri = federal_register_identifier(document_number)
    notes: list[str] = []
    extra_nodes: list[dict[str, Any]] = []
    edges: list[DeterministicEdge] = []
    activities: list[ExtractionActivitySpec] = []

    agency_slugs = _json_list(row.get("agency_slugs"))
    claimant = f"{_FR_AGENCY_IRI}{agency_slugs[0]}" if agency_slugs else None

    # The proceedings table is the join: it is the only published row that names
    # this FR document, and everything else (the RIN, the dockets, the CFR
    # targets) hangs off it. Nothing is re-parsed out of the document to find it.
    proceeding_row: Mapping[str, Any] | None = None
    proceeding_iri: str | None = None
    rin = ""
    for proceeding in tables.rows("proceedings"):
        if document_number in _json_list(proceeding.get("fr_document_numbers_json")):
            proceeding_row = proceeding
            proceeding_iri = f"{partner}:proceeding:{_clean(proceeding.get('proceeding_id'))}"
            rin = _clean(proceeding.get("rin"))
            break
    rule_target_rows = tables.rows("rule_targets", rin=rin) if rin else []

    docket_iris: list[str] = []
    if proceeding_row is not None and proceeding_iri is not None:
        stage = _PROCEEDING_STAGE_BY_CURRENT.get(_clean(proceeding_row.get("current_stage")).lower())
        cfr_targets = [
            value
            for value in _json_list(proceeding_row.get("cfr_target_iris_json"))
            if value.startswith("urn:rkaf:us:cfr:")
        ]
        for docket_id in _json_list(proceeding_row.get("docket_ids_json")):
            try:
                docket_iris.append(canonical_regsgov_iri(docket_id))
            except ValueError:
                notes.append(f"docket identifier {docket_id!r} is not expressible in rkaf:us-regsgov")
        proceeding_node: dict[str, Any] = {
            "@id": proceeding_iri,
            "@type": "rkaf:Proceeding",
            "rkaf:hasProceedingIdentifier": proceeding_iri,
            "rkaf:proceedingIdentifierScheme": "rkaf:partner-defined",
        }
        if stage:
            proceeding_node["rkaf:proceedingStage"] = stage
        if EMIT_PROFILE_EDGE_PROJECTIONS and docket_iris:
            proceeding_node["rkaf:hasDocket"] = list(docket_iris)
        if EMIT_PROFILE_EDGE_PROJECTIONS and cfr_targets:
            proceeding_node["rkaf:proceedingAffectsCitation"] = list(cfr_targets)
        extra_nodes.append(proceeding_node)
        for docket_iri in docket_iris:
            extra_nodes.append(
                {
                    "@id": docket_iri,
                    "@type": "rkaf:Docket",
                    "rkaf:hasDocketIdentifier": docket_iri,
                    "rkaf:docketIdentifierScheme": "rkaf:us-regsgov",
                }
            )
        activities.append(
            ExtractionActivitySpec(
                key="proceedings",
                method="rkaf:deterministicParse",
                run_id=_clean(proceeding_row.get("run_id")),
                actor_id=_clean(proceeding_row.get("actor_id")) or "spicy-regs:proceedings:v1",
                version="v1",
                instructions="spicy-regs deterministic proceeding assembly (proceedings.parquet row)",
                input_row=proceeding_row,
            )
        )
        # The document -> proceeding link is reified too, so turning the profile
        # edges off (finding G5) never drops the fact — it only moves where it
        # is stated. Without this the document would be orphaned the moment the
        # plain edges become derived projections.
        edges.append(
            DeterministicEdge(
                key="published-in-proceeding",
                subject=artifact_iri,
                predicate="rkaf:publishedInProceeding",
                object=proceeding_iri,
                table="proceedings",
                record_key=_clean(proceeding_row.get("proceeding_id")),
                activity_key="proceedings",
                asserted_at=_clean(proceeding_row.get("asserted_at")),
                claimant_identity=claimant,
                profile_edge=(artifact_iri, "rkaf:publishedInProceeding", proceeding_iri),
            )
        )
        for docket_iri, raw_docket in zip(docket_iris, _json_list(proceeding_row.get("docket_ids_json"))):
            edges.append(
                DeterministicEdge(
                    key=f"docket-{raw_docket}",
                    subject=proceeding_iri,
                    predicate="rkaf:hasDocket",
                    object=docket_iri,
                    table="proceedings",
                    record_key=_clean(proceeding_row.get("proceeding_id")),
                    activity_key="proceedings",
                    asserted_at=_clean(proceeding_row.get("asserted_at")),
                    surface_forms=(f"Docket No. {raw_docket}", raw_docket),
                    claimant_identity=claimant,
                    profile_edge=(proceeding_iri, "rkaf:hasDocket", docket_iri),
                )
            )

    if rin:
        rin_iri = canonical_rin_iri(rin)
        extra_nodes.append(
            {
                "@id": rin_iri,
                "@type": "rkaf:RegulatoryAgendaItem",
                "rkaf:hasAgendaItemIdentifier": rin_iri,
                "rkaf:agendaItemIdentifierScheme": "rkaf:us-rin",
            }
        )
        authority = _authority_edge(tables, rin=rin, rin_iri=rin_iri)
        if authority is not None:
            edges.append(replace(authority, claimant_identity=claimant))
            activity = _authority_activity(tables, rin=rin)
            if activity is not None:
                activities.append(activity)

    for candidate in rule_target_rows:
        target = _cfr_iri(candidate)
        if target is None or proceeding_iri is None:
            continue
        title, part = _clean(candidate.get("cfr_title")), _clean(candidate.get("cfr_part"))
        edges.append(
            DeterministicEdge(
                key=f"cfr-target-{title}-{part}",
                subject=proceeding_iri,
                predicate="rkaf:proceedingAffectsCitation",
                object=target,
                table="rule_targets",
                record_key=f"{_clean(candidate.get('docket_id'))}:{_clean(candidate.get('cfr_ref'))}",
                activity_key="rule-targets",
                asserted_at=_clean(candidate.get("asserted_at")),
                surface_forms=(
                    f"{title} CFR Part {part}",
                    f"{title} CFR part {part}",
                    f"{title} CFR {part}",
                ),
                claimant_identity=claimant,
                profile_edge=(proceeding_iri, "rkaf:proceedingAffectsCitation", target),
            )
        )
        activities.append(
            ExtractionActivitySpec(
                key="rule-targets",
                method="rkaf:deterministicParse",
                run_id=_clean(candidate.get("run_id")),
                actor_id=_clean(candidate.get("actor_id")),
                version="v1",
                instructions=(
                    "spicy-regs deterministic rule-targets extraction over docket documents "
                    "and FR metadata (rule_targets.parquet row)"
                ),
                input_row=candidate,
            )
        )
        break

    # G2 / rulemaking §5.3: the document's own docket membership. This is the
    # document -> docket fact the FR record states outright, NOT a restatement of
    # the proceeding's rkaf:hasDocket: a proceeding may span dockets a given one
    # of its documents was not filed in, and neither edge implies the other.
    published_in_docket: tuple[str, ...] = ()
    if EMIT_DOCUMENT_DOCKET_EDGE:
        docket_edge_iris, docket_edge_nodes, docket_notes = _document_docket_iris(
            row, tables=tables, known_docket_iris=docket_iris
        )
        published_in_docket = tuple(docket_edge_iris)
        extra_nodes.extend(docket_edge_nodes)
        notes.extend(docket_notes)
    elif _json_list(row.get("docket_ids_json")):
        notes.append(
            "finding G2: the document's own docket_ids_json is not directly expressible — "
            "there is no document->docket predicate, so the docket is reached through the Proceeding"
        )

    return ProfileFacts(
        profile_id=artifact.profile_id,
        artifact_iri=artifact_iri,
        evidence_field="federal_register.body_html",
        artifact_identifiers=(artifact_iri,),
        artifact_schemes=("rkaf:urn-persistent",),
        regulatory_identifier=regulatory_iri,
        regulatory_scheme=scheme,
        published_in_proceeding=(proceeding_iri,) if proceeding_iri else (),
        published_in_docket=published_in_docket,
        extra_nodes=tuple(extra_nodes),
        edges=tuple(edges),
        activities=tuple({spec.key: spec for spec in activities}.values()),
        claimant_identity=claimant,
        notes=tuple(notes),
    )


def unified_agenda_facts(
    artifact: SourceArtifact,
    row: Mapping[str, Any],
    *,
    tables: PublishedTables,
    partner: str,
) -> ProfileFacts:
    """Everything a Unified Agenda observation row states about its RIN.

    CFR references and legal authorities are parsed from the row's own JSON
    columns through :mod:`rulespec_projection.citations`; the authority edge,
    when the published tables carry one, is reified with its activity.
    """
    rin = _clean(row.get("rin"))
    edition = _clean(row.get("agenda_edition"))
    rin_iri = canonical_rin_iri(rin)
    artifact_iri = _clean(row.get("url")) or f"{partner}:agenda-observation:{rin}:{edition}"
    notes: list[str] = []
    edges: list[DeterministicEdge] = []
    activities: list[ExtractionActivitySpec] = []

    affects = []
    for reference in _json_list(row.get("cfr_references_json")):
        for citation in parse_cfr_citation(reference):
            try:
                affects.append(canonical_cfr_iri(citation.title, citation.part, citation.section))
            except ValueError:
                notes.append(f"CFR reference {reference!r} is not expressible in rkaf:us-cfr")
    authority = []
    for reference in _json_list(row.get("legal_authority_json")):
        for citation in parse_authority_citation(reference):
            try:
                if citation.authority_type == "usc":
                    authority.append(canonical_usc_iri(citation.usc_title, citation.usc_section))
                elif citation.pl_number:
                    authority.append(canonical_pl_iri(citation.pl_number))
            except ValueError:
                notes.append(f"authority reference {reference!r} is not expressible")

    observation: dict[str, Any] = {
        "@id": artifact_iri,
        "@type": "rkaf:RegulatoryAgendaObservation",
        "rkaf:hasArtifactIdentifier": [artifact_iri],
        "rkaf:artifactIdentifierScheme": ["rkaf:urn-persistent"],
        "foaf:primaryTopic": rin_iri,
    }
    stage = _AGENDA_STAGE_BY_RULE_STAGE.get(_clean(row.get("rule_stage")).lower())
    if stage:
        observation["rkaf:agendaStage"] = stage
    priority = _AGENDA_PRIORITY_BY_CATEGORY.get(_clean(row.get("priority_category")).lower())
    if priority:
        observation["rkaf:agendaPriority"] = priority
    if EMIT_PROFILE_EDGE_PROJECTIONS and affects:
        observation["rkaf:agendaAffectsCitation"] = list(dict.fromkeys(affects))
    if EMIT_PROFILE_EDGE_PROJECTIONS and authority:
        observation["rkaf:agendaAuthorityCitation"] = list(dict.fromkeys(authority))

    extra_nodes: list[dict[str, Any]] = [
        observation,
        {
            "@id": rin_iri,
            "@type": "rkaf:RegulatoryAgendaItem",
            "rkaf:hasAgendaItemIdentifier": rin_iri,
            "rkaf:agendaItemIdentifierScheme": "rkaf:us-rin",
        },
    ]
    # An rkaf:SourceFragment's oa:hasSource is class-ranged to rkaf:Artifact
    # (compiled/shacl/core/source-fragment.ttl). rkaf:RegulatoryAgendaObservation
    # is described in the profile as a subclass of rkaf:Artifact but no shape or
    # context file declares `rdfs:subClassOf`, so RDFS inference cannot reach it.
    # The observation therefore carries BOTH types, as two nodes on one IRI, so
    # each dispatches to a real compiled schema at L2 instead of an @type array
    # that L2 skips silently. See the report's finding list.
    notes.append(
        "finding: rkaf:RegulatoryAgendaObservation is documented as a profile subclass of "
        "rkaf:Artifact but no shapes file declares rdfs:subClassOf, so the observation must "
        "also be typed rkaf:Artifact for its own fragments to satisfy the oa:hasSource range"
    )

    edge = _authority_edge(tables, rin=rin, rin_iri=rin_iri)
    if edge is not None:
        edges.append(edge)
        activity = _authority_activity(tables, rin=rin)
        if activity is not None:
            activities.append(activity)

    return ProfileFacts(
        profile_id=artifact.profile_id,
        artifact_iri=artifact_iri,
        evidence_field="unified_agenda.abstract",
        artifact_identifiers=(artifact_iri,),
        artifact_schemes=("rkaf:urn-persistent",),
        extra_nodes=tuple(extra_nodes),
        edges=tuple(edges),
        activities=tuple(activities),
        notes=tuple(notes),
    )


@dataclass(frozen=True)
class ConceptJudgment:
    """One accepted concept assignment, with its verified evidence region."""

    concept_id: str
    concept_iri: str
    concept_label: str
    preferred_labels: Mapping[str, str]
    alternate_labels: Mapping[str, str | tuple[str, ...]]
    hidden_labels: Mapping[str, str | tuple[str, ...]]
    definitions: Mapping[str, str | tuple[str, ...]]
    scheme_iri: str
    release_iri: str
    facet: str
    role: str
    confidence: float
    fragment: ProjectedFragment
    candidate_id: str
    evidence_text: str
    alignment_method: str
    candidate_channels: tuple[str, ...]
    candidate_rank: int | None
    candidate_score: float | None
    candidate_score_state: str
    indexed_representation_version: str
    mapping_paths: tuple[Mapping[str, str], ...]
    selected_channel: str
    selected_mapping_path: Mapping[str, str] | None


@dataclass(frozen=True)
class ModelLayer:
    """What the model was asked, what it said, and what survived checking."""

    model_id: str
    instructions_sha256: str
    schema_sha256: str
    input_context_sha256: str
    run_directory: str
    receipt_sha256: str
    selector_version: str
    vocabulary_sha256: str
    vocabulary_default_language: str
    vocabulary_nodes: tuple[Mapping[str, Any], ...]
    vocabulary_concepts: Mapping[str, "VocabularyConcept"]
    candidate_concept_count: int
    judgments: tuple[ConceptJudgment, ...]
    rejections: tuple[Mapping[str, Any], ...]
    call_count: int
    candidate_selection_receipt: Mapping[str, Any] | None = None
    concept_domain_mapping_sha256: str | None = None
    candidate_selection_sha256: str = ""
    candidate_selection_ledger: tuple[Mapping[str, Any], ...] = ()
    segment_count: int = 0
    segments_projected: int = 0
    temperature: float = 0.0


@dataclass(frozen=True)
class VocabularyConcept:
    """One production concept resolved through normalized authored records."""

    concept_iri: str
    scheme_iri: str
    release_iri: str
    facet: str
    preferred_labels: Mapping[str, str]
    alternate_labels: Mapping[str, str | tuple[str, ...]]
    hidden_labels: Mapping[str, str | tuple[str, ...]]
    definitions: Mapping[str, str | tuple[str, ...]]

    def display_label(self, default_language: str) -> str:
        preferred = self.preferred_labels
        if default_language in preferred:
            return preferred[default_language]
        return preferred[sorted(preferred)[0]]


ASSIGNMENT_ROLE_IRIS: dict[str, str] = {
    "primary": "rkaf:assignmentPrimary",
    "substantive": "rkaf:assignmentSubstantive",
    "mention": "rkaf:assignmentMention",
    "contextual": "rkaf:assignmentContextual",
}


ASSIGNMENT_ROLE_ABSOLUTE_IRIS: dict[str, str] = {
    name: value.replace(
        "rkaf:",
        "https://rulespec.org/ns/v1#",
    )
    for name, value in ASSIGNMENT_ROLE_IRIS.items()
}


def verify_candidate_rows(
    artifact: SourceArtifact,
    rows: Sequence[Mapping[str, Any]],
    *,
    artifact_iri: str,
    evidence_field: str,
    vocabulary_concepts: Mapping[str, VocabularyConcept] | None = None,
    allowed_assignment_role_iris: Sequence[str] | None = None,
) -> tuple[list[ConceptJudgment], list[dict[str, Any]]]:
    """Re-verify accepted tag candidates and turn survivors into judgments.

    The tag task already grounded these quotes once. This pass exists because
    the projection makes a stronger claim than the tag table does: it mints a
    carrier-local URN whose digest a stranger will recompute. So the offsets are
    re-sliced against the stored field here, and anything that fails becomes a
    rejection row rather than a fragment.
    """
    judgments: list[ConceptJudgment] = []
    rejections: list[dict[str, Any]] = []
    for row in rows:
        concept_id = _clean(row.get("concept_id"))
        base = {
            "candidate_id": _clean(row.get("candidate_id")),
            "concept_id": concept_id or None,
            "role": _clean(row.get("role")),
            "source_field": _clean(row.get("source_field")),
            "evidence_text": row.get("evidence_text"),
        }
        if not concept_id:
            # The tag task admits a novel concept the model proposes. A novel
            # concept has no normalized vocabulary row, and this projection never mints
            # identity, so it is refused here rather than registered.
            rejections.append(
                {
                    **base,
                    "reason": "model_proposed_concept_not_in_normalized_vocabulary",
                }
            )
            continue
        if _clean(row.get("source_field")) != evidence_field:
            rejections.append({**base, "reason": "evidence_outside_projected_text_state"})
            continue
        if _clean(row.get("evidence_grade")) != SOURCE_EXACT_EVIDENCE_GRADE:
            rejections.append({**base, "reason": "evidence_not_source_exact"})
            continue
        role = ASSIGNMENT_ROLE_IRIS.get(_clean(row.get("role")))
        if role is None:
            rejections.append({**base, "reason": "unknown_assignment_role"})
            continue
        absolute_role = ASSIGNMENT_ROLE_ABSOLUTE_IRIS[_clean(row.get("role"))]
        if allowed_assignment_role_iris is not None and absolute_role not in allowed_assignment_role_iris:
            rejections.append(
                {
                    **base,
                    "reason": "assignment_role_not_selected",
                }
            )
            continue
        start, end = int(row.get("source_start_char") or 0), int(row.get("source_end_char") or 0)
        try:
            fragment = verify_fragment(
                artifact,
                key=f"assignment-{_clean(row.get('candidate_id'))}",
                source_field=evidence_field,
                start=start,
                end=end,
                artifact_iri=artifact_iri,
                expected_text=str(row.get("evidence_text") or ""),
            )
        except OffsetVerificationError as error:
            rejections.append({**base, "reason": "offset_verification_failed", "detail": str(error)})
            continue
        vocabulary_concept = vocabulary_concepts.get(concept_id) if vocabulary_concepts is not None else None
        if vocabulary_concepts is not None and vocabulary_concept is None:
            rejections.append(
                {
                    **base,
                    "reason": "normalized_vocabulary_concept_not_resolved",
                }
            )
            continue
        if vocabulary_concept is None:
            # Compatibility for callers that use this verification helper in
            # isolation. The production model path always supplies normalized
            # vocabulary metadata and never enters this branch.
            facet = _clean(row.get("facet")) or _clean(row.get("scheme"))
            concept_iri = concept_id
            scheme_iri = f"urn:spicy-regs:unresolved-scheme:{facet}"
            release_iri = "urn:spicy-regs:unresolved-release"
            label = _clean(row.get("concept_label"))
            preferred_labels: Mapping[str, str] = {"und": label}
            definitions: Mapping[str, str | tuple[str, ...]] = (
                {"und": _clean(row.get("definition"))} if _clean(row.get("definition")) else {}
            )
            alternate_labels: Mapping[str, str | tuple[str, ...]] = {}
            hidden_labels: Mapping[str, str | tuple[str, ...]] = {}
        else:
            facet = vocabulary_concept.facet
            concept_iri = vocabulary_concept.concept_iri
            scheme_iri = vocabulary_concept.scheme_iri
            release_iri = vocabulary_concept.release_iri
            label = vocabulary_concept.display_label("en")
            preferred_labels = vocabulary_concept.preferred_labels
            alternate_labels = vocabulary_concept.alternate_labels
            hidden_labels = vocabulary_concept.hidden_labels
            definitions = vocabulary_concept.definitions
        raw_channels = row.get("candidate_channels")
        candidate_channels = (
            tuple(
                _clean(value)
                for value in raw_channels
                if _clean(value)
            )
            if isinstance(raw_channels, Sequence)
            and not isinstance(raw_channels, (str, bytes))
            else ()
        )
        raw_paths = row.get("mapping_paths")
        mapping_paths = (
            tuple(
                {
                    str(key): str(value)
                    for key, value in path.items()
                }
                for path in raw_paths
                if isinstance(path, Mapping)
            )
            if isinstance(raw_paths, Sequence)
            and not isinstance(raw_paths, (str, bytes))
            else ()
        )
        raw_rank = row.get("candidate_rank")
        candidate_rank = (
            int(raw_rank)
            if isinstance(raw_rank, int)
            and not isinstance(raw_rank, bool)
            and raw_rank > 0
            else None
        )
        raw_score = row.get("candidate_score")
        candidate_score = (
            float(raw_score)
            if isinstance(raw_score, (int, float))
            and not isinstance(raw_score, bool)
            else None
        )
        raw_selected_path = row.get("selected_mapping_path")
        selected_mapping_path = (
            {
                str(key): str(value)
                for key, value in raw_selected_path.items()
            }
            if isinstance(raw_selected_path, Mapping)
            else None
        )
        judgments.append(
            ConceptJudgment(
                concept_id=concept_id,
                concept_iri=concept_iri,
                concept_label=label,
                preferred_labels=preferred_labels,
                alternate_labels=alternate_labels,
                hidden_labels=hidden_labels,
                definitions=definitions,
                scheme_iri=scheme_iri,
                release_iri=release_iri,
                facet=facet,
                role=role,
                confidence=float(row.get("confidence") or 0.0),
                fragment=fragment,
                candidate_id=_clean(row.get("candidate_id")),
                evidence_text=str(row.get("evidence_text") or ""),
                alignment_method=_clean(row.get("evidence_alignment_method")),
                candidate_channels=candidate_channels,
                candidate_rank=candidate_rank,
                candidate_score=candidate_score,
                candidate_score_state=(
                    _clean(row.get("candidate_score_state"))
                    or "notRecorded"
                ),
                indexed_representation_version=_clean(
                    row.get("indexed_representation_version")
                ),
                mapping_paths=mapping_paths,
                selected_channel=_clean(
                    row.get("selected_channel")
                ),
                selected_mapping_path=selected_mapping_path,
            )
        )
    return judgments, rejections


@dataclass
class ProjectionResult:
    """The emitted JSON-LD document plus the record of how it was produced."""

    document: dict[str, Any]
    run_record: dict[str, Any]
    transcript: list[str]

    @property
    def node_count(self) -> int:
        return len(self.document.get("@graph", []))


@dataclass(frozen=True)
class ProjectionSettings:
    """Everything the assembler needs that is not the document itself."""

    corpus_dir: Path
    tables_dir: Path
    rulespec_version: str
    rulespec_constraint_digest: str
    rulespec_source_revision: str | None = None
    partner: str = "urn:rkaf:partner:spicy-regs"
    scope: str = "document-rkaf-projection"
    context_ref: str = "./rkaf-context.jsonld"
    asserted_at: str | None = None
    attestor_id: str = ""
    migration_vocabulary_directory: Path | None = None
    migration_vocabulary_manifest_path: Path | None = None
    vocabulary_default_language: str = "en"
    prompt_concept_limit: int = 12
    max_segments: int = 0
    """Cap on the segments sent to the model; ``0`` means every segment. A cap
    bounds provider spend on a long document, and it changes what the emitted
    document can claim, so both the cap and the segment count are recorded."""
    extra_notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not _RULESPEC_VERSION_PATTERN.fullmatch(self.rulespec_version):
            raise ProjectionError("rulespec_version must be an exact semantic version")
        if not _CONSTRAINT_DIGEST_PATTERN.fullmatch(self.rulespec_constraint_digest):
            raise ProjectionError("rulespec_constraint_digest must be sha256:<64 lowercase hex>")
        if self.rulespec_source_revision is not None and not _RULESPEC_REVISION_PATTERN.fullmatch(
            self.rulespec_source_revision
        ):
            raise ProjectionError(
                "rulespec_source_revision must be a 40-character Git revision or None for a local candidate"
            )


def _selector_node(fragment: ProjectedFragment) -> dict[str, Any]:
    return {
        "@id": fragment.selector_iri,
        "@type": _SELECTOR_KIND,
        "oa:start": fragment.start,
        "oa:end": fragment.end,
        "rkaf:coordinateSystem": _COORDINATE_SYSTEM,
    }


def _fragment_node(fragment: ProjectedFragment, *, artifact_iri: str, artifact_digest: str) -> dict[str, Any]:
    return {
        "@id": fragment.urn,
        "@type": "rkaf:SourceFragment",
        "oa:hasSource": artifact_iri,
        "oa:hasSelector": fragment.selector_iri,
        "rkaf:selectorKind": [_SELECTOR_KIND],
        "rkaf:fragmentIdentityScheme": _EVIDENCE_SCHEME,
        "rkaf:fragmentContentDigest": f"sha256:{fragment.text_sha256}",
        "rkaf:sourceArtifactDigest": f"sha256:{artifact_digest}",
    }


def _activity_node(spec: ExtractionActivitySpec, *, partner: str) -> dict[str, Any]:
    contract, input_digest = request_contract_digest(spec)
    node: dict[str, Any] = {
        "@id": f"{partner}:activity:{spec.key}",
        "@type": "rkaf:ExtractionActivity",
        "rkaf:extractionMethod": spec.method,
        "rkaf:extractionRun": f"{partner}:run:{spec.run_id}" if spec.run_id else f"{partner}:run:unknown",
        "rkaf:extractedBy": f"{partner}:actor:{spec.key}",
        "rkaf:extractorVersion": spec.version,
        "rkaf:inputDigest": [f"sha256:{input_digest}"],
    }
    if spec.method in REQUEST_CONTRACT_DIGEST_REQUIRED_FOR:
        node["rkaf:requestContractDigest"] = f"sha256:{contract}"
    if spec.model_ref:
        node["rkaf:extractionModelRef"] = spec.model_ref
    if spec.prompt_ref:
        node["rkaf:extractionPromptRef"] = spec.prompt_ref
    return node


def assemble(
    artifact: SourceArtifact,
    facts: ProfileFacts,
    *,
    settings: ProjectionSettings,
    model_layer: ModelLayer | None = None,
) -> ProjectionResult:
    """Turn verified facts and verified judgments into the RKAF document."""
    partner = settings.partner
    context = RunContext.resolve(asserted_at=settings.asserted_at, prefix="rkaf-projection")
    artifact_iri = facts.artifact_iri
    evidence_field = facts.evidence_field
    if evidence_field not in artifact.raw_fields:
        raise ProjectionError(
            f"{facts.profile_id}: the projected evidence field {evidence_field!r} is absent from this artifact "
            f"(available: {sorted(artifact.raw_fields)})"
        )
    artifact_digest = artifact.field_sha256[evidence_field]
    transcript: list[str] = [
        "== Source text state ==",
        f"profile          : {facts.profile_id}",
        f"subject_id       : {artifact.subject_id}",
        f"artifact_id      : {artifact.artifact_id}",
        f"version digest   : {artifact.content_sha256}  (source.py _content_digest; NOT hasContentDigest)",
        f"projected field  : {evidence_field}",
        f"length           : {len(artifact.raw_fields[evidence_field])} Unicode code points",
        f"sha256(UTF-8)    : {artifact_digest}",
        "",
        "== SourceFragment offset verification "
        "(unicode code points, half-open [start,end), re-sliced from the stored field) ==",
    ]

    graph: list[dict[str, Any]] = []
    fragments: dict[str, ProjectedFragment] = {}
    provenance_records: set[str] = set()

    def note_fragment(fragment: ProjectedFragment) -> None:
        if fragment.urn in fragments:
            return
        fragments[fragment.urn] = fragment
        transcript.extend(
            [
                f"  {fragment.key} [{fragment.start},{fragment.end})",
                f"     slice: {json.dumps(fragment.text[:160], ensure_ascii=False)}",
                f"     sha256(region): {fragment.text_sha256}",
                f"     urn: {fragment.urn}",
            ]
        )

    # ------------------------------------------------------------- Artifact
    artifact_node: dict[str, Any] = {
        "@id": artifact_iri,
        "@type": "rkaf:Artifact",
        "rkaf:hasArtifactIdentifier": list(facts.artifact_identifiers),
        "rkaf:artifactIdentifierScheme": list(facts.artifact_schemes),
        "rkaf:hasContentDigest": f"sha256:{artifact_digest}",
    }
    if facts.regulatory_identifier and facts.regulatory_scheme:
        artifact_node["rkaf:hasRegulatoryIdentifier"] = facts.regulatory_identifier
        artifact_node["rkaf:regulatoryIdentifierScheme"] = facts.regulatory_scheme
    if EMIT_PROFILE_EDGE_PROJECTIONS and facts.published_in_proceeding:
        artifact_node["rkaf:publishedInProceeding"] = list(facts.published_in_proceeding)
    # Not gated on EMIT_PROFILE_EDGE_PROJECTIONS: this edge projects no
    # assertion, it is the source-native fact itself (rulemaking §5.3), so
    # turning the assertion projections off must not delete it.
    if EMIT_DOCUMENT_DOCKET_EDGE and facts.published_in_docket:
        artifact_node[DOCUMENT_DOCKET_PREDICATE] = list(facts.published_in_docket)
    graph.append(artifact_node)
    graph.extend(dict(node) for node in facts.extra_nodes)

    # ------------------------------------------ deterministic relationships
    activities: dict[str, ExtractionActivitySpec] = {spec.key: spec for spec in facts.activities}
    edge_records: list[dict[str, Any]] = []
    for edge in facts.edges:
        assertion_iri = (
            f"{partner}:assertion:{stable_id('assertion', edge.subject, edge.predicate, edge.object, length=16)}"
        )
        record_iri = f"{partner}:record:{edge.table}:{edge.record_key}"
        provenance_records.add(record_iri)
        assertion: dict[str, Any] = {
            "@id": assertion_iri,
            "@type": "rkaf:RelationshipAssertion",
            "rkaf:assertsSubject": edge.subject,
            "rkaf:assertsPredicate": edge.predicate,
            "rkaf:assertsObject": edge.object,
            "rkaf:assertionPolarity": "rkaf:affirmed",
            "rkaf:assertionOrigin": ASSERTION_ORIGIN_DETERMINISTIC,
            "rkaf:epistemicBasis": "rkaf:deterministicDerivation",
            "rkaf:assertedAt": edge.asserted_at or context.asserted_at,
            "rkaf:usageEligibility": DETERMINISTIC_USAGE_ELIGIBILITY,
            "prov:wasDerivedFrom": [record_iri],
        }
        # Since G3 landed, rkaf:deterministicExtraction REQUIRES
        # rkaf:hasExtractionProvenance on every compiled target: a claim of
        # mechanical reproducibility that names no run is not checkable. An edge
        # whose activity is missing is a projection bug, not a weaker assertion,
        # so it aborts rather than emitting a non-conforming node.
        if edge.activity_key not in activities:
            raise ProjectionError(
                f"edge {edge.key!r} asserts {ASSERTION_ORIGIN_DETERMINISTIC} but names no extraction "
                f"activity {edge.activity_key!r}; the contract requires rkaf:hasExtractionProvenance "
                f"for that origin (known activities: {sorted(activities)})"
            )
        assertion["rkaf:hasExtractionProvenance"] = f"{partner}:activity:{edge.activity_key}"
        grounded = ground_literal(
            artifact,
            key=f"edge-{edge.key}",
            source_field=evidence_field,
            artifact_iri=artifact_iri,
            surface_forms=edge.surface_forms,
        )
        record = {
            "key": edge.key,
            "subject": edge.subject,
            "predicate": edge.predicate,
            "object": edge.object,
            "table": edge.table,
            "assertion": assertion_iri,
            "grounded": grounded is not None,
        }
        if grounded is not None:
            note_fragment(grounded)
            record["evidence"] = grounded.urn
            graph.append(
                {
                    "@id": f"{partner}:binding:{edge.key}",
                    "@type": "rkaf:EvidenceBinding",
                    "rkaf:bindsAssertion": assertion_iri,
                    "rkaf:bindsSourceFragment": [grounded.urn],
                    "rkaf:evidenceRole": "rkaf:textualEvidence",
                    "rkaf:evidentiaryFunction": "rkaf:supports",
                }
            )
            if edge.claimant_identity:
                claimant_iri = f"{partner}:claimant:{edge.key}"
                assertion["rkaf:hasSourceClaimant"] = claimant_iri
                graph.append(
                    {
                        "@id": claimant_iri,
                        "@type": "rkaf:SourceClaimant",
                        "rkaf:claimsAssertion": assertion_iri,
                        "rkaf:claimantAttribution": "rkaf:claimantIsDocumentIssuer",
                        "rkaf:claimantIdentity": edge.claimant_identity,
                        "rkaf:attributedInFragment": [grounded.urn],
                    }
                )
        else:
            record["reason"] = "no unique verbatim restatement of this citation in the projected field"
            graph.append(
                {
                    "@id": f"{partner}:binding:{edge.key}",
                    "@type": "rkaf:EvidenceBinding",
                    "rkaf:bindsAssertion": assertion_iri,
                    "rkaf:noEvidenceReason": "rkaf:inferred-from-warrant-class",
                }
            )
        edge_records.append(record)
        graph.append(assertion)

    # -------------------------------------------------- concept assignments
    judgment_records: list[dict[str, Any]] = []
    assignment_iris: list[str] = []
    if model_layer is not None and model_layer.judgments:
        lineage_iri = f"{partner}:lineage:{settings.scope}"
        graph.extend(dict(node) for node in model_layer.vocabulary_nodes)
        graph.append(
            {
                "@id": lineage_iri,
                "@type": "rkaf:AILineage",
                "rkaf:modelId": model_layer.model_id,
                "rkaf:modelVersion": model_layer.model_id,
                "rkaf:promptTemplateRef": f"{partner}:prompt:concept-tags-v1:{model_layer.instructions_sha256[:16]}",
                # The pinned arms are reasoning-effort models with no sampling
                # temperature to report; #AILineage requires the field anyway.
                "rkaf:temperature": model_layer.temperature,
                "rkaf:inputContextHash": f"sha256:{model_layer.input_context_sha256}",
            }
        )
        graph.append(
            _activity_node(
                ExtractionActivitySpec(
                    key="concept-tags",
                    method="rkaf:modelExtraction",
                    run_id=model_layer.run_directory,
                    actor_id=f"{partner}:actor:concept-tags",
                    version="concept_tags_v1",
                    instructions=f"docpipeline concept_tags_v1 @ sha256:{model_layer.instructions_sha256}",
                    input_row={
                        "instructions_sha256": model_layer.instructions_sha256,
                        "schema_sha256": model_layer.schema_sha256,
                        "input_context_sha256": model_layer.input_context_sha256,
                        "selector_version": model_layer.selector_version,
                        "vocabulary_sha256": model_layer.vocabulary_sha256,
                        "vocabulary_default_language": (model_layer.vocabulary_default_language),
                        "candidate_selection_sha256": (
                            model_layer.candidate_selection_sha256
                        ),
                        **(
                            {
                                "concept_domain_mapping_sha256": (
                                    model_layer.concept_domain_mapping_sha256
                                )
                            }
                            if model_layer.concept_domain_mapping_sha256
                            is not None
                            else {}
                        ),
                    },
                    model_ref=f"{partner}:model:{model_layer.model_id}",
                    prompt_ref=f"{partner}:prompt:concept-tags-v1:{model_layer.instructions_sha256[:16]}",
                ),
                partner=partner,
            )
        )
        for judgment in model_layer.judgments:
            note_fragment(judgment.fragment)
            assignment_iri = f"{partner}:assignment:{judgment.candidate_id}"
            assignment_iris.append(assignment_iri)
            record_iri = (
                f"{partner}:record:normalized-vocabulary:"
                f"{stable_id(judgment.concept_iri, judgment.release_iri, length=20)}"
            )
            provenance_records.add(record_iri)
            graph.append(
                {
                    "@id": assignment_iri,
                    "@type": "rkaf:ConceptAssignment",
                    "rkaf:assertsSubject": artifact_iri,
                    "rkaf:assertsPredicate": judgment.role,
                    "rkaf:assertsObject": judgment.concept_iri,
                    "rkaf:assertionPolarity": "rkaf:affirmed",
                    "rkaf:assignedConceptRelease": judgment.release_iri,
                    "rkaf:assertionOrigin": ASSERTION_ORIGIN_MODEL,
                    "rkaf:epistemicBasis": "rkaf:statisticalInference",
                    "rkaf:hasAILineage": lineage_iri,
                    "rkaf:hasExtractionProvenance": f"{partner}:activity:concept-tags",
                    "rkaf:assertedAt": context.asserted_at,
                    "rkaf:usageEligibility": MODEL_USAGE_ELIGIBILITY,
                    "prov:wasDerivedFrom": [record_iri],
                }
            )
            graph.append(
                {
                    "@id": f"{partner}:binding:assignment:{judgment.candidate_id}",
                    "@type": "rkaf:EvidenceBinding",
                    "rkaf:bindsAssertion": assignment_iri,
                    "rkaf:bindsSourceFragment": [judgment.fragment.urn],
                    "rkaf:evidenceRole": "rkaf:textualEvidence",
                    "rkaf:evidentiaryFunction": "rkaf:supports",
                }
            )
            judgment_records.append(
                {
                    "candidate_id": judgment.candidate_id,
                    "assignment": assignment_iri,
                    "concept_id": judgment.concept_id,
                    "concept_iri": judgment.concept_iri,
                    "concept_label": judgment.concept_label,
                    "scheme_iri": judgment.scheme_iri,
                    "release_iri": judgment.release_iri,
                    "role": judgment.role,
                    "evidence_urn": judgment.fragment.urn,
                    "evidence_text": judgment.evidence_text,
                    "alignment_method": judgment.alignment_method,
                    "candidate_channels": list(
                        judgment.candidate_channels
                    ),
                    "candidate_rank": judgment.candidate_rank,
                    "candidate_score": judgment.candidate_score,
                    "candidate_score_state": (
                        judgment.candidate_score_state
                    ),
                    "indexed_representation_version": (
                        judgment.indexed_representation_version
                    ),
                    "mapping_paths": [
                        dict(path) for path in judgment.mapping_paths
                    ],
                    "selected_channel": judgment.selected_channel,
                    "selected_mapping_path": (
                        dict(judgment.selected_mapping_path)
                        if judgment.selected_mapping_path is not None
                        else None
                    ),
                    "verified": True,
                }
            )

    # ------------------------------------------------- selectors + fragments
    for fragment in fragments.values():
        graph.append(_selector_node(fragment))
        graph.append(_fragment_node(fragment, artifact_iri=artifact_iri, artifact_digest=artifact_digest))

    # ---------------------------------------------------------- activities
    for spec in activities.values():
        graph.append(_activity_node(spec, partner=partner))

    # ---------------------------------------------------- provenance records
    # L3 enforces `sh:class prov:Entity` on every prov:wasDerivedFrom value
    # (compiled/shacl/core/{assertion,concept-assignment,relationship-assertion}.ttl),
    # so each cited table row is materialized as a typed node. Finding G1.
    for record_iri in sorted(provenance_records):
        graph.append({"@id": record_iri, "@type": "prov:Entity"})

    # --------------------------------------------------------- attestation
    attestation_record: dict[str, Any] | None = None
    if model_layer is not None and assignment_iris:
        scope_iri = f"{partner}:scope:{settings.scope}"
        attestor = settings.attestor_id or f"{partner}:model:{model_layer.model_id}"
        rationale = (
            f"Produced by {model_layer.model_id} through the concept_tags_v1 structured-output contract "
            f"(instructions sha256:{model_layer.instructions_sha256[:16]}…, schema sha256:{model_layer.schema_sha256[:16]}…). "
            f"Every assignment's evidence quote was re-sliced from the stored {evidence_field} state "
            f"(sha256:{artifact_digest}) and its SHA-256 matched the carrier-local URN digest; "
            f"{len(model_layer.rejections)} judgment(s) were refused and are recorded with reasons. "
            "This attestation records production and requests review; it is not approval."
        )
        attestation_record = attestation_row(
            attestor_id=attestor,
            attestor_kind=ATTESTOR_KIND_AI_MODEL,
            targets=list(assignment_iris),
            decision=MODEL_ATTESTATION_DECISION,
            attestation_scope=scope_iri,
            context=context,
            rationale=rationale,
        )
        graph.append(
            {
                "@id": f"{partner}:attestation:{attestation_record['attestation_id']}",
                "@type": "rkaf:Attestation",
                "rkaf:attestor": attestation_record["attestor_id"],
                "rkaf:attestorKind": attestation_record["attestor_kind"],
                "rkaf:targets": json.loads(attestation_record["target_ids_json"]),
                "rkaf:decision": attestation_record["decision"],
                "rkaf:attestationScope": attestation_record["attestation_scope"],
                "rkaf:attestedAt": attestation_record["attested_at"],
                "rkaf:rationale": attestation_record["rationale"],
            }
        )

    document = {"@context": settings.context_ref, "@graph": graph}
    candidate_selection = (
        model_layer.candidate_selection_receipt
        if model_layer is not None
        else None
    )
    run_record = {
        "schema_version": PROJECTION_SCHEMA_VERSION,
        "generated_at": context.asserted_at,
        "run_id": context.run_id,
        "inputs": {
            "profile_id": facts.profile_id,
            "subject_id": artifact.subject_id,
            "corpus_dir": str(settings.corpus_dir),
            "tables_dir": str(settings.tables_dir),
        },
        "artifact": {
            "artifact_id": artifact.artifact_id,
            "version_digest": f"sha256:{artifact.content_sha256}",
            "artifact_iri": artifact_iri,
            "projected_evidence_field": evidence_field,
            "content_digest": f"sha256:{artifact_digest}",
            "available_fields": sorted(artifact.raw_fields),
        },
        "contract_flags": {
            "rulespec_version": settings.rulespec_version,
            "rulespec_source_revision": settings.rulespec_source_revision,
            "rulespec_constraint_digest": (settings.rulespec_constraint_digest),
            "rulespec_pin_state": (
                "callerDeclaredRevision" if settings.rulespec_source_revision is not None else "localCandidate"
            ),
            "assertion_origin_deterministic": ASSERTION_ORIGIN_DETERMINISTIC,
            "request_contract_digest_required_for": sorted(REQUEST_CONTRACT_DIGEST_REQUIRED_FOR),
            "emit_document_docket_edge": EMIT_DOCUMENT_DOCKET_EDGE,
            "document_docket_predicate": DOCUMENT_DOCKET_PREDICATE,
            "emit_profile_edge_projections": EMIT_PROFILE_EDGE_PROJECTIONS,
            "model_attestation_decision": MODEL_ATTESTATION_DECISION,
        },
        "candidate_selection": {
            "state": (
                "configured"
                if candidate_selection is not None
                else CANDIDATE_SELECTION_STATE
            ),
            "mode": CANDIDATE_OUTPUT_MODE,
            "receipt": candidate_selection,
            "accepted_output_authorized": False,
            "usage_ceiling": (
                "diagnosticCandidateOnly"
                if candidate_selection is not None
                else MODEL_USAGE_ELIGIBILITY
            ),
        },
        "deterministic": {
            "fragments": [
                {
                    "key": fragment.key,
                    "source_field": fragment.source_field,
                    "start": fragment.start,
                    "end": fragment.end,
                    "sha256": fragment.text_sha256,
                    "urn": fragment.urn,
                }
                for fragment in fragments.values()
            ],
            "edges": edge_records,
            "activities": sorted(activities),
        },
        "model": None,
        "judgments": {"accepted": judgment_records, "rejected": []},
        "attestation": attestation_record,
        "notes": (
            list(facts.notes)
            + list(settings.extra_notes)
            + (
                [
                    "Rulespec source_revision is null; this run names a local "
                    "candidate and cannot support an immutable conformance claim."
                ]
                if settings.rulespec_source_revision is None
                else []
            )
            + (
                [
                    "The selected vocabulary asset, exact reference release, "
                    "facet, assignment role, route, and local lookup index are "
                    "recorded as diagnostic candidate inputs. They grant no "
                    "accepted-output or deployment authority."
                ]
                if candidate_selection is not None
                else [
                    "No published candidate source was selected. Model results "
                    "are diagnostic review-queue candidates only and cannot "
                    "enter accepted output."
                ]
            )
        ),
        "offset_verification": transcript,
        "node_count": len(graph),
    }
    if model_layer is not None:
        run_record["model"] = {
            "model_id": model_layer.model_id,
            "instructions_sha256": model_layer.instructions_sha256,
            "schema_sha256": model_layer.schema_sha256,
            "input_context_sha256": model_layer.input_context_sha256,
            "extraction_run_directory": model_layer.run_directory,
            "extraction_receipt_sha256": model_layer.receipt_sha256,
            "candidate_selector_version": model_layer.selector_version,
            "candidate_vocabulary_sha256": model_layer.vocabulary_sha256,
            "candidate_vocabulary_default_language": (model_layer.vocabulary_default_language),
            "candidate_concept_count": model_layer.candidate_concept_count,
            "candidate_selection_sha256": (
                model_layer.candidate_selection_sha256
            ),
            "candidate_selection_ledger": [
                dict(record)
                for record in model_layer.candidate_selection_ledger
            ],
            "provider_call_count": model_layer.call_count,
            "segment_count": model_layer.segment_count,
            "segments_projected": model_layer.segments_projected,
        }
        if model_layer.concept_domain_mapping_sha256 is not None:
            run_record["model"]["concept_domain_mapping_sha256"] = (
                model_layer.concept_domain_mapping_sha256
            )
        if model_layer.segments_projected < model_layer.segment_count:
            run_record["notes"].append(
                f"only {model_layer.segments_projected} of {model_layer.segment_count} segments were sent "
                "to the model (--max-segments); the concept assignments cover that prefix, not the document"
            )
        run_record["judgments"]["rejected"] = [dict(row) for row in model_layer.rejections]
    transcript.append("")
    transcript.append(f"assembled {len(graph)} graph nodes")
    return ProjectionResult(document=document, run_record=run_record, transcript=transcript)


class InMemoryTables:
    """:class:`PublishedTables` over rows the caller already holds.

    Same equality semantics as the producer's Parquet-backed view: both sides
    of every comparison pass through :func:`_clean`, so ``None``, ``"None"``,
    ``"nan"``, ``"null"``, and surrounding whitespace all state nothing.
    """

    def __init__(self, tables: Mapping[str, Sequence[Mapping[str, Any]]]) -> None:
        self._tables = {name: [dict(row) for row in rows] for name, rows in tables.items()}

    def rows(self, table: str, **equals: Any) -> list[dict[str, Any]]:
        return [
            row
            for row in self._tables.get(table, [])
            if all(_clean(row.get(column)) == _clean(value) for column, value in equals.items())
        ]
