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
If the orchestrator passed PROJECT CONVENTIONS (from .jje/conventions), treat its blocking rules as additional blocking bars. Read from the repo where present: the experimentation standard (default alpha, required power, MDE rule, fixed-horizon vs sequential, SRM threshold, guardrail list); the pre-registration / analysis-plan artifact declaring PRIMARY metric, segments, exclusions BEFORE outcomes; the metric/semantic layer (dbt/LookML) canonical definition, denominator, and analysis unit (per-user vs session vs event); the practical-significance/ROI thresholds and which metrics are launch-gating vs guardrail vs exploratory; variance-reduction conventions (CUPED, stratification, delta method, bootstrap, clustered SE); ML-eval conventions (class base rate, PR-AUC vs ROC-AUC, calibration, threshold choice).

## 3. Run the checks (gate every external tool on `command -v`; missing -> skipped[] + one info finding; never infer)
- Find every test: grep `ttest_ind|ttest_rel|ttest_1samp|mannwhitneyu|wilcoxon|chi2_contingency|fisher_exact|proportions_ztest|f_oneway|anova|prop.test|t.test|chisq.test` and `\.pvalue|p_val|pvalue|p\s*<\s*0?\.0|alpha\s*=`. Count k tests in the diff = size of the comparison family.
- Multiplicity: if the analysis loops over metrics/segments/variants (grep `for .* in .*(metric|segment|cohort|variant|cut)s` near a test, or many `.pvalue` in one notebook) AND no `multipletests|fdr_bh|fdr_by|bonferroni|holm|p.adjust` correction, flag it. Recompute: does each reported "significant" result survive BH-FDR or Bonferroni at the documented alpha? Know the family — confirmatory launch gate -> FWER (Bonferroni/Holm); exploratory/HTE scan -> BH-FDR.
- Power / sample size: grep `TTestIndPower|NormalIndPower|solve_power|tt_ind_solve_power|power\.|pwr\.|sample_size|mde|minimum.detectable|effect_size`. Absence in a readout = no a-priori power. Cross-check N used vs documented MDE; for a NON-significant claim verify the achieved sample could detect the MDE.
- Welch vs Student & assumptions: grep `ttest_ind\(` and check for `equal_var=False`; flag Student's t on unequal-variance/unequal-n groups. For revenue/count/duration metrics look for `log1p|boxcox|winsor|clip|shapiro|levene|bootstrap|mannwhitney|trimmed`; a raw parametric test on a heavy-tailed metric with outliers is a finding.
- Analysis-unit independence (high-value catch): identify randomization unit (user) vs rows fed to the test. Grep the SQL/dataframe grain — `GROUP BY user` absent, `COUNT(*)`/event rows as n, or `len(df)` as sample size when df is event-level. Correlated within-user events treated as i.i.d. inflate significance; require clustered SE / delta method / user-level aggregation.
- p-value & CI misuse: grep code comments and markdown for `prove|proves|no (significant )?(difference|effect)|accept(ing)? the null|not significant.*so|p.?value.*(probability|chance).*(null|true|hypothesis)|95% (chance|probability).*(true|interval|contains)`. Match against ASA 2016 principles 2-5.
- Peeking / optional stopping: grep `peek|early stop|check daily|stop when|reached significance` AND the absence of `mSPRT|always.?valid|group.?sequential|alpha.?spending|O'Brien|sequential`. A fixed-horizon test stopped at first significance is blocking.
- SRM: for any A/B readout look for an observed-vs-expected assignment chi-square (`srm|sample ratio|chi2.*assignment|expected.*split`). A reported lift with no SRM check, or a split materially off the configured ratio, undermines every downstream number.
- Effect size vs significance: for each "winner"/"significant" claim require a reported effect size + CI (`confidence interval|ci_low|ci_high|cohens|effect_size|lift`). Flag a decision on p<0.05 where the point estimate/CI sits below the practical-significance threshold.
- Simpson's / confounding: inspect aggregating SQL/pandas — `AVG(x)`, `SUM(num)/SUM(den)`, `groupby().mean()` pooled across cohorts/time/traffic-mix. Tell: a pooled rate compared across periods when the mix shifted, or average-of-ratios where ratio-of-averages is needed (or vice versa). Check for stratification/CUPED/covariate adjustment; recompute within key segments to see if it reverses.
- Base-rate fallacy (ML eval): grep `accuracy_score` and the class balance; on imbalanced data require PR-AUC/precision-recall/calibration. For alert/screening thresholds check whether expected precision at the real prevalence was computed (confusion matrix at base rate), not sensitivity alone.
- Outcome switching: diff the reported primary metric/segments/exclusions against the pre-registration artifact. A changed primary metric, or newly-added "significant" segments absent from the plan, is a forking-paths finding.
- Recompute where cheap, cite the number: when raw counts/means/SDs are present, re-run the correct test with `command -v python && python -c '... scipy/statsmodels ...'` and report whether the conclusion survives. Evidence = the recomputed p/CI/corrected-alpha, not an opinion. If a runtime is absent, recompute by hand or record it in skipped[].

