#!/usr/bin/env python3
"""Discover AFP candidates, retaining only current receipts and active work."""
import collections
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import xml.etree.ElementTree as ET

import afp_common as common
import scan
from state import State
from scan_store import (METHOD, POLICY, SCHEMA, Store, aggregate, completed_receipt,
                        digest, file_digest, inventory, unit_input)

def tools_identity():
    """Bind this run to the actual pipeline sources without copying them."""
    paths = list(common.HERE.glob("*.py")) + list(common.HERE.glob("*.ML")) + list(common.HERE.glob("*.scala"))
    for directory, patterns in ((common.PROJECT / "translate", ("*.thy", "*.ML")),
                                (common.PROJECT / "optimize", ("src/**/*.rs", "Cargo.toml", "Cargo.lock")),
                                (common.PROJECT.parent / "RustLightAST", ("src/**/*.rs", "Cargo.toml", "Cargo.lock"))):
        for pattern in patterns:
            paths.extend(directory.glob(pattern))
    return {common.relative(p): file_digest(p) for p in sorted(set(paths)) if p.is_file()}


def compiler_identity(name, value, env):
    """Capture the actual executable behind directory-valued ROOT conditions."""
    path = Path(value).expanduser()
    selected = path
    if path.is_dir():
        suffix = {"ISABELLE_GOEXE": "go",
                  "ISABELLE_CAKEML_HOME": "bin/" + env["ISABELLE_PLATFORM64"] + "/cake"}.get(name)
        if suffix:
            selected = path / suffix
    wrapper = selected
    extra = []
    if name == "ISABELLE_GHC":
        marker = Path(env["ISABELLE_STACK_ROOT"]) / ("ISABELLE_GHC_EXE-" + env["ISABELLE_PLATFORM_FAMILY"])
        if marker.is_file():
            extra.append(marker)
            selected = Path(marker.read_text().strip())
    if name == "ISABELLE_CAKEML_HOME":
        extra.append(path / "basis_ffi.c")
    if name == "ISABELLE_MLTON":
        extra.append(path.parent.parent / "lib/mlton/mlton-compile")
    if name == "ISABELLE_OCAMLFIND":
        found = shutil.which("ocamlc", path=env.get("PATH"))
        if found:
            extra.append(Path(found))
    if name == "ISABELLE_GOEXE" and env.get("ISABELLE_GOROOT"):
        extra.append(Path(env["ISABELLE_GOROOT"]) / "VERSION")
    result = {"value": value, "resolved": str(selected.resolve()), "exists": selected.exists(),
              "support": {str(p.resolve()): file_digest(p) for p in [wrapper, *extra] if p.is_file()}}
    if selected.is_file():
        result["sha256"] = file_digest(selected)
        result["executable"] = os.access(selected, os.X_OK)
    elif selected.is_dir():
        result["files"] = inventory(selected)
    return result


def source_inputs(args, env, data):
    """One independent input snapshot, separate from execution/resource settings."""
    thys = args.afp / "thys"
    conditions = sorted({c for info in data["entries"].values()
                         for t in info["theories"] for c in t.get("conditions", [])})
    installed = Path(env["ISABELLE_HOME"])
    sources = {"afp": inventory(thys), "isabelle_src": inventory(installed / "src"),
               "conditions": {c: compiler_identity(c, env[c], env) if env.get(c) else {"value": ""}
                              for c in conditions},
               "isabelle_home": str(installed), "afp_root": str(args.afp),
               "settings": {}}
    # Settings and runtime executables supplement source identity. Component
    # names alone are not a proof that a patched binary is still the same input.
    paths = [installed / "bin/isabelle", installed / "lib/scripts/getsettings"]
    for component in env.get("ISABELLE_COMPONENTS", "").split(os.pathsep):
        paths += [Path(component) / "etc" / name for name in ("settings", "options", "components")]
    for key, suffix in (("ML_HOME", "poly"), ("JAVA_HOME", "bin/java")):
        if env.get(key):
            paths.append(Path(env[key]) / suffix)
    for path in paths:
        if path.is_file():
            sources["settings"][str(path.resolve())] = file_digest(path)
    return sources


