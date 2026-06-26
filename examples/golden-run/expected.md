# Golden run — sample-target, `quick` preset

LLM output is nondeterministic, so the golden run asserts STRUCTURAL invariants,
not exact text. Running `/jje "fix the SQL injection and make the email test
pass"` against `examples/sample-target/` with the `quick` preset should produce:

## Iteration 1

- **Planner** writes `plan.json` with success criteria covering "no string-built
  SQL" and "email test passes".
- **Executor** builds a candidate on the scratch branch.
- **Jury** (`quick` = correctness + security), parallel:
  - `security-juror` → one `blocking: true` finding, `category: security`,
    `check` referencing the injection, `evidence` citing `app/handler.py`
    (the `build_user_query` line), `id` shaped `sec-...-app/handler.py:<line>`.
  - `correctness-juror` → one `blocking: true` finding citing the failing test
    `test_normalize_email_strips_and_lowercases`, `evidence` = the pytest node id.
- **check-guards** → `blocking_now: 2`, `recurring: []`, `recommend_escalate: false`.
- **Judge** → `REVISE`, `feedback` naming both findings, `unresolved` listing
  both ids.

## Iteration 2

- **Executor** (revise) parameterizes the query and strips+lowercases the email —
  fixes ONLY the two flagged findings.
- **Jury** re-runs (same seating): both verdicts now have empty `findings` (or
  only advisory `info`).
- **check-guards** → `blocking_now: 0`.
- **Judge** → `ACCEPT`.
- **CI** (`jje_state.py ci` → `make ci`) exits 0; `ci-result.json` records exit 0.
- **accept** validates the artifact and writes `.jje/COMMIT_APPROVED`.

## Asserted invariants (in `tests/`)

- Every verdict file validates against `schema/verdict.schema.json`.
- The Judge decision validates against `schema/decision.schema.json` and is one
  of `ACCEPT | REVISE | REPLAN | ESCALATE`.
- The planted injection surfaces as a `blocking` security finding in iteration 1.
- The candidate never lands on a protected branch without `.jje/COMMIT_APPROVED`.

The live-LLM leg of this is opt-in (gated behind an API key) so forks pass CI
without one; the always-on tests exercise the deterministic core and schemas.
