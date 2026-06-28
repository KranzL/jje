---
type: eval-pass
pass: scale
tags: [eval, key-finding]
---
# Scale eval (pass 3 — the one that failed)

Realistic multi-file PRs (avg 7.3 files, 380 total) with one buried disguised
defect among legitimate distractors. Juror reviews the whole PR; a judge scores
recall (located the buried defect) + false alarms (flagged distractor code).

**Recall 35/38 · 17 false alarms · 21/38 flawless.** The first pass that could
fail, and did — usefully.

## The 3 misses (all un-tool-backed subtle-diff lanes)
- [[interface-compat]] — missed a public type narrowing buried among additive changes.
- [[data-contract]] — missed a `decimal(18,4)→(18,2)` cut sitting next to a *widening* distractor.
- [[terraform]] — missed the IAM defect and flagged the wrong thing, **only because checkov/trivy were absent**.

False alarms clustered in the reasoning lanes; the tool-backed lanes were clean
on both axes. → the sharpest confirmation of [[tool-backing]]. Fixes are in
[[hot|the active threads]]. Combined: [[scorecard]].

Data: [`examples/eval/scale-results.json`](../../examples/eval/scale-results.json)
