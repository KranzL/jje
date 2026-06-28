---
type: concept
tags: [concept, key-lever]
---
# Tool-backing (the single biggest lever)

A reviewer that runs an executable check and cites its output beats one that
reasons from the diff. Two independent lines of evidence say this is *the* lever:

1. **Research** (the 2026 correlated-errors result): a panel of same-family LLM
   judges gives far fewer effective independent votes than its headcount. Since
   every juror is Claude, their real independence comes from **distinct tools and
   evidence**, not from being different models. See [[agent-design]].
2. **Our own [[scale-eval]]**: the 3 recall misses were all **un-tool-backed**
   lanes ([[interface-compat]], [[data-contract]], [[terraform]]), and
   [[terraform]] missed *only* because checkov/trivy weren't installed — the same
   juror aced the isolated fixture. The tool-backed lanes were clean on recall
   *and* false alarms.

> [!takeaway] The reasoning-only review loses the needle under noise and
> over-flags ambiguous code; the tool finds the defect regardless of burial and
> grounds the verdict.

**Implication (active in [[hot|the hot cache]]):** tool-back the soft lanes —
interface-compat → an API-differ, data-contract → a schema/precision diff,
terraform → require its scanners. For irreducibly-judgment lanes, add an
adversarial refutation pass and explicit anti-pattern criteria.
