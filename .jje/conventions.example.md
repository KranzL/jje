# Project conventions (example)

Drop project-specific review criteria in `.jje/conventions/<name>.md` (that
directory is gitignored — your conventions stay local and are never published).
The orchestrator reads every file there, and for each seated juror passes the
section whose `### <lane>` header matches the juror's domain, as additional
review criteria. Jurors treat `(blocking)` rules here as extra blocking bars for
their lane; `(advisory)` rules are weighed but do not gate.

Organize one `### <lane>` section per juror domain you want to constrain. Lane
names match the juror domains: `correctness`, `security`, `structure`,
`observability`, `interface`, `data-contract`, `idempotency`, `cost`,
`data-quality`, `governance`, `table-format`, `partitioning-layout`,
`storage-format`, `go-concurrency`, `go-error-handling`, `go-performance`,
`terraform`, `deployment`.

## Example

```markdown
## This service (context every juror needs)

One short paragraph: what the system is, the stack, the non-obvious constraints a
reviewer must know to judge a change.

## Conventions to review against, by lane

### security
- All external input crossing the API boundary must be validated by the shared
  `validate.Input` helper, not ad hoc. (blocking)
- Internal service-to-service calls must carry the mTLS client cert. (blocking)

### data-contract
- Public event payloads are versioned; a breaking field change needs a new
  `v<N+1>` topic, never an in-place edit. (blocking)
- New optional fields are fine without a version bump. (advisory)

### cost
- A new table scan over the `events` hot table must use the `dt` partition
  predicate. (blocking)
```

Keep rules concrete and checkable, mark each `(blocking)` or `(advisory)`, and
group them under the lane that owns them. See your real conventions files (local,
gitignored) for the full set.
