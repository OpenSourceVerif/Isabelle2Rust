"""Run entry-local scan, plan and export, followed by six-language compilation."""
from collections import Counter, deque
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
import copy
import csv
import json
import os
from pathlib import Path
import shlex
import signal
import sys
import threading
import time

import afp_common as common
import dependency_plan as dp
import entry_audit as checks
import fixed_export
import fixed_pipeline
import full
import scan_frozen
from result_store import EntryStore
from scan_store import Store, digest
from state import State
import target_compile


def optimizer_path(base):
    return base / "_build/optimizer-target/debug/cargo-opt"


def prepare_optimizer(base, args, env):
    optimizer = optimizer_path(base)
    command = [*shlex.split(args.cargo), "build", "--locked", "--offline",
               "--manifest-path", str(common.PROJECT / "optimize/Cargo.toml"),
               "--bin", "cargo-opt", "--target-dir", str(optimizer.parent.parent)]
    result = common.command(command, base / "optimizer-build.log", args, env)
    if result["status"] != "passed" or not optimizer.is_file():
        raise ValueError("Optimizer preparation failed: " + result["log"])
    return optimizer


def seed_compilation(base, plan, record):
    state = State(base)
    for run in record.get("full_export", {}).get("runs", []):
        if not run["closed"]:
            continue
        manifests = full.rust_manifests({"full_export": {"runs": [run]}})
        compiled = {m: record["full_compile"][m] for m in manifests if m in record.get("full_compile", {})}
        key = "compile-group/" + plan["entry"] + "/" + run["group"]
        if compiled and not state.get(key):
            state.put(key, {"input": {"plan": plan["id"], "group": run["group"], "export": digest(run)},
                            "compiled": compiled})


