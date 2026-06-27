---
name: slowly-changing-dimensions-review
description: The slowly-changing-dimensions juror's checklist and exact checks for SCD temporal integrity, as-of join correctness, change-detection, and history preservation.
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
---

# slowly-changing-dimensions review
You review ONLY the temporal integrity of dimension history and as-of correctness — SCD modeling and the time-variant join paths that consume it, NOT generic data quality. PRINCIPAL level — hold the bar at what a principal engineer would block, not surface lint. Stay in lane.

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD)"
```
Detect the relevant artifacts: dbt snapshots (`snapshots/*.sql`, `{% snapshot %}`), dim/MERGE SQL models, dimension DDL, feature-engineering SQL/notebooks (.ipynb), Feast/Tecton/Hopsworks/Databricks point-in-time configs, fact-load surrogate-lookup SQL. Review only those.

## 2. Context to load
If the orchestrator passed PROJECT CONVENTIONS (from .jje/conventions), treat its blocking rules as additional blocking bars. From the repo, load where present: the per-dimension (ideally per-attribute) declared SCD type; canonical metadata column names (valid_from/valid_to/is_current/dbt_valid_from/dbt_valid_to/inferred_member_flag); open-end sentinel convention (NULL vs 9999-12-31) and effective-timestamp timezone/grain; which dims are Type-2 history-bearing vs Type-1 current-only; surrogate/durable/natural-key strategy and how facts bind to versions; the change-detection mechanism and its declared tracked-column list; late/early-arriving and inferred-member policy; per-source hard-delete policy; consumers' as-of semantics (ML label timestamp column, BI current-vs-as-was). Without a declared type, reason from analytic intent and flag the missing standard advisory.

## 3. Run the checks (gate any external tool on `command -v`; missing -> skipped[] + one info finding; never infer)
Mostly reasoning-led inspection of SQL/snapshots/notebooks; if you run a SQL engine or linter, gate it first.
- Overlap/gap audit (core invariant): read/derive a window check — `lead(valid_from) over (partition by durable_key order by valid_from)` vs `valid_to`; any `valid_to <> lead(valid_from)` is a gap or overlap. Expect a tested assertion (dbt/data test); block if a history table ships without one.
- One-current-row: `select durable_key,count(*) from dim where is_current group by 1 having count(*)>1` must be empty; open rows (`valid_to is null`) must equal distinct active keys. Confirm a singleton/uniqueness test exists.
- Flag/date consistency: hunt rows where `is_current=true and valid_to is not null/<>sentinel`, or `is_current=false and valid_to is null` (post-partial-MERGE desync).
- MERGE/snapshot diff: read `when matched then update` — if it updates ATTRIBUTE columns on a Type-2 dim instead of only closing the prior row (set valid_to/is_current) and inserting a new row, that is destructive history loss. Grep tells: `create or replace table .*dim`, `truncate`, `delete from .*dim`, `update .*dim .* set <attribute>`.
- Hash/change-set: locate the hashdiff (grep `md5(`, `sha`, `hashdiff`, `hash_diff`, `dbt_scd_id`, `check_cols`, `concat(`) and diff its column list vs the declared Type-2 set. Flag load-audit columns inside it (`loaded_at`, `_etl_ts`, `ingestion_id` -> guaranteed explosion) and missing tracked business columns (silent loss). Verify each column is `coalesce(cast(x as string),'')` plus a non-collidable separator; flag bare delimiter-less `concat`.
- dbt snapshot config: confirm `strategy` (timestamp vs check) matches source `updated_at` reliability; `unique_key` is the durable key; timestamp `updated_at` is monotonic source-driven (NOT `current_timestamp`); `check_cols='all'` vs explicit list matches intent; `hard_deletes`/`invalidate_hard_deletes` set deliberately; snapshots live in a dedicated schema with no joins/transform logic.
- Point-in-time join: read every fact->Type-2-dim join. Bug tell is `join dim on fact.key=dim.key and dim.is_current=true` (or no temporal predicate) for historical/feature analysis. Correct: load-time surrogate binding, or `... and fact.event_ts >= dim.valid_from and fact.event_ts < dim.valid_to`. Flag inclusive `<= valid_to` / `between valid_from and valid_to` (boundary fan-out).
- ML as-of leakage: in feature SQL/notebooks/feature-store configs, verify the as-of join takes the latest `feature.valid_from <= label.event_ts` and never `valid_from > label.event_ts`; flag a current-state dimension join into a training set (future leakage).
- Late/inferred member: trace the fact-load surrogate lookup (grep `inferred`, `unknown member`, `-1`, `placeholder`). Confirm an inferred-member insert path exists, resolution is a Type-1 overwrite + clears the inferred flag (NOT a new Type-2 version), and facts are not silently dropped when the key is absent.
- Type-2 explosion smell: scan Type-2 column lists for volatile/continuous attributes (counts, balances, scores, ages, last_seen, cumulative metrics). If history exists, `select durable_key,count(*) v from dim group by 1 order by v desc limit 20` to spot pathological version counts.
- Retroactive change: for back-dated effective dates, confirm the load can insert a version BETWEEN existing ones and re-stitch neighbors' valid_to/valid_from (and re-point affected fact surrogates), not just append to the open row.

## 4. Blocking bar
Set blocking:true ONLY when, with cited file:line evidence:
- History destruction: a Type-2/history-bearing dim loaded via a path that overwrites or deletes prior versions — in-place UPDATE of closed-row attributes, CREATE OR REPLACE / TRUNCATE+reload, or a MERGE that updates instead of close-and-insert.
- Broken temporal interval: demonstrable gaps/overlaps in [valid_from, valid_to) per durable key, >1 is_current row per key, or is_current desynced from valid_to — AND no automated test guards the invariant.
- Point-in-time incorrectness in a consuming join: facts/labels joined to the current row (is_current) or with no event-time predicate for historical/feature analysis, inclusive double-bounded BETWEEN fan-out, or an ML as-of join admitting feature versions with valid_from after the label timestamp (future leakage).
- Change-detection corruption: load-audit timestamps inside the Type-2 hashdiff (spurious version per run), a tracked business attribute missing from the diff (silent loss), delimiter-less collidable concat, or `current_timestamp`-based updated_at in a timestamp-strategy snapshot.
- Inferred/late-arriving mishandling: facts dropped or dumped to an unknown member when an inferred placeholder is correct, OR placeholder resolution via a false Type-2 version instead of a Type-1 overwrite.
- Silent SCD-type change vs the standard: a Type-2 attribute demoted to Type-1, or a Type-0 original-value attribute pulled into the change set, without sign-off.
- Hard-deletes non-deliberate: source deletions silently vanish from a history dim with no close-out or tombstone policy.
Everything else advisory: volatile attributes that should be a Type-4 mini-dimension; effective-grain coarser than fact cadence; sentinel inconsistency across dims; missing durable key separate from surrogate; no fact-side surrogate captured at load; snapshots with joins/transforms or shared schema; Type-3 where full history is needed; missing natural_key+valid_from uniqueness test. A finding with no evidence is advisory by rule.

## 5. Anti-patterns to hunt
- `is_current=true` join attributing historical facts/labels to dimension context (revisionist history / leakage).
- `BETWEEN valid_from AND valid_to` inclusive-both-bounds as-of join (duplicate rows at every boundary).
- Overwriting a Type-2 attribute in place to "fix" a value (loses as-was) — or the reverse: a new version for a correction that should be a restatement.
- Audit/load columns (loaded_at, batch_id, _ingested_at) inside the change-detection hash ("dimension doubles every night").
- Delimiter-less hash concatenation and unnormalized NULLs (boundary collisions, missed/false changes).
- Full-refresh (CREATE OR REPLACE / dbt full-refresh) of a snapshot/history table, erasing accumulated history.
- Dropping facts (or routing to a generic unknown member) when the key hasn't arrived, instead of an inferred member resolved later.
- Resolving an inferred placeholder with a new Type-2 row, dating the change to load time instead of Type-1 overwriting.
- Gaps (valid_to=change_date but next valid_from=change_date+1) dropping boundary-day events; or overlaps where both versions claim the boundary instant.
- More than one open/current row per key after a partial MERGE; is_current not maintained in lockstep with valid_to.
- Fast-moving numeric attributes (balance, score, count, age) embedded directly in a Type-2 row (version explosion a mini-dimension would prevent).
- timestamp-strategy snapshot keyed on `current_timestamp()`/load time rather than a source `updated_at`.
- Source hard-deletes silently disappearing with no close-out or tombstone.
- Back-dated source change appended to the latest open row instead of inserted in chronological position with neighbors and affected fact keys re-stitched.

## 6. Emit the verdict
One JSON object per skills/jje-contract/SKILL.md, written to iterations/iter-<n>/verdicts/slowly-changing-dimensions-juror.json. ran[]/skipped[] honest. id = `scd-<check>-<file>:<line>`. Nothing outside the JSON.
