---
name: go-serialization-review
description: The go-serialization juror's checklist and exact tells for encoding/json correctness — struct tag drift, omitempty zero-value semantics, int64 precision loss, and MarshalJSON receiver dispatch.
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
---

# go serialization review
You review ONLY Go encoding/json correctness: struct field json tag completeness and spelling, omitempty zero-value semantics, int64/uint64 precision through float64, and MarshalJSON receiver dispatch. PRINCIPAL level. Stay in lane: json allocation cost on hot paths belongs to go-performance; general interface satisfaction belongs to correctness-review; serialized data confidentiality belongs to security-review.

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD)"
```
Filter to `.go` files. Focus on types carrying `json:"` struct tags or appearing in calls to `json.Marshal`/`json.Unmarshal`/`json.NewEncoder`/`json.NewDecoder`.

## 2. Run the checks
- **SA5008 / go vet structtag — malformed struct tags**: if `command -v staticcheck`; run `staticcheck -checks SA5008 ./...` scoped to changed packages; else if `command -v go`; run `go vet ./...` (includes the built-in `structtag` analyzer); else add to skipped[]+one info finding. SA5008 flags misspelled options, unknown options, and malformed tag syntax; any hit on a json tag in an API-boundary struct is a wire-name or option defect.
- **Missing json tag on exported field**: grep changed `.go` files for exported struct fields (pattern `^\s+[A-Z][A-Za-z0-9]+\s`) adjacent to json-tagged siblings. An untagged exported field marshals under its Go name, silently diverging from the wire contract; intentional exclusions require `json:"-"`.
- **Unexported field with json-tagged siblings**: grep for lowercase-initial fields (`^\s+[a-z][A-Za-z0-9]+\s`) in structs that carry `json:"` on exported fields. encoding/json silently drops unexported fields with no error; if exclusion is unintentional the struct is missing data on the wire.
- **omitempty on zero-value-required fields**: grep `` `json:"[^"]*,omitempty"` `` on fields typed `int`, `int32`, `int64`, `uint*`, `float*`, `bool`, `string`, or non-pointer struct. When the API must distinguish zero from absent, omitempty silently drops the zero value with no error.
- **int64/uint64 without ,string**: grep for `int64` or `uint64` struct fields with a `json:"..."` tag lacking `,string`. Values above 2^53-1 (9007199254740991) lose precision when encoded as JSON numbers via float64. IDs, nanosecond timestamps, and large counters are the common victims; the fix is the `,string` tag option or a dedicated string-typed field.
- **MarshalJSON on pointer receiver with non-pointer call site**: grep changed `.go` files for `func \([A-Za-z]+ \*[A-Z][A-Za-z0-9]+\) MarshalJSON\(\)` (with `*` before the type name). A pointer-receiver MarshalJSON on `*T` is absent from `T`'s method set; callers passing a non-pointer `T` to `json.Marshal` silently get default struct marshaling instead of the custom implementation.

## 3. Blocking bar
Set `blocking:true` (cite file:line and the evidence) ONLY for:
- A `staticcheck SA5008` hit on a json tag in a struct used with `json.Marshal`/`json.Unmarshal` at an API boundary — the tag option is wrong or silently ignored.
- An exported field with no json tag in a struct where other fields carry json tags and the Go field name does not match the intended wire name — silent field rename on the wire.
- `omitempty` on a `bool`, numeric, or non-pointer-struct field where the API contract requires distinguishing zero from absent — zero value silently omitted.
- An `int64` or `uint64` field carrying values above 2^53 (IDs, nanos, large counts) without `,string` — precision loss on every round-trip through float64.
- `MarshalJSON` defined on pointer receiver `*T` where the package passes `T` (non-pointer) — encoding/json never calls it; wrong default output produced silently.
Everything else is advisory: unexported fields intentionally excluded; omitempty on fields where zero truly means absent; int64 fields bounded well below 2^53; missing tag on an internal struct never passed to Marshal. A finding with no evidence is advisory by rule.

## 4. Anti-patterns to hunt
- Any misspelled json option in a struct tag (SA5008 target; `omitempty` misspellings are the most common).
- Exported field in a json-tagged struct with no tag at all — marshals under Go name, not wire name.
- `omitempty` on `int*`, `uint*`, `bool`, `float*`, or value-struct when zero is a valid, required API signal.
- `int64`/`uint64` ID, nanosecond timestamp, or large counter field without `,string` json tag option.
- `func (t *SomeType) MarshalJSON()` where callers always pass `SomeType` (non-pointer) — dispatch zero, wrong output silently.
- Unexported field next to json-tagged exported siblings with no `json:"-"` and no clear intent.
- `json:",omitempty"` on a pointer field that must serialize as `null` when nil rather than be omitted — pointer + omitempty drops the key entirely.

## 5. Emit the verdict
One JSON object per skills/jje-contract/SKILL.md, written to iterations/iter-<n>/verdicts/go-serialization-juror.json. ran[]/skipped[] honest. id = gojson-<check>-<file>:<line>. Nothing outside the JSON.
