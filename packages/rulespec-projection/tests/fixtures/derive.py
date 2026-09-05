"""Derive the parity fixtures by running spicy-regs at 8d9e7a2. Not a test.

Usage, from the rulespec repository root, with a detached checkout of spicy-regs
at 8d9e7a2 (``git worktree add --detach <dir> 8d9e7a2`` in that repository)::

    cd <dir> && env -u ONTOLOGY_RUN_ID PYTHONPATH=<dir>/src \\
        uv run --no-project --python 3.12 --with pyarrow --with loguru --with rdflib \\
        python <rulespec>/packages/rulespec-projection/tests/fixtures/derive.py \\
        <rulespec>/packages/rulespec-projection/tests/fixtures

Run with PYTHONPATH pointing at a checkout of spicy-regs 8d9e7a2 and an
environment carrying pyarrow, loguru, and rdflib. Every expected value in the
emitted JSON comes from the original code; the port's tests read these files
and never compute an expectation of their own.
"""
from __future__ import annotations
import dataclasses, json, os, sys, tempfile
from pathlib import Path
import pyarrow as pa, pyarrow.parquet as pq
from spicy_regs.docpipeline import rkaf_projection as rp
from spicy_regs.ontology import citations as cit
from spicy_regs.ontology.llm import resolve_exact_evidence_offsets

assert "ONTOLOGY_RUN_ID" not in os.environ, "unset ONTOLOGY_RUN_ID so run ids derive from asserted_at"
OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
REF = {"derived_from": "spicy-regs 8d9e7a2 src/spicy_regs/docpipeline/rkaf_projection.py", "generator": "packages/rulespec-projection/tests/fixtures/derive.py, run against spicy-regs 8d9e7a2 on 2026-09-05"}

FR_BODY = (
    "<html><body>"
    "<ul><li>9 CFR Part 381</li><li>[Docket No. TEST-2026-0001]</li></ul>"
    "<p>This proposed rule concerns poultry slaughter inspection at establishments.</p>"
    "<p>Authority: 7 U.S.C. 450 governs the program.</p>"
    "<p>Establishments must keep inspection records. Inspection records are reviewed.</p>"
    "</body></html>"
)
UA_ABSTRACT = "FSIS proposes to amend 9 CFR 381 under 7 U.S.C. 450 to modernize poultry slaughter inspection."

def write(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = sorted({k for r in rows for k in r})
    pq.write_table(pa.table({c: [r.get(c) for r in rows] for c in columns}), path)

def plain(value):
    if dataclasses.is_dataclass(value) and not isinstance(value, type): return plain(dataclasses.asdict(value))
    if isinstance(value, dict): return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)): return [plain(v) for v in value]
    if hasattr(value, "items"): return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, Path): return str(value)
    return value

def artifact_fields(a):
    return {"artifact_id": a.artifact_id, "content_sha256": a.content_sha256, "subject_id": a.subject_id,
            "profile_id": a.profile_id, "raw_fields": dict(a.raw_fields), "field_sha256": dict(a.field_sha256)}

tmp = Path(tempfile.mkdtemp()); corpus = tmp / "corpus"; tables_dir = tmp / "tables"
FR_ROW = {"document_number": "2026-00001", "title": "Poultry slaughter inspection", "abstract": "A proposed rule.",
          "document_type": "Proposed Rule", "agency_slugs": json.dumps(["food-safety-and-inspection-service"]),
          "body_html": FR_BODY, "docket_ids_json": json.dumps(["TEST-2026-0001", "TEST-2026-0002", "Docket No. TEST-2026-0001"]),
          "topics_json": json.dumps(["Poultry and poultry products"])}
UA_ROW = {"rin": "0583-AE99", "agenda_edition": "202510", "title": "Modernization of Poultry Slaughter Inspection",
          "abstract": UA_ABSTRACT, "rule_stage": "Proposed Rule Stage", "priority_category": "Other Significant",
          "cfr_references_json": json.dumps(["9 CFR 381", "not a citation"]), "legal_authority_json": json.dumps(["7 U.S.C. 450", "Pub. L. 85-172"]),
          "url": "https://www.reginfo.gov/public/do/eAgendaViewRule?pubId=202510&RIN=0583-AE99"}
