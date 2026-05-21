#!/usr/bin/env bash
set -euo pipefail

echo "Setting up Numeris..."
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
(cd frontend && npm install)
mkdir -p data_cache/chroma data_cache/parquet data_cache/analyses models
echo "Setup complete. Configure .env and Vercel environment variables before production deploy."