def make_units(data, sources):
    owners = {s: e for e, info in data["entries"].items() for s in info["sessions"]}
    entry_digests = {
        e: digest({p: h for p, h in sources["afp"].items() if p.startswith(e + "/")})
        for e in data["entries"]}
    shared = digest({"isabelle": sources["isabelle_src"], "settings": sources["settings"],
                     "ROOTS": sources["afp"].get("ROOTS"), "proofs": "checked"})
    units = {}
    for entry, info in data["entries"].items():
        for session in info["sessions"]:
            required = set(info["session_requirements"].get(session, [])) | {session}
            dependencies = {owners[s] for s in required if s in owners} | {entry}
            conditions = {c for e in dependencies for t in data["entries"][e]["theories"]
                          if t["session"] in required for c in t.get("conditions", [])}
            source = {"shared": shared, "entries": {e: entry_digests[e] for e in sorted(dependencies)},
                      "conditions": {c: sources["conditions"][c] for c in sorted(conditions)}}
            units[session] = unit_input(entry, session, info, source)
    return units


def active_children(base):
    """Find detached old natives by a run marker inherited through their env.

    This catches Poly/ML even when its Java parent died and PPID changed.
    Read only the one marker; never serialize arbitrary environment secrets.
    """
    marker = ("AFP_SCAN_RUN=" + str(base)).encode()
    active = []
    for path in Path("/proc").iterdir():
        if path.name.isdigit() and int(path.name) != os.getpid():
            try:
                if marker in (path / "environ").read_bytes().split(b"\0"):
                    active.append({"pid": int(path.name),
                                   "identity": common.process_identity(int(path.name))})
            except (OSError, PermissionError):
                pass
    return active


def initialize(base, args, env, metadata):
    """Create one run, with one manifest and one input/configuration identity."""
    if base.exists() and any(base.iterdir()):
        raise ValueError("initialization requires an empty, isolated output directory")
    # Failed discovery leaves the output empty so initialization can be retried.
    with tempfile.TemporaryDirectory(prefix="afp-init-") as temporary:
        args.manifest_dir = Path(temporary)
        data = common.manifest(args, env)
        counts = (len(data["entries"]), sum(len(i["sessions"]) for i in data["entries"].values()),
                  sum(len(i["theories"]) for i in data["entries"].values()))
        if counts != (893, 922, 9122):
            raise ValueError("unexpected AFP universe: " + repr(counts))
        if any(i["source_errors"] for i in data["entries"].values()):
            raise ValueError("manifest source errors require review")
        sources = source_inputs(args, env, data)
        unavailable = [name for name, value in sources["conditions"].items()
                       if not value.get("exists") or not value.get("executable")]
        if unavailable:
            raise ValueError("conditional compiler prerequisites unavailable: " + repr(unavailable))
        run = {"schema": 1, "created": common.timestamp(), "manifest": data,
               "sources": sources, "tools": tools_identity(), "environment": metadata}
        state = State(base)
        state.put("run", run)
        return run


def validate_contract(base, args, env):
    run = State(base).get("run")
    if not run or run.get("schema") != 1:
        raise ValueError("missing or incompatible run; initialize first")
    actual = source_inputs(args, env, run["manifest"])
    # AFP sessions may create exported files beside their sources. Only files
    # present at initialization are immutable inputs; generated additions are outputs.
    actual["afp"] = {k: actual["afp"].get(k) for k in run["sources"]["afp"]}
    if actual != run["sources"]:
        raise ValueError("source/compiler inputs changed; start a new run")
    if tools_identity() != run["tools"]:
        raise ValueError("pipeline sources changed; start a new run")
    return run, run["manifest"], make_units(run["manifest"], run["sources"])


def failure_receipt(store, attempt, unit, run, built, inspected=None, error=None):
    """Unknown failures stay unresolved; absence of a regex match proves nothing."""
    checks = [c for c in (built, inspected) if c]
    failed_sessions = sorted({s for c in checks for s in c.get("failed_sessions", [])})
    paths = [p for p in attempt.rglob("*") if p.is_file() and not p.name.endswith(".tmp")]
    receipt = {"schema": SCHEMA, "unit": unit, "unit_id": digest(unit),
               "status": "unresolved_infrastructure", "committed": common.timestamp(),
               "build": built, "inspect": inspected, "error": error,
               "failed_sessions": failed_sessions, "tool_generation": run["tool_generation"],
               "evidence": store.evidence(paths)}
    if any(c.get("status") == "interrupted" for c in checks):
        receipt["status"] = "interrupted"
    return receipt


