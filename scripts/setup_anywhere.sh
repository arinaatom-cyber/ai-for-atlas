#!/usr/bin/env bash
# Atlas Discovery — установка на Linux/macOS
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "=== Atlas Discovery Setup ==="

command -v python3 >/dev/null || { echo "Python 3 required"; exit 1; }

python3 -m pip install --upgrade pip
pip install -r requirements.txt

if [[ ! -f config.yaml ]]; then
  cp config.example.yaml config.yaml
  echo "Created config.yaml"
fi

if [[ ! -f data/projects.csv ]]; then
  echo "WARN: data/projects.csv missing — add your catalog (read-only)"
fi

echo ""
echo "Ready:"
echo "  python run_discovery.py scan"
echo "  streamlit run discovery_app.py"
echo "  open docs/site/discovery.html"
echo ""
echo "Catalog projects.csv is never published on the site — only new PXD/PDC."
