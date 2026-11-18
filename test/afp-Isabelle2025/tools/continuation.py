"""Explicit, immutable continuation of a live analysis snapshot.

The parent keeps its analysis processes. Only sealed files are copied; new
exports and compilation never write to the parent. Deferral is an authorized
disposition, not a fabricated native failure or a successful dependency graph.
"""
import argparse
import copy
import fcntl
import json
import os
from pathlib import Path
import shutil
import sqlite3

import afp_common as common
from scan_store import Store, digest, file_digest
from state import State, encode

# Continuation may change orchestration, but must preserve the native analysis,
# classifier, graph rules, serializers, optimizer and compiler inputs.
ORCHESTRATION = {
    "test/afp-Isabelle2025/tools/" + name for name in
    ("afp.py", "fixed_plan.py", "fixed_export.py", "full.py", "full_report.py", "full_audit.py",
     "continuation.py", "fixed_pipeline.py", "state.py")
}


def policy(base):
    state = State(base)
    value = state.get("continuation-policy")
    if not value:
        return None
    run = state.get("run", {})
    origin = state.get("continuation-origin", {})
    if (value.get("schema") != 1 or run.get("continuation") != digest(value)
            or value.get("origin") != digest(origin)
            or not value.get("reason") or not value.get("deferred_entries")
            or value.get("allow_partial_compile") is not True):
        raise ValueError("Missing/changed explicit continuation authorization")
    return value


def analysis_tools(base, actual):
    value = policy(base)
    if not value:
        if State(base).get("run", {}).get("continuation"):
            raise ValueError("Missing continuation provenance")
        return actual
    origin = State(base).get("continuation-origin")
    inherited = origin["tools"]
    changed = {p for p in set(inherited) | set(actual) if inherited.get(p) != actual.get(p)}
    if changed - ORCHESTRATION:
        raise ValueError("Continuation changed native/semantic inputs: " + repr(sorted(changed - ORCHESTRATION)))
    if State(base).get("run", {}).get("tools") != actual:
        raise ValueError("Continuation execution tools changed")
    return inherited


def deferred_request(base, entry, key, inputs, create=False, authorization=None):
    authorization = authorization if authorization is not None else policy(base)
    if not authorization or entry not in authorization["deferred_entries"]:
        if create:
            raise ValueError("Entry has no explicit deferral authorization")
        return None
    state = State(base)
    deferred_key = "analysis-deferred/" + digest(key)
    failure = {"phase": "user_deferred", "message": authorization["reason"],
               "error": "Analysis unresolved at the authorized snapshot cutoff",
               "cutoff": authorization["cutoff"], "parent": authorization["parent"]}
    expected = {"schema": 1, "policy": digest(authorization), "entry": entry,
                "key": key, "input": inputs, "failure": failure}
    saved = state.get(deferred_key)
    if saved and (saved != expected or state.get(key) is not None):
        raise ValueError("Changed deferred request or conflicting native evidence")
    if saved is None and create and state.get(key) is None:
        state.put(deferred_key, expected)
        saved = expected
    if saved is None:
        return None
    return {"evidence": deferred_key, "seal": digest(saved), "failure": failure}


def relocate(value, source, destination):
    """Move locators, preserving all non-path diagnostic strings verbatim."""
    if isinstance(value, str):
        return str(destination) + value[len(str(source)):] if (
            value == str(source) or value.startswith(str(source) + "/")) else value
    if isinstance(value, list):
        return [relocate(v, source, destination) for v in value]
    if isinstance(value, dict):
        return {k: relocate(v, source, destination) for k, v in value.items()}
    return value


def copy_sealed(source, destination, expected):
    if source.is_symlink() or not source.is_file():
        raise ValueError("Missing/nonregular sealed evidence: " + str(source))
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Reflinks copy on write, unlike hardlinks to a live parent's evidence.
    with source.open("rb") as src, destination.open("xb") as dst:
        try:
            fcntl.ioctl(dst.fileno(), 0x40049409, src.fileno())  # FICLONE
        except OSError:
            shutil.copyfileobj(src, dst, 1024 * 1024)
    if destination.stat().st_size != expected["bytes"] or file_digest(destination) != expected["sha256"]:
        raise ValueError("Snapshot evidence changed: " + str(source))


