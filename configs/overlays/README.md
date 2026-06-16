# Config Overlays

This directory holds **per-company configuration overlays** for RedGuard Suite.

An overlay is a small YAML document that is layered on top of a base config to
produce the effective configuration for a single engagement. The pattern keeps
shared defaults in one place (`default.yaml`) while letting each engagement
override only the values it needs (`<company>.yaml`).

> **Public repo safety:** Every file in this directory is a *template*. It must
> only ever contain safe placeholders — `example.com`, fictional company names
> such as `acme-corp`, and `0.0.0.0`-style addresses. Real domains, IPs,
> credentials, or company names belong in the private `internal/` overlay repo,
> never here. See [`CLAUDE.md`](../../CLAUDE.md) and [`SECURITY.md`](../../SECURITY.md).

## How overlays are layered

Overlays are merged in order, last-writer-wins, with dictionaries merged
recursively and scalars/lists replaced wholesale:

```
base config (configs/config.public.example.json)
  └── default.yaml        # defaults shared by every company
        └── <company>.yaml # engagement-specific overrides
```

The resulting document uses the same schema as the JSON configs consumed by the
orchestrator (`targets`, `modules`, `risk_matrix`, `safety`, ...), so a merged
overlay can be serialised to JSON and passed to `redguard --config`.

## Files

| File             | Purpose                                                        |
| ---------------- | ------------------------------------------------------------- |
| `default.yaml`   | Baseline overlay every engagement inherits. Safe by default.   |
| `acme-corp.yaml` | Worked example of a per-company overlay (fictional company).    |

## Creating a new overlay

1. Copy `acme-corp.yaml` to `<your-company>.yaml`.
2. Override only the keys that differ from `default.yaml`.
3. Keep `safety.dry_run: true` unless an authorised, signed Rules of Engagement
   (RoE) explicitly permits active testing for the scoped window.
4. Validate that the file contains no real targets before committing to a public
   repo — company-specific values go in the private `internal/` repo.

## Merge precedence summary

- **Dictionaries** are deep-merged.
- **Lists and scalars** from the higher-precedence overlay replace the lower one.
- Keys absent from an overlay fall through to the layer below.
