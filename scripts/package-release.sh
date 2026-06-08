#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${OUT_DIR:-$ROOT_DIR/release}"
NAME="${NAME:-lingmirror-ai}"
mkdir -p "$OUT_DIR"
cd "$ROOT_DIR"
rm -f "$OUT_DIR/$NAME.tar.gz" "$OUT_DIR/$NAME.zip"
tar -czf "$OUT_DIR/$NAME.tar.gz" \
  --transform="s#^#$NAME/#" \
  package.json package-lock.json .env.example .gitignore README.md README_FINAL_DEPLOY.md LICENSE backend public storage scripts ops
if command -v zip >/dev/null 2>&1; then
  TMP="$(mktemp -d)"
  mkdir -p "$TMP/$NAME"
  cp -a package.json package-lock.json .env.example .gitignore README.md README_FINAL_DEPLOY.md LICENSE backend public storage scripts ops "$TMP/$NAME/"
  (cd "$TMP" && zip -qr "$OUT_DIR/$NAME.zip" "$NAME")
  rm -rf "$TMP"
fi
ls -lh "$OUT_DIR/$NAME.tar.gz" "$OUT_DIR/$NAME.zip" 2>/dev/null || ls -lh "$OUT_DIR/$NAME.tar.gz"
