---
type: eval-scorecard
tags: [eval, scorecard]
---
# Eval scorecard (all 3 passes)

38 jurors. **Floor** 38/38 · **Adversarial** 38/38 · **Scale 35/38 recall, 17 false alarms**.
Passes: [[floor-eval]] · [[adversarial-eval]] · [[scale-eval]]. Lever: [[tool-backing]].

Weakest first (scale misses, then false alarms).

| Juror | Lane | Kind | Floor | Adv | Scale recall | Scale FA |
|---|---|---|---|---|---|---|
| **[[terraform]]** | iac | tool | Y | Y | MISS | 1 |
| **[[interface-compat]]** | code | reason | Y | Y | MISS | 0 |
| **[[data-contract]]** | pipeline | tool | Y | Y | MISS | 0 |
| **[[deployment]]** | deploy | reason | Y | Y | caught | 2 |
| **[[model-serving-mlops]]** | machine-learning | reason | Y | Y | caught | 2 |
| **[[dimensional-modeling]]** | data-modeling | reason | Y | Y | caught | 1 |
| **[[semantic-layer-metrics]]** | data-modeling | reason | Y | Y | caught | 1 |
| **[[distributed-compute-spark]]** | data-platforms | reason | Y | Y | caught | 1 |
| **[[orchestration-dag]]** | data-platforms | reason | Y | Y | caught | 1 |
| **[[streaming-eventtime]]** | data-platforms | reason | Y | Y | caught | 1 |
| **[[causal-inference]]** | data-science | reason | Y | Y | caught | 1 |
| **[[experimentation-abtest]]** | data-science | reason | Y | Y | caught | 1 |
| **[[notebook-productionization]]** | data-science | reason | Y | Y | caught | 1 |
| **[[ml-reproducibility]]** | machine-learning | reason | Y | Y | caught | 1 |
| **[[model-evaluation]]** | machine-learning | reason | Y | Y | caught | 1 |
| **[[model-monitoring-drift]]** | machine-learning | reason | Y | Y | caught | 1 |
| **[[governance]]** | pipeline | reason | Y | Y | caught | 1 |
| [[correctness]] | code | tool | Y | Y | caught | 0 |
| [[observability]] | code | reason | Y | Y | caught | 0 |
| [[security]] | code | tool | Y | Y | caught | 0 |
| [[structure]] | code | tool | Y | Y | caught | 0 |
| [[normalization-relational]] | data-modeling | reason | Y | Y | caught | 0 |
| [[slowly-changing-dimensions]] | data-modeling | reason | Y | Y | caught | 0 |
| [[query-performance-sql]] | data-platforms | tool | Y | Y | caught | 0 |
| [[statistical-rigor]] | data-science | reason | Y | Y | caught | 0 |
| [[partitioning-layout]] | datalake | reason | Y | Y | caught | 0 |
| [[storage-format]] | datalake | reason | Y | Y | caught | 0 |
| [[table-format]] | datalake | tool | Y | Y | caught | 0 |
| [[algorithmic-complexity]] | ds-and-algorithms | reason | Y | Y | caught | 0 |
| [[data-structure-selection]] | ds-and-algorithms | reason | Y | Y | caught | 0 |
| [[go-concurrency]] | go | tool | Y | Y | caught | 0 |
| [[go-error-handling]] | go | tool | Y | Y | caught | 0 |
| [[go-performance]] | go | tool | Y | Y | caught | 0 |
| [[data-leakage]] | machine-learning | reason | Y | Y | caught | 0 |
| [[feature-engineering]] | machine-learning | reason | Y | Y | caught | 0 |
| [[cost]] | pipeline | tool | Y | Y | caught | 0 |
| [[data-quality]] | pipeline | tool | Y | Y | caught | 0 |
| [[idempotency]] | pipeline | reason | Y | Y | caught | 0 |

## Misses (3) — see [[scale-eval]]
- [[interface-compat]] (code)
- [[data-contract]] (pipeline)
- [[terraform]] (iac)
