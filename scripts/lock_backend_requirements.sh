#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../backend"
python -m pip install -r requirements-dev.txt
python -m piptools compile --strip-extras --generate-hashes -o requirements.lock.txt requirements.in
