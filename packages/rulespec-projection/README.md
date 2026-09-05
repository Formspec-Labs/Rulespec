# rulespec-projection

The deterministic layer of the Rulespec (RKAF) document projection: the code
that turns one source document plus the relationship rows already published
about it into a gate-valid RKAF JSON-LD document, with every identity minted
from a published row or a re-sliced, re-hashed region of stored text.

Moved from spicy-regs `docpipeline/rkaf_projection.py` at `8d9e7a2` (spicy-regs
`docs/disposition.md` item 4). It depends on nothing outside the standard
library.

## What it does

- `verify_fragment` re-slices a stored field at `[start, end)`, hashes the
  region, and mints the carrier-local fragment URN; a coordinate that does not
  slice what it claims aborts.
- `ground_literal` finds a citation's own words in the projected field and
  binds evidence only when they occur exactly once.
- `federal_register_facts` and `unified_agenda_facts` read the document row and
  the published tables (proceedings, rule targets, authority edges, dockets) and
  return every relationship, activity, and canonical IRI they state.
- `verify_candidate_rows` re-verifies a model layer's candidate concept
  assignments against the stored text and a supplied vocabulary, turning
  survivors into judgments and everything else into rejection rows with reasons.
- `assemble` builds the JSON-LD graph, the run record, and the offset
  transcript. Same inputs, same bytes.
- `citations` carries the CFR, U.S.C., Public Law, RIN, Federal Register, and
  regulations.gov parsers and canonical IRI minters.

## The two seams

The producer read Parquet in two places. Both are Protocols here, and the
producer's own types satisfy them unchanged:

- `SourceArtifact`: the six attributes the projection reads (`artifact_id`,
  `content_sha256`, `subject_id`, `profile_id`, `raw_fields`, `field_sha256`).
- `PublishedTables`: one query, `rows(table, **equals)`. `InMemoryTables`
  implements it over rows the caller holds, with the projection's own
  whitespace-and-sentinel cleaning on both sides of every comparison.

`load_artifact`, which located a row in a Parquet corpus and built the artifact,
stays with the orchestration; it is the caller's adapter.

## Tests

`make test-package-projection` runs the suite in tree, builds the wheel,
installs it alone, proves the installed closure is exactly this package with no
third-party module loaded, and reruns the suite against the installed copy.

`tests/test_parity.py` reads `tests/fixtures/*.json`, produced by running the
original code at `8d9e7a2` through `tests/fixtures/derive.py` (recipe in its
docstring). The port computes no expectation of its own. `tests/test_boundary.py`
freezes the outbound import list at empty. `tests/test_contract.py` carries the
producer's contract properties: aborts, refusals, the URN grammar,
reproducibility.

The repository's audit suite adds two checks this package cannot run alone:
every `rkaf:` term the package emits exists in the generated term registry, and
the fixture documents pass the repository's own conformance gate.

## Known costs, inherited from `8d9e7a2` and deliberately not changed in the move

Recorded here so the next reader neither rediscovers them nor mistakes them for
damage done by the port. The move reproduced the producer byte for byte; these
are its shapes, and the fix for each is a per-snapshot index built by the caller
or a later change measured against the parity fixtures.

- `federal_register_facts` finds a document's proceeding by scanning every
  proceedings row and parsing its `fr_document_numbers_json` on each call:
  O(N × P × J) over N documents, P proceedings, J numbers per row. Fix shape:
  one document-number to proceeding index per snapshot, preserving row order
  and first match.
- `_document_docket_iris` tests membership against a growing list and queries
  the whole dockets table per stated docket, and the authority rows are queried
  twice per RIN (edge, then activity): O(D² + D × T). Fix shape: membership
  sets and a docket-id index, preserving first-match order.
- `parse_authority_citation` in `citations` copies the surrounding text for
  every citation it grades and deduplicates with list membership, and the CFR
  deduplication and chapter parsing do likewise: O(C × L + C²) over C citations
  in a value of length L. Fix shape: pass the next boundary instead of
  reslicing, and deduplicate with an order-preserving set.