write(corpus / "federal_register.parquet", [FR_ROW])
write(corpus / "unified_agenda.parquet", [UA_ROW])
TABLES = {
    "proceedings": [{"proceeding_id": "proceeding_test", "rin": "0583-AE99", "docket_ids_json": json.dumps(["TEST-2026-0001"]),
                     "fr_document_numbers_json": json.dumps(["2026-00001"]), "cfr_target_iris_json": json.dumps(["urn:rkaf:us:cfr:9:381"]),
                     "current_stage": "proposed", "actor_id": "spicy-regs:proceedings:v1", "run_id": "test-run", "asserted_at": "2026-07-01T00:00:00Z"}],
    "rule_targets": [{"docket_id": "TEST-2026-0001", "cfr_ref": "9-381", "cfr_title": "9", "cfr_part": "381", "cfr_section": None,
                      "rin": "0583-AE99", "actor_id": "spicy-regs:rule-targets:v1", "run_id": "test-run", "asserted_at": "2026-07-01T00:00:00Z"}],
    "authority_edges": [{"rin": "0583-AE99", "authority_raw": "7 U.S.C. 450", "usc_title": "7", "usc_section": "450", "pl_number": None,
                         "authority_type": "usc", "parse_status": "partial", "agenda_edition": "202510",
                         "actor_id": "spicy-regs:authority-parser:v1", "run_id": "test-run", "asserted_at": "2026-07-01T00:00:00Z"}],
    "dockets": [{"docket_id": "TEST-2026-0001", "title": "Poultry slaughter inspection docket"}],
}
for name, rows in TABLES.items(): write(tables_dir / f"{name}.parquet", rows)
tables_json = {name: pq.read_table(tables_dir / f"{name}.parquet").to_pylist() for name in TABLES}
published = rp.PublishedTables(tables_dir)

def settings(**over):
    base = dict(corpus_dir=Path("corpus"), tables_dir=Path("tables"), rulespec_version="0.0.0-test",
                rulespec_constraint_digest="sha256:" + "a" * 64, rulespec_source_revision=None,
                asserted_at="2026-07-28T00:00:00Z", vocabulary_default_language="en", prompt_concept_limit=4)
    base.update(over); return rp.ProjectionSettings(**base)
SETTINGS_FIELDS = {"corpus_dir": "corpus", "tables_dir": "tables", "rulespec_version": "0.0.0-test",
                   "rulespec_constraint_digest": "sha256:" + "a" * 64, "rulespec_source_revision": None,
                   "asserted_at": "2026-07-28T00:00:00Z", "vocabulary_default_language": "en", "prompt_concept_limit": 4}

# ---- federal register, deterministic only
fr_artifact, fr_row = rp.load_artifact("federal-register-document-v1", "2026-00001", corpus_dir=corpus)
fr_facts = rp._federal_register_facts(fr_artifact, fr_row, tables=published, partner=settings().partner)
fr_result = rp.assemble(fr_artifact, fr_facts, settings=settings(), model_layer=None)
(OUT / "federal_register_document.json").write_text(json.dumps({**REF, "artifact": artifact_fields(fr_artifact), "row": plain(fr_row),
    "tables": plain(tables_json), "settings": SETTINGS_FIELDS, "facts": plain(fr_facts),
    "result": {"document": fr_result.document, "run_record": plain(fr_result.run_record), "transcript": fr_result.transcript}}, indent=1, ensure_ascii=False, sort_keys=True) + "\n")

# ---- federal register with no published tables (artifact-only degradation)
empty = rp.PublishedTables(tmp / "no-tables")
fr_facts_empty = rp._federal_register_facts(fr_artifact, fr_row, tables=empty, partner=settings().partner)
fr_result_empty = rp.assemble(fr_artifact, fr_facts_empty, settings=settings(), model_layer=None)
(OUT / "federal_register_document_no_tables.json").write_text(json.dumps({**REF, "artifact": artifact_fields(fr_artifact), "row": plain(fr_row), "tables": {},
    "settings": SETTINGS_FIELDS, "facts": plain(fr_facts_empty), "result": {"document": fr_result_empty.document, "run_record": plain(fr_result_empty.run_record), "transcript": fr_result_empty.transcript}}, indent=1, ensure_ascii=False, sort_keys=True) + "\n")

