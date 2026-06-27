#!/usr/bin/env python3
"""
JJE deterministic state machine + safety helper.

All loop-state mutations that must be trustworthy (the iteration counter, the
finding-id ledger, the oscillation guard, the CI-result artifact, the
COMMIT_APPROVED marker) live here rather than in the orchestrating model's
head. The /jje skill calls these subcommands; it never hand-edits the JSON.

Run dir layout (.jje/runs/<run-id>/):
  run.json                         run metadata + authoritative iteration counter
  plan.json                        current plan (Planner writes; replan keeps prior as plan-v<n>.json)
  seating.json                     jurors seated for the current cycle (orchestrator writes)
  ledger.json                      finding fingerprint ledger for the oscillation guard
  iterations/iter-<n>/
      self-report.json             Executor self-report
      candidate.diff               snapshot of the candidate diff
      verdicts/<juror>.json        one verdict per juror (each juror writes its own)
      decision.json                Judge decision {decision, rationale, feedback, unresolved, contradictions}
      ci-result.json               CI command + exit code + sha (written by `ci`; validated by `accept`)
      executor-spawns              plain int, maintained by the loop-guard hook (model-independent cap)
  ESCALATION.md                    written on ESCALATE
(.jje root)
  ACTIVE                           run lock; serializes runs and arms the commit gate
  COMMIT_APPROVED                  written only by `accept` after Judge ACCEPT + validated green CI; consumed by the hook
"""
import argparse, hashlib, json, os, re, sys, time, datetime, glob, subprocess

ROOT = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
JJE = os.path.join(ROOT, ".jje")
RUNS = os.path.join(JJE, "runs")
ACTIVE = os.path.join(JJE, "ACTIVE")
MARKER = os.path.join(JJE, "COMMIT_APPROVED")

# A CI result older than this (seconds) is treated as stale and will not gate a commit.
CI_FRESHNESS_SECONDS = 3600
TERMINAL = ("escalated", "committed")


def _load(p, default=None):
    if not os.path.exists(p):
        return default
    with open(p) as f:
        return json.load(f)


def _save(p, obj):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        json.dump(obj, f, indent=2)
        f.write("\n")


def _config():
    return _load(os.path.join(JJE, "config.json"),
                 _load(os.path.join(JJE, "config.example.json"), {})) or {}


def _run_dir(run_id):
    # Accept either a bare run id or a full/relative run dir path.
    if os.path.isabs(run_id) or run_id.startswith(".jje") or os.path.sep in run_id:
        return run_id
    return os.path.join(RUNS, run_id)


def _emit(obj):
    print(json.dumps(obj, indent=2))


def _die(msg, code=3):
    _emit({"error": msg})
    sys.exit(code)


# Required keys for a minimally well-formed verdict (the load-bearing subset of
# the verdict contract). A verdict missing these, or with non-list findings, is
# treated as malformed and fails safe in check-guards.
def _load_verdict(vp):
    try:
        with open(vp) as f:
            v = json.load(f)
    except Exception as e:
        return None, f"unparseable JSON ({e.__class__.__name__})"
    if not isinstance(v, dict):
        return None, "verdict is not a JSON object"
    for k in ("juror", "category", "findings", "ran", "skipped"):
        if k not in v:
            return None, f"missing required field '{k}'"
    if not isinstance(v["findings"], list):
        return None, "'findings' is not a list"
    for fnd in v["findings"]:
        if not isinstance(fnd, dict) or "blocking" not in fnd:
            return None, "a finding is missing the 'blocking' field"
    return v, None


def _cleanup_worktree(run):
    """Best-effort removal of a run's worktree (used on close, after a merge)."""
    wt = os.path.join(ROOT, run.get("worktree", "")) if run.get("worktree") else ""
    if wt and os.path.isdir(wt):
        subprocess.run(["git", "-C", ROOT, "worktree", "remove", "--force", wt],
                       capture_output=True)
    br = run.get("scratch_branch", "")
    if br:
        subprocess.run(["git", "-C", ROOT, "branch", "-D", br], capture_output=True)


