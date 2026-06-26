# sample-target

A throwaway fixture repo JJE runs against in tests and demos. It contains two
planted defects in `app/handler.py`:

1. **SQL injection** in `build_user_query` — user input concatenated into SQL.
   The `security-juror` should emit a `blocking` finding.
2. **A failing unit test** — `normalize_email` does not strip surrounding
   whitespace, so `tests/test_handler.py::test_normalize_email_strips_and_lowercases`
   fails. The `correctness-juror` should emit a `blocking` finding citing the test.

`make ci` runs the suite (red until both are fixed).

The expected JJE behavior — REVISE on the blocking findings, then ACCEPT once the
canned fix lands — is recorded in `../golden-run/expected.md`.

To try it: copy the repo's `.claude/` and `.jje/` here, `git init`, then run
`/jje "fix the SQL injection and make the email test pass"` and seat the `quick`
preset.
