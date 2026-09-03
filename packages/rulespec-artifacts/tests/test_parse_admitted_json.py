"""``parse_admitted_json`` keeps every parse-time refusal, drops only the re-encode.

The canonical parser proves two things at once: that the bytes decode to a
well-formed, unambiguous JSON value, and that they were written in canonical
form. Only the first is still unknown while reading a member of an artifact
admission has already streamed, hashed and matched against its declared digest.
These tests pin that the first is unchanged -- same values, same refusal codes --
and that the second is the only difference.
"""

from __future__ import annotations

import json
import unittest

from rulespec_artifacts import (
    ArtifactVerificationError,
    canonical_json_bytes,
    parse_admitted_json,
    parse_canonical_json,
)

CANONICAL_VALUES = [
    {},
    [],
    {"a": 1, "b": [1, 2, 3]},
    {"nested": {"deep": [{"x": None}, True, False]}},
    {"escapes": "control \x00\x1f, non-bmp \U0001f600, combining \u00e9, rtl \u05d0\u05d1"},
    # The encoder bounds integers to the JSON safe range, not int64.
    {"big": 2**53 - 1, "negative": -(2**53 - 1)},
    "bare string",
    0,
    True,
    None,
]

REFUSED = [
    (b"\xef\xbb\xbf{}", "byte order mark"),
    (b"\xff\xfe not utf-8", "invalid utf-8"),
    (b'{"a":1,"a":2}', "duplicate keys"),
    (b'{"a":1.5}', "float"),
    (b'{"a":NaN}', "nan constant"),
    (b'{"a":Infinity}', "infinity constant"),
    (b"{", "truncated"),
    (b"", "empty"),
    (b"{'a':1}", "single quotes"),
]

NONCANONICAL = [
    (b'{"a": 1}', "inserted whitespace"),
    (b'{"b":1,"a":2}', "unsorted keys"),
    (b'{"a":"\\u00e9"}', "escaped non-ascii"),
]


class ParseAdmittedJsonTest(unittest.TestCase):
    def test_parses_the_same_value_as_the_canonical_parser(self) -> None:
        for value in CANONICAL_VALUES:
            with self.subTest(value=value):
                raw = canonical_json_bytes(value)
                self.assertEqual(parse_admitted_json(raw), value)
                self.assertEqual(parse_admitted_json(raw), parse_canonical_json(raw))

    def test_refuses_exactly_what_the_canonical_parser_refuses(self) -> None:
        for raw, label in REFUSED:
            with self.subTest(case=label):
                with self.assertRaises(ArtifactVerificationError) as canonical:
                    parse_canonical_json(raw)
                with self.assertRaises(ArtifactVerificationError) as admitted:
                    parse_admitted_json(raw)
                self.assertEqual(
                    admitted.exception.issue.code, canonical.exception.issue.code
                )
                self.assertEqual(
                    admitted.exception.issue.path, canonical.exception.issue.path
                )

    def test_accepts_noncanonical_bytes_the_canonical_parser_rejects(self) -> None:
        """The one intended difference: canonical form is the build gate's job.

        These bytes are well formed and unambiguous, they are simply not the
        canonical spelling. A member carrying them is refused at admission by
        its digest, not by re-deriving the spelling of every row.
        """

        for raw, label in NONCANONICAL:
            with self.subTest(case=label):
                with self.assertRaises(ArtifactVerificationError):
                    parse_canonical_json(raw)
                self.assertEqual(
                    parse_admitted_json(raw), json.loads(raw.decode("utf-8"))
                )

    def test_the_path_and_code_a_caller_supplies_are_used(self) -> None:
        with self.assertRaises(ArtifactVerificationError) as error:
            parse_admitted_json(b"{", path="payload/rows", code="invalid.schema")
        self.assertEqual(error.exception.issue.path, "payload/rows")
        self.assertEqual(error.exception.issue.code, "invalid.schema")


if __name__ == "__main__":
    unittest.main()
