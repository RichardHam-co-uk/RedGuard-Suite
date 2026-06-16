#!/usr/bin/env bash
# Read a HashiCorp Vault KV v2 path and emit `export KEY=value` lines for each
# secret stored there, so RedGuard modules can read them from the environment.
#
# Usage:    ./scripts/vault-load.sh <kv-path> [mount]
# Example:  ./scripts/vault-load.sh redguard/engagement-acme        # mount=secret
#           source <(./scripts/vault-load.sh redguard/engagement-acme)
#
# Requires:
#   - vault CLI on PATH
#   - jq on PATH
#   - VAULT_ADDR set, and a valid token (VAULT_TOKEN or `vault login`)
#
# Values are emitted with single-quote escaping; review the output before
# sourcing it. Nothing is written to disk.
set -euo pipefail

KV_PATH="${1:-}"
MOUNT="${2:-secret}"

if [[ -z "$KV_PATH" ]]; then
    echo "Usage: $0 <kv-path> [mount]" >&2
    exit 64
fi

for tool in vault jq; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo "ERROR: '$tool' not found. See config/encrypted-config.md." >&2
        exit 1
    fi
done

if [[ -z "${VAULT_ADDR:-}" ]]; then
    echo "ERROR: VAULT_ADDR is not set (e.g. https://vault.example.com:8200)." >&2
    exit 1
fi

# KV v2 stores data under .data.data. Fetch as JSON and turn each key/value into
# a shell-safe `export KEY='value'` line, escaping any single quote in the value
# as the standard '\'' sequence so `source <(...)` is safe.
read -r -d '' JQ_PROG <<'JQ' || true
.data.data
| to_entries[]
| "export \(.key)='" + (.value | tostring | gsub("'"; "'\\''")) + "'"
JQ

vault kv get -format=json -mount="$MOUNT" "$KV_PATH" | jq -r "$JQ_PROG"