def _fingerprint(category, finding):
    """Stable identity of a finding across iterations: severity-independent,
    line-tolerant. A finding is 'the same' if its lane + check + file +
    normalized message match. This is what the oscillation guard keys on."""
    issue = re.sub(r"\d+", "#", (finding.get("issue") or "").lower())
    issue = re.sub(r"\s+", " ", issue).strip()
    f = finding.get("evidence", "") or ""
    file_ref = ""
    m = re.search(r"([\w./-]+\.\w+):(\d+)", f + " " + (finding.get("issue") or ""))
    if m:
        file_ref = m.group(1)  # file only, not line, so a shifted line still matches
    key = f"{category}|{finding.get('check','')}|{file_ref}|{issue}"
    return "f-" + hashlib.sha1(key.encode()).hexdigest()[:12]


# ---------------------------------------------------------------- init
def cmd_init(a):
    os.makedirs(RUNS, exist_ok=True)
    # Serialize runs: one active JJE run per repo so the single COMMIT_APPROVED
    # marker and the loop-guard's "newest run" resolution can never cross runs.
    if os.path.exists(ACTIVE) and not a.force:
        cur = _load(ACTIVE, {})
        _die(f"a JJE run is already active ({cur.get('run_id')}); "
             f"finish it (close/escalate) or pass --force", code=4)
    cfg = _config()
    run_id = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    slug = re.sub(r"[^a-z0-9]+", "-", a.request.lower())[:24].strip("-")
    if slug:
        run_id = f"{run_id}-{slug}"
    rd = _run_dir(run_id)
    branch = f"jje/{run_id}"
    run = {
        "run_id": run_id,
        "request": a.request,
        "budget": a.budget if a.budget is not None else cfg.get("default_budget", 6),
        "iteration": 0,
        "status": "planning",
        "scratch_branch": branch,
        "worktree": os.path.join(".jje", "worktrees", run_id),
        "base_ref": a.base or "HEAD",
        "ci_command": cfg.get("ci_command", "make ci"),
        "escalation_policy": cfg.get("escalation_policy", "stop"),
        "created_at": datetime.datetime.now().isoformat(timespec="seconds"),
    }
    _save(os.path.join(rd, "run.json"), run)
    _save(os.path.join(rd, "ledger.json"), {"findings": {}, "contradictions": []})
    os.makedirs(os.path.join(rd, "iterations"), exist_ok=True)
    _save(ACTIVE, {"run_id": run_id, "run_dir": rd, "armed_at": time.time()})
    _emit({"run_id": run_id, "run_dir": rd, "scratch_branch": branch,
           "worktree": run["worktree"], "base_ref": run["base_ref"],
           "budget": run["budget"], "ci_command": run["ci_command"]})


# ---------------------------------------------------------------- iteration counter (authoritative)
def cmd_start_iteration(a):
    rd = _run_dir(a.run)
    run = _load(os.path.join(rd, "run.json"))
    if run is None:
        _die("no such run")
    if run["iteration"] >= run["budget"]:
        _emit({"blocked": True, "reason": "iteration_budget_exhausted",
               "iteration": run["iteration"], "budget": run["budget"],
               "action": "ESCALATE"})
        sys.exit(2)  # non-zero so the orchestrator must branch to escalate
    run["iteration"] += 1
    run["status"] = "executing"
    _save(os.path.join(rd, "run.json"), run)
    it = run["iteration"]
    os.makedirs(os.path.join(rd, "iterations", f"iter-{it}", "verdicts"), exist_ok=True)
    _emit({"iteration": it, "budget": run["budget"],
           "remaining": run["budget"] - it})