def archive_failed_build(attempt, unit, built, args, env):
    """Archive mutable session DBs immediately, before another build replaces them."""
    import full
    record = {"entries": {unit["entry"]: {"scan": {"loading": [built]}}}}
    full.archive_scan_messages(attempt, record, args, env)


def run_unit(store, unit, args, env, runtime, identity):
    attempt = store.next_attempt(unit)
    run = {"unit_id": digest(unit), "tool_generation": digest(identity),
           "runtime": runtime, "started": common.timestamp()}
    common.write_record(attempt / "attempt.json", run)
    (attempt / "theories.txt").write_text("\n".join(unit["requested"]) + "\n")
    actual = dict(env, AFP_SCAN_POLICY=POLICY, AFP_SCAN_UNIT=digest(unit),
                  AFP_SCAN_RUN=str(store.base), AFP_SCAN_THEORIES=str(attempt / "theories.txt"),
                  AFP_SCAN_OUTPUT=str(attempt / "catalogue.xml"))
    built, inspected = {}, None
    try:
        with common.build_lock():
            built = common.command([args.isabelle, "build", "-v", "-b", *common.build_options(args),
                                    "-d", str(args.afp / "thys"), unit["session"]],
                                   attempt / "load.log", args, actual)
            built["session"] = unit["session"]
            if built["status"] != "passed":
                built["failed_sessions"] = scan.failed_sessions_in_log(
                    (attempt / "load.log").read_text(errors="replace"), built["status"])
                # A process dying before a lifecycle line still blocks this
                # session, without guessing which shared prerequisite failed.
                if not built["failed_sessions"]:
                    built["failed_sessions"] = [unit["session"]]
                archive_failed_build(attempt, unit, built, args, actual)
            else:
                inspected = scan.inspect_session(unit["session"], args, actual,
                    attempt / "scan.log", collector=common.HERE / "scan.ML")
                inspected["session"] = unit["session"]
        if inspected and inspected["status"] == "passed":
            receipt = completed_receipt(store, attempt, unit, run, built, inspected)
        else:
            receipt = failure_receipt(store, attempt, unit, run, built, inspected)
    except (OSError, ValueError, ET.ParseError) as error:
        receipt = failure_receipt(store, attempt, unit, run, built, inspected, str(error))
    return store.commit(attempt, receipt)


def failed_dependencies(units, store):
    failures = {}
    for session, unit in units.items():
        receipt = store.read(unit)
        if receipt and receipt["status"] not in {"complete", "blocked_dependency"}:
            for failed in receipt.get("failed_sessions", []) or (
                    [session] if receipt.get("build", {}).get("status") != "passed" else []):
                failures[failed] = {"session": session, "unit_id": digest(unit)}
    return failures


def checkpoint(store, data, units, metadata):
    """Completion requires every session to have a validated, explained terminal."""
    result, exports = aggregate(store, data, units, metadata)
    counts, issues = collections.Counter(), []
    failures = failed_dependencies(units, store)
    for session, unit in units.items():
        receipt = store.read(unit)
        status = receipt["status"] if receipt else "pending"
        counts[status] += 1
        if status not in {"complete", "failed_source", "blocked_dependency"}:
            issues.append({"session": session, "status": status})
        elif status == "blocked_dependency":
            for blocker in receipt.get("dependencies", []):
                cause = failures.get(blocker)
                if not cause or (store.read(units[cause["session"]]) or {}).get("status") != "failed_source":
                    issues.append({"session": session, "status": "unresolved_dependency", "blocker": blocker})
    # A complete receipt set is insufficient if its union omits a manifest
    # theory. Preserve reviewed source/dependency failures as terminal states,
    # but never certify a purportedly complete entry with a coverage gap.
    for entry, record in result["entries"].items():
        scan = record["scan"]
        states = scan["unit_states"].values()
        if states and all(s == "complete" for s in states) and scan["missing_theories"]:
            issues.append({"entry": entry, "status": "incomplete_theory_coverage",
                           "missing_theories": scan["missing_theories"]})
    gate = {"phase": "scan", "checked": common.timestamp(), "passed": not issues,
            "unit_counts": dict(counts), "issues": issues,
            "scan_signature": __import__("full").scan_signature(result, exports),
            "entries": len(data["entries"]), "candidate_count": result["coverage"]["distinct_candidates"]}
    common.write_record(store.base / "scan-checkpoint.json", gate)
    return gate