def execute(base, data, units, metadata, selected, phase, args, env):
    store = Store(base)
    state = store.state
    selected = set(selected)
    scanning = phase in {"run", "scan"}
    planning = phase in {"run", "plan"}
    exporting = phase in {"run", "export"}
    compiling = phase in {"run", "compile"}
    limits = {"scan": 1, "plan": args.plan_workers, "export": args.export_workers,
              "compile": args.compile_workers}
    if min(limits.values()) < 1:
        raise ValueError("Plan, export and compile worker limits must be positive")
    ordered = scan_frozen.ordered_sessions(data, units, selected) if scanning else []
    scan_queue = deque(ordered)
    plan_queue, export_queue, compile_queue = deque(), deque(), deque()
    pending, failures, active, errors = {}, {}, {}, []
    optimizer = None
    optimizer_state = "pending"
    counts = Counter()
    tool_generation = state.get("tool-generation", {})
    scans, scopes = {}, {}
    entries = EntryStore(base, scans, scopes)
    options = copy.copy(args)
    cancel = options.cancel_event = threading.Event()
    runtime = {"experiment": dp.ENTRY_PIPELINE, "pid": os.getpid(),
               "identity": common.process_identity(os.getpid()), "command": sys.argv,
               "started": common.timestamp()}
    last_write = 0

    def progress(status="running"):
        nonlocal last_write
        if status != "running" or time.monotonic() - last_write >= 10:
            state.put("driver-state.json", {**runtime, "status": status, "phase": phase,
                      "updated": common.timestamp(), "counts": dict(counts), "errors": errors})
            last_write = time.monotonic()

    def problem(label, error):
        errors.append({"job": label, "reason": str(error)})
        print("[blocked]", label, str(error), flush=True)

    def admit(entry):
        if phase == "scan":
            return
        try:
            scans[entry], scopes[entry], expected, issues = checks.scan_input(store, data, units, metadata, entry)
            if expected is None:
                problem(entry + " scan", ", ".join(issues))
                return
            published = state.get("published/" + entry, {})
            if phase == "run" and published.get("complete") and state.get("entry/" + entry):
                counts["entries_resumed"] += 1
                return
            active[entry] = {"expected": expected, "exports": 0, "compiles": 0}
            plan_queue.append(entry)
        except checks.EVIDENCE_ERRORS as error:
            problem(entry + " scan", error)

    def publish(entry):
        work = active[entry]
        if work["exports"] or work["compiles"]:
            return
        plan = work["plan"]
        try:
            def validate(record):
                _, scope, current, issues = checks.scan_input(Store(base), data, units, metadata, entry)
                if current != work["expected"] or scope != scopes[entry]:
                    raise ValueError("Scan input changed before publication: " + ", ".join(issues))
                return checks.publication(base, plan, current, record, optimizer_path(base), compiling)

            fixed_pipeline.publish_entry(base, plan, entries[entry], scopes[entry], entries, validate)
            counts["entries_published"] += 1
        except checks.EVIDENCE_ERRORS as error:
            problem(entry + " publication", error)
        del active[entry]

    def start_groups(entry, plan):
        work = active[entry]
        work["plan"] = plan
        if not (exporting or compiling):
            del active[entry]
            return
        record = entries[entry]
        seed_compilation(base, plan, record)
        fixed_export.seed_progress(base, plan, record)
        groups = fixed_export.groups(plan)
        work["exports"] = len(groups)
        export_queue.append((entry, iter(groups.values())))
        publish(entry)

    def read_export(entry, context, group):
        saved = state.get("fixed-progress/" + entry + "/" + group["id"], {})
        if saved.get("plan_id") != active[entry]["plan"]["id"] or not saved.get("run"):
            raise ValueError("Missing export for compilation: " + group["id"])
        run = saved["run"]
        if run["closed"] != fixed_export.check_run(base, run, context, group):
            raise ValueError("Export closure changed before compilation")
        return run

    def export_result(entry, context, group, run):
        work = active[entry]
        work["exports"] -= 1
        counts["exports_closed" if run.get("closed") else "exports_unresolved"] += 1
        if compiling and run.get("closed") and full.rust_manifests({"full_export": {"runs": [run]}}):
            work["compiles"] += 1
            compile_queue.append((entry, context, group))
        publish(entry)

    def next_export():
        while export_queue:
            entry, groups = export_queue.popleft()
            item = next(groups, None)
            if item is not None:
                export_queue.append((entry, groups))
                return entry, *item
        return None

    pending_sessions = {entry: set(data["entries"][entry]["sessions"]) for entry in selected}
    if scanning:
        for session in ordered:
            unit = units[session]
            try:
                receipt = store.recover(unit)
                if receipt and receipt["status"] in {"complete", "failed_source"}:
                    scan_frozen.note_scan_failure(failures, receipt)
                    if unit["entry"] in selected:
                        pending_sessions[unit["entry"]].discard(session)
            except checks.EVIDENCE_ERRORS as error:
                failures[session] = {"session": session, "unit_id": digest(unit)}
                problem(session + " recovery", error)
    else:
        for remaining in pending_sessions.values():
            remaining.clear()
    for entry in data["order"]:
        if entry in selected and not pending_sessions[entry]:
            admit(entry)
    progress()
    pools = {kind: ThreadPoolExecutor(max_workers=limit) for kind, limit in limits.items()}
    busy = Counter()
    compile_slots = deque(range(args.compile_workers))

    def submit(kind, payload, call, *params):
        pending[pools[kind].submit(call, *params)] = kind, payload
        busy[kind] += 1

    def compile_saved(entry, plan, context, group, slot):
        run = read_export(entry, context, group)
        return fixed_pipeline.compile_group(base, plan, context, group, run, options,
                                            full.compilation_environment(env, base, slot), optimizer)

    try:
        while True:
            if scan_queue and not busy["scan"]:
                session = scan_queue.popleft()
                unit = units[session]
                submit("scan", session, scan_frozen.scan_session, store, unit, failures, options, env,
                       runtime, tool_generation)
            while plan_queue and busy["plan"] < limits["plan"]:
                entry = plan_queue.popleft()
                expected = active[entry]["expected"]
                if planning:
                    submit("plan", entry, checks.freeze, base, entry, expected, options, dict(env))
                else:
                    try:
                        plan = state.get("plan/" + entry)
                        checks.validate_plan(base, plan, expected)
                        start_groups(entry, plan)
                    except checks.EVIDENCE_ERRORS as error:
                        problem(entry + " plan", error)
                        active.pop(entry, None)
            while busy["export"] < limits["export"]:
                job = next_export()
                if job is None:
                    break
                entry, context, group = job
                if exporting:
                    submit("export", job, fixed_export.execute_group, base, active[entry]["plan"]["id"],
                           context, group, options, dict(env))
                else:
                    try:
                        export_result(entry, context, group, read_export(entry, context, group))
                    except checks.EVIDENCE_ERRORS as error:
                        problem(entry + " export " + group["id"], error)
                        active[entry]["exports"] -= 1
                        publish(entry)
            if compile_queue and optimizer_state == "pending":
                submit("compile", None, prepare_optimizer, base, options, env)
                optimizer_state = "preparing"
            while compile_queue and compile_slots and optimizer_state in {"ready", "failed"}:
                entry, context, group = compile_queue.popleft()
                if optimizer_state == "failed":
                    active[entry]["compiles"] -= 1
                    publish(entry)
                    continue
                slot = compile_slots.popleft()
                submit("compile", (entry, slot), compile_saved, entry, active[entry]["plan"], context, group, slot)
            if not pending:
                if scan_queue or plan_queue:
                    continue
                break
            done, _ = wait(pending, timeout=10, return_when=FIRST_COMPLETED)
            for future in done:
                kind, payload = pending.pop(future)
                busy[kind] -= 1
                value = None
                try:
                    value = future.result()
                except checks.EVIDENCE_ERRORS as error:
                    label = payload[0] if isinstance(payload, tuple) else payload
                    problem(str(label or "optimizer") + " " + kind, error)
                if kind == "scan":
                    unit = units[payload]
                    if value:
                        scan_frozen.note_scan_failure(failures, value)
                        counts["scan_" + value["status"]] += 1
                        print("[scan]", unit["entry"], payload, value["status"], flush=True)
                    else:
                        failures[payload] = {"session": payload, "unit_id": digest(unit)}
                    remaining = pending_sessions.get(unit["entry"])
                    if remaining and payload in remaining:
                        remaining.remove(payload)
                        if not remaining:
                            admit(unit["entry"])
                elif kind == "plan":
                    if value:
                        counts["entries_planned"] += 1
                        print("[plan]", payload, dp.statistics(value), flush=True)
                        try:
                            start_groups(payload, value)
                        except checks.EVIDENCE_ERRORS as error:
                            problem(payload + " plan", error)
                            active.pop(payload, None)
                    else:
                        del active[payload]
                elif kind == "export":
                    entry, context, group = payload
                    export_result(entry, context, group, value or {})
                elif payload is None:
                    optimizer, optimizer_state = value, "ready" if value else "failed"
                else:
                    entry, slot = payload
                    compile_slots.append(slot)
                    active[entry]["compiles"] -= 1
                    if value:
                        counts["rust_crates"] += value["crates"]
                        counts["rust_crates_closed"] += value["closed"]
                    publish(entry)
            progress()
    except BaseException:
        cancel.set()
        progress("interrupted")
        raise
    finally:
        for pool in pools.values():
            pool.shutdown(wait=True, cancel_futures=True)
    progress("processed")
    return errors


