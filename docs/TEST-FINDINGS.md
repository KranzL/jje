# Test findings (gap-hardening pass)

Evidence-driven results from testing the four gap buckets. Fixes in Phase 2 are
keyed to these IDs.

## Bucket 1 — safety assumptions

| ID | Test | Result |
|---|---|---|
| T1.1 | Do the hooks fire in a real (headless) session? | **Conditional.** Hooks load and fire **only when the workspace is trusted** (`hasTrustDialogAccepted`). An untrusted workspace silently loads neither hooks nor permission rules — the entire enforcement layer no-ops. Verified: a sentinel logged `ci-gate fired` once trusted; before trust, a commit to `main` landed with a "workspace not trusted" warning. |
| T1.1b | Are hook denials honored? | **Not under `bypassPermissions`.** With the gate armed, the ci-gate hook fired and returned `exit 2` + a deny, but under `--permission-mode bypassPermissions` the commit to `main` **landed anyway**. Allowlisted commands also appear to skip their PreToolUse hook. |
| T1.2 | Subagent commits | Not independently isolable in headless tests, but the conclusion holds regardless (below). |
| T1.3 | Did jurors run on their configured models? | **PASS.** Live-run transcripts: planner/executor/correctness = `claude-sonnet-4-6`, security = `claude-haiku-4-5`, judge = `claude-opus-4-8`. The `model:` frontmatter works; the cost model holds. |

**Conclusion:** the hooks are **conditional defense-in-depth, not a hard guarantee.** They require a trusted workspace and a non-bypass permission mode. The real, unconditional safety must come from the deterministic CLI (`start-iteration` refuses past budget; `accept` validates the CI artifact) plus orchestrator discipline (the candidate lives on a scratch branch; only the post-`accept` merge touches `main`). The docs overstated the hooks as "hard guarantees" — that framing must change.

## Bucket 3 — design holes (all confirmed)

| ID | Test | Result |
|---|---|---|
| T3.1 | Malformed verdict vs `check-guards` | **Crashes.** An invalid-JSON verdict raises an uncaught `JSONDecodeError`; a finding missing the `blocking` key is silently treated as non-blocking. No runtime schema validation. |
| T3.2 | Marker bound to the CI'd sha? | **No.** `accept` records `ci_sha` but the gate only checks the marker *exists*, not that the committed sha matches. TOCTOU window. |
| T3.3 | Gate evasion | **Evadable.** `git $(echo commit) -m x` passes the gate (exit 0) while `git commit` is denied. String-parsing a shell command is inherently leaky. |

## Bucket 4 — operational hygiene

| ID | Test | Result |
|---|---|---|
| T4.1 | Cleanup | Run dirs accumulate under `.jje/runs/`; `close`/`escalate` do not remove the worktree or scratch branch. No GC. |

## Bucket 2 — live paths

See the REVISE + tool-backed run below (T2.1/T2.2). Live ESCALATE (T2.3) is
covered deterministically by the unit tests (budget refusal + oscillation
fingerprint); its hook-based backstop inherits the Bucket 1 caveats, so the
authoritative escalate is the CLI's `start-iteration` budget refusal.
