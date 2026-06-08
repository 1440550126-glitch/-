#!/usr/bin/env bash
set -euo pipefail
mkdir -p release
NAME=lingmirror-ai
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/$NAME/storage"
for item in .env.example README.md README_FINAL_DEPLOY.md package.json package-lock.json backend public scripts ops LICENSE; do
  [ -e "$item" ] && rsync -a "$item" "$TMP/$NAME/"
done
cp storage/.gitkeep "$TMP/$NAME/storage/.gitkeep" 2>/dev/null || touch "$TMP/$NAME/storage/.gitkeep"
find "$TMP/$NAME" -type f \( -name '*.js' -o -name '*.html' -o -name '*.md' -o -name '.env.example' \) -print0 | xargs -0 grep -E 'VOLCENGINE_ARK_API_KEY=.+[A-Za-z0-9]{12}|MODEL_GATEWAY_API_KEY=.+[A-Za-z0-9]{12}|GOOGLE_CLIENT_SECRET=.+[A-Za-z0-9]{12}' && { echo 'Possible real secret found'; exit 1; } || true
tar -C "$TMP" -czf release/lingmirror-ai.tar.gz "$NAME"
( cd "$TMP" && zip -qr "$OLDPWD/release/lingmirror-ai.zip" "$NAME" )
echo "Created release/lingmirror-ai.tar.gz and release/lingmirror-ai.zip"
