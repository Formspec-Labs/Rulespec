# RS-P3: Register a `rkaf:formspec-need` artifact-identifier scheme

- **Date:** 2026-07-27
- **Status:** Proposed — awaiting Rulespec maintainer decision
- **Origin:** Formspec Needs Specification, Appendix C proposal RS-P3
  (`formspec-stack/formspec/specs/needs/needs-spec.md`)
- **Consumers:** Rulespec, Formspec
- **Touches:** `spec/rkaf-core.md` §4.1 (`rkaf:artifactIdentifierScheme`), §3
  (closed-taxonomy discipline), §11 (compatibility)

## What Formspec is asking for

Add `rkaf:formspec-need` to the closed `rkaf:artifactIdentifierScheme` enum,
denoting a Formspec Needs Document `url` + `need.id` pair:

```
<docUrl>#<needId>              e.g. https://benefits.example.gov/apps/assistance/needs#proof-of-filing
<docUrl>#<needId>@<revision>   e.g. …/needs#proof-of-filing@2
```

The `@<revision>` suffix is optional. A Formspec Need carries an integer
`revision` covering its statement and grounding; an assertion that needs to
pin the wording it saw uses the suffixed form, one that tracks the Need as
currently worded omits it. This mirrors the pinning discipline the needs spec
already draws between authored citations (unpinned) and generated anchors
(pinned).

Per the closed-taxonomy discipline (§3), adding an enum value requires a
release with a declared URI.

## Acceptance criteria

*(Verbatim from the needs spec's Appendix C.)*

1. **Enum value declared** in `rkaf:artifactIdentifierScheme`.
2. **One positive fixture** of an assertion citing a product Need as evidence
   subject.
3. **One negative fixture**: a mutable URL carried without the scheme tag is
   rejected.

The negative is the important one. §4.1 already requires that "an Artifact
identifier MUST resolve to, or be derived from, one immutable edition,
publication, snapshot, or content payload" — a bare Needs Document URL is a
current-state URL, exactly the class §4.1 rejects for eCFR. The scheme tag is
what makes the `#<needId>@<revision>` form legible as an edition rather than a
live page.

## What this buys, and who it buys it for

Formspec gains nothing structural. It gains the **reverse edge**.

Today the citation runs one way: a Need cites a Rulespec assertion as evidence
that the need is legitimate. With this scheme registered, an assertion can cite
a product Need first-class — a compliance finding, an adopted policy position,
a regulator's determination can name the product commitment it is about. "The
policy corpus knows what the product committed to" becomes expressible, and
Formspec does nothing to make it so.

Without the scheme, the same citation is possible via `rkaf:partner-defined`,
but a Need citation becomes indistinguishable from an arbitrary partner URI in
federation queries. That is the whole cost of not doing this.

## Cost to Rulespec's charter

**Low but real.** One closed-enum extension, release-gated, naming a partner
format in the universal vocabulary. Precedent exists: `rkaf:eli`, `rkaf:uslm`,
`rkaf:aknt-eId`, `rkaf:doi`, `rkaf:isbn`, `rkaf:issn` all name external
schemes. The charter's first boundary ("universal ontology, not
consumer-coupled") is about *shapes*, and this adds no shape — it adds one
value to a list whose entire purpose is naming external identifier grammars.

## Why Formspec cannot do this from its side

The enum is closed and Rulespec owns it. This is the only proposal in the set
where the asymmetry is total: the assertion→need direction is unreachable
without a Rulespec change, and Formspec's own citation direction already works.

## Open questions for the maintainer

- **Fragment grammar.** `#<needId>@<revision>` puts a version marker inside a
  URI fragment. Rulespec's existing schemes carry versioning in the path
  (`rkaf:eli`) or in a hash (`rkaf:cid`). If a fragment-embedded revision reads
  wrong here, the alternative is a separate `rkaf:hasArtifactVersion`-style
  property — but that is a bigger change than one enum value, and the needs
  spec would rather have the small one.
- **Release shape.** TODO.md's "US regulatory vocabulary and rulemaking
  follow-through" section already carries an open decision on how to cut the
  next release. This enum value should join that decision rather than force its
  own tag.