def finalize(base, data, units, metadata, errors=(), report=True):
    state = State(base)
    gate, result, scopes, totals = checks.reconcile(Store(base), data, units, metadata, data["order"],
                                                     "all", optimizer_path(base))
    gate["problems"].extend(errors)
    problem = target_compile.checkpoint_problem(base, data["order"])
    if problem:
        gate["problems"].append(problem)
    gate["passed"] = not gate["problems"]
    if report:
        from full_report import build_report
        summary = build_report(base, data, result, scopes, verified=gate["passed"])
        with (base / "report/entries.csv").open(newline="", encoding="utf-8") as stream:
            reported = [row["entry"] for row in csv.DictReader(stream)]
        if (reported != data["order"] or summary["entry_count"] != len(data["entries"])
                or gate["passed"] and any(summary.get(key) != value for key, value in totals.items())):
            gate["problems"].append({"reason": "Report totals differ from current entry results"})
            if gate["passed"]:
                build_report(base, data, result, scopes, verified=False)
            gate["passed"] = False
    state.put("audit.json", gate)
    driver = state.get("driver-state.json", {})
    state.put("driver-state.json", dict(driver, status="complete" if gate["passed"] else "incomplete",
                                      updated=common.timestamp(), audit_problems=len(gate["problems"])))
    print(json.dumps({"passed": gate["passed"], "entries": len(gate["entries"]),
                      "problems": gate["problems"][:25], **totals}, ensure_ascii=False), flush=True)
    return int(not gate["passed"])


