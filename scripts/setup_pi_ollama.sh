#!/usr/bin/env bash
set -euo pipefail

# Install and prepare local Ollama on Raspberry Pi 5.
# Usage:
#   chmod +x scripts/setup_pi_ollama.sh
#   ./scripts/setup_pi_ollama.sh
# Optional:
#   OLLAMA_MODEL=qwen2.5:0.5b ./scripts/setup_pi_ollama.sh

OLLAMA_MODEL="${OLLAMA_MODEL:-qwen2.5:0.5b}"

echo "[AOJ] Installing Ollama runtime..."
curl -fsSL https://ollama.com/install.sh | sh

echo "[AOJ] Enabling Ollama service..."
sudo systemctl enable --now ollama

echo "[AOJ] Waiting for Ollama API..."
for _ in $(seq 1 40); do
  if curl -fsS http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

echo "[AOJ] Pulling model: ${OLLAMA_MODEL}"
ollama pull "${OLLAMA_MODEL}"

echo "[AOJ] Installed models:"
ollama list

echo "[AOJ] Ollama setup complete."
