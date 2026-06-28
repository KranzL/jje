---
type: research
tags: [research, datalake, private-source]
private: true
---
# Research: lakehouse (private — linked, not copied)

> [!warning] The lakehouse design notes are **private** and live outside this
> public repo. This note is a non-sensitive pointer only — do **not** paste the
> architecture or internal system names here.

## Source (private, local-only)
- `~/Documents/GitHub/luke-kranz-docs/lakehouse/` (README + `research/*`)
- The team conventions distilled from it live in `.jje/conventions/lakehouse.md`
  (gitignored, never published) — see [[conventions-overlay]].

## What it informs (publicly safe)
The datalake-lane jurors review against the team's lakehouse decisions via the
conventions overlay: [[table-format]], [[data-contract]], [[idempotency]],
[[partitioning-layout]], [[storage-format]], [[governance]], [[cost]],
[[data-quality]]. Validated: a juror flagged an `iceberg-rust` append-only
violation that generic Iceberg review would not have caught.

For anything specific, open the private source above — it is intentionally not
mirrored into the vault.
