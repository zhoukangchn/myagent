#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$ROOT/apps/python-gateway"
uv run --extra dev pytest -q

cd "$ROOT/plugins/ts-openclaw-channel"
npm install --silent
npm run check
rm -rf node_modules

echo "smoke ok"
