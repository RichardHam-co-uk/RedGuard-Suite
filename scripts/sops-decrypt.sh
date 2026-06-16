#!/usr/bin/env bash
# Decrypt a SOPS-encrypted secrets file (age backend).
#
# Usage:   ./scripts/sops-decrypt.sh <ciphertext-in> [plaintext-out]
# Example: ./scripts/sops-decrypt.sh config/secrets.enc.yaml config/secrets.yaml
#
# Requires SOPS_AGE_KEY_FILE to point at your private age key, e.g.
#   export SOPS_AGE_KEY_FILE="$HOME/.config/sops/age/keys.txt"
#
# The decrypted output is plaintext — it is git-ignored and must never be committed.
set -euo pipefail

IN="${1:-}"
OUT="${2:-}"

if [[ -z "$IN" ]]; then
    echo "Usage: $0 <ciphertext-in> [plaintext-out]" >&2
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

if [[ -z "${SOPS_AGE_KEY_FILE:-}" ]]; then
    echo "WARNING: SOPS_AGE_KEY_FILE is not set; sops will search default locations." >&2
fi

if [[ -z "$OUT" ]]; then
    # Strip a .enc segment if present (foo.enc.yaml -> foo.yaml), else print to stdout.
    if [[ "$IN" == *.enc.* ]]; then
        OUT="${IN/.enc./.}"
    else
        sops --decrypt "$IN"
        exit 0
    fi
fi

echo "Decrypting '$IN' -> '$OUT' ..."
sops --decrypt "$IN" > "$OUT"
echo "Done. '$OUT' is PLAINTEXT — do not commit it; delete it when finished."
