#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$ROOT/apps/python-gateway"
uv sync --extra dev --no-install-project
PYTHONPATH=src .venv/bin/pytest tests/ -q

cd "$ROOT/plugins/ts-openclaw-channel"
npm install --silent
npm run check
rm -rf node_modules

echo "smoke ok"
