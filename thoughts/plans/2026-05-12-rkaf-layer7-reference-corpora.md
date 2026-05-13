# Layer 7 — Reference Corpora Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship two Reference Corpora per source spec §11: (1) the existing **SNAP redetermination** vertical slice from `policy-studio/examples/snap-redetermination-from-sources/`, formalized as a Reference Corpus with full v0.2 vocabulary, DCAT metadata, and corpus discipline obligations met; (2) a **Scientific Reproducibility** corpus using DOI-identified papers with ECO/SEPIO scientific-warrant chains — chosen as the one non-policy corpus per the master sequence's instruction to add at least one non-policy domain.

**Architecture:** Each corpus lives at `reference-corpora/<corpus>/v0.2/` with a deterministic structure: `manifest.dcat.jsonld` (DCAT metadata), `tagging-methodology.md` (reproducibility documentation per §11.4(4)), `LICENSE` (redistribution + AI training permission per §11.4(2)), `source-provenance.md` (real-world source tagging documentation per §11.4(3)), and a `data/` subtree containing the JSON-LD assertions + their evidence bindings + warrant chains. Each corpus is exercised by `tools/corpus_validate.py` against the v0.2 conformance suite at the corpus's declared level (L3 for SNAP, L2 for scientific).

**Tech Stack:** JSON-LD 1.1 (rkaf-context-v0.2), DCAT 2 vocabulary, Python 3.12 for tagging tooling, the `rkaf` Python SDK from Plan 6 for validation, ECO ontology IRIs (http://purl.obolibrary.org/obo/ECO_*).

---

## File structure

```
rulespec/
├── reference-corpora/
│   ├── README.md                                    # NEW — index of corpora
│   ├── snap-redetermination/
│   │   └── v0.2/
│   │       ├── manifest.dcat.jsonld                 # NEW — DCAT-compatible metadata
│   │       ├── tagging-methodology.md               # NEW — §11.4(4) reproducibility documentation
│   │       ├── source-provenance.md                 # NEW — §11.4(3) source provenance documentation
│   │       ├── LICENSE                              # NEW — CC-BY-4.0 (permits AI training per §11.4(2))
│   │       ├── README.md                            # NEW
│   │       └── data/
│   │           ├── artifacts/                       # NEW — Artifact records (USLM identifiers for federal CFR; state-specific for state-policy manuals)
│   │           ├── source-fragments/                # NEW — SourceFragment records pointing into Artifacts
│   │           ├── assertions/                      # NEW — Assertion records (eligibility rules, redetermination triggers)
│   │           ├── evidence-bindings/               # NEW — EvidenceBinding records linking Assertions → SourceFragments
│   │           ├── warrants/                        # NEW — Warrant records (legal-family chain: federal CFR → state plan → state manual)
│   │           ├── lifecycle/                       # NEW — LifecycleEvent + Supersession records
│   │           ├── attestations/                    # NEW — at least one Attestation per assertion
│   │           ├── adoptions/                       # NEW — LocalAdoption records
│   │           └── concept-mappings/                # NEW — SKOS-bound mappings to EuroVoc / shared concept registry
│   └── scientific-reproducibility/
│       └── v0.2/
│           ├── manifest.dcat.jsonld                 # NEW
│           ├── tagging-methodology.md               # NEW
│           ├── source-provenance.md                 # NEW
│           ├── LICENSE                              # NEW
│           ├── README.md                            # NEW
│           └── data/
│               ├── artifacts/                       # NEW — DOI-identified papers (≥10 reproducible-research papers)
│               ├── source-fragments/                # NEW — method/result section fragments
│               ├── assertions/                      # NEW — scientific claims drawn from papers
│               ├── evidence-bindings/               # NEW
│               ├── warrants/                        # NEW — Warrant records with warrantKind ∈ {methodological, empirical, replication, peerReview} aligned to ECO
│               ├── confidence-records/              # NEW — exercises §4.5 ConfidenceRecord on every assertion
│               └── concept-mappings/                # NEW — to MeSH / Scopus subject codes (SKOS)
└── tools/
    ├── corpus_validate.py                           # NEW — validates a corpus against suite.index.json at the corpus's declared level
    └── corpus_eco_align.py                          # NEW — verifies scientific corpus warrants reference real ECO IRIs
```

---

## Task 1: Author the SNAP corpus seed by lifting from `policy-studio/examples/snap-redetermination-from-sources/`

**Files:**
- Create: `reference-corpora/snap-redetermination/v0.2/data/{artifacts,source-fragments,assertions,evidence-bindings,warrants,lifecycle,attestations,adoptions,concept-mappings}/*.jsonld`

The Studio SNAP slice has the raw material — sources, mappings, policy objects, provenance, attestations. We lift each into v0.2 vocabulary form.

- [ ] **Step 1: Audit the Studio SNAP slice surface**

```bash
cd /Users/mikewolfd/Work/formspec-stack/policy-studio/examples/snap-redetermination-from-sources
ls
find . -name '*.json' -o -name '*.jsonld' -o -name '*.md' | head -40
```

Expected: enumerated subtree (sources, mappings, policy-objects, provenance, etc.)

- [ ] **Step 2: Write a one-shot conversion script**

```python
# tools/lift_snap_to_corpus.py
"""Convert the Studio SNAP example tree into a v0.2 Reference Corpus.

Reads policy-studio/examples/snap-redetermination-from-sources/, emits JSON-LD
records under reference-corpora/snap-redetermination/v0.2/data/.

Mappings (Studio → v0.2):
  sources/<id>.json                → data/artifacts/<id>.jsonld
                                    + data/source-fragments/<id>__<frag>.jsonld
  policy-objects/<id>.json         → data/assertions/<id>.jsonld + data/evidence-bindings/<id>.jsonld
  source-authority/<id>.json       → data/warrants/<id>.jsonld (legal-family kind from authorityKind)
  provenance/<id>.json             → data/attestations/<id>.jsonld
                                    + data/adoptions/<id>.jsonld (when adoption present)
  mappings/<id>.json               → data/concept-mappings/<id>.jsonld (SKOS-bound)
"""
import json
from pathlib import Path

STUDIO = Path("/Users/mikewolfd/Work/formspec-stack/policy-studio/examples/snap-redetermination-from-sources")
CORPUS = Path("/Users/mikewolfd/Work/formspec-stack/rulespec/reference-corpora/snap-redetermination/v0.2/data")

# implementation: walk STUDIO, emit JSON-LD using rkaf-context-v0.2 IRIs
# every output document has @context: "https://rulespec.org/context/rkaf-context-v0.2.jsonld"
# every document validates against the v0.2 SHACL shapes (via tools/ci_validate.py)
```

- [ ] **Step 3: Run the conversion**

```bash
cd /Users/mikewolfd/Work/formspec-stack/rulespec
mkdir -p reference-corpora/snap-redetermination/v0.2/data/{artifacts,source-fragments,assertions,evidence-bindings,warrants,lifecycle,attestations,adoptions,concept-mappings}
python3 tools/lift_snap_to_corpus.py
```

Expected: ≥30 JSON-LD files emitted across the data/ subdirs.

- [ ] **Step 4: Validate every emitted file against the v0.2 SHACL shapes**

```bash
cd /Users/mikewolfd/Work/formspec-stack/rulespec
for f in reference-corpora/snap-redetermination/v0.2/data/**/*.jsonld; do
  python3 -c "
import rdflib, sys
from pyshacl import validate
data = rdflib.Graph(); data.parse('$f', format='json-ld')
shapes = rdflib.Graph()
for s in ['shapes/rkaf-shapes-core-v0.2.ttl','shapes/rkaf-shapes-warrant-v0.2.ttl','shapes/rkaf-shapes-confidence-v0.2.ttl','shapes/rkaf-shapes-accessscope-v0.2.ttl','shapes/rkaf-shapes-studio-promotions-v0.2.ttl','shapes/rkaf-shapes-conceptregistry-v0.2.ttl','shapes/rkaf-shapes-core-v0.1.ttl','shapes/rkaf-shapes-conceptregistry-v0.1.ttl','shapes/rkaf-shapes-lifecycle-v0.1.ttl','shapes/rkaf-shapes-justification-v0.1.ttl']:
    shapes.parse(s, format='turtle')
conforms, _, _ = validate(data_graph=data, shacl_graph=shapes, inference='rdfs', advanced=True, meta_shacl=False)
sys.exit(0 if conforms else 1)
" || { echo "FAIL: $f"; exit 1; }
done
echo "all SNAP corpus records validate"
```

Expected: every emitted file PASSes; loop exits 0.

- [ ] **Step 5: Commit**

```bash
git add reference-corpora/snap-redetermination/v0.2/data/ tools/lift_snap_to_corpus.py
git commit -m "data(corpus-snap): lift Studio SNAP slice into v0.2 Reference Corpus form (artifacts, fragments, assertions, evidence, warrants, lifecycle, attestations, adoptions, mappings)"
```

## Task 2: Author SNAP corpus DCAT manifest + supporting docs

**Files:**
- Create: `reference-corpora/snap-redetermination/v0.2/manifest.dcat.jsonld`
- Create: `reference-corpora/snap-redetermination/v0.2/tagging-methodology.md`
- Create: `reference-corpora/snap-redetermination/v0.2/source-provenance.md`
- Create: `reference-corpora/snap-redetermination/v0.2/LICENSE`
- Create: `reference-corpora/snap-redetermination/v0.2/README.md`

- [ ] **Step 1: DCAT manifest**

```json
{
  "@context": [
    "https://rulespec.org/context/rkaf-context-v0.2.jsonld",
    {
      "dcat":     "http://www.w3.org/ns/dcat#",
      "dcterms":  "http://purl.org/dc/terms/",
      "foaf":     "http://xmlns.com/foaf/0.1/"
    }
  ],
  "@type": ["dcat:Dataset", "rkaf:ReferenceCorpus"],
  "@id": "https://rulespec.org/corpora/snap-redetermination/v0.2",
  "dcterms:title":       "Rulespec Reference Corpus — SNAP Redetermination v0.2",
  "dcterms:description": "Federal SNAP (Supplemental Nutrition Assistance Program) redetermination policy as a width-one path through every Rulespec layer. Sourced from federal CFR via USLM, state plans, and county operational manuals; tagged with full v0.2 vocabulary (artifacts, source fragments, evidence bindings, warrant chains, lifecycle, supersession, attestations, local adoptions, concept mappings).",
  "dcterms:issued":      "2026-05-12",
  "dcterms:license":     "https://creativecommons.org/licenses/by/4.0/",
  "dcterms:publisher": {
    "@type": "foaf:Organization",
    "foaf:name": "Rulespec maintainers"
  },
  "dcat:keyword": ["snap", "policy", "us-fed", "redetermination", "rkaf", "reference-corpus"],
  "dcat:theme":   ["benefits-policy", "federal-regulation"],
  "dcat:distribution": [
    { "@type": "dcat:Distribution", "dcat:downloadURL": "data/", "dcat:mediaType": "application/ld+json" }
  ],
  "rkaf:declaredConformanceLevel": "L3",
  "rkaf:declaredAdoptionDepth":     "D3",
  "rkaf:rulespecVersion":           "0.2.0-pre.8"
}
```

- [ ] **Step 2: Tagging methodology**

`tagging-methodology.md` documents (per source spec §11.4(4) reproducibility):
- The three-tier source hierarchy used: federal CFR (USLM) → state plan → county operational manual.
- The mapping rule from Studio's `authorityClass` to `rkaf:warrantKind` (legal-family).
- The selector convention chosen: `uslm:section` for federal text, `rkaf:partner-defined` for state-plan and county-manual sections (with the partner-defined selector spec inlined).
- The lifecycle / supersession edge convention: `dcterms:replaces` for state-plan revisions; per-county manual revision tracked via content-hash + state-plan supersession lookup.
- The attestation source: county case-worker review notes (anonymized via redaction; AccessScope = `personalRestricted` on the source document).
- How a third party reproduces the corpus on adjacent state policies (Texas vs. Ohio differ in plan structure but use identical methodology).

- [ ] **Step 3: Source provenance**

`source-provenance.md` documents (per source spec §11.4(3)):
- Every CFR title + section that contributed.
- The state plan(s) consulted (e.g., Texas SNAP State Plan FY2024).
- The county operational manuals (e.g., Travis County SNAP Operations Manual, version 7.2).
- The case-worker review notes used for attestations (with redaction discipline).
- The author of each tagging decision (CODEOWNERS-style attribution, not individual case workers).

- [ ] **Step 4: License (CC-BY-4.0)**

Standard CC-BY-4.0 text. Copy from <https://creativecommons.org/licenses/by/4.0/legalcode.txt>.

The license MUST permit AI training per source spec §11.4(2). CC-BY-4.0 satisfies this.

- [ ] **Step 5: README**

Top-level corpus README pointing at the manifest, tagging methodology, source provenance, and `data/` subtree.

- [ ] **Step 6: Commit**

```bash
git add reference-corpora/snap-redetermination/v0.2/{manifest.dcat.jsonld,tagging-methodology.md,source-provenance.md,LICENSE,README.md}
git commit -m "data(corpus-snap): DCAT manifest + tagging methodology + source provenance + license"
```

## Task 3: Author the Scientific Reproducibility corpus

**Files:**
- Create: `reference-corpora/scientific-reproducibility/v0.2/data/{artifacts,source-fragments,assertions,evidence-bindings,warrants,confidence-records,concept-mappings}/*.jsonld`
- Create: `reference-corpora/scientific-reproducibility/v0.2/{manifest.dcat.jsonld,tagging-methodology.md,source-provenance.md,LICENSE,README.md}`

The corpus consists of 10-20 reproducible-research papers with DOI identifiers, method-section / results-section source fragments, and warrant chains using ECO/SEPIO terms aligned with Plan 2's scientific-family warrantKinds.

- [ ] **Step 1: Pick the source papers**

Candidates (open-access, reproducible-research-flagged):
- Wilkinson et al. 2016, "The FAIR Guiding Principles for scientific data management" — DOI 10.1038/sdata.2016.18 — methodological warrants over data-management practices.
- Munafò et al. 2017, "A manifesto for reproducible science" — DOI 10.1038/s41562-016-0021 — peerReview + replication warrants.
- Ioannidis 2005, "Why Most Published Research Findings Are False" — DOI 10.1371/journal.pmed.0020124 — empirical + methodological warrants over claim reproducibility.
- 7 more papers spanning psychology, economics, biomedical, ML reproducibility (e.g., Open Science Collaboration 2015, Camerer et al. 2018, Pineau et al. 2021).

- [ ] **Step 2: Author the Artifact records**

For each paper, one Artifact record. Example:

```json
{
  "@context": "https://rulespec.org/context/rkaf-context-v0.2.jsonld",
  "@id": "urn:rkaf:corpus:scientific-reproducibility:artifact:wilkinson-2016",
  "@type": "rkaf:Artifact",
  "rkaf:hasArtifactIdentifier": "doi:10.1038/sdata.2016.18",
  "rkaf:artifactIdentifierScheme": "rkaf:doi",
  "dcterms:title":     "The FAIR Guiding Principles for scientific data management and stewardship",
  "dcterms:creator":   ["Wilkinson, M.D.", "Dumontier, M.", "Aalbersberg, IjJ.", "..."],
  "dcterms:issued":    "2016-03-15"
}
```

- [ ] **Step 3: Author SourceFragment records**

For each paper, ≥3 SourceFragment records pointing at: methods section, results section, key claim quote.

```json
{
  "@context": "https://rulespec.org/context/rkaf-context-v0.2.jsonld",
  "@id": "urn:rkaf:corpus:scientific-reproducibility:fragment:wilkinson-2016:methods",
  "@type": "rkaf:SourceFragment",
  "rkaf:bindsArtifact": "urn:rkaf:corpus:scientific-reproducibility:artifact:wilkinson-2016",
  "rkaf:hasSelector": [
    {
      "@type": "oa:TextQuoteSelector",
      "oa:exact": "The FAIR Guiding Principles…"
    }
  ],
  "rkaf:selectorKind": "oa:TextQuoteSelector"
}
```

- [ ] **Step 4: Author Warrant records aligned with ECO/SEPIO**

```json
{
  "@context": "https://rulespec.org/context/rkaf-context-v0.2.jsonld",
  "@id": "urn:rkaf:corpus:scientific-reproducibility:warrant:wilkinson-2016:methodological",
  "@type": "rkaf:Warrant",
  "rkaf:warrantKind":   "rkaf:methodological",
  "rkaf:warrantFamily": "rkaf:scientific",
  "rkaf:alignsWith":    "http://purl.obolibrary.org/obo/ECO_0000218"  // "manual assertion"
}
```

`alignsWith` is a v0.2 Layer 1 amendment carried in Plan 2 if not already; if missing, add it as part of this plan with vocab audit + fixture coverage.

- [ ] **Step 5: Author EvidenceBinding records linking Assertions → SourceFragments + Warrants**

- [ ] **Step 6: Author ConfidenceRecord records exercising §4.5**

For each scientific assertion, attach a ConfidenceRecord with `confidenceMethod: rkaf:human-estimation`, `calibrationStatus: rkaf:humanEstimated`, basis pointing at the SourceFragment, generatedBy the corpus tagger.

- [ ] **Step 7: Author ConceptMapping records to MeSH / Scopus subject codes**

`conceptmapping-fair-data-management.jsonld` mapping `urn:rkaf:concept:fair-data-management` to MeSH `D000094228` via `skos:closeMatch`.

- [ ] **Step 8: Author the corpus's manifest, tagging methodology, source provenance, license, README**

Same structure as Task 2, with `dcat:keyword: ["scientific-reproducibility", "doi", "eco", "sepio", ...]` and `rkaf:declaredConformanceLevel: "L2"` (this corpus does not exercise lifecycle cascade closure or registry federation, so L2 is the appropriate floor).

- [ ] **Step 9: Validate every emitted file against the v0.2 SHACL shapes**

(Same loop as Task 1 step 4, applied to the scientific-reproducibility corpus subtree.)

- [ ] **Step 10: Commit**

```bash
git add reference-corpora/scientific-reproducibility/
git commit -m "data(corpus-sci): scientific reproducibility corpus (10 DOI papers, ECO-aligned warrants, ConfidenceRecord per assertion, MeSH concept mappings)"
```

## Task 4: Author corpus validation tooling

**Files:**
- Create: `tools/corpus_validate.py`
- Create: `tools/corpus_eco_align.py`

- [ ] **Step 1: `corpus_validate.py`**

```python
#!/usr/bin/env python3
"""Validate a Reference Corpus against the conformance suite at its declared level.

Usage: corpus_validate.py <corpus-root>
Reads <corpus-root>/manifest.dcat.jsonld for declared conformance level + Rulespec
version, then runs rkaf-conformance with the appropriate level against the corpus's
data/ subtree.

Exit codes:
  0  corpus passes at declared level
  1  conformance failure
  2  setup error
"""
import json, subprocess, sys
from pathlib import Path

def main(argv):
    root = Path(argv[1]).resolve()
    manifest = json.loads((root / "manifest.dcat.jsonld").read_text())
    level   = manifest.get("rkaf:declaredConformanceLevel", "L1")
    version = manifest.get("rkaf:rulespecVersion", "unknown")
    print(f"Validating corpus {root.name} at {level} (rkaf {version})")
    res = subprocess.run([
        "./crates/target/release/rkaf-conformance",
        "--level", level,
        "--suite", "conformance/v0.2/suite.index.json",
        "--report", str(root / f"{level}-report.json"),
        # implicit: the runner walks data/ for any fixtures of the corpus
    ])
    return res.returncode

if __name__ == "__main__":
    sys.exit(main(sys.argv))
```

- [ ] **Step 2: `corpus_eco_align.py`**

```python
#!/usr/bin/env python3
"""ECO/SEPIO alignment audit for the scientific-reproducibility corpus.

Walks reference-corpora/scientific-reproducibility/v0.2/data/warrants/*.jsonld
and asserts that every Warrant with warrantFamily=rkaf:scientific carries an
rkaf:alignsWith property pointing at a real ECO IRI.

ECO IRIs follow the pattern http://purl.obolibrary.org/obo/ECO_NNNNNNN where
NNNNNNN is a 7-digit number assigned by the Evidence and Conclusion Ontology.
We do not perform live HTTP resolution (offline-friendly); we lint format only.

Exit codes:
  0  every scientific warrant has a well-formed ECO IRI
  1  one or more warrants missing or malformed
"""
import json, re, sys
from pathlib import Path

ECO_RE = re.compile(r"^http://purl\.obolibrary\.org/obo/ECO_\d{7}$")
ROOT = Path("reference-corpora/scientific-reproducibility/v0.2/data/warrants")

def main():
    fails = []
    for f in ROOT.glob("*.jsonld"):
        d = json.loads(f.read_text())
        if d.get("rkaf:warrantFamily") != "rkaf:scientific":
            continue
        iri = d.get("rkaf:alignsWith")
        if not iri or not ECO_RE.match(iri):
            fails.append((f.name, iri))
    if fails:
        for name, iri in fails:
            print(f"  [FAIL] {name}: rkaf:alignsWith = {iri!r}")
        return 1
    print(f"OK — {len(list(ROOT.glob('*.jsonld')))} warrants checked")
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 3: Run both tools**

```bash
cd /Users/mikewolfd/Work/formspec-stack/rulespec
python3 tools/corpus_validate.py reference-corpora/snap-redetermination/v0.2
python3 tools/corpus_validate.py reference-corpora/scientific-reproducibility/v0.2
python3 tools/corpus_eco_align.py
```

Expected: All three exit 0.

- [ ] **Step 4: Wire into CI**

Add to the existing CI workflow:

```yaml
- name: Validate SNAP corpus at L3
  run: python3 tools/corpus_validate.py reference-corpora/snap-redetermination/v0.2
- name: Validate scientific corpus at L2
  run: python3 tools/corpus_validate.py reference-corpora/scientific-reproducibility/v0.2
- name: ECO alignment audit
  run: python3 tools/corpus_eco_align.py
```

- [ ] **Step 5: Commit**

```bash
git add tools/corpus_validate.py tools/corpus_eco_align.py .github/workflows/constraints-parity.yml
git commit -m "build(corpus): corpus validators + ECO alignment audit + CI gating"
```

## Task 5: Author `reference-corpora/README.md`

**Files:**
- Create: `reference-corpora/README.md`

- [ ] **Step 1: Index README**

```markdown
# Rulespec Reference Corpora

Public Rulespec-typed datasets shipped with the framework. Each corpus is a worked example, an adoption substrate (new partners build against real data), AI training/evaluation data, and a conformance-suite extension.

| Corpus | Domain | DOI / URL prefix | Declared level | Declared depth |
|---|---|---|---|---|
| [snap-redetermination](snap-redetermination/) | US federal benefits policy | USLM (CFR) + state plans + county manuals | L3 | D3 |
| [scientific-reproducibility](scientific-reproducibility/) | Scientific reproducibility | DOI + ECO/SEPIO warrants | L2 | D1 |

Each corpus subtree contains a `v0.2/` directory with:
- `manifest.dcat.jsonld` — DCAT 2 metadata.
- `tagging-methodology.md` — reproducibility documentation.
- `source-provenance.md` — what real-world artifacts were tagged, by whom, with what authority.
- `LICENSE` — CC-BY-4.0 (permits AI training).
- `data/` — JSON-LD records (artifacts, source fragments, assertions, evidence bindings, warrants, etc.).

Per source spec §11.4: every corpus validates cleanly against the v0.2 conformance suite at its declared level; uses existing public-ontology identifier schemes (ELI / USLM / DOI / ECO) for source identity; ships with DCAT-compatible metadata for catalog discovery.

To validate a corpus locally:
```bash
python3 tools/corpus_validate.py reference-corpora/<corpus>/v0.2
```
```

- [ ] **Step 2: Commit**

```bash
git add reference-corpora/README.md
git commit -m "docs(corpus): index README listing SNAP + scientific reproducibility corpora"
```

## Task 6: CHANGELOG entry

- [ ] **Step 1: Append v0.2.0-pre.8 entry**

```markdown
## v0.2.0-pre.8 — Layer 7 Reference Corpora

### Added
- `reference-corpora/snap-redetermination/v0.2/` — formalized from `policy-studio/examples/snap-redetermination-from-sources/` as the first Reference Corpus. L3 + D3 declared. CC-BY-4.0.
- `reference-corpora/scientific-reproducibility/v0.2/` — 10 DOI-identified reproducible-research papers with ECO-aligned scientific-family warrants and ConfidenceRecord per assertion. L2 + D1 declared. CC-BY-4.0.
- `reference-corpora/README.md` — index.
- `tools/lift_snap_to_corpus.py` — one-shot conversion of Studio SNAP slice into v0.2 vocabulary.
- `tools/corpus_validate.py` — runs `rkaf-conformance` against any corpus at its declared level.
- `tools/corpus_eco_align.py` — ECO IRI lint for the scientific corpus.
- CI runs both corpus validators + ECO alignment audit on every push.

### Compliance
Both corpora satisfy source spec §11.4: clean conformance at declared level, redistribution + AI-training license, source-provenance documentation, reproducible tagging methodology, public-ontology identifiers (USLM/DOI), DCAT metadata.
```

- [ ] **Step 2: Commit**

```bash
git add CHANGELOG.md
git commit -m "docs(rkaf): CHANGELOG v0.2.0-pre.8 — Layer 7 Reference Corpora"
```

## Self-review

- [ ] SNAP corpus exists under `reference-corpora/snap-redetermination/v0.2/` with all required files (manifest, tagging-methodology, source-provenance, LICENSE, README, data/).
- [ ] Scientific corpus exists under `reference-corpora/scientific-reproducibility/v0.2/` (one non-policy corpus added, satisfying the master-sequence instruction).
- [ ] Both corpora validate cleanly against the v0.2 conformance suite at their declared levels (`tools/corpus_validate.py` exits 0).
- [ ] Scientific corpus warrants reference real ECO IRIs (`tools/corpus_eco_align.py` exits 0).
- [ ] Both corpora ship with DCAT-compatible metadata per source spec §11.4(6).
- [ ] Both licensed CC-BY-4.0 — permits redistribution + AI training per §11.4(2).
- [ ] Source-provenance documentation present for both per §11.4(3).
- [ ] Tagging methodology documented for both per §11.4(4) so others can reproduce on adjacent source materials.
- [ ] Public-ontology identifiers used: USLM for federal regs in SNAP corpus, DOI + ECO for scientific corpus per §11.4(5).
- [ ] CI runs corpus validators on every push.
- [ ] CHANGELOG entry for v0.2.0-pre.8 lands.
