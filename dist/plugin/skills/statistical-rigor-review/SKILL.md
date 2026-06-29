---
name: statistical-rigor-review
description: The statistical-rigor juror's checklist and exact commands for inferential validity — multiplicity, power, peeking, SRM, analysis-unit independence, Simpson's, and p-value/CI misuse.
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
---

# statistical rigor review
You review ONLY the inferential validity of changes that draw a conclusion from data — experiment notebooks/scripts, A/B configs and readouts, metric-layer/dbt metric definitions used for decisioning, model-eval reports, launch-gating dashboards, and SQL that computes rates/lifts/significance. The one question: does the math support the claim, or does a researcher degree of freedom / unstated assumption / aggregation artifact let a false claim through? PRINCIPAL level — hold the bar at what a principal would block, not surface lint. You do NOT review data correctness (nulls/dupes/RI), schema/contract, cost, partitioning, or storage. Stay in lane.

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD)"
```
Filter to `*.ipynb`, `*.py`, `*.r`/`*.R`, `*.sql`, metric/experiment YAML, and analysis/readout markdown. For notebooks read code AND markdown cells (narrative claims live in markdown): `command -v jupyter && jupyter nbconvert --to script --stdout <nb>`, else parse the `.ipynb` JSON directly.

## 2. Context to load
Canon anchors: Kohavi, Tang & Xu 2020 (Trustworthy Online Controlled Experiments) — guardrail/primary protocol, fixed-horizon vs sequential; Gelman & Loken 2013 — forking-paths FWER inflation from researcher degrees of freedom; Wasserstein, Schirm & Lazar 2019 (The American Statistician 73:sup1) — ASA 2019 authority shifted to effect-size estimation and CI width.

If the orchestrator passed PROJECT CONVENTIONS (from .jje/conventions), treat its blocking rules as additional blocking bars. Read from the repo where present: the experimentation standard (default alpha, required power, MDE rule, fixed-horizon vs sequential, SRM threshold, guardrail list); the pre-registration / analysis-plan artifact declaring PRIMARY metric, segments, exclusions BEFORE outcomes; the metric/semantic layer (dbt/LookML) canonical definition, denominator, and analysis unit (per-user vs session vs event); the practical-significance/ROI thresholds and which metrics are launch-gating vs guardrail vs exploratory; variance-reduction conventions (CUPED, stratification, delta method, bootstrap, clustered SE).

## 3. Run the checks (gate every external tool on `command -v`; missing -> skipped[] + one info finding; never infer)
- Power / sample size: grep `TTestIndPower|NormalIndPower|solve_power|tt_ind_solve_power|power\.|pwr\.|sample_size|mde|minimum.detectable|effect_size`. Absence in a readout = no a-priori power. Cross-check N used vs documented MDE; for a NON-significant claim verify the achieved sample could detect the MDE.
- Welch vs Student & assumptions: grep `ttest_ind\(` and check for `equal_var=False`; flag Student's t when Levene p<0.05 or variance ratio >4:1. For revenue/count/duration metrics look for `log1p|boxcox|winsor|clip|shapiro|levene|bootstrap|mannwhitney|trimmed`; a raw parametric test on a heavy-tailed metric with outliers is a finding.
- p-value & CI misuse: grep code comments and markdown for `prove|proves|no (significant )?(difference|effect)|accept(ing)? the null|not significant.*so|p.?value.*(probability|chance).*(null|true|hypothesis)|95% (chance|probability).*(true|interval|contains)`. Match against ASA 2016 principles 2-5 and ASA 2019 (Wasserstein et al.).
- Effect size vs significance: for each "winner"/"significant" claim require a reported effect size + CI (`confidence interval|ci_low|ci_high|cohens|effect_size|lift`). Flag a decision on p<0.05 where the point estimate/CI sits below the practical-significance threshold.
- Simpson's / confounding: inspect aggregating SQL/pandas — `AVG(x)`, `SUM(num)/SUM(den)`, `groupby().mean()` pooled across cohorts/time/traffic-mix. Tell: a pooled rate compared across periods when the mix shifted, or average-of-ratios where ratio-of-averages is needed (or vice versa). Check for stratification/CUPED/covariate adjustment; recompute within key segments to see if it reverses.
- Outcome switching: diff the reported primary metric/segments/exclusions against the pre-registration artifact. A changed primary metric, or newly-added "significant" segments absent from the plan, is a forking-paths finding (Gelman & Loken 2013).
- Recompute where cheap, cite the number: when raw counts/means/SDs are present, re-run the correct test with `command -v python && python -c '... scipy/statsmodels ...'` and report whether the conclusion survives. Evidence = the recomputed p/CI/corrected-alpha, not an opinion. If a runtime is absent, recompute by hand or record it in skipped[].

## 4. Blocking bar
Set blocking:true (with evidence: the line, count, or recomputed number) ONLY for:
- A "no effect"/"no difference" conclusion from an underpowered, non-significant result (no a-priori power, or achieved sample cannot detect the documented MDE).
- A categorical ASA-2016 misstatement driving a decision: "p>0.05 proves no effect", "p is the probability the null/hypothesis is true", "95% probability the true value lies in this CI". The wording itself is the evidence.
- A launch decision on significance alone where the effect size/CI is below the practical-significance threshold, OR a winner declared with a p-value but no effect size + CI at all.
- Winner's curse: a launch decision citing the inflated point estimate from an underpowered significant result without shrinkage, producing a demonstrably wrong shipped forecast.
- Wrong test that changes the call: Student's t with Levene p<0.05 or variance ratio >4:1 (use Welch), or a raw parametric test on a heavy-tailed revenue/count metric with no transform/robust/nonparametric alternative, where correcting it removes the claimed significance.
- Simpson's paradox: a pooled aggregate used for a decision whose direction reverses or is materially distorted under the relevant confounder, no stratification/adjustment. Cite the per-segment recomputation.
- Outcome switching: the reported primary metric/segment differs from the pre-registered plan and the new metric carries the positive result.

Advisory (not blocking): survivor/truncation bias in cohort construction (metric restricted to users crossing a treatment-affected threshold, e.g. session-length analysis limited to sessions >60s when treatment shifts that boundary); CUPED applied without verifying pre-treatment covariate correlation; no final holdout when CV is otherwise correct; carry-over / missing washout for within-subject or crossover designs; winner's curse documented but not driving a shipped forecast. A finding with no evidence is advisory by rule. A skipped core check (missing runtime) goes to skipped[] and is NOT a clean pass.

## 5. Anti-patterns to hunt
- Garden of forking paths (Gelman & Loken 2013): which metric/segment/exclusion/transform/covariate to report chosen AFTER seeing outcomes; many candidate cuts, one reported significant.
- Treating p>0.05 as proof of no effect; underpowered null read as "no difference".
- Winner's-curse naivety: quoting the inflated point estimate from an underpowered significant result without shrinkage.
- p-value/CI verbal fallacies: "p = chance the hypothesis is true", "95% probability the parameter is in the CI", "real because p<0.05".
- Effect size ignored: practically meaningless lifts declared wins on significance; p with no CI/effect size.
- Student's t / ANOVA on skewed revenue/count data with outliers and no transform/robust/nonparametric; Student instead of Welch when Levene p<0.05 or variance ratio >4:1.
- Pooling across heterogeneous cohorts/time/traffic-mix (Simpson's); average-of-ratios vs ratio-of-averages confusion; no stratification/CUPED for known confounders.
- HARKing / outcome switching: hypothesis or primary metric rewritten post hoc; analysis plan and readout silently disagree.

## 6. Emit the verdict
One JSON object per skills/jje-contract/SKILL.md, written to iterations/iter-<n>/verdicts/statistical-rigor-juror.json. ran[]/skipped[] honest. id = stat-<check>-<file>:<line>. Nothing outside the JSON.
