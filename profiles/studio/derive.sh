#!/usr/bin/env bash
# Regenerate the Studio schemas-derived/ surface from Rulespec-owned sources.
#
# Run from anywhere:
#   profiles/studio/derive.sh

set -euo pipefail

PROFILE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="$PROFILE_DIR/schema-source"
DERIVED_DIR="$PROFILE_DIR/schemas-derived"

if [[ ! -d "$SOURCE_DIR" ]]; then
  echo "missing schema source directory: $SOURCE_DIR" >&2
  exit 1
fi

rm -rf "$DERIVED_DIR"
mkdir -p "$DERIVED_DIR/api"

cp "$SOURCE_DIR"/*.schema.json "$DERIVED_DIR"/
if compgen -G "$SOURCE_DIR/api/*.schema.json" > /dev/null; then
  cp "$SOURCE_DIR"/api/*.schema.json "$DERIVED_DIR/api"/
fi

(
  cd "$DERIVED_DIR"
  find . -type f -name '*.schema.json' -print | sort | xargs shasum -a 256
) > "$DERIVED_DIR/SHA256SUMS"

echo "derived $(find "$DERIVED_DIR" -type f -name '*.schema.json' | wc -l | tr -d ' ') Studio schemas"