# ---- unified agenda
ua_artifact, ua_row = rp.load_artifact("unified-agenda-observation-v1", json.dumps({"rin": "0583-AE99", "agenda_edition": "202510"}), corpus_dir=corpus)
ua_facts = rp._unified_agenda_facts(ua_artifact, ua_row, tables=published, partner=settings().partner)
ua_result = rp.assemble(ua_artifact, ua_facts, settings=settings(), model_layer=None)
(OUT / "unified_agenda_observation.json").write_text(json.dumps({**REF, "artifact": artifact_fields(ua_artifact), "row": plain(ua_row), "tables": plain(tables_json),
    "settings": SETTINGS_FIELDS, "facts": plain(ua_facts), "result": {"document": ua_result.document, "run_record": plain(ua_result.run_record), "transcript": ua_result.transcript}}, indent=1, ensure_ascii=False, sort_keys=True) + "\n")

# ---- model layer: candidate rows through verify_candidate_rows, then assemble with attestation
field = "federal_register.body_html"
def span(text): s = FR_BODY.index(text); return s, s + len(text)
s1, e1 = span("poultry slaughter inspection"); s2, e2 = span("7 U.S.C. 450")
vocab = {"c1": rp.VocabularyConcept(concept_iri="urn:test:concept:c1", scheme_iri="urn:test:scheme:subject", release_iri="urn:test:release:1", facet="subject",
                                    preferred_labels={"en": "Poultry inspection", "fr": "Inspection de la volaille"}, alternate_labels={"en": ("Poultry slaughter",)}, hidden_labels={}, definitions={"en": "Inspection of poultry slaughter."}),
         "c2": rp.VocabularyConcept(concept_iri="urn:test:concept:c2", scheme_iri="urn:test:scheme:subject", release_iri="urn:test:release:1", facet="subject",
                                    preferred_labels={"de": "Rechtsgrundlage"}, alternate_labels={}, hidden_labels={}, definitions={})}
def cand(cid, **over):
    row = {"candidate_id": cid, "concept_id": "c1", "role": "primary", "source_field": field, "evidence_text": FR_BODY[s1:e1], "evidence_grade": "source-exact",
           "source_start_char": s1, "source_end_char": e1, "confidence": 0.91, "evidence_alignment_method": "unique-exact", "candidate_channels": ["lexical", "embedding"],
           "candidate_rank": 1, "candidate_score": 0.75, "candidate_score_state": "recorded", "indexed_representation_version": "repr-v1",
           "mapping_paths": [{"from": "label", "to": "concept"}], "selected_channel": "lexical", "selected_mapping_path": {"from": "label", "to": "concept"}}
    row.update(over); return row
candidate_rows = [
    cand("k-accepted"),
    cand("k-accepted-no-default-language", concept_id="c2", role="mention", evidence_text=FR_BODY[s2:e2], source_start_char=s2, source_end_char=e2, candidate_rank=0, candidate_score=None, candidate_channels="not-a-list", mapping_paths=None, selected_mapping_path=None, candidate_score_state=""),
    cand("k-novel", concept_id=""),
    cand("k-wrong-field", source_field="federal_register.title"),
    cand("k-parser-grade", evidence_grade="parser-derived"),
    cand("k-bad-role", role="chief"),
    cand("k-unselected-role", role="contextual"),
    cand("k-drifted", source_end_char=e1 + 1),
    cand("k-unresolved", concept_id="c-missing"),
]
allowed_roles = [rp.ASSIGNMENT_ROLE_ABSOLUTE_IRIS["primary"], rp.ASSIGNMENT_ROLE_ABSOLUTE_IRIS["mention"]]
judgments, rejections = rp.verify_candidate_rows(fr_artifact, candidate_rows, artifact_iri=fr_facts.artifact_iri, evidence_field=field, vocabulary_concepts=vocab, allowed_assignment_role_iris=allowed_roles)
judgments_bare, rejections_bare = rp.verify_candidate_rows(fr_artifact, [cand("k-bare", concept_id="urn:test:concept:c1", facet="subject", concept_label="Poultry inspection", definition="Inspection of poultry slaughter.")], artifact_iri=fr_facts.artifact_iri, evidence_field=field)
model_fields = dict(model_id="fixture-model-2026", instructions_sha256="1" * 64, schema_sha256="2" * 64, input_context_sha256="3" * 64, run_directory="runs/fixture-run",
                    receipt_sha256="4" * 64, selector_version="anchored-v2", vocabulary_sha256="5" * 64, vocabulary_default_language="en",
                    vocabulary_nodes=({"@id": "urn:test:concept:c1", "@type": "skos:Concept", "skos:prefLabel": "Poultry inspection"},),
                    candidate_concept_count=2, call_count=1, candidate_selection_receipt={"asset": "fixture-atlas", "release": "urn:test:release:1"},
                    concept_domain_mapping_sha256="6" * 64, candidate_selection_sha256="7" * 64, candidate_selection_ledger=({"step": "select", "count": 2},),
                    segment_count=3, segments_projected=2, temperature=0.0)
