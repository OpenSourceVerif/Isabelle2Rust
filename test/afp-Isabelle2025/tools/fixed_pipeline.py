"""Bounded fixed-request export/compile pipeline for an authorized continuation.

No request is split or regrouped here. Each Rust input is admitted using its
own sealed, closed six-target export result. The global completion checkpoints
remain strict even when the user authorizes partial compilation.
"""
import copy
from collections import deque
from concurrent.futures import ThreadPoolExecutor, FIRST_COMPLETED, wait
import json
import shlex
import sys
import threading

import afp_common as common
import fixed_export as fe
import fixed_plan
import full
from result_store import EntryStore
from scan_store import digest
from state import State


def jobs(plans):
    """Round robin over fixed groups so a large entry cannot starve the rest."""
    queue = deque((entry, iter(sorted(fe.groups(plan).items()))) for entry, plan in plans.items())
    while queue:
        entry, groups = queue.popleft()
        item = next(groups, None)
        if item is None:
            continue
        gid, (context, group) = item
        yield entry, context, group
        queue.append((entry, groups))


def compile_group(base, plan, context, group, run, args, env, optimizer):
    if not run.get("closed") or not fe.check_run(base, run, context, group, require_complete=True):
        raise ValueError("Partial compilation requires a sealed closed export request")
    state = State(base)
    key = "compile-group/" + context["entry"] + "/" + group["id"]
    inputs = {"plan": plan["id"], "group": group["id"], "export": digest(run)}
    saved = state.get(key, {})
    if saved and saved.get("input") != inputs:
        raise ValueError("Compilation progress refers to a different frozen export")
    record = {"full_export": {"mode": "fixed-plan-v2", "runs": [run]}, "full_compile": saved.get("compiled", {})}
    if not full.rust_manifests(record):
        raise ValueError("No successful Rust artifact for compilation")
    def persist():
        state.put(key, {"input": inputs, "compiled": record["full_compile"]})
    full.compile_entry(context["entry"], record, base, args, env, optimizer, persist)
    persist()
    return {"crates": len(record["full_compile"]),
            "closed": sum(full.crate_complete(v) for v in record["full_compile"].values())}


def publish_entry(base, plan, record, scope, entries):
    state = State(base)
    stage = fe.stage_for(plan, record, scope)
    compiled = {}
    for gid, (context, group) in sorted(fe.groups(plan).items()):
        saved = state.get("fixed-progress/" + plan["entry"] + "/" + gid, {})
        if saved.get("plan_id") != plan["id"] or not saved.get("run"):
            raise ValueError("Missing frozen request result during publication")
        run = saved["run"]
        closed = fe.check_run(base, run, context, group)
        if run.get("closed") != closed:
            raise ValueError("Export closure changed before publication")
        stage["runs"].append(run)
        item = state.get("compile-group/" + plan["entry"] + "/" + gid)
        if item:
            expected = {"plan": plan["id"], "group": gid, "export": digest(run)}
            if not closed or item["input"] != expected:
                raise ValueError("Compilation result no longer matches a closed export")
            compiled.update(item["compiled"])
    fe.finish(stage)
    record["full_export"], record["full_compile"] = stage, compiled
    entries[plan["entry"]] = record
    entries.commit(plan["entry"])
    state.put("updated", common.timestamp())
    state.update({}, remove=[*state.keys("fixed-progress/" + plan["entry"] + "/"),
                             *state.keys("compile-group/" + plan["entry"] + "/")])
    print("[published]", plan["entry"], stage["status"], "Rust crates", len(compiled), flush=True)


