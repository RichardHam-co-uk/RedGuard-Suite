#!/usr/bin/env bash
# Encrypt a plaintext secrets file with SOPS (age backend).
#
# Usage:   ./scripts/sops-encrypt.sh <plaintext-in> [ciphertext-out]
# Example: ./scripts/sops-encrypt.sh config/secrets.yaml config/secrets.enc.yaml
#
# Recipients are taken from .sops.yaml (see config/encrypted-config.md).
# Never commit the plaintext input — only the encrypted output is safe to commit.
set -euo pipefail

IN="${1:-}"
OUT="${2:-}"

if [[ -z "$IN" ]]; then
    echo "Usage: $0 <plaintext-in> [ciphertext-out]" >&2
    exit 64
fi

if ! command -v sops >/dev/null 2>&1; then
    echo "ERROR: 'sops' not found. See config/encrypted-config.md for install steps." >&2
    exit 1
fi

if [[ ! -f "$IN" ]]; then
    echo "ERROR: input file '$IN' does not exist." >&2
    exit 1
fi

if [[ ! -f ".sops.yaml" ]]; then
    echo "ERROR: .sops.yaml not found. Copy .sops.yaml.example and add your age keys." >&2
    exit 1
fi

# Default output: insert .enc before the final extension (foo.yaml -> foo.enc.yaml)
if [[ -z "$OUT" ]]; then
    ext="${IN##*.}"
    base="${IN%.*}"
    OUT="${base}.enc.${ext}"
fi

echo "Encrypting '$IN' -> '$OUT' ..."
sops --encrypt "$IN" > "$OUT"
echo "Done. Commit '$OUT'; then delete the plaintext '$IN'."
