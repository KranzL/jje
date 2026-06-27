# Eval corpus — measuring juror recall

The single highest-leverage way to make the jury stronger is to **measure whether
jurors actually catch known defects.** Without that, blocking bars are guesses.
This corpus is the instrument: a set of fixtures each with a **known planted
defect** that a specific juror must flag as `blocking`.

## What's here

- `cases.json` — the case manifest. Each case names the `lane`, the `juror` that
  owns it, the `fixture` directory, the `planted_defect`, and `expect_match`
  (substrings that must appear in the blocking finding's `check`/`issue`).
- Fixtures: `examples/sample-target` (SQL injection + failing test),
  `terraform/public-s3` (public S3 + open SG + unencrypted EBS), `go-race`
  (concurrent map write — `go test -race` fails).

## Two harnesses

1. **Structural (CI-able, no LLM):** `tests/validate-eval.sh` checks that
   `cases.json` parses, every fixture exists, and every named juror is registered
   in the config. This runs in CI on every push.
2. **Recall (opt-in, needs live jurors):** `tests/run-eval.sh` (manual) seats the
   case's juror against its fixture, then asserts the juror produced a `blocking`
   finding matching `expect_match`. A case that does NOT produce the expected
   blocker is a **false negative** — the signal you feed back into the juror's
   review skill (tighten the bar, add the missed anti-pattern). This leg is
   gated behind an API key / run manually because each case spawns a live juror.

## Why recall, not exact text

LLM jurors phrase findings differently every run, so the harness asserts
*structural* invariants: the expected juror flagged a `blocking` finding whose
evidence matches the planted defect — never an exact string. Track the
**per-lane false-negative rate** over time; when a lane regresses, the fix is a
skill edit, not a loop change (the extensibility contract holds).

## Adding a case

Drop a fixture with one planted defect, add a row to `cases.json` naming the
owning juror and `expect_match`, and run `tests/validate-eval.sh`. See
[CONTRIBUTING.md](../../CONTRIBUTING.md).