# ---------------------------------------------------------------- guards (oscillation + budget)
def cmd_check_guards(a):
    """Run after the jury verdicts land and before the Judge step. Folds the
    current iteration's BLOCKING findings into the ledger, then reports any
    fingerprint seen in >1 iteration (recurrence) plus the remaining budget.
    `recommend_escalate` is the hard backstop the orchestrator must honor."""
    rd = _run_dir(a.run)
    run = _load(os.path.join(rd, "run.json"))
    it = run["iteration"]
    ledger = _load(os.path.join(rd, "ledger.json"))
    vdir = os.path.join(rd, "iterations", f"iter-{it}", "verdicts")
    current = []
    malformed = []
    for vp in sorted(glob.glob(os.path.join(vdir, "*.json"))):
        juror_name = os.path.basename(vp)[:-5]
        v, err = _load_verdict(vp)
        if err:
            # Fail SAFE: a malformed or schema-invalid verdict is itself treated
            # as a blocking finding, so the loop never silently routes on corrupt
            # data and never crashes on bad JSON.
            fnd = {"id": f"malformed-{juror_name}", "check": "verdict-validation",
                   "severity": "error", "blocking": True,
                   "issue": f"verdict from {juror_name} is invalid: {err}",
                   "evidence": vp}
            current.append((_fingerprint("malformed", fnd), fnd, juror_name))
            malformed.append({"juror": juror_name, "error": err})
            continue
        for fnd in v.get("findings", []):
            if not fnd.get("blocking"):
                continue
            fp = _fingerprint(v.get("category", v.get("juror", "?")), fnd)
            current.append((fp, fnd, v.get("juror")))
    recurring = []
    for fp, fnd, juror in current:
        entry = ledger["findings"].setdefault(
            fp, {"id": fnd.get("id"), "issue": fnd.get("issue"),
                 "juror": juror, "iterations": []})
        if it not in entry["iterations"]:
            entry["iterations"].append(it)
        if len(entry["iterations"]) >= 2:
            recurring.append({"fingerprint": fp, "id": entry["id"],
                              "issue": entry["issue"], "juror": juror,
                              "iterations": entry["iterations"]})
    _save(os.path.join(rd, "ledger.json"), ledger)
    escalate = bool(recurring) or bool(ledger["contradictions"]) \
        or run["iteration"] >= run["budget"]
    _emit({"iteration": it, "blocking_now": len(current),
           "malformed": malformed,
           "recurring": recurring, "contradictions": ledger["contradictions"],
           "budget_remaining": run["budget"] - it,
           "recommend_escalate": escalate})


def cmd_record_contradiction(a):
    """The Judge calls this when it sees an irreconcilable pair: reviewer A
    demands X, fixing X trips reviewer B. Forces ESCALATE on the next guard
    check so the loop never thrashes on it."""
    rd = _run_dir(a.run)
    ledger = _load(os.path.join(rd, "ledger.json"))
    ledger["contradictions"].append(
        {"a": a.a, "b": a.b, "note": a.note,
         "iteration": _load(os.path.join(rd, "run.json"))["iteration"]})
    _save(os.path.join(rd, "ledger.json"), ledger)
    _emit({"recorded": True, "contradictions": ledger["contradictions"]})


# ---------------------------------------------------------------- decision routing
def cmd_record_decision(a):
    rd = _run_dir(a.run)
    run = _load(os.path.join(rd, "run.json"))
    it = run["iteration"]
    dp = os.path.join(rd, "iterations", f"iter-{it}", "decision.json")
    decision = a.decision.upper()
    if decision not in ("ACCEPT", "REVISE", "REPLAN", "ESCALATE"):
        _die(f"illegal decision {decision}")
    _save(dp, {"iteration": it, "decision": decision,
               "feedback": a.feedback, "ts": time.time()})
    run["status"] = {"ACCEPT": "accepted", "REVISE": "revising",
                     "REPLAN": "replanning", "ESCALATE": "escalated"}[decision]
    _save(os.path.join(rd, "run.json"), run)
    _emit({"iteration": it, "decision": decision, "status": run["status"]})


