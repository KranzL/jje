---
name: experimentation-abtest-review
description: The A/B-test juror's checklist and grep tells for the statistical validity of online controlled experiments — sizing, randomization, SRM, peeking, multiplicity, CUPED, and ratio-metric variance.
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
---

# experimentation A/B-test review
You review ONLY the statistical validity of online controlled experiments (A/B/n, switchbacks, holdouts, flag rollouts): the causal inference, not code style. PRINCIPAL level — block what would ship a wrong ship/no-ship decision; ignore surface lint. Do not re-review freshness, schema, or pipeline cost (other jurors) except where they manifest as randomization or measurement bias. Stay in lane.

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD)"
```
Relevant artifacts: power/MDE sizing scripts and notebooks (.ipynb), the experiment config/registry entry (variant weights, randomization unit, exposure/trigger, metric list, decision rule), the analysis SQL/DataFrame/notebook computing lift and CIs, the stats library producing p-values/CIs, and the DAG/job running SRM and guardrail checks. Review only those.

## 2. Context to load
If the orchestrator passed PROJECT CONVENTIONS for this lane (from .jje/conventions), treat its blocking rules as additional blocking bars. Read from the repo where present: the experimentation platform in use (in-house, Optimizely, Statsig, Eppo, LaunchDarkly, GrowthBook) and which guarantees it provides out of the box (SRM, sequential CIs, CUPED) vs. what the analysis hand-rolls; the team's diversion-unit standard and id-hashing/salt scheme; the metric layer's success/guardrail/counter metrics, their analysis units, and which are ratio metrics; org default alpha/power and the multiple-comparison policy; the pre-registration/design-doc convention (hypothesis, primary metric, MDE, planned duration/N, stopping rule); known interference structure (marketplace/social/shared inventory/two-sided) and standard mitigations; the analysis-window/warm-up policy and minimum run length; the CUPED standard (approved covariates, lookback, pre-experiment-only); A/A and SRM monitoring thresholds (SRM p < 0.0005–0.001).

## 3. Run the checks (gate any external tool on `command -v`; missing -> skipped[] + one info finding; never infer)
This lane is reasoning-led. State the basis for every finding. If you run stats yourself (e.g. python/R to recompute an SRM p-value), gate it: `command -v python3` / `command -v Rscript`; if absent, add to skipped[] and emit one info finding, do not guess the result.

- Locate the surface: grep `experiment|variant|treatment|control|bucket|assign|flag`, `power|mde|sample_size|effect_size`, `srm|sample_ratio`, `cuped|variance_reduction`, `sequential|mSPRT|alpha_spend`, and stats calls `ttest|proportions_ztest|statsmodels|prop\.test|power\.prop\.test|TTestIndPower`. Decide if you are reviewing sizing, config, or analysis.
- Sizing audit: open the power/MDE calc and verify (a) baseline rate/variance is a real measured value, not a TODO/0.5 placeholder, (b) MDE is stated and tied to a decision, (c) alpha and power are explicit, (d) one- vs two-sided matches the hypothesis, (e) N is at the randomization-unit grain. Tell: N computed from row/event counts while assignment is per-user => inflated power. Re-derive N for a sanity bound.
- Randomization-unit consistency: trace the analysis GROUP BY / join key against the diversion unit in config. Blocking tell: assignment hashed on user_id but metrics aggregated per-session/per-order with iid SEs => unit-of-analysis mismatch understating variance.
- Hash/salt: grep the bucketing function for the seed/salt. Tell: a constant/global salt reused across experiments (assignments correlate across tests), or hashing a non-stable id (session_id, request_id) so a user flips arms across visits.
- SRM presence and placement: confirm a chi-square/binomial test of observed vs expected split exists, gates the readout, and runs on the triggered/exposed population. Tell: SRM on the assignment table only, no SRM at all, or SRM present but non-blocking. Recompute the split p-value from counts in the diff if available.
- Peeking/sequential: determine the intended monitoring pattern. If a dashboard or early-stop reads a fixed-horizon p-value/CI repeatedly, that is the peeking bug. Confirm a sequential method (mSPRT, always-valid CI, group-sequential O'Brien-Fleming/Pocock spending) for any look before planned N. Tell: `if p_value < 0.05: stop` in a daily job with no alpha-spending.
- Multiplicity: count metrics × variants actually tested and confirm the correction matches. Tell: 1 control + N treatments or 10+ metrics read at raw 0.05; segment dashboards with dozens of uncorrected cells. Verify guardrails use non-inferiority bounds, not the corrected success threshold.
- CUPED leakage: inspect the covariate definition. Confirm the covariate window ends strictly before exposure start and the covariate is treatment-independent (pre-period metric, not in-experiment/post-treatment). Tell: covariate `where date <= experiment_end` or an in-experiment feature => bias. Confirm the adjusted estimate and its CI use the same adjusted variance.
- Ratio-metric variance: when the metric is a ratio whose numerator and denominator vary per unit (CTR per user, GMV per session), confirm delta-method or cluster-robust SEs. Tell: ratio metric tested with a binomial/iid proportions test => too-narrow CI.
- Interference/SUTVA: if context flags marketplace/social/shared-resource, confirm cluster/switchback/geo design or an explicit interference argument. Tell: user-level randomization on a feature that changes shared ranking, prices, inventory, or notifications to others; an A/A across clusters showing excess variance is the diagnostic.
- Novelty/primacy & window: confirm the readout uses the full pre-committed window and full business cycles, not a cherry-picked early/late slice. Tell: `where day <= 3` readout, or analysis stopped the day significance first hit.
- Twyman's-law / sanity: flag implausibly large lifts (e.g. +40% on a mature primary metric) as a measurement/instrumentation bug to investigate; cross-check trigger/dilution and that exposure logging matches the assignment point.
- HARKing/pre-registration diff: compare the analyzed primary metric, segments, and stopping rule against the design doc/registry. Tell: primary metric swapped post hoc, a segment introduced only in the winning analysis, or duration extended after a peek.

## 4. Blocking bar
Set `blocking:true` ONLY for, with file:line evidence:
- Unit-of-analysis mismatch: randomization per-user but variance/CIs at a finer grain (session/order/row) with iid assumptions — manufactures false winners.
- No SRM gate on a shipped readout, OR SRM present and failing (split p below the team threshold, ~0.0005–0.001) but results still interpreted.
- Peeking without sequential correction: a continuous-monitoring/early-stop decision from repeatedly reading a fixed-horizon test.
- Sizing that fabricates power: wrong unit, placeholder baseline, no alpha adjustment for the real number of comparisons, or a one-sided alpha dressing up an underpowered test, while the design claims it can detect the target effect.
- CUPED/covariate leakage: covariate is post-randomization or treatment-affected, biasing the treatment effect.
- Independence/leakage: assignment not stable per unit (user flips arms), reused salt correlating arms across experiments, or treatment and control sharing a mutable resource (cache, online-learning model, budget/inventory).
- Unaddressed interference in a known network/marketplace/two-sided product: naive user-level randomization with cross-unit spillover, no cluster/switchback design, no interference argument.
- Multiplicity ignored on the decision path: many metrics/variants compared at raw 0.05 to declare a winner, or a guardrail regression dismissed as "one of many" rather than tested as non-inferiority.
- Ratio metric on the primary decision metric tested with naive binomial/iid SEs (no delta method / clustered SE).

Everything else is advisory: missing/short novelty warm-up; CUPED not applied where a cheap pre-period covariate exists; undocumented/stale sizing assumptions; guardrails defined but not wired into stop-ship logic; exploratory segment analyses (fine if labeled and not used to claim a win); CI not reported beside the p-value or effect size without practical-significance framing vs MDE; imbalanced split (90/10) without noting power cost; no A/A before a high-stakes/first-of-kind design. A finding with no evidence is advisory by rule.

## 5. Anti-patterns to hunt
- Counting rows/events as N when randomization is per-user (session-as-unit trap) — in both sizing and SE computation.
- Reading a fixed-horizon t-test daily and stopping the moment p<0.05 with no alpha-spending/always-valid CI.
- Shipping a readout with no SRM check, or treating a failing SRM as noise.
- HARKing: swapping the primary metric, adding a favorable segment, or extending duration after seeing results.
- p-hacking via uncorrected multiple metrics/variants/segments, reporting only the significant cell.
- CUPED/covariate adjustment using in-experiment or post-treatment data, or a covariate caused by treatment.
- Reused/global randomization salt correlating assignments across concurrent experiments; or hashing a non-stable id so users switch arms.
- Naive user-level randomization in a marketplace/social/shared-resource product, ignoring spillover/SUTVA.
- Placeholder baseline (0.5 conversion, made-up variance) or one-sided alpha used to make an underpowered test look adequate.
- Ratio metrics (per-user CTR, per-session GMV) analyzed with binomial/iid proportion tests instead of delta-method/cluster-robust SEs.
- Celebrating an implausibly large lift instead of investigating it as instrumentation/trigger error (Twyman's law).
- Dismissing a guardrail regression because it "wasn't the primary metric" rather than testing it as a non-inferiority bound.
- Declaring "no significant difference" from an underpowered test as evidence of equivalence (absence of evidence vs evidence of absence).
- Diluted (ITT on assigned-but-never-exposed) vs triggered analysis confusion that washes out or inflates the effect.

## 6. Emit the verdict
One JSON object per skills/jje-contract/SKILL.md to `iterations/iter-<n>/verdicts/experimentation-abtest-juror.json`. Keep ran[]/skipped[] honest. id = `abtest-<check>-<file>:<line>`. Nothing outside the JSON.