def main():
    parser = common.arguments(__doc__)
    parser.set_defaults(timeout=0)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--initialize", action="store_true")
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    if args.timeout or args.skip_proofs:
        raise ValueError("full scans require timeout=0 and checked proofs")
    if args.refresh_manifest:
        raise ValueError("start a new run to change the manifest")
    base = args.output_dir.resolve()
    env, metadata = common.environment(args)
    if args.initialize:
        initialize(base, args, env, metadata)
    contract, data, units = validate_contract(base, args, env)
    store = Store(base)
    native = active_children(base)
    if native:
        raise ValueError("previous native processes are still active: " + repr(native))
    identity = tools_identity()
    retries = {s for s, unit in units.items() if args.retry_failed and
               (store.read(unit) or {}).get("status") != "complete"}
    selected_entries = args.entries or data["order"]
    if not set(selected_entries) <= set(data["entries"]):
        raise ValueError("unknown selected entries")
    # Recover already completed XML before constructing the queue. A corrupt
    # receipt blocks here; corruption must never be treated as permission to scan.
    for unit in units.values():
        store.recover(unit)
    ordered = [s for e in selected_entries for s in data["entries"][e]["sessions"]]
    queue = []
    for session in ordered:
        receipt = store.read(units[session])
        if not receipt or receipt["status"] in {"interrupted", "blocked_dependency"} or session in retries:
            queue.append(session)
    runtime = {"min_available_mb": args.min_available_mb, "command": sys.argv,
               "pid": os.getpid(), "identity": common.process_identity(os.getpid())}
    state = {"status": "prepared" if args.prepare_only else "running", "phase": "scan",
             "started": common.timestamp(), **runtime}
    common.write_record(base / "driver-state.json", state)
    if args.prepare_only:
        checkpoint(store, data, units, metadata)
        return 0
    for index, session in enumerate(queue, 1):
        if tools_identity() != identity:
            raise ValueError("live tool files changed; current generation stopped before next unit")
        unit = units[session]
        # Recheck the authoritative completion fact even if a stale plan is used.
        current = store.read(unit)
        if current and current["status"] == "complete":
            continue
        failures = failed_dependencies(units, store)
        blockers = sorted(set(unit["requirements"]) & set(failures))
        print(f"[scan {index}/{len(queue)}] {unit['entry']} / {session}", flush=True)
        if blockers:
            if current and current["status"] == "blocked_dependency" and current.get("dependencies") == blockers:
                continue
            attempt = store.next_attempt(unit)
            receipt = {"schema": SCHEMA, "unit": unit, "unit_id": digest(unit),
                       "status": "blocked_dependency", "dependencies": blockers,
                       "causes": {s: failures[s] for s in blockers}, "evidence": {},
                       "committed": common.timestamp()}
            store.commit(attempt, receipt)
        else:
            receipt = run_unit(store, unit, args, env, runtime, identity)
        state.update(current_session=session, last_status=receipt["status"], updated=common.timestamp())
        common.write_record(base / "driver-state.json", state)
        print("  " + receipt["status"], flush=True)
        # The receipt was already committed. Summaries are a recoverable view.
        checkpoint(store, data, units, metadata)
    gate = checkpoint(Store(base), data, units, metadata)
    state.update(status="scan_complete" if gate["passed"] else "scan_needs_review",
                 finished=common.timestamp(), unit_counts=gate["unit_counts"])
    common.write_record(base / "driver-state.json", state)
    print(json.dumps(gate, ensure_ascii=False), flush=True)
    return 0 if gate["passed"] else 1


if __name__ == "__main__":
    try:
        with common.experiment_lock():
            sys.exit(main())
    except (ValueError, RuntimeError) as error:
        sys.exit(str(error))
    except KeyboardInterrupt:
        sys.exit(130)