# ---------------------------------------------------------------- CI (decoupled from the model)
def cmd_ci(a):
    """Run the configured CI command on the candidate and record a verifiable
    artifact. `accept` validates this artifact, so the gate does not depend on
    the orchestrating model truthfully reporting that CI passed."""
    rd = _run_dir(a.run)
    run = _load(os.path.join(rd, "run.json"))
    if run is None:
        _die("no such run")
    it = run["iteration"]
    wt = os.path.join(ROOT, run["worktree"])
    cmd = a.command or run.get("ci_command") or "make ci"
    try:
        sha = subprocess.run(["git", "-C", wt, "rev-parse", "HEAD"],
                             capture_output=True, text=True).stdout.strip()
    except Exception:
        sha = ""
    proc = subprocess.run(cmd, shell=True, cwd=wt, capture_output=True, text=True)
    result = {"command": cmd, "exit_code": proc.returncode, "sha": sha,
              "branch": run["scratch_branch"], "ts": time.time(),
              "stdout_tail": proc.stdout[-2000:], "stderr_tail": proc.stderr[-2000:]}
    _save(os.path.join(rd, "iterations", f"iter-{it}", "ci-result.json"), result)
    _emit({"exit_code": proc.returncode, "green": proc.returncode == 0, "sha": sha,
           "next": "accept" if proc.returncode == 0 else "REVISE (CI failed; counts against budget)"})
    sys.exit(0 if proc.returncode == 0 else 2)


# ---------------------------------------------------------------- final gate markers
def cmd_accept(a):
    """Called only after Judge ACCEPT. Validates the CI artifact (exit 0, sha
    present, fresh) before writing the COMMIT_APPROVED marker the PreToolUse
    hook requires. No valid CI artifact => no marker, regardless of status."""
    rd = _run_dir(a.run)
    run = _load(os.path.join(rd, "run.json"))
    if run is None:
        _die("no such run")
    if run["status"] != "accepted":
        _die("run not in accepted state; record-decision ACCEPT first")
    it = run["iteration"]
    ci = _load(os.path.join(rd, "iterations", f"iter-{it}", "ci-result.json"))
    if not ci:
        _die("no ci-result.json for this iteration; run `ci` first (CI is the final gate)")
    if ci.get("exit_code") != 0:
        _die(f"CI did not pass (exit {ci.get('exit_code')}); cannot mint commit marker")
    if not ci.get("sha"):
        _die("ci-result has no sha; refusing to approve")
    if time.time() - ci.get("ts", 0) > CI_FRESHNESS_SECONDS:
        _die("ci-result is stale; re-run `ci` on the current candidate")
    _save(MARKER, {"run_id": run["run_id"], "iteration": it,
                   "scratch_branch": run["scratch_branch"],
                   "ci_sha": ci["sha"], "approved_at": time.time()})
    run["status"] = "ci_green"
    _save(os.path.join(rd, "run.json"), run)
    _emit({"committable": True, "marker": MARKER, "ci_sha": ci["sha"]})


def cmd_escalate(a):
    rd = _run_dir(a.run)
    run = _load(os.path.join(rd, "run.json"))
    ledger = _load(os.path.join(rd, "ledger.json"))
    open_findings = [v for v in ledger["findings"].values()
                     if len(v["iterations"]) >= 1]
    lines = [f"# JJE escalation: {run['run_id']}", "",
             f"Request: {run['request']}",
             f"Scratch branch (candidate): `{run['scratch_branch']}`",
             f"Worktree: `{run['worktree']}`",
             f"Iterations used: {run['iteration']}/{run['budget']}",
             f"Policy: {run.get('escalation_policy', 'stop')}",
             f"Reason: {a.reason}", "", "## Open findings"]
    for f in open_findings:
        lines.append(f"- [{f.get('juror')}] {f.get('id')}: {f.get('issue')} "
                     f"(seen in iters {f['iterations']})")
    if ledger["contradictions"]:
        lines += ["", "## Contradictory pairs"]
        for c in ledger["contradictions"]:
            lines.append(f"- {c['a']} <-> {c['b']}: {c['note']}")
    with open(os.path.join(rd, "ESCALATION.md"), "w") as fh:
        fh.write("\n".join(lines) + "\n")
    run["status"] = "escalated"
    _save(os.path.join(rd, "run.json"), run)
    _clear_active(run["run_id"])
    _emit({"escalated": True, "report": os.path.join(rd, "ESCALATION.md"),
           "candidate_branch": run["scratch_branch"]})