def execute(base, data, result, exports, args, env, optimizer):
    from continuation import policy
    if not policy(base):
        raise ValueError("Partial compilation requires an explicit continuation policy")
    if args.export_workers <= 0 or args.compile_workers <= 0:
        raise ValueError("Worker limits must be positive")
    fixed_plan.require_gate(base, data, result, exports)
    state = State(base)
    plans = {e: state.get("plan/" + e) for e in data["order"]}
    scans = full.entry_headers(result)
    entries = EntryStore(base, scans, exports)
    remaining, compiling, published = {}, {}, set()
    for entry, plan in plans.items():
        if not plan:
            raise ValueError("Missing frozen plan: " + entry)
        fe.seed_progress(base, plan, entries[entry])
        # Completed compilation is seeded by request, preserving exactly its
        # source group identity; no shared mutable entry writes happen in workers.
        for run in entries[entry].get("full_export", {}).get("runs", []):
            if run.get("closed"):
                manifests = full.rust_manifests({"full_export": {"runs": [run]}})
                old = {m: entries[entry].get("full_compile", {})[m] for m in manifests
                       if m in entries[entry].get("full_compile", {})}
                key = "compile-group/" + entry + "/" + run["group"]
                if old and not state.get(key):
                    state.put(key, {"input": {"plan": plan["id"], "group": run["group"], "export": digest(run)},
                                    "compiled": old})
        remaining[entry], compiling[entry] = len(fe.groups(plan)), 0
    cancel = threading.Event()
    options = copy.copy(args)
    options.cancel_event = cancel
    export_pending, compile_pending, ready = {}, {}, deque()
    slots = deque(range(args.compile_workers))
    source = iter(jobs(plans))
    exhausted = False
    counts = {"requests": sum(remaining.values()), "export_attempted": 0, "export_closed": 0,
              "export_unresolved": 0, "compiled_crates": 0, "compile_closed": 0,
              "entries_published": 0}
    started = common.timestamp()

    def progress(status="running"):
        state.put("fixed-pipeline", {"status": status, "started": started, "updated": common.timestamp(),
                  "meaning": "partial_results_until_global_checkpoints_pass", **counts})

    def publish_ready(entry):
        if not remaining[entry] and not compiling[entry] and entry not in published:
            publish_entry(base, plans[entry], entries[entry], exports[entry], entries)
            published.add(entry)
            counts["entries_published"] += 1

    ep = ThreadPoolExecutor(max_workers=args.export_workers)
    cp = ThreadPoolExecutor(max_workers=args.compile_workers)
    try:
        for entry in plans:
            publish_ready(entry)
        while True:
            while ready and slots:
                entry, context, group, run = ready.popleft()
                slot = slots.popleft()
                future = cp.submit(compile_group, base, plans[entry], context, group, run,
                                   options, full.compilation_environment(env, base, slot), optimizer)
                compile_pending[future] = (entry, slot)
            while not exhausted and len(export_pending) < args.export_workers and len(ready) < 2 * args.compile_workers:
                job = next(source, None)
                if job is None:
                    exhausted = True
                    break
                entry, context, group = job
                future = ep.submit(fe.execute_group, base, plans[entry]["id"], context, group, options, dict(env))
                export_pending[future] = job
            if not export_pending and not compile_pending and not ready and exhausted:
                break
            done, _ = wait([*export_pending, *compile_pending], timeout=50, return_when=FIRST_COMPLETED)
            for future in done:
                value = future.result()
                if future in export_pending:
                    entry, context, group = export_pending.pop(future)
                    remaining[entry] -= 1
                    counts["export_attempted"] += 1
                    counts["export_closed" if value.get("closed") else "export_unresolved"] += 1
                    if value.get("closed") and full.rust_manifests({"full_export": {"runs": [value]}}):
                        compiling[entry] += 1
                        ready.append((entry, context, group, value))
                    publish_ready(entry)
                else:
                    entry, slot = compile_pending.pop(future)
                    slots.append(slot)
                    compiling[entry] -= 1
                    counts["compiled_crates"] += value["crates"]
                    counts["compile_closed"] += value["closed"]
                    publish_ready(entry)
            progress()
        progress("requests_processed")
    except BaseException:
        cancel.set()
        for future in [*export_pending, *compile_pending]:
            future.cancel()
        progress("interrupted")
        raise
    finally:
        ep.shutdown(wait=True, cancel_futures=True)
        cp.shutdown(wait=True, cancel_futures=True)
    if isinstance(result["entries"], EntryStore):
        result["entries"].cache_key = result["entries"].cache_record = None
    return counts


def main():
    from pathlib import Path
    parser = common.arguments(__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--cargo", default="cargo +1.94.0")
    args = parser.parse_args()
    base = args.output_dir.resolve()
    env, _ = common.environment(args)
    env["CARGO"] = args.cargo
    env["RUSTFLAGS"] = (env.get("RUSTFLAGS", "") + " -Awarnings").strip()
    with common.experiment_lock():
        from scan_frozen import validate_contract, active_children
        from continuation import policy
        validate_contract(base, args, env)
        if not policy(base) or args.skip_proofs or active_children(base):
            raise ValueError("Invalid continuation policy, proof configuration or live child")
        data, result, exports = full.load(base)
        full.require_scan_gate(base, result, exports)
        target = base / "_build/optimizer-target"
        prepared = common.command([*shlex.split(args.cargo), "build", "--locked", "--offline",
                   "--manifest-path", str(common.PROJECT / "optimize/Cargo.toml"), "--bin", "cargo-opt",
                   "--target-dir", str(target)], base / "optimizer-build.log", args, env)
        if prepared["status"] != "passed":
            raise ValueError("Optimizer preparation failed: " + prepared["log"])
        counts = execute(base, data, result, exports, args, env, target / "debug/cargo-opt")
        export_gate = full.export_checkpoint(base, data, result, exports)
        compile_gate = full.compile_checkpoint(base, result)
        closed = export_gate["passed"] and compile_gate["passed"]
        State(base).put("pipeline-outcome", {"status": "results_closed" if closed else "incomplete",
                       "finished": common.timestamp(), "export_passed": export_gate["passed"],
                       "compile_passed": compile_gate["passed"], **counts})
        print(json.dumps({"results_closed": closed, **counts}), flush=True)
    import afp
    if closed:
        audit = afp.call(common.HERE / "full_audit.py", ["--output-dir", str(base), "--data-only"])
        if audit:
            return audit
        report = afp.call(common.HERE / "full_report.py", ["--output-dir", str(base)])
        if report:
            return report
        return afp.call(common.HERE / "full_audit.py", ["--output-dir", str(base)])
    afp.call(common.HERE / "full_report.py", ["--output-dir", str(base), "--preview"])
    afp.call(common.HERE / "full_audit.py", ["--output-dir", str(base), "--preview"])
    return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, RuntimeError) as error:
        sys.exit(str(error))
    except KeyboardInterrupt:
        sys.exit(130)
