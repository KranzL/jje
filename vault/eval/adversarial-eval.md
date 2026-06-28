---
type: eval-pass
pass: adversarial
tags: [eval]
---
# Adversarial eval (pass 2)

A disguised real defect + a guilty-looking decoy per juror, **authored blind to
the skills** (no teaching to the test). Recall semantically judged; precision =
silence on the decoy. **38/38 recall + 38/38 precision.**

The decoy result is the credible signal: jurors stayed quiet on code built to
bait them (an allowlisted interpolation that looks like injection; a correct
dependency-inversion that looks like a layering violation). **The jurors reason;
they do not grep.**

Caveats: small single-defect fixtures (no needle-in-haystack) and judge anchoring
on recall. That gap motivated [[scale-eval]]. Combined: [[scorecard]].

Data: [`examples/eval/adversarial-results.json`](../../examples/eval/adversarial-results.json)