def _clear_active(run_id):
    cur = _load(ACTIVE)
    if cur and cur.get("run_id") == run_id and os.path.exists(ACTIVE):
        os.remove(ACTIVE)


def cmd_close(a):
    """Release the run lock after a successful merge/commit or manual wrap-up.
    Marks the run committed/closed so a new JJE run can start."""
    rd = _run_dir(a.run)
    run = _load(os.path.join(rd, "run.json"))
    cleaned = False
    if run is not None:
        run["status"] = a.status or "committed"
        _save(os.path.join(rd, "run.json"), run)
        _clear_active(run["run_id"])
        if not a.keep_worktree:
            _cleanup_worktree(run)   # GC: the run is done, the candidate is merged
            cleaned = True
    if os.path.exists(MARKER):
        os.remove(MARKER)
    _emit({"closed": True, "status": run["status"] if run else None,
           "worktree_removed": cleaned})


def cmd_status(a):
    rd = _run_dir(a.run)
    run = _load(os.path.join(rd, "run.json"))
    if run is None:
        _die("no such run")
    ledger = _load(os.path.join(rd, "ledger.json"), {"findings": {}, "contradictions": []})
    open_finding_count = len([v for v in ledger["findings"].values()
                              if len(v["iterations"]) >= 1])
    _emit({"iteration": run["iteration"], "budget": run["budget"],
           "status": run["status"], "open_finding_count": open_finding_count})


def main():
    p = argparse.ArgumentParser(prog="jje_state")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("init"); s.add_argument("--request", required=True)
    s.add_argument("--budget", type=int); s.add_argument("--base")
    s.add_argument("--force", action="store_true")
    s.set_defaults(fn=cmd_init)

    s = sub.add_parser("start-iteration"); s.add_argument("--run", required=True)
    s.set_defaults(fn=cmd_start_iteration)

    s = sub.add_parser("check-guards"); s.add_argument("--run", required=True)
    s.set_defaults(fn=cmd_check_guards)

    s = sub.add_parser("record-contradiction"); s.add_argument("--run", required=True)
    s.add_argument("--a", required=True); s.add_argument("--b", required=True)
    s.add_argument("--note", default=""); s.set_defaults(fn=cmd_record_contradiction)

    s = sub.add_parser("record-decision"); s.add_argument("--run", required=True)
    s.add_argument("--decision", required=True); s.add_argument("--feedback", default="")
    s.set_defaults(fn=cmd_record_decision)

    s = sub.add_parser("ci"); s.add_argument("--run", required=True)
    s.add_argument("--command", default=""); s.set_defaults(fn=cmd_ci)

    s = sub.add_parser("accept"); s.add_argument("--run", required=True)
    s.set_defaults(fn=cmd_accept)

    s = sub.add_parser("escalate"); s.add_argument("--run", required=True)
    s.add_argument("--reason", default=""); s.set_defaults(fn=cmd_escalate)

    s = sub.add_parser("close"); s.add_argument("--run", required=True)
    s.add_argument("--status", default=""); s.add_argument("--keep-worktree", action="store_true")
    s.set_defaults(fn=cmd_close)

    s = sub.add_parser("status"); s.add_argument("--run", required=True)
    s.set_defaults(fn=cmd_status)

    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
