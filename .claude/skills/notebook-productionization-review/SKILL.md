---
name: notebook-productionization-review
description: The notebook-productionization juror's checklist and exact commands for cold-kernel reproducibility, hidden execution state, parameterization, dtype coercion, unbounded memory, and EDA-to-pipeline refactor quality.
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
---

# notebook productionization review
You review ONLY the engineering quality of the exploratory-notebook to production-pipeline transition (and notebooks scheduled as jobs via papermill/nbclient/Databricks). PRINCIPAL level — hold the bar at what a principal engineer would block, not surface lint. Reason about hidden out-of-order execution state, not cell counts. Stay in lane: you do NOT judge schema-contract compatibility, idempotent re-run/merge keys, warehouse cost/partitioning/file-format, null/dup data-quality, PII/governance, or table-format semantics — flag the notebook-origin defect and defer the downstream concern to its sibling juror.

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD)"
```
Act only on changed .ipynb / .py / .dag artifacts on the pipeline or scheduled-job path.

## 2. Reference specs and canonical tools
- **nbformat v4** (nbformat.readthedocs.io): `execution_count` is null on unexecuted cells and an integer for executed ones; a non-monotonic sequence or null among executed cells is the standard heuristic for out-of-order execution detection.
- **Papermill**: `parameters` cell tag is the standard parameterization contract for notebooks-as-jobs; one cell tagged `parameters` per notebook is the required structure.
- **Ploomber** (`upstream`/`product` declarations): canonical notebook-to-DAG framework; a verbatim EDA cell pasted into a Ploomber task with no function boundary is a first-class EDA-melt defect against this framework's contract.
- **DVC** (`dvc.yaml` pipeline stages): canonical artifact-pinning and pipeline wiring tool alongside notebooks; check for `dvc repro` wiring in CI.
- **Environment pinning**: conda-lock, uv.lock, poetry.lock, and pip-tools `requirements.in`→pinned `requirements.txt` are all valid lockfile forms; absence of any lockfile or image digest on a production-scheduled notebook is a defect.

## 3. Run the checks
Gate every external tool on `command -v`; if absent, add to skipped[], emit one info finding "check skipped: <tool> not installed", and reason statically — never claim a skipped run would pass or fail.

- **Execution-state integrity**: `jq '.cells[] | select(.cell_type=="code") | .execution_count' nb.ipynb` — flag null among executed cells and any non-monotonic/decreasing sequence.
- **Cold-kernel reproducibility**: `command -v jupyter && jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 nb.ipynb`, or `papermill nb.ipynb /tmp/out.ipynb`, or `pytest --nbmake nb.ipynb` / `pytest --nbval-lax`. Clean top-to-bottom execution is the proof. No runner → skipped[] and reason statically.
- **IPython artifact scan**: `grep -nrE '(^%%time|^%%timeit|^%run |^%matplotlib|^%load_ext|get_ipython\(|from IPython|IPython\.display)' <extracted .py and DAG operator files>` — any match in a non-.ipynb production-path file is a hard defect; magic commands and `IPython.display` calls silently error or no-op outside a Jupyter kernel.
- **EDA artifact scan**: `grep -nrE 'warnings\.(filterwarnings|simplefilter)\(.*["\']ignore["\']' <production-path .py>` — silences DeprecationWarning and schema-mismatch warnings in scheduled jobs. `grep -nrE 'plt\.show\(\)' <production-path .py>` — flag occurrences with no preceding `plt.savefig(` or `plt.close(` in scope; hangs headless/non-TTY execution and accumulates memory.
- **Hidden-state tell**: build a cell-order symbol table — flag names referenced before their defining cell in document order, dataframes reassigned in-place across non-adjacent cells. grep tell: variable used in an early cell but `def`/assignment only later.
- **Hardcoded paths**: `git diff "$BASE"...HEAD | grep -nE '/Users/|/home/[a-z]|C:\\\\|/dbfs/|/content/drive|s3://[a-z0-9.-]+/|gs://|abfss://'` — flag personal/local absolute paths on the production path. Flag `os.getcwd()` used to construct data paths — execution-directory-dependent, breaks under orchestrators that set a different CWD. Cross-ref security juror for any credential or token patterns found.
- **Parameterization**: `jq '.cells[] | select(.metadata.tags[]? == "parameters")' nb.ipynb` must return exactly one cell for a notebook-as-job. grep magic constants: `date(2024,...)`, `'2025-01-01'`, thresholds, `n_estimators=`, bucket names mid-body. Flag `os.environ` reads scattered outside a config block.
- **Tests + CI wiring**: find an extracted-module test or testbook/nbmake/nbval config in pyproject/CI. Verify CI wiring: `grep -rE '(nbmake|nbval|papermill|nbconvert.*--execute|testbook)' .github/workflows/ .circleci/ Jenkinsfile azure-pipelines.yml 2>/dev/null` — if no match and notebooks are scheduled as jobs, the library installed is not the same as exercised on commit. Inside productionized code grep: `assert`, `pandera`/`@pa.check_*`/`DataFrameSchema`, `great_expectations`, row-count/`.shape`/`.empty` guards. Absence + only `.head()`/`.describe()`/`display(` = head()-driven correctness.
- **Silent dtype coercion**: `grep -nE 'to_numeric\(.*errors=.(ignore|coerce)|astype\(|read_csv\('` — flag missing `dtype=`/`parse_dates=` on read_csv/read_sql, `errors='coerce'` turning parse failures to NaN, implicit object columns, schema inferred by `read_*` instead of declared, category/precision loss on concat/merge.
- **Unbounded memory**: `grep -nE 'read_csv\(|read_sql\(|read_parquet\(|SELECT \*|\.toPandas\(|\.collect\(\)|pd\.concat\('` — flag full reads with no `chunksize=`/`nrows=`/LIMIT/column projection/predicate. Default blocking threshold when no team envelope is defined: any unguarded read of a source >1M rows or >1GB. Spark `.collect()`/`.toPandas()` on unfiltered frames; concat/append inside a loop (quadratic).
- **Reproducibility/seed**: `grep -niE 'np\.random|random\.|torch\.|tf\.|train_test_split|sample\(|shuffle'` — verify a seed/random_state is set; flag `datetime.now()`/`date.today()`/`time.time()` feeding outputs or filenames in a scheduled run.
- **Serialization**: `grep -nE 'pickle\.(dump|dumps)|joblib\.dump'` on production-path .py — flag objects likely containing lambdas or closures; these are undeserializable outside the original kernel scope and require explicit serialization contracts.
- **Data leakage (ML)**: note the pattern and cross-ref to data-leakage juror; do not issue an independent verdict.
- **EDA-melt / git hygiene**: diff for verbatim exploratory cells in a DAG operator or .py with zero function boundaries, commented-out experiment blocks, dead cells. Committed outputs: `jq '[.cells[].outputs[]?] | length' nb.ipynb` >0 with no nbstripout/jupytext filter.

## 4. Blocking bar
Set blocking:true ONLY when, with cited file:line evidence:
- Notebook or extracted code on the production path does not execute reproducibly from a cold kernel top-to-bottom: committed `execution_count` non-monotonic or null on executed cells (heuristic for out-of-order execution; monotonicity is an inference, not a spec constraint), OR a symbol used before its defining cell in document order — proven hidden out-of-order state. Flagship condition.
- An IPython magic command (`%%time`, `%%timeit`, `%run`, `%matplotlib`, `%load_ext`, `get_ipython()`) or `from IPython`/`IPython.display` import appears in a non-.ipynb production-path file — silently errors or no-ops outside a Jupyter kernel; the single most common notebook-origin defect class.
- Production-scheduled/served code parameterized only by hardcoded magic constants — no papermill `parameters` cell or config object — so a new date/input requires editing source.
- Productionized logic ships with zero tests AND zero runtime data assertions, correctness established only by head()/describe()/display eyeballing AND no notebook-execution step wired in CI (`nbmake`/`nbval`/`papermill` absent from all CI config files) for a scheduled-notebook job.
- A silent dtype coercion that changes values without an error: `errors='coerce'` parse-failure→NaN on a load feeding downstream logic, or implicit int→float/object coercion on a join/concat key, with no assertion guarding the schema.
- Unbounded full-dataset materialization on data exceeding the team in-memory envelope (default fallback when no envelope is defined: >1M rows or >1GB source without chunksize/nrows/LIMIT/pushdown), Spark `.collect()`/`.toPandas()` on an unfiltered frame, or concat-in-loop — OOM the realistic scheduled-run outcome.
- Non-determinism in a scheduled job: unseeded RNG in sampling/splitting/modeling, or now()/today() embedded in results or output filenames.

Everything else is advisory: committed output cells without nbstripout, dead/commented experiment cells, inline-but-reproducible logic not yet extracted, partial RNG coverage where determinism is non-critical, stable labeled magic constants, read_csv without dtype= on small bounded inputs, missing shape invariant where a test already covers the contract, `warnings.filterwarnings('ignore')` only in a dev cell not on the scheduled execution path, `plt.show()` in a notebook cell (not extracted .py), hardcoded personal paths or credential patterns (cross-ref security juror). A finding with no evidence is advisory by rule.

## 5. Emit the verdict
One JSON object per skills/jje-contract/SKILL.md, written to iterations/iter-<n>/verdicts/notebook-productionization-juror.json. ran[]/skipped[] honest, id = nb-<check>-<file>:<line>. Nothing outside the JSON.
