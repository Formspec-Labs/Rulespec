"""Verify exact reference-release membership in a pinned RefSpec atlas."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Self

from rdflib import BNode, Dataset, Graph, Literal, Namespace, URIRef
from rdflib.namespace import PROV, RDF

try:
    from rulespec_release import (
        canonical_digest,
        canonical_json_bytes,
        content_digest,
    )
except ModuleNotFoundError:  # imported as a tools package
    from tools.rulespec_release import (
        canonical_digest,
        canonical_json_bytes,
        content_digest,
    )

ATLAS_FORMAT = "refspec-vocabulary-atlas-nquads-1.0"
ATLAS = Namespace("https://refspec.org/ns/vocabulary-atlas/v1#")
RKAF = Namespace("https://rulespec.org/ns/v1#")

_SHA256 = re.compile(r"sha256:[0-9a-f]{64}\Z")
_ABSOLUTE_IRI = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*:[^\s<>]+\Z")
_ROOT_FIELDS = {
    "id",
    "type",
    "schemaVersion",
    "format",
    "generationDigest",
    "inputs",
    "implementation",
    "policies",
    "graphs",
    "output",
    "counts",
    "canonicalPayloadDigest",
}
_POLICIES = {
    "releaseFacts": "copiedManagedReleaseFactsOnly",
    "analysis": "replaceableMachineAnalysis",
    "labelEquality": "clusterOnly",
    "mappingEligibility": "twoIndependentMachinesSearchOnly",
    "humanFeedback": "appendOnlyNonAuthorizing",
}
_COUNT_FIELDS = {
    "managedReleases",
    "releaseFacts",
    "analysisFacts",
    "labelClusters",
    "mappingCandidates",
    "searchOnlyMappings",
    "machineValidations",
    "feedback",
}


class AtlasIntegrityError(ValueError):
    """The selected atlas does not prove the requested consumer view."""


def _validate_ref_value(value: object, *, label: str) -> None:
    """Apply the REF canonical JSON value restrictions."""

    if value is None or isinstance(value, float):
        raise AtlasIntegrityError(f"{label} contains a null or floating-point value")
    if isinstance(value, bool | str):
        return
    if isinstance(value, int):
        if not (-(2**53) + 1 <= value <= (2**53) - 1):
            raise AtlasIntegrityError(f"{label} contains an unsafe integer")
        return
    if isinstance(value, list | tuple):
        for item in value:
            _validate_ref_value(item, label=label)
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise AtlasIntegrityError(f"{label} contains a non-string object key")
            _validate_ref_value(item, label=label)
        return
    raise AtlasIntegrityError(f"{label} contains an unsupported JSON value")


def _strict_json_object(payload: bytes, *, label: str) -> dict[str, Any]:
    def object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise AtlasIntegrityError(f"{label} repeats JSON key {key!r}")
            result[key] = value
        return result

    def reject_constant(value: str) -> None:
        raise AtlasIntegrityError(f"{label} contains non-finite number {value}")

    try:
        value = json.loads(
            payload,
            object_pairs_hook=object_pairs,
            parse_constant=reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AtlasIntegrityError(f"{label} is not valid UTF-8 JSON") from error
    if not isinstance(value, dict):
        raise AtlasIntegrityError(f"{label} must contain a JSON object")
    _validate_ref_value(value, label=label)
    return value


def _require_digest(value: object, *, label: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise AtlasIntegrityError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _require_iri(value: object, *, label: str) -> str:
    if not isinstance(value, str) or _ABSOLUTE_IRI.fullmatch(value) is None:
        raise AtlasIntegrityError(f"{label} must be an absolute IRI")
    return value


def _mapping(value: object, *, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise AtlasIntegrityError(f"{label} must be an object")
    return value


def _sequence(value: object, *, label: str) -> Sequence[Any]:
    if not isinstance(value, Sequence) or isinstance(value, str | bytes):
        raise AtlasIntegrityError(f"{label} must be an array")
    return value


def _is_integer(value: object) -> bool:
    """Accept JSON integers without treating booleans as numbers."""

    return isinstance(value, int) and not isinstance(value, bool)


def _one_literal(graph: Graph, subject: URIRef, predicate: URIRef) -> Literal:
    values = tuple(graph.objects(subject, predicate))
    if len(values) != 1 or not isinstance(values[0], Literal):
        raise AtlasIntegrityError(f"{subject} must have one literal-valued {predicate}")
    return values[0]


def _canonical_nquads(dataset: Dataset) -> bytes:
    for subject, predicate, object_, graph in dataset.quads((None, None, None, None)):
        if any(
            isinstance(value, BNode) for value in (subject, predicate, object_, graph)
        ):
            raise AtlasIntegrityError("vocabulary atlas must not contain blank nodes")
    serialized = dataset.serialize(format="nquads")
    text = serialized.decode("utf-8") if isinstance(serialized, bytes) else serialized
    lines = sorted(line for line in text.splitlines() if line.strip())
    return ("\n".join(lines) + "\n").encode("utf-8")


def _validate_managed_pin(value: Mapping[str, Any]) -> None:
    if (
        set(value)
        != {
            "role",
            "manifestDigest",
            "publicationReleaseId",
            "rulespecGraph",
        }
        or value.get("role") != "ManagedReleaseView"
    ):
        raise AtlasIntegrityError("managed-release input has unsupported fields")
    _require_digest(
        value.get("manifestDigest"), label="managed-release manifest digest"
    )
    _require_iri(
        value.get("publicationReleaseId"), label="managed publication release id"
    )
    graph = _mapping(value.get("rulespecGraph"), label="managed rulespecGraph")
    if set(graph) != {"id", "digest"}:
        raise AtlasIntegrityError("managed rulespecGraph has unsupported fields")
    _require_iri(graph.get("id"), label="managed rulespecGraph id")
    _require_digest(graph.get("digest"), label="managed rulespecGraph digest")


def _validate_core_pin(value: Mapping[str, Any]) -> None:
    if (
        set(value) != {"role", "fileDigest", "releaseId", "releaseDigest"}
        or value.get("role") != "RulespecCoreRelease"
    ):
        raise AtlasIntegrityError("Rulespec Core input has unsupported fields")
    _require_digest(value.get("fileDigest"), label="Rulespec Core file digest")
    _require_iri(value.get("releaseId"), label="Rulespec Core release id")
    release_digest = _require_digest(
        value.get("releaseDigest"), label="Rulespec Core release digest"
    )
    if value.get("releaseId") != "urn:rulespec:core:" + release_digest.removeprefix(
        "sha256:"
    ):
        raise AtlasIntegrityError("Rulespec Core release id differs from its digest")


def _validate_crosswalk_pin(value: Mapping[str, Any]) -> None:
    if (
        set(value) != {"role", "id", "digest", "fileDigest", "mediaType"}
        or value.get("role") != "CrosswalkBundle"
    ):
        raise AtlasIntegrityError("crosswalk input has unsupported fields")
    _require_iri(value.get("id"), label="crosswalk id")
    _require_digest(value.get("digest"), label="crosswalk digest")
    _require_digest(value.get("fileDigest"), label="crosswalk file digest")
    if (
        value.get("mediaType")
        != "application/vnd.refspec.vocabulary-atlas-crosswalk+json"
    ):
        raise AtlasIntegrityError("crosswalk media type is unsupported")


def _reference_release_digest(graph: Graph, release: URIRef) -> str:
    if (release, RDF.type, RKAF.ReferenceResourceRelease) not in graph:
        raise AtlasIntegrityError(
            f"atlas release {release} is not a ReferenceResourceRelease"
        )
    return _require_digest(
        str(_one_literal(graph, release, RKAF.referenceReleaseDigest)),
        label=f"atlas release {release} digest",
    )


def _validate_membership_semantics(
    dataset: Dataset, *, release_graph_id: str, analysis_graph_id: str
) -> None:
    """Check analysis membership only against authoritative release facts."""

    release_graph = dataset.graph(URIRef(release_graph_id))
    analysis = dataset.graph(URIRef(analysis_graph_id))

    for member, release in analysis.subject_objects(ATLAS.memberOfRelease):
        if not isinstance(member, URIRef) or not isinstance(release, URIRef):
            raise AtlasIntegrityError("atlas membership must connect two IRIs")
        _reference_release_digest(release_graph, release)
        if (release, PROV.hadMember, member) not in release_graph:
            raise AtlasIntegrityError(
                "atlas analysis membership is absent from authoritative release facts"
            )


@dataclass(frozen=True, slots=True)
class ExactReleasePin:
    """One exact release identity returned by verified static facts."""

    release_id: str
    release_digest: str


@dataclass(frozen=True, slots=True)
class RefSpecVocabularyAtlas:
    """A verified RefSpec manifest and immutable two-graph distribution."""

    manifest: Mapping[str, Any]
    manifest_digest: str
    output_digest: str
    release_facts_graph_id: str
    analysis_graph_id: str
    _dataset: Dataset

    @classmethod
    def open(
        cls,
        directory: Path | str,
        *,
        expected_manifest_digest: str,
        expected_output_digest: str,
    ) -> Self:
        """Open one atlas selected only by its two external file digests."""

        expected_manifest_digest = _require_digest(
            expected_manifest_digest, label="expected atlas manifest digest"
        )
        expected_output_digest = _require_digest(
            expected_output_digest, label="expected atlas output digest"
        )
        root = Path(directory)
        if root.is_symlink():
            raise AtlasIntegrityError(
                "vocabulary atlas directory must not be a symlink"
            )
        try:
            root = root.resolve(strict=True)
        except FileNotFoundError as error:
            raise AtlasIntegrityError(
                "vocabulary atlas directory does not exist"
            ) from error
        if not root.is_dir():
            raise AtlasIntegrityError("vocabulary atlas path must be a directory")

        manifest_path = root / "atlas-manifest.json"
        if manifest_path.is_symlink() or not manifest_path.is_file():
            raise AtlasIntegrityError("atlas-manifest.json must be a regular file")
        manifest_bytes = manifest_path.read_bytes()
        if content_digest(manifest_bytes) != expected_manifest_digest:
            raise AtlasIntegrityError(
                "atlas manifest bytes differ from the external pin"
            )
        manifest = _strict_json_object(manifest_bytes, label="atlas manifest")
        if manifest_bytes != canonical_json_bytes(manifest) + b"\n":
            raise AtlasIntegrityError("atlas manifest bytes are not canonical REF JSON")
        if set(manifest) != _ROOT_FIELDS:
            raise AtlasIntegrityError(
                "atlas manifest fields differ from the supported format"
            )
        if (
            manifest.get("schemaVersion") != "1.0"
            or manifest.get("format") != ATLAS_FORMAT
        ):
            raise AtlasIntegrityError("atlas manifest version or format is unsupported")
        if manifest.get("type") != "urn:ref:type:VocabularyAtlasManifest":
            raise AtlasIntegrityError("atlas manifest type is unsupported")

        generation_digest = _require_digest(
            manifest.get("generationDigest"), label="atlas generationDigest"
        )
        asset_id = _require_iri(manifest.get("id"), label="atlas id")
        manifest_payload = dict(manifest)
        declared_payload_digest = _require_digest(
            manifest_payload.pop("canonicalPayloadDigest"),
            label="atlas canonicalPayloadDigest",
        )
        if canonical_digest(manifest_payload) != declared_payload_digest:
            raise AtlasIntegrityError(
                "atlas canonicalPayloadDigest does not match the manifest"
            )

        implementation = _mapping(
            manifest.get("implementation"), label="atlas implementation"
        )
        if set(implementation) != {"id", "version", "sourceModules", "runtime"}:
            raise AtlasIntegrityError("atlas implementation has unsupported fields")
        _require_iri(implementation.get("id"), label="atlas implementation id")
        if (
            not isinstance(implementation.get("version"), str)
            or not implementation["version"].strip()
        ):
            raise AtlasIntegrityError("atlas implementation version is required")
        modules = list(
            _sequence(
                implementation.get("sourceModules"),
                label="atlas implementation sourceModules",
            )
        )
        observed_paths: list[str] = []
        for raw_module in modules:
            module = _mapping(raw_module, label="atlas implementation source module")
            if (
                set(module) != {"path", "digest"}
                or not isinstance(module.get("path"), str)
                or not module["path"].strip()
            ):
                raise AtlasIntegrityError(
                    "atlas implementation source module has unsupported fields"
                )
            path = str(module["path"])
            if path in observed_paths:
                raise AtlasIntegrityError(
                    "atlas implementation repeats a source module"
                )
            observed_paths.append(path)
            _require_digest(
                module.get("digest"), label=f"atlas implementation module {path}"
            )
        if not observed_paths:
            raise AtlasIntegrityError(
                "atlas implementation needs at least one source module"
            )
        runtime = _mapping(
            implementation.get("runtime"), label="atlas implementation runtime"
        )
        if not runtime or any(
            not isinstance(key, str)
            or not key.strip()
            or not isinstance(value, str)
            or not value.strip()
            for key, value in runtime.items()
        ):
            raise AtlasIntegrityError(
                "atlas implementation runtime must contain named version strings"
            )

        inputs = list(_sequence(manifest.get("inputs"), label="atlas inputs"))
        managed_inputs = [
            _mapping(value, label="managed-release input")
            for value in inputs
            if isinstance(value, Mapping) and value.get("role") == "ManagedReleaseView"
        ]
        core_inputs = [
            _mapping(value, label="Rulespec Core input")
            for value in inputs
            if isinstance(value, Mapping) and value.get("role") == "RulespecCoreRelease"
        ]
        crosswalk_inputs = [
            _mapping(value, label="crosswalk input")
            for value in inputs
            if isinstance(value, Mapping) and value.get("role") == "CrosswalkBundle"
        ]
        if (
            len(managed_inputs) < 1
            or len(core_inputs) != 1
            or len(crosswalk_inputs) > 1
        ):
            raise AtlasIntegrityError(
                "atlas inputs require managed releases, one Rulespec Core, and at most one crosswalk"
            )
        if len(managed_inputs) + len(core_inputs) + len(crosswalk_inputs) != len(
            inputs
        ):
            raise AtlasIntegrityError("atlas contains an unsupported input role")
        for pin in managed_inputs:
            _validate_managed_pin(pin)
        _validate_core_pin(core_inputs[0])
        if crosswalk_inputs:
            _validate_crosswalk_pin(crosswalk_inputs[0])

        graph_rows = list(_sequence(manifest.get("graphs"), label="atlas graphs"))
        if len(graph_rows) != 2:
            raise AtlasIntegrityError("atlas must declare exactly two named graphs")
        graph_by_role: dict[str, Mapping[str, Any]] = {}
        for raw_row in graph_rows:
            row = _mapping(raw_row, label="atlas graph")
            if set(row) != {"role", "id", "quadCount"}:
                raise AtlasIntegrityError(
                    "atlas graph declaration has unsupported fields"
                )
            role = row.get("role")
            if role not in {"releaseFacts", "analysis"} or role in graph_by_role:
                raise AtlasIntegrityError(
                    "atlas graph roles must be releaseFacts and analysis"
                )
            _require_iri(row.get("id"), label=f"atlas {role} graph id")
            if not _is_integer(row.get("quadCount")) or int(row["quadCount"]) < 1:
                raise AtlasIntegrityError(
                    "atlas graph quadCount must be a positive integer"
                )
            graph_by_role[str(role)] = row

        output = _mapping(manifest.get("output"), label="atlas output")
        if set(output) != {"path", "mediaType", "digest", "byteLength", "quadCount"}:
            raise AtlasIntegrityError("atlas output declaration has unsupported fields")
        if (
            output.get("path") != "atlas.nq"
            or output.get("mediaType") != "application/n-quads"
        ):
            raise AtlasIntegrityError("atlas output format is unsupported")
        output_digest = _require_digest(
            output.get("digest"), label="atlas output digest"
        )
        if output_digest != expected_output_digest:
            raise AtlasIntegrityError(
                "atlas output digest differs from the consumer pin"
            )
        output_path = root / "atlas.nq"
        if output_path.is_symlink() or not output_path.is_file():
            raise AtlasIntegrityError("atlas.nq must be a regular file")
        payload = output_path.read_bytes()
        if (
            not _is_integer(output.get("byteLength"))
            or output["byteLength"] != len(payload)
            or content_digest(payload) != output_digest
        ):
            raise AtlasIntegrityError("atlas.nq bytes differ from the manifest")
        try:
            dataset = Dataset(default_union=False)
            dataset.parse(data=payload, format="nquads")
        except Exception as error:
            raise AtlasIntegrityError("atlas.nq is not valid N-Quads") from error
        if _canonical_nquads(dataset) != payload:
            raise AtlasIntegrityError("atlas N-Quads bytes are not canonical")
        graph_ids = {str(graph.identifier) for graph in dataset.graphs() if len(graph)}
        declared_graph_ids = {str(row["id"]) for row in graph_by_role.values()}
        if graph_ids != declared_graph_ids:
            raise AtlasIntegrityError("atlas.nq graph names differ from the manifest")
        total_quads = sum(1 for _ in dataset.quads((None, None, None, None)))
        if (
            not _is_integer(output.get("quadCount"))
            or output["quadCount"] != total_quads
        ):
            raise AtlasIntegrityError("atlas output quadCount differs")
        for role, row in graph_by_role.items():
            if len(dataset.graph(URIRef(str(row["id"])))) != row["quadCount"]:
                raise AtlasIntegrityError(f"atlas {role} graph count differs")

        counts = _mapping(manifest.get("counts"), label="atlas counts")
        if set(counts) != _COUNT_FIELDS or any(
            not _is_integer(value) or value < 0 for value in counts.values()
        ):
            raise AtlasIntegrityError("atlas counts must be nonnegative integers")
        release_graph = dataset.graph(URIRef(str(graph_by_role["releaseFacts"]["id"])))
        analysis_graph = dataset.graph(URIRef(str(graph_by_role["analysis"]["id"])))
        observed_counts = {
            "managedReleases": len(managed_inputs),
            "releaseFacts": len(release_graph),
            "analysisFacts": len(analysis_graph),
            "labelClusters": len(
                set(analysis_graph.subjects(RDF.type, ATLAS.LabelCluster))
            ),
            "mappingCandidates": len(
                set(analysis_graph.subjects(RDF.type, ATLAS.MappingCandidate))
            ),
            "searchOnlyMappings": len(
                {
                    subject
                    for subject in analysis_graph.subjects(
                        RDF.type, RKAF.ConceptMapping
                    )
                    if (subject, RKAF.usageEligibility, RKAF.searchOnly)
                    in analysis_graph
                }
            ),
            "machineValidations": len(
                set(analysis_graph.subjects(RDF.type, ATLAS.MachineValidation))
            ),
            "feedback": len(
                set(analysis_graph.subjects(RDF.type, ATLAS.MappingFeedback))
            ),
        }
        if dict(counts) != observed_counts:
            raise AtlasIntegrityError(
                "atlas counts differ from the static distribution"
            )
        _validate_membership_semantics(
            dataset,
            release_graph_id=str(graph_by_role["releaseFacts"]["id"]),
            analysis_graph_id=str(graph_by_role["analysis"]["id"]),
        )
        policies = _mapping(manifest.get("policies"), label="atlas policies")
        if dict(policies) != _POLICIES:
            raise AtlasIntegrityError(
                "atlas policies differ from the supported search-only boundary"
            )
        computed_generation_digest = canonical_digest(
            {
                "format": ATLAS_FORMAT,
                "inputs": inputs,
                "implementation": dict(implementation),
                "policies": dict(policies),
            }
        )
        if generation_digest != computed_generation_digest:
            raise AtlasIntegrityError(
                "atlas generationDigest differs from its exact generation inputs"
            )
        expected_asset_id = (
            "urn:ref:vocabulary-atlas:"
            + computed_generation_digest.removeprefix("sha256:")
        )
        if asset_id != expected_asset_id:
            raise AtlasIntegrityError(
                "atlas identifier does not match its generation digest"
            )
        expected_graph_ids = {
            "releaseFacts": expected_asset_id + ":release-facts",
            "analysis": expected_asset_id + ":analysis",
        }
        if any(
            str(graph_by_role[role]["id"]) != graph_id
            for role, graph_id in expected_graph_ids.items()
        ):
            raise AtlasIntegrityError(
                "atlas graph identifiers do not match the generated asset"
            )

        return cls(
            manifest=manifest,
            manifest_digest=expected_manifest_digest,
            output_digest=output_digest,
            release_facts_graph_id=str(graph_by_role["releaseFacts"]["id"]),
            analysis_graph_id=str(graph_by_role["analysis"]["id"]),
            _dataset=dataset,
        )

    @property
    def asset_id(self) -> str:
        """Return the content-derived atlas identifier."""

        return str(self.manifest["id"])

    def pin(self) -> dict[str, str]:
        """Return the exact fields an ExtrapolationRelease should retain."""

        return {
            "asset_id": self.asset_id,
            "manifest_digest": self.manifest_digest,
            "distribution_digest": self.output_digest,
        }

    def rulespec_core_pin(self) -> ExactReleasePin:
        """Return the one Rulespec Core identity sealed into the manifest."""

        values = [
            value
            for value in self.manifest["inputs"]
            if isinstance(value, Mapping) and value.get("role") == "RulespecCoreRelease"
        ]
        if len(values) != 1:
            raise AtlasIntegrityError(
                "atlas must contain exactly one Rulespec Core input"
            )
        return ExactReleasePin(
            release_id=str(values[0]["releaseId"]),
            release_digest=str(values[0]["releaseDigest"]),
        )

    def require_member(self, *, member_id: str, release_id: str) -> ExactReleasePin:
        """Return the exact release pin or reject an assignment target."""

        member = URIRef(_require_iri(member_id, label="member id"))
        release = URIRef(_require_iri(release_id, label="reference release id"))
        release_facts = self._dataset.graph(URIRef(self.release_facts_graph_id))
        release_digest = _reference_release_digest(release_facts, release)
        if (release, PROV.hadMember, member) not in release_facts:
            raise AtlasIntegrityError(
                f"atlas release {release_id} does not contain member {member_id}"
            )
        return ExactReleasePin(
            release_id=str(release),
            release_digest=release_digest,
        )


__all__ = [
    "ATLAS_FORMAT",
    "AtlasIntegrityError",
    "ExactReleasePin",
    "RefSpecVocabularyAtlas",
]