def main():
    parser = common.arguments(__doc__)
    parser.add_argument("phase", choices=("init", "run", "scan", "plan", "export", "compile", "compile-targets", "status",
        "scan-checkpoint", "plan-checkpoint", "export-checkpoint", "compile-checkpoint", "audit", "report"))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--cargo", default="cargo +1.94.0")
    parser.add_argument("--with-report", action="store_true")
    args = parser.parse_args()
    base = args.output_dir.resolve()
    if args.phase == "status":
        state = State(base)
        if not state.get("run"):
            raise ValueError("Initialize the run first")
        print(json.dumps(dict(state.get("driver-state.json", {}), experiment=dp.ENTRY_PIPELINE,
                              plans=len(state.keys("plan/")), publications=len(state.keys("published/"))),
                         ensure_ascii=False, indent=2))
        return 0
    if args.timeout or args.skip_proofs or args.refresh_manifest:
        raise ValueError("Entry pipeline requires checked proofs, frozen inputs and unlimited native time")
    env, metadata = common.environment(args)
    env["CARGO"] = args.cargo
    env["RUSTFLAGS"] = (env.get("RUSTFLAGS", "") + " -Awarnings").strip()

    def contract():
        run, data, units = scan_frozen.validate_contract(base, args, env)
        if run["experiment"] != dp.ENTRY_PIPELINE:
            raise ValueError("fixed-plan-v3 requires a fresh work root")
        selected = list(dict.fromkeys(args.entries or data["order"]))
        if set(selected) - data["entries"].keys():
            raise ValueError("Unknown selected entries")
        return run, data, units, selected

    if args.phase.endswith("-checkpoint"):
        run, data, units, selected = contract()
        phase = args.phase.removesuffix("-checkpoint")
        gate, _, _, _ = checks.reconcile(Store(base), data, units, run["environment"], selected,
                                          phase, optimizer_path(base))
        if phase == "compile":
            problem = target_compile.checkpoint_problem(base, selected)
            if problem:
                gate["problems"].append(problem)
                gate["passed"] = False
        key = args.phase + ".json" if args.entries is None else "checkpoint/" + phase + "/" + digest(selected)
        State(base).put(key, gate)
        print(json.dumps(gate, ensure_ascii=False, indent=2))
        return int(not gate["passed"])
    with common.experiment_lock():
        native = scan_frozen.active_children(base)
        if native:
            raise ValueError("Previous native processes are still active: " + repr(native))
        if args.phase == "compile-targets":
            return int(not target_compile.run(base, args.entries, args, env)["complete"])
        if args.phase == "init" or (args.phase == "run" and not (base / "state.sqlite3").is_file()):
            scan_frozen.initialize(base, args, env, metadata)
            if args.phase == "init":
                return 0
        run, data, units, selected = contract()
        if args.phase in {"audit", "report"}:
            return finalize(base, data, units, run["environment"], report=args.phase == "report" or args.with_report)
        if args.phase in {"run", "plan", "export"}:
            import native_patch
            native_patch.verify(env["ISABELLE_HOME"])
        errors = execute(base, data, units, run["environment"], selected, args.phase, args, env)
        if args.phase in {"run", "compile"}:
            compiled = target_compile.run(base, selected, args, env)
            if args.phase == "compile" and not compiled["complete"]:
                errors.append({"reason": "Five-language compilation did not account for every requested export"})
        if args.phase == "run":
            return finalize(base, data, units, run["environment"], errors)
        gate, _, _, _ = checks.reconcile(Store(base), data, units, run["environment"], selected,
                                          args.phase, optimizer_path(base))
        return int(bool(errors) or not gate["passed"])


def interrupt(signum, frame):
    raise KeyboardInterrupt


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, interrupt)
    try:
        sys.exit(main())
    except (ValueError, RuntimeError, OSError) as error:
        sys.exit(str(error))
    except KeyboardInterrupt:
        sys.exit(130)
