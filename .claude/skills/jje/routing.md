# Judge routing logic

Reason over the verdicts. Do not re-review the candidate. Evaluate in order,
first match wins.

1. Any unresolved `blocking` finding that is **fixable within the current plan**
   → **REVISE**. Pass those findings (id + suggested_fix) as `feedback` for the
   Executor.
2. Blocking findings showing the **plan's approach is wrong** (the change cannot
   be made correct without a different approach) → **REPLAN**. Put the why in
   `feedback`.
3. No blocking findings → **ACCEPT**.
4. A blocking finding seen in a prior iteration (the guard's `recurring`), or two
   blocking findings that contradict each other (reviewer A demands X, fixing X
   trips reviewer B), or the iteration budget exhausted → **ESCALATE**.

The guard output is authoritative for rule 4: if `check-guards` returns
`recommend_escalate: true`, you MUST return ESCALATE even if rules 1-3 would
otherwise match. When you detect a contradictory pair yourself, name the two
finding fingerprints so the orchestrator can record it.

REVISE vs REPLAN heuristic: if every blocking finding points at a *defect in the
work* (missing check, bug, wrong predicate) → REVISE. If a finding points at the
*plan itself* (wrong pattern, cannot satisfy the contract) → REPLAN. When unsure,
REVISE once; if the same class of finding survives the fix, REPLAN. That bounds
wasted replans.

Return exactly:
```json
{"decision": "REVISE", "rationale": "...", "feedback": "...",
 "unresolved": ["sec-001"], "contradictions": []}
```
No prose outside the JSON.