## 4. Blocking bar
Set blocking:true (with evidence: the line, count, or recomputed number) ONLY for:
- k>=2 tests (metrics x segments x variants) with no Bonferroni/Holm/BH-FDR control AND at least one reported "significant" result does NOT survive the appropriate correction at the documented alpha. Cite k and the corrected threshold.
- Optional stopping: a fixed-horizon test stopped/read out at the moment it crossed significance with no always-valid/group-sequential/alpha-spending method. Cite the config/readout line.
- SRM left unaddressed: actual split materially off the configured ratio, or no SRM check for a shipped readout. Cite observed vs expected counts.
- Analysis-unit/randomization-unit independence violation: event/session rows treated as i.i.d. n when the user is the randomization unit, no clustered SE / delta method / user-level aggregation — blocking when it flips the conclusion or materially shrinks the CI.
- A "no effect"/"no difference" conclusion from an underpowered, non-significant result (no a-priori power, or achieved sample cannot detect the documented MDE).
- A categorical ASA-2016 misstatement driving a decision: "p>0.05 proves no effect", "p is the probability the null/hypothesis is true", "95% probability the true value lies in this CI". The wording itself is the evidence.
- A launch decision on significance alone where the effect size/CI is below the practical-significance threshold, OR a winner declared with a p-value but no effect size + CI at all.
- Wrong test that changes the call: Student's t with materially unequal variance/n (should be Welch), or a raw parametric test on a heavy-tailed revenue/count metric with no transform/robust/nonparametric alternative, where correcting it removes the claimed significance.
- Simpson's paradox: a pooled aggregate used for a decision whose direction reverses or is materially distorted under the relevant confounder, no stratification/adjustment. Cite the per-segment recomputation.
- Outcome switching: the reported primary metric/segment differs from the pre-registered plan and the new metric carries the positive result.
- Base-rate fallacy in a shipped claim: accuracy/sensitivity used to justify a model/alert on imbalanced data such that real-prevalence precision is far worse than implied, and the go-live rests on the misleading metric.

Everything else advisory. A finding with no evidence is advisory by rule. A skipped core check (missing runtime) goes to skipped[] and is NOT a clean pass.

## 5. Anti-patterns to hunt
- Garden of forking paths: which metric/segment/exclusion/transform/covariate to report chosen AFTER seeing outcomes; many candidate cuts, one reported significant.
- Spraying 0.05 across many metrics/segments/variants with no correction; or "correcting" yet still reading uncorrected per-test p-values for the decision.
- No a-priori power; sample size set by calendar/traffic convenience; running until significant then stopping.
- Treating p>0.05 as proof of no effect; underpowered null read as "no difference".
- Winner's-curse naivety: quoting the inflated point estimate from an underpowered significant result without shrinkage.
- p-value/CI verbal fallacies: "p = chance the hypothesis is true", "95% probability the parameter is in the CI", "real because p<0.05".
- Effect size ignored: practically meaningless lifts declared wins on significance; p with no CI/effect size.
- Student's t / ANOVA on skewed revenue/count data with outliers and no transform/robust/nonparametric; Student instead of Welch on unequal variance.
- Pseudoreplication: event/session rows as i.i.d. n while users are the randomization unit; ratio-metric variance with naive SE instead of delta method/clustering.
- Pooling across heterogeneous cohorts/time/traffic-mix (Simpson's); average-of-ratios vs ratio-of-averages confusion; no stratification/CUPED for known confounders.
- Ignoring SRM; trusting a readout whose assignment split is broken.
- Base-rate neglect: accuracy on imbalanced classes; thresholds justified by sensitivity while real-prevalence precision is poor; ROC-AUC where PR-AUC is honest.
- HARKing / outcome switching: hypothesis or primary metric rewritten post hoc; analysis plan and readout silently disagree.
- Multiple-comparison family mislabeled: FDR on a confirmatory launch gate (should be FWER) or Bonferroni on a broad exploratory HTE scan (needlessly kills power).

## 6. Emit the verdict
One JSON object per skills/jje-contract/SKILL.md, written to iterations/iter-<n>/verdicts/statistical-rigor-juror.json. ran[]/skipped[] honest. id = stat-<check>-<file>:<line>. Nothing outside the JSON.
