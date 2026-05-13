#!/usr/bin/env bash
# Install pinned CUE binary into ./.tools/cue. Re-runnable.
set -euo pipefail
VERSION="0.10.0"
ARCH="$(uname -m)"
OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
case "$OS" in
  darwin) PLAT="darwin" ;;
  linux)  PLAT="linux"  ;;
  *) echo "Unsupported OS: $OS" >&2; exit 1 ;;
esac
case "$ARCH" in
  arm64|aarch64) ARCH_TAG="arm64" ;;
  x86_64|amd64)  ARCH_TAG="amd64" ;;
  *) echo "Unsupported arch: $ARCH" >&2; exit 1 ;;
esac
mkdir -p .tools
URL="https://github.com/cue-lang/cue/releases/download/v${VERSION}/cue_v${VERSION}_${PLAT}_${ARCH_TAG}.tar.gz"
curl -sSfL "$URL" -o .tools/cue.tgz
tar -C .tools -xzf .tools/cue.tgz cue
chmod +x .tools/cue
.tools/cue version