def snapshot(source, destination, entries, reason, tools, processes=None):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if (source == destination or destination.is_relative_to(source)
            or source.is_relative_to(destination) or (destination.exists() and any(destination.iterdir()))):
        raise ValueError("Continuation requires a fresh separate work root")
    if not entries or not reason.strip():
        raise ValueError("Specify the deferred entries and explicit user instruction")
    destination.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect((source / "state.sqlite3").as_uri() + "?mode=ro", uri=True, timeout=60) as src:
        with sqlite3.connect(destination / "state.sqlite3") as dst:
            src.backup(dst)
    state = State(destination)
    parent = state.get("run")
    if not parent or parent.get("experiment") != "fixed-plan-v2" or parent.get("continuation"):
        raise ValueError("Only an original fixed-plan-v2 analysis run can be continued")
    if set(entries) - set(parent["manifest"]["entries"]):
        raise ValueError("Unknown deferred entry")
    if state.keys("fixed-progress/") or any(
            state.get(k).get("full_export") for k in state.keys("entry/")):
        raise ValueError("Snapshot continuation currently requires a pre-export parent")
    origin = {"parent_run": digest(parent), "tools": parent["tools"],
              "record_signature": state.signature(("",)),
              "relocation": {"from": str(source), "to": str(destination)},
              "preserved_processes": processes or []}
    authorization = {"schema": 1, "parent": str(source), "cutoff": common.timestamp(),
                     "deferred_entries": sorted(set(entries)), "reason": reason,
                     "allow_partial_compile": True, "origin": digest(origin)}
    changed = {p for p in set(tools) | set(parent["tools"]) if tools.get(p) != parent["tools"].get(p)}
    if changed - ORCHESTRATION:
        raise ValueError("Incompatible analysis tools: " + repr(sorted(changed - ORCHESTRATION)))
    # A backup is the cutoff. Later native results are never imported.
    evidence = {}
    with state.connect() as db:
        rows = db.execute("SELECT key,value FROM records").fetchall()
    sealed_directories = set()
    for key, raw in rows:
        if key.startswith(("receipt/", "analysis-context/", "analysis-selection/")):
            value = json.loads(raw)
            for path, seal in value.get("evidence", {}).items():
                if path in evidence and evidence[path] != seal:
                    raise ValueError("Conflicting snapshot file identities")
                evidence[path] = seal
                sealed_directories.add(str(Path(path).parent))
    store, target = Store(source), Store(destination)
    for index, (path, seal) in enumerate(sorted(evidence.items()), 1):
        copy_sealed(store.path(path), target.path(path), seal)
        if index % 10000 == 0:
            print("[snapshot] copied", index, "/", len(evidence), flush=True)
    updates, removes = {}, []
    for key, raw in rows:
        if (key in {"plan-checkpoint.json", "pipeline-outcome", "processes.json"}
                or key.startswith("analysis-active/")
                or (key.startswith("analysis/") and str(Path(key).parent) not in sealed_directories)):
            removes.append(key)
        else:
            old = json.loads(raw)
            new = relocate(old, source, destination)
            if new != old:
                updates[key] = new
    run = copy.deepcopy(parent)
    run.update(created=authorization["cutoff"], tools=tools, continuation=digest(authorization))
    updates.update({"run": run, "continuation-origin": origin, "continuation-policy": authorization})
    state.update(updates, removes)
    print("[snapshot] sealed", len(evidence), "files", flush=True)
    return authorization


def freeze(base):
    """Replay inherited evidence; only authorized missing requests are deferred."""
    import dependency_plan as dp
    import fixed_plan
    import full
    from scan_frozen import tools_identity
    authorization = policy(base)
    if not authorization:
        raise ValueError("No explicit snapshot continuation")
    analysis_tools(base, tools_identity())
    data, result, exports = full.load(base)
    full.require_scan_gate(base, result, exports)
    state = State(base)
    for entry in data["order"]:
        saved = state.get("plan/" + entry)
        if saved:
            continue
        if entry not in authorization["deferred_entries"]:
            raise ValueError("Missing non-deferred plan: " + entry)
        expected = fixed_plan.identity(base, entry, data["entries"][entry], result["entries"][entry], exports[entry])
        plan, _ = fixed_plan.build_entry(base, entry, expected, replay=True, defer_missing=True)
        state.update({"plan/" + entry: plan, "plan-status/" + entry:
                      {"status": "complete", "meaning": "disposition_inventory_valid"}},
                     remove=["plan-checkpoint.json"])
        print("[deferred plan]", entry, json.dumps(dp.statistics(plan)), flush=True)
    gate = fixed_plan.checkpoint(base, data, result, exports)
    if not gate["passed"]:
        raise ValueError("Continuation plan evidence failed: " + repr(gate["problems"][:10]))
    return gate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-work", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--defer-entries", nargs="+")
    parser.add_argument("--reason")
    parser.add_argument("--processes", type=json.loads, default=[])
    args = parser.parse_args()
    with common.experiment_lock():
        if args.from_work:
            from scan_frozen import tools_identity
            snapshot(args.from_work, args.output_dir, args.defer_entries, args.reason, tools_identity(), args.processes)
        gate = freeze(args.output_dir)
        print(json.dumps({"passed": gate["passed"], "meaning": gate["meaning"], "plans": len(gate["plans"])}))


if __name__ == "__main__":
    main()
