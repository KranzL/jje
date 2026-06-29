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

## 2. Canon, thresholds, and context to load
Canon: Kohavi, Tang, Xu _Trustworthy Online Controlled Experiments_ (Cambridge 2020) — SRM thresholds, sequential methods, CUPED, novelty/primacy, collision/orthogonality. Deng, Xu, Kohavi, Walker "Improving the Sensitivity of Online Controlled Experiments by Utilizing Pre-Experiment Data" (KDD 2013) — CUPED; theta must be estimated on pre-experiment data only. Johari, Pekelis, Walsh "Always Valid Inference: Bringing Sequential Analysis to A/B Testing" — mSPRT/always-valid CI. Benjamini & Hochberg "Controlling the False Discovery Rate" (JRSS-B 1995) — BH step-up FDR. Reference thresholds: SRM gate chi-square p < 0.001; minimum run length < 7 days blocking for known day-of-week-seasonal designs, < 2 full weeks advisory (novelty/primacy washout floor); named multiplicity corrections: Bonferroni (α/m per comparison), Holm-Bonferroni (stepwise FWER), BH step-up (sort p-values, reject p_i ≤ i·α/m) — BH or stronger required on the primary-metric decision path.
Load from the repo: experimentation platform in use and which guarantees it provides out of the box (SRM, sequential CIs, CUPED) vs what the analysis hand-rolls; diversion-unit standard and id-hashing/salt scheme; metric layer success/guardrail metrics, analysis units, and which are ratio metrics; org default alpha/power and multiple-comparison policy; pre-registration/design doc (hypothesis, primary metric, MDE, planned duration/N, stopping rule); known interference structure and mitigations; CUPED standard (approved covariates, lookback, pre-experiment-only theta estimation).

