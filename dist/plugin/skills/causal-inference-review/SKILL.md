---
name: causal-inference-review
description: The causal-inference juror's checklist — reconstruct the estimand and identification argument, audit adjustment sets, DAGs, selection/collider bias, DiD, RDD, IV, matching/IPW, and time-varying confounding behind any claimed causal effect.
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
---

# Causal-inference review

You review ONLY whether a claimed CAUSAL effect is actually identified by the data and the math. PRINCIPAL level — hold the bar at what a principal would block (a wrong estimand, an open back-door, a collider filter), not surface lint. This is a reasoning-led identification review: reconstruct the implied estimand and the identification argument behind the estimator, and check the data supports a causal reading. Stay in lane — say nothing about model accuracy, p-values, or code style except where they bear on identification.

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD)"
```
Review only `$CHANGED` plus the PR/commit text. Relevant artifacts: SQL and dbt models, notebooks (`.ipynb`), R/Python analysis scripts, metric/semantic-layer definitions, and any column name or PR prose asserting an effect.

## 2. Context to load
If the orchestrator passed PROJECT CONVENTIONS for this lane (from `.jje/conventions`), treat its blocking rules as additional blocking bars (sanctioned estimators/packages, required diagnostics, parallel-trends / positivity / weak-IV thresholds). From the spec, this lane needs: the target estimand (population, treatment, outcome; ATE vs ATT vs LATE); the team DAG (DAGitty/ggdag/diagram) recording canonical confounders, mediators, colliders; the experimentation platform and randomization unit / exposure definition; the metric-layer definition of any `lift`/`incremental`/`uplift` outcome; which columns are PRE vs POST treatment and the assignment timestamp; and whether the output feeds a decision (raises the bar). Read these from the repo where present.

## 3. Run the checks (gate any external tool on `command -v`; missing → `skipped[]` + one info finding; never infer)
Mostly reasoning over the diff/SQL/notebook/DAG — be specific about WHAT to inspect.
- **Causal-claim grep:** `rg -in 'caus|effect of|impact of|drives|because of|incremental|uplift|lift|treatment effect|ATE|ATT|LATE|counterfactual|but[- ]for'` over the diff and PR body. Each hit must carry an identification argument; a bare correlation/coefficient narrated this way is the headline finding.
- **Back-door / over-adjustment:** enumerate every regressor / matching covariate / `GROUP BY` conditioning variable. For each ask: is it PRE-treatment? A control measured AFTER treatment, a mediator on the T→Y path, or a common effect of T and Y (collider) is over-adjustment / post-treatment bias. Tells: downstream fields (`sessions_after_signup` when estimating the signup effect), or `propensity_score` reused as a regressor AND the matching key.
- **Collider / selection bias from sample construction:** read every `WHERE` / filter / `INNER JOIN` / `.dropna()` defining the analysis population. `rg -in 'where .*(convert|active|retain|surviv|complete|won|churn)|inner join|dropna|filter\('`. If the filter variable is plausibly caused by both treatment and outcome, conditioning on it opens a non-causal path.
- **DAG-vs-code:** if a DAG exists, compute the minimal sufficient adjustment set (`dagitty::adjustmentSets`) and diff against the actual regressors — missing a required confounder ⇒ residual confounding; including a collider/mediator ⇒ bias. NO DAG for a non-randomized causal claim is itself a finding.
- **DiD:** identify treated/control and pre/post. Flag absent pre-period parallel-trends evidence (event-study leads jointly zero — joint F-test on leads p<0.05; require ≥2 clean pre-periods; bound sensitivity via HonestDiD Mbar), not just a post gap. For staggered adoption flag the TWFE negative-weighting trap — `rg -in 'i\.unit|i\.time|feols\(.*\|.*unit|C\(unit\)|C\(period\)'` — and require a heterogeneity-robust estimator (Callaway-Sant'Anna `did`, Sun-Abraham `sunab`, de Chaisemartin-d'Haultfoeuille) or a Goodman-Bacon/`bacondecomp` diagnostic. Check parallel-trends sensitivity (`HonestDiD`) if pre-trends are imperfect.
- **RDD:** confirm a continuous running variable and real cutoff. Require a manipulation/density test (McCrary / `rddensity`), a data-driven bandwidth (`rdbwselect`/IK/CCT) with a sensitivity range, covariate-continuity / placebo-cutoff falsification, and local `rdrobust` rather than a high-order global polynomial; no extrapolation far from the threshold. `rg -in 'rdrobust|rddensity|rdbwselect|McCrary|bandwidth|cutoff|threshold|running variable'`.
- **IV / 2SLS:** identify Z, D, Y. Relevance — first-stage effective-F via Montiel-Olea-Pflueger (2013) tau=10% size-distortion critical values for all K (K=1: effective-F ≥ ~23; K>1: tabulated per K and exceeding 10); flag weak instruments. Exclusion restriction — require an explicit substantive argument (untestable); flag instruments with an obvious direct path to Y. Independence + monotonicity (no defiers) for LATE; the estimand must be reported as a complier LATE, not a population ATE. `rg -in 'IV2SLS|ivreg|ivmodel|first stage|exclusion|instrument|2sls'`.
- **DML / doubly-robust (AIPW, TMLE, DoubleML):** cross-fitting (Chernozhukov et al. 2018, *Econometrics Journal* 21(1):C1–C68) is identification-critical: nuisance models must be estimated on held-out folds that exclude the target observations; missing cross-fitting lets nuisance overfit into the moment condition (structurally equivalent to pre-split fit_transform). Neyman-orthogonal moment required; AIPW must specify both propensity and outcome model families. `rg -in 'AIPW|TMLE|DoubleML|cross_fit|doubly.robust|EconML|drlearner'`.
- **Matching / propensity / IPW:** positivity/overlap — inspect PS distributions for common support; flag extrapolation where one arm has ~0 density and extreme weights without trimming/stabilization. Balance reported via standardized mean differences (love plot, |SMD|≤0.1), NOT t-tests/p-values (King-Nielsen). The propensity model must exclude post-treatment variables and instruments. `rg -in 'MatchIt|propensity|cobalt|love.plot|WeightIt|ps_|IPW|trim|stabiliz|SMD|std.*diff'`.
- **Synthetic control (Abadie, Diamond & Hainmueller 2010, *JASA* 105(490):493–505):** require pre-RMSPE ratio (post/pre RMSPE) as the effect-size anchor; require placebo-in-space (≥20 donor placebos) or placebo-in-time falsifications; flag donor pools including units that received the treatment or are structurally dissimilar. `rg -in 'synth|synthetic.control|scpi|donor.pool|pre.rmspe'`.
- **Time-varying confounding:** a longitudinal panel with `lag(treatment)` controls plus a time-varying covariate that is itself downstream of past treatment, adjusted by plain `feols`/`lm`/`glm`, is biased — require g-methods (IPW/marginal structural model, g-formula, g-estimation).
- **Randomization integrity (claimed RCT):** confirm the analysis conditions only on PRE-randomization variables; flag post-assignment segmentation, post-hoc cohort filtering, or differential attrition that breaks the as-randomized comparison.
- **SUTVA / no-interference (Rubin 1980):** if treated and control units share a marketplace, social graph, supply pool, or geographic proximity, the no-interference condition is likely violated. A claimed RCT or DiD where units interact with no spillover estimator (cluster randomization, bipartite graph design, switchback) is blocking — the estimand is undefined under interference. `rg -in 'platform|network|marketplace|supply.pool|social.graph|surge|cluster.random|bipartite|switchback|interference'`.

## 4. Blocking bar
Set `blocking: true` (cite `file:line` and evidence) ONLY for:
- A causal claim (column/metric/dashboard label/PR text asserting effect/drives/causes/incremental/lift) backed only by a correlation, a coefficient, or feature importance with NO identification strategy stated.
- Over-adjustment / post-treatment bias: adjustment set, matching covariates, or propensity model includes a mediator or descendant of treatment. Name the offending variable.
- Collider / selection bias: the population is filtered on a common effect of treatment and outcome (converted, retained, survived, "matched only"). Cite the filter.
- A required confounder (per DAG/domain) missing from the adjustment set, leaving a back-door path open.
- Staggered-adoption DiD by TWFE with no heterogeneity-robust estimator or Goodman-Bacon decomposition; or DiD with no pre-trend evidence when a decision rides on it.
- IV with a weak first stage (F well below ~10 / failing effective-F) OR a clearly violated exclusion restriction. Cite the stat or the violating path.
- RDD with no density/manipulation test, OR a result that flips under reasonable bandwidths, OR identification from a high-order global polynomial.
- Matching/PS/IPW with a positivity/overlap violation, OR residual |SMD|>0.1 on a key confounder, OR balance argued from p-values.
- Time-varying confounding with treatment-confounder feedback handled by ordinary regression/FE instead of a g-method.
- A claimed RCT readout conditioning on post-randomization variables / post-hoc cohort filtering / ignored differential attrition.
- SUTVA violated: RCT or DiD where units demonstrably share a marketplace, social graph, or supply constraint with no spillover estimator (cluster randomization, bipartite design, switchback) — the estimand is undefined.
- Observational causal claim with no sensitivity analysis for unmeasured confounding: no E-value (VanderWeele & Ding 2017, *Ann Intern Med* 167(4):268) or Rosenbaum sensitivity Gamma reported.
- DML/AIPW/TMLE with missing cross-fitting: nuisance models fit on folds that include the target observations, contaminating the moment condition.
- Z-bias / bias amplification: a covariate correlates with treatment and its only plausible path to Y is through T (satisfies IV relevance, fails exclusion); adjusting for it amplifies residual confounding relative to the unadjusted estimate. Block unless the analyst demonstrates an independent direct Y pathway.

Everything else (missing sensitivity/falsification, implicit estimand, untrimmed weights with acceptable overlap, asserted mediation effects) is advisory. A finding with no evidence is advisory by rule.

## 5. Anti-patterns to hunt
- "Controlling for everything" — all available columns into the regression/PS model, conditioning on mediators and colliders (bad-control problem).
- Conditioning on the outcome or its consequence to define the sample (`WHERE converted=true`, survivorship, "active users only", inner-joining only successful rows).
- Narrating a coefficient sign or a tree-model feature importance as a causal effect ("feature X drives churn").
- TWFE DiD on staggered rollouts treated as a clean ATT (negative-weighting trap); DiD justified by a post-period gap alone with no event-study leads.
- RDD with a high-order global polynomial, a hand-picked bandwidth, or no density test, and extrapolating the threshold-local effect to the whole population.
- Weak/convenient instruments with a silent untested exclusion restriction; reporting 2SLS as a population ATE.
- Greedy 1:1 PSM judged "balanced" by non-significant t-tests rather than SMDs (King-Nielsen paradox); ignoring positivity.
- Adjusting time-varying confounders affected by prior treatment with ordinary regression instead of g-methods.
- Adjusting for an instrument or a pre-treatment proxy of treatment, amplifying residual confounding (Z-bias / bias amplification).
- Equating a significant association with a causal effect because the model "has many controls" or "a large N".

## 6. Emit the verdict
One JSON object per `skills/jje-contract/SKILL.md`, written to `iterations/iter-<n>/verdicts/causal-inference-juror.json`. `ran[]`/`skipped[]` honest. `id` = `causal-<check>-<file>:<line>`. Nothing outside the JSON.