model_layer = rp.ModelLayer(**model_fields, vocabulary_concepts=vocab, judgments=tuple(judgments), rejections=tuple(rejections))
model_result = rp.assemble(fr_artifact, fr_facts, settings=settings(attestor_id=""), model_layer=model_layer)
(OUT / "model_layer.json").write_text(json.dumps({**REF, "artifact": artifact_fields(fr_artifact), "artifact_iri": fr_facts.artifact_iri, "evidence_field": field,
    "vocabulary_concepts": plain(vocab), "allowed_assignment_role_iris": allowed_roles, "candidate_rows": candidate_rows,
    "judgments": plain(judgments), "rejections": plain(rejections),
    "bare_candidate_rows": [cand("k-bare", concept_id="urn:test:concept:c1", facet="subject", concept_label="Poultry inspection", definition="Inspection of poultry slaughter.")],
    "bare_judgments": plain(judgments_bare), "bare_rejections": plain(rejections_bare),
    "model_layer": plain({**model_fields, "vocabulary_nodes": list(model_fields["vocabulary_nodes"]), "candidate_selection_ledger": list(model_fields["candidate_selection_ledger"])}),
    "tables": plain(tables_json), "settings": SETTINGS_FIELDS,
    "result": {"document": model_result.document, "run_record": plain(model_result.run_record), "transcript": model_result.transcript}}, indent=1, ensure_ascii=False, sort_keys=True) + "\n")

# ---- fragment verification and grounding cases
cases = []
def frag_case(name, **kw):
    try:
        f = rp.verify_fragment(fr_artifact, key=name, artifact_iri=fr_facts.artifact_iri, **kw)
        cases.append({"name": name, "args": kw, "fragment": plain(f), "error": None})
    except rp.OffsetVerificationError as error:
        cases.append({"name": name, "args": kw, "fragment": None, "error": str(error)})
frag_case("exact", source_field=field, start=s1, end=e1, expected_text=FR_BODY[s1:e1])
frag_case("no-expected-text", source_field=field, start=s2, end=e2)
frag_case("end-before-start", source_field=field, start=10, end=5)
frag_case("past-end", source_field=field, start=0, end=len(FR_BODY) + 1)
frag_case("drifted", source_field=field, start=s1, end=e1 + 1, expected_text=FR_BODY[s1:e1])
frag_case("missing-field", source_field="federal_register.nope", start=0, end=1)
frag_case("empty-region", source_field=field, start=0, end=0)
grounds = []
for forms in (["Docket No. TEST-2026-0001", "TEST-2026-0001"], ["Inspection records"], ["inspection records"], ["absent phrase"], ["", "9 CFR Part 381"], ["9 CFR part 381", "9 CFR 381"]):
    g = rp.ground_literal(fr_artifact, key="ground", source_field=field, artifact_iri=fr_facts.artifact_iri, surface_forms=forms)
    grounds.append({"surface_forms": forms, "fragment": plain(g)})
