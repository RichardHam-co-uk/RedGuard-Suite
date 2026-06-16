# Encrypted Config Management (SOPS & HashiCorp Vault)

RedGuard configs frequently need to reference sensitive material — API tokens for
C2 frameworks, BloodHound/Neo4j credentials, cloud keys, or target-scoped
secrets defined in the engagement's Rules of Engagement. **None of these may ever
be committed in plaintext** (see `CLAUDE.md` → *Safety Rules*).

This guide describes the two supported approaches for keeping secrets out of the
repository while still feeding them to RedGuard modules at runtime:

| Approach | Best for | Secrets live in |
| --- | --- | --- |
| [SOPS](#1-sops-mozilla-sops) | Small teams, GitOps, encrypted files in a repo | Encrypted file (committed) |
| [HashiCorp Vault](#2-hashicorp-vault) | Shared infra, dynamic/rotating secrets, audit | Central Vault server |

Both integrate through the same contract: a decrypted secret is materialised into
a process **environment variable** (or an ephemeral file under `secrets/`, which
is git-ignored) and read by a module via `os.environ`. RedGuard code never reads
ciphertext directly.

> ⚠️ Every example below uses safe placeholders (`example.com`, `AGE-...EXAMPLE`,
> `s.EXAMPLETOKEN`). Replace them with real values **only** in your local,
> untracked environment — never in a commit.

---

## 1. SOPS (Mozilla sops)

[SOPS](https://github.com/getsops/sops) encrypts the *values* of a YAML/JSON file
while leaving the *keys* readable, so an encrypted config is still diff-friendly
and reviewable. It supports `age`, GPG, AWS KMS, GCP KMS, Azure Key Vault, and
HashiCorp Vault as key backends. We standardise on **age** because it needs no
cloud dependency and is trivial to rotate.

### 1.1 Install

```bash
# macOS
brew install sops age

# Debian/Ubuntu
sudo apt-get install -y age
# sops: download the binary from the GitHub releases page (getsops/sops)
```

### 1.2 Generate an age key (one-time, per operator)

```bash
mkdir -p ~/.config/sops/age
age-keygen -o ~/.config/sops/age/keys.txt
# Public key (age1...) is printed — share THIS with the team.
# The file's AGE-SECRET-KEY-... line is private. NEVER commit it.
```

Point SOPS at your private key:

```bash
export SOPS_AGE_KEY_FILE="$HOME/.config/sops/age/keys.txt"
```

### 1.3 Declare recipients in `.sops.yaml`

Copy [`.sops.yaml.example`](../.sops.yaml.example) to `.sops.yaml` at the repo
root and replace the placeholder public keys with each operator's `age1...` key.
SOPS reads this automatically — no need to pass `--age` on every call.

```yaml
creation_rules:
  - path_regex: config/secrets\.(enc\.)?ya?ml$
    age: >-
      age1exampleoperatoraaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaq,
      age1exampleoperatorbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbq
```

### 1.4 Encrypt / decrypt with the helper scripts

A plaintext template lives at
[`config/secrets.example.yaml`](secrets.example.yaml). Copy it, fill in real
values locally, then encrypt:

```bash
cp config/secrets.example.yaml config/secrets.yaml   # git-ignored, plaintext
$EDITOR config/secrets.yaml                           # add real values

./scripts/sops-encrypt.sh config/secrets.yaml config/secrets.enc.yaml
git add config/secrets.enc.yaml                        # ciphertext is safe to commit
rm config/secrets.yaml                                 # never keep plaintext around
```

Decrypt back to plaintext (e.g. to edit):

```bash
./scripts/sops-decrypt.sh config/secrets.enc.yaml config/secrets.yaml
```

To edit ciphertext in place without ever writing plaintext to disk:

```bash
sops config/secrets.enc.yaml      # opens decrypted in $EDITOR, re-encrypts on save
```

### 1.5 Feed secrets to RedGuard at runtime

`sops exec-env` decrypts into a child process's environment and nothing touches
disk:

```bash
sops exec-env config/secrets.enc.yaml 'redguard run --config configs/config.public.example.json'
```

Inside a module:

```python
import os

token = os.environ.get("MYTHIC_API_TOKEN", "")
if not token:
    return {"status": "skipped", "detail": "MYTHIC_API_TOKEN not provided"}
```

### 1.6 Rotating keys

When an operator leaves or a key is compromised:

```bash
# 1. Remove/replace their age1... key in .sops.yaml
# 2. Re-encrypt every managed file against the new recipient set:
sops updatekeys config/secrets.enc.yaml
```

---

## 2. HashiCorp Vault

[Vault](https://developer.hashicorp.com/vault) is preferred when secrets are
shared across an engagement team, must be rotated dynamically, or require an
audit trail. RedGuard reads from Vault's **KV v2** secrets engine.

### 2.1 Authenticate

```bash
export VAULT_ADDR="https://vault.example.com:8200"
vault login            # or: export VAULT_TOKEN="s.EXAMPLETOKEN..."
```

`vault login` supports OIDC, AppRole, and token auth; for CI use AppRole:

```bash
export VAULT_TOKEN="$(vault write -field=token auth/approle/login \
    role_id="$VAULT_ROLE_ID" secret_id="$VAULT_SECRET_ID")"
```

### 2.2 Store engagement secrets

```bash
vault kv put redguard/engagement-acme \
    MYTHIC_API_TOKEN="REPLACE_ME" \
    NEO4J_PASSWORD="REPLACE_ME"
```

### 2.3 Load secrets into the environment

The [`vault-load.sh`](../scripts/vault-load.sh) helper reads a KV v2 path and
emits `export KEY=value` lines, so you can source it:

```bash
# Print export statements (review before sourcing):
./scripts/vault-load.sh redguard/engagement-acme

# Load directly into the current shell:
source <(./scripts/vault-load.sh redguard/engagement-acme)

redguard run --config configs/config.public.example.json
```

### 2.4 SOPS + Vault together

SOPS can also use Vault Transit as its key backend (`sops --hc-vault-transit`),
giving you encrypted-files-in-git *and* centralised key custody. See the SOPS
docs for `Hc Vault` setup; the file-handling scripts above are unchanged.

---

## 3. Safety checklist

- [ ] `.sops.yaml` contains only **public** `age1...` keys.
- [ ] No `AGE-SECRET-KEY-...`, `s.<token>`, or PEM private key is ever staged.
- [ ] Plaintext `config/secrets.yaml` is deleted after encrypting (it is also
      git-ignored — see the `config/secrets.yaml` entry in `.gitignore` — but
      delete it anyway so it never lingers).
- [ ] Ciphertext (`*.enc.yaml`) is reviewed in PRs like any other file.
- [ ] Vault tokens are short-lived; prefer AppRole over root tokens.
- [ ] `git status` is clean of any plaintext secret before every commit.

See also: [`docs/playbooks/operational_security.md`](../docs/playbooks/operational_security.md).
