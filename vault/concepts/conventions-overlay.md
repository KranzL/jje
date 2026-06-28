---
type: concept
tags: [concept, conventions]
---
# Project conventions overlay

A generic mechanism so jurors review against *your* standards, not just generic
best practice. Drop `### <lane>`-organized rules in `.jje/conventions/*.md`
(gitignored — local, never published); the orchestrator passes each juror the
section matching its domain, and `(blocking)` rules become extra blocking bars.

- The **mechanism** is public and reusable: see
  [`.jje/conventions.example.md`](../../.jje/conventions.example.md).
- The **content** stays local. The team [[lakehouse]] conventions live in a
  gitignored file and drive the datalake-lane jurors ([[table-format]],
  [[data-contract]], [[idempotency]], …) — validated: a juror flagged an
  iceberg-rust-append-only violation that generic Iceberg review would miss.

Pairs with [[principal-data-jurors|the principal data lanes]]: a team can teach
`[[dimensional-modeling]]` its modeling standard or `[[experimentation-abtest]]`
its experiment platform the same way.