(OUT / "fragments.json").write_text(json.dumps({**REF, "artifact": artifact_fields(fr_artifact), "artifact_iri": fr_facts.artifact_iri, "verify_fragment": cases, "ground_literal": grounds,
    "encode_for_uri": {s: rp.encode_for_uri(s) for s in ["https://www.federalregister.gov/d/2026-00001", "a b/c?d=é", "plain-._~", "漢字", "%41"]},
    "resolve_exact_evidence_offsets": [{"quote": q, "resolution": plain(resolve_exact_evidence_offsets(FR_BODY, q, None, None))} for q in ["poultry", "Inspection records", "inspection", "zzz", ""]]},
    indent=1, ensure_ascii=False, sort_keys=True) + "\n")

# ---- citations: the ten names the projection uses, over representative inputs
def try_call(fn, *args):
    try: return {"value": plain(fn(*args)), "error": None}
    except Exception as error: return {"value": None, "error": f"{type(error).__name__}: {error}"}
citations = {
    "canonical_cfr_iri": [{"args": a, **try_call(cit.canonical_cfr_iri, *a)} for a in [["9", "381", None], ["9", "381", "1"], ["40", "60", "60.1"], ["0", "1", None], ["9", "", None], ["51", "1", None]]],
    "canonical_usc_iri": [{"args": a, **try_call(cit.canonical_usc_iri, *a)} for a in [["7", "450"], ["42", "7401"], ["7", "450a"], ["", "450"], ["7", ""]]],
    "canonical_pl_iri": [{"args": a, **try_call(cit.canonical_pl_iri, *a)} for a in [["85-172"], ["Pub. L. 85-172"], ["117-58"], ["nonsense"]]],
    "canonical_rin_iri": [{"args": a, **try_call(cit.canonical_rin_iri, *a)} for a in [["0583-AE99"], ["0583-ae99"], ["AE99"], [""]]],
    "canonical_regsgov_iri": [{"args": a, **try_call(cit.canonical_regsgov_iri, *a)} for a in [["TEST-2026-0001"], ["FSIS-2026-0001-0002"], ["Docket No. TEST-2026-0001"], ["bad id"]]],
    "docket_reference_as_stated": [{"args": [a], **try_call(cit.docket_reference_as_stated, a)} for a in ["Docket No. TEST-2026-0001", "  TEST-2026-0001 ", "None", "null", "nan", "", "Docket No.", "Docket Nos. TEST-2026-0001; TEST-2026-0002"]],
    "normalize_docket_reference": [{"args": [a], **try_call(cit.normalize_docket_reference, a)} for a in ["Docket No. TEST-2026-0001", "TEST-2026-0001", "test-2026-0001", "TEST 2026 0001", "not a docket", "FSIS-2026-0001-0002"]],
    "federal_register_identifier": [{"args": [a], **try_call(cit.federal_register_identifier, a)} for a in ["2026-00001", "94-120124", "X97-10423", "E9-31172", "2013-58", "", "nonsense"]],
    "parse_cfr_citation": [{"args": [a], **try_call(cit.parse_cfr_citation, a)} for a in ["9 CFR 381", "9 CFR Part 381", "9 CFR 381.1", "40 CFR Parts 60 and 63", "9-381", "not a citation", "9 CFR 381.1 through 381.9", "21 CFR 1.1-1.9"]],
    "parse_authority_citation": [{"args": [a], **try_call(cit.parse_authority_citation, a)} for a in ["7 U.S.C. 450", "7 U.S.C. 450; 21 U.S.C. 451-470", "Pub. L. 85-172", "42 U.S.C. 7401 et seq.", "26 U.S.C. 501", "E.O. 12866", "nothing here", "7 USC 450 and 451"]],
}
(OUT / "citations.json").write_text(json.dumps({**REF, "derived_from": "spicy-regs 8d9e7a2 src/spicy_regs/ontology/citations.py", **citations}, indent=1, ensure_ascii=False, sort_keys=True) + "\n")
print("wrote", sorted(p.name for p in OUT.iterdir()))
print("fr graph nodes:", len(fr_result.document["@graph"]), "| ua nodes:", len(ua_result.document["@graph"]), "| model nodes:", len(model_result.document["@graph"]), "| judgments:", len(judgments), "rejections:", len(rejections))