## 3. Run the checks
Gate every external tool on `command -v`; missing → skipped[] + one info finding; never infer.
- Locate the surface: grep `experiment|variant|treatment|control|bucket|assign`, `power|mde|sample_size`, `srm|sample_ratio`, `cuped|variance_reduction`, `sequential|mSPRT|alpha_spend`, `ttest|proportions_ztest|statsmodels|prop\.test`.
- Sizing: verify (a) baseline rate/variance is a real measured value, not 0.5/TODO; (b) MDE stated and tied to a decision; (c) alpha and power explicit; (d) one- vs two-sided matches hypothesis; (e) N at the randomization-unit grain, not row/event counts. Re-derive N as a sanity bound.
- Randomization-unit consistency: trace analysis `GROUP BY`/join key against diversion unit in config. Blocking tell: assignment hashed on `user_id` but iid SEs computed per session/order/row.
- Hash/salt: grep the bucketing function for seed/salt. Tells: constant/global salt reused across experiments (correlated assignments); hashing a non-stable id (session_id, request_id) so users flip arms across visits.
- SRM: confirm chi-square/binomial test of observed vs expected split gates the readout and runs on the triggered/exposed population at p < 0.001. Tell: SRM on assignment table only; no SRM; SRM present but non-blocking.
- Peeking/sequential: confirm any look before planned N uses mSPRT, always-valid CI (Johari et al.), or group-sequential spending (O'Brien-Fleming/Pocock). Tell: `if p_value < 0.05: stop` in a daily job with no alpha-spending.
- Multiplicity: count metrics × variants. Confirm Bonferroni (α/m), Holm-Bonferroni, or BH FDR (p_i ≤ i·α/m, BH 1995) on the decision path. Tell: 10+ metrics or N treatments at raw α = 0.05. Guardrails use non-inferiority bounds, not corrected success thresholds.
- CUPED: confirm covariate window ends strictly before exposure start AND theta is estimated on pre-experiment data only — estimating theta on a pre+experiment window contaminates adjustment with treatment effect (Deng et al. KDD 2013). Confirm adjusted estimate and CI use adjusted variance.
- Experiment collision: when multiple concurrent experiments share a surface, confirm orthogonal holdouts or a modeled interaction term. Tell: multi-experiment assignment code with no orthogonality assertion, holdout check, or interaction term (Kohavi et al. 2020).
- ITT vs triggered: confirm the denominator matches the claim. Tell: triggered analysis without a logged exposure event at the trigger point; ITT and triggered estimators compared without acknowledging dilution.
- Ratio-metric variance: when metric is per-unit CTR/GMV, confirm delta-method or cluster-robust SEs (aggregate to unit-level totals, compute covariances). Tell: ratio metric tested with binomial/iid proportions test.
- Novelty/window: flag readout < 7 days (blocking for seasonal designs) or < 2 weeks (advisory). Tell: `where day <= 3` readout; analysis stopped the day significance first hit.
- HARKing: compare analyzed primary metric, segments, stopping rule against design doc. Tell: metric swapped post hoc; segment introduced only in the winning analysis; duration extended after a peek.

## 4. Blocking bar
Set `blocking:true` (cite file:line evidence) ONLY for:
- Unit-of-analysis mismatch: assignment per-user but iid SEs computed per session/order/row — manufactures false winners.
- SRM gate absent or failing: no SRM check on a shipped readout, OR SRM p < 0.001 but results still interpreted.
- Peeking without sequential correction: early-stop/continuous-monitoring decision from a fixed-horizon test without mSPRT or alpha-spending (Johari et al.).
- Sizing fabricating power: wrong unit grain, placeholder baseline (0.5/TODO), no alpha adjustment for actual comparison count, or one-sided alpha masking an underpowered test.
- CUPED/covariate leakage: post-randomization or treatment-affected covariate, OR theta estimated on any window overlapping the experiment period (Deng et al. KDD 2013).
- Multiplicity ignored on decision path: metrics/variants compared at raw α = 0.05 to declare a winner, or a guardrail regression dismissed without a non-inferiority test; BH FDR or stronger FWER-controlling correction (Bonferroni/Holm) required (BH 1995).
- Assignment independence violated: non-stable id causing arm flips, reused salt correlating arms across concurrent experiments, or treatment/control sharing a mutable resource (cache, online-learning model, shared budget/inventory).
- Ratio metric on primary decision path tested with naive binomial/iid SEs; delta-method or cluster-robust SEs required.
- Experiment collision: concurrent experiments sharing a surface with no orthogonal holdouts and no modeled interaction (Kohavi et al. 2020).
- Run length too short for seasonal design: known day-of-week patterns, readout < 7 days (Kohavi et al. 2020).
Everything else is advisory: < 2-week run on a non-seasonal design; CUPED not applied where a cheap pre-period covariate exists; stale sizing assumptions; guardrails not wired into stop-ship logic; labeled exploratory segment analyses; CI not reported beside p-value; imbalanced split without noting power cost; no A/A before a high-stakes first-of-kind design. A finding with no evidence is advisory by rule.

## 5. Anti-patterns to hunt
- Session/row as N in sizing or SE computation when randomization is per-user.
- `if p_value < 0.05: stop` in a daily job with no alpha-spending or always-valid CI (Johari et al.).
- No SRM gate on a shipped readout, or treating a failing SRM (p < 0.001) as noise.
- 10+ metrics or N treatments compared at raw α = 0.05 with no Bonferroni (α/m), Holm-Bonferroni, or BH FDR correction (BH 1995).
- CUPED theta estimated on a window that overlaps the experiment period, or using an in-experiment/post-treatment covariate (Deng et al. KDD 2013).
- Experiment collision: multi-experiment assignment to the same surface with no orthogonality assertion or holdout check (Kohavi et al. 2020).
- Reused/global randomization salt correlating assignments across concurrent experiments; hashing a non-stable id causing arm flips.
- Placeholder baseline (0.5, made-up variance) or one-sided alpha making an underpowered test look adequate.
- Ratio metrics (per-user CTR, per-session GMV) tested with binomial/iid proportion tests instead of delta-method/cluster-robust SEs.
- Implausibly large lift on a mature primary metric celebrated instead of investigated as instrumentation/trigger error (Twyman's law).
- Guardrail regression dismissed as "not the primary metric" rather than tested as non-inferiority.
- "No significant difference" from an underpowered test asserted as evidence of equivalence.
- ITT dilution: triggered analysis claimed without a logged exposure event at the trigger point.
- HARKing: primary metric swapped, favorable segment added, or duration extended after a peek.

## 6. Emit the verdict
One JSON object per skills/jje-contract/SKILL.md to `iterations/iter-<n>/verdicts/experimentation-abtest-juror.json`. Keep ran[]/skipped[] honest. id = `abtest-<check>-<file>:<line>`. Nothing outside the JSON.
