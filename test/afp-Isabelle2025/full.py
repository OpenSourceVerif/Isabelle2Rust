#!/usr/bin/env python3
"""Checkpointed AFP experiment: shared-frontend exports, then Rust compilation.

The original scan.py remains the candidate collector. This driver consumes its
separate output directory, preserves every export attempt, and never executes
generated programs. A phase checkpoint must match the current inputs before the
following phase can start.
"""

import collections
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import sys
import xml.etree.ElementTree as ET

import afp_common as common
from run import compile_crates

TARGETS = ("Rust", "SML", "OCaml", "Haskell", "Scala", "Go")
TERMINAL = {"passed", "failed"}


def digest(value):
    return hashlib.sha256(value).hexdigest()


def scope_digest(scope):
    return digest("\n".join(common.candidates(scope)).encode())


def inputs(base):
    """Bind gates to both discovery results and the explicit candidate scope."""
    return {name: digest((base / name).read_bytes())
            for name in ("exports.json", "results.json")}


def load(base):
    data = common.read_json(common.HERE / "_build/manifest.json")
    result = common.read_json(base / "results.json")
    exports = common.read_json(base / "exports.json")
    if not data or not result or exports is None:
        raise ValueError("Initialize the experiment and run scan.py first")
    if set(data["entries"]) != set(result["entries"]) or set(data["entries"]) != set(exports):
        raise ValueError("The manifest, result rows, and export rows must cover the same AFP entries")
    return data, result, exports


def save(base, result, exports):
    common.save_results(result, exports, base)


def infrastructure(text):
    """Keep configuration failures out of backend defect statistics."""
    patterns = {
        "timeout": r"(?m)^timeout$|timed out|Timeout\.TIMEOUT|\*\*\*.*timeout|Timeout after",
        "memory_or_stack": r"memory_limit|out of memory|unable to increase stack|Interrupt_Breakdown|cannot allocate|java heap space",
        "missing_dependency": r"command not found|no such file or directory|missing .*installation|missing .*compiler|cannot find.*(?:ocaml|ghc|sml|go)|Bad session",
        "tooling": r"Protocol_Message|has not been declared|Static Errors|ML error",
    }
    return [category for category, pattern in patterns.items()
            if re.search(pattern, text, re.IGNORECASE)]


def log_text(item):
    log = item.get("log")
    path = common.PROJECT / log if log else None
    return path.read_text(errors="replace") if path and path.is_file() else item.get("error_excerpt", "")


def scan_checkpoint(base, data, result, exports):
    """Inspect failed commands and conditions before permitting any exports."""
    problems = []
    rows = []
    for entry in data["order"]:
        record = result["entries"][entry]
        scan = record.get("scan", {})
        status = scan.get("status", "pending")
        if status not in {"passed", "failed", "blocked"}:
            problems.append({"entry": entry, "reason": "scan has not finished"})
        # Reused successful scans can still contain failed code certificates.
        # A truncated excerpt is insufficient when its original XML was cleaned.
        for diagnostic in scan.get("certificate_errors", []) + scan.get("context_merge_errors", []):
            if diagnostic.get("truncated") and not (
                    common.PROJECT / diagnostic.get("detail", "__missing__")).is_file():
                problems.append({"entry": entry, "reason": "missing full diagnostic",
                                 "constant": diagnostic.get("name"), "detail": diagnostic.get("detail")})
        for missing in scan.get("missing_theories", []):
            if missing.get("missing_conditions"):
                problems.append({"entry": entry, "reason": "missing_conditions", "theory": missing})
        for check in scan.get("loading", []) + scan.get("inspections", []):
            if check.get("status") in {"passed", "blocked"}:
                continue
            issues = infrastructure(check.get("status", "") + "\n" + log_text(check))
            if issues:
                problems.append({"entry": entry, "session": check.get("session"),
                                 "issues": issues, "log": check.get("log")})
        rows.append({"entry": entry, "status": status,
                     "theories": len(scan.get("theories", [])),
                     "expected_theories": len(data["entries"][entry]["theories"]),
                     "candidates": len(common.candidates(exports[entry]))})
    gate = {"phase": "scan", "checked": common.timestamp(), "inputs": inputs(base),
            "passed": not problems, "infrastructure_failures": problems, "entries": rows,
            "phase_counts": dict(collections.Counter(row["status"] for row in rows))}
    common.write_json(base / "scan-checkpoint.json", gate)
    return gate


def scan_signature(result, exports):
    # Export and compilation records change results.json. The scope and scan
    # evidence, rather than unrelated downstream fields, define discovery identity.
    return digest(json.dumps({"scan": {e: r["scan"] for e, r in result["entries"].items()},
                              "exports": exports}, sort_keys=True).encode())


def require_scan_gate(base, result, exports):
    gate = common.read_json(base / "scan-checkpoint.json", {})
    if not gate.get("passed") or gate.get("scan_signature") != scan_signature(result, exports):
        raise ValueError("A current passing scan-checkpoint is required; inspect/fix scan failures first")


def maximal_sessions(info, scan):
    """Use loaded maximal sessions; a failed example cannot erase its usable core."""
    loaded = [x["session"] for x in scan.get("loading", []) if x.get("status") == "passed"]
    requirements = info.get("session_requirements", {})
    return [s for s in loaded if not any(s in requirements.get(other, []) for other in loaded if other != s)]


def next_attempt(root):
    # Never overwrite an earlier failed command or its partial successful exports.
    for number in range(1, 1000000):
        directory = root / f"attempt-{number:04d}"
        if not directory.exists():
            directory.mkdir(parents=True)
            return directory
    raise ValueError("Too many attempts: " + str(root))


def export_command(session, work, args, env):
    """Load backends on the original checked heap, without rebuilding AFP proofs."""
    expression = (
        'Context.setmp_generic_context (SOME (Context.Theory '
        '(Thy_Info.get_theory "Go.Go_Setup"))) (ML_Context.eval_file ML_Compiler.flags) '
        '(Path.explode ' + common.quote(str(common.HERE / "full_export.ML")) + ')')
    argv = [args.isabelle, "process", "-l", session, "-d", str(common.PROJECT),
            "-d", str(args.afp / "thys"), "-o", "threads=1", "-o", "parallel_proofs=0",
            "-o", "timeout=" + str(args.timeout), "-o", "skip_proofs=false",
            "-T", "Rust.Rust_BigInt_Setup", "-T", "Go.Go_Setup", "-e", expression]
    actual = dict(env, AFP_FULL_OUTPUT=str(work), AFP_FULL_SCOPE=str(work / "scope.txt"),
                  AFP_FULL_THEORIES=str(work / "theories.txt"))
    # These raw processes only read existing heaps. The full experiment lock
    # serializes the main phases; the fixture may use a separate immutable HOL heap.
    check = common.command(argv, work / "process.log", args, actual)
    common.write_json(work / "process.json", check)
    return check


def collect_attempts(work):
    records = []
    for file in sorted(work.glob("attempts/**/*.xml")):
        node = ET.parse(file).getroot()
        value = dict(node.attrib, evidence=common.relative(file),
                     constants=[c.attrib["name"] for c in node.findall("constant")],
                     languages=[c.text for c in node.findall("language")],
                     files=[common.relative(work / c.text) for c in node.findall("file")],
                     error=(node.findtext("error", "")[:2000]),
                     error_sha256=digest(node.findtext("error", "").encode()),
                     error_truncated=len(node.findtext("error", "")) > 2000,
                     library_only=node.findtext("library_only") == "true")
        records.append(value)
    return records


def resolve_candidates(names, runs):
    """A failed group is diagnostic; only singleton failures condemn a constant."""
    outcomes = {c: {t: {"status": "blocked", "evidence": []} for t in TARGETS} for c in names}
    for run in runs:
        for attempt in run.get("attempts", []):
            cs = attempt["constants"]
            if attempt.get("target") in TARGETS:
                targets = [attempt["target"]]
            elif attempt.get("target") in {"frontend", "context"} and attempt.get("status") == "failed":
                targets = attempt["languages"]
            else:
                continue
            for c in cs:
                if c not in outcomes:
                    raise ValueError("Exported constant outside the requested scope: " + c)
                for target in targets:
                    outcome = outcomes[c][target]
                    if attempt["status"] == "passed":
                        outcome.update(status="passed")
                        outcome["evidence"].append(attempt["evidence"])
                    elif (len(cs) == 1 or attempt.get("stage") == "context_loading") and outcome["status"] != "passed":
                        # Full exception text lives in immutable XML; do not duplicate it
                        # six times per constant in the coverage matrix.
                        outcome.update(status="failed", stage=attempt["stage"],
                                       error_excerpt=attempt["error"][:500])
                        outcome["evidence"].append(attempt["evidence"])
    return outcomes


def entry_scan_signature(record):
    # Later code-equation theories can change behavior without adding a name.
    # Bind exports to their discovery contexts as well as their constant list.
    return digest(json.dumps(record["scan"], sort_keys=True).encode())


def serializer_signature():
    paths = sorted(list((common.PROJECT / "translate").glob("*.ML"))
                   + list((common.PROJECT / "translate").glob("*.thy"))
                   + [common.HERE / "full_export.ML"])
    return digest(b"".join(str(p.relative_to(common.PROJECT)).encode() + b"\0" + p.read_bytes()
                            for p in paths))


def export_entry(entry, info, record, scope, base, args, env):
    names = common.candidates(scope)
    if record.get("full_compile"):
        record.setdefault("full_compile_history", []).append(record.pop("full_compile"))
    stage = {"scope_sha256": scope_digest(scope), "serializer_sha256": serializer_signature(),
             "scan_sha256": entry_scan_signature(record), "started": common.timestamp(), "runs": []}
    record["full_export"] = stage
    if not names:
        stage.update(status="no_candidates" if record["scan"]["status"] == "passed" else "blocked",
                     candidates={}, languages={t: "no_candidates" if record["scan"]["status"] == "passed"
                                               else "blocked" for t in TARGETS})
        return
    sessions = maximal_sessions(info, record["scan"])
    for session in sessions:
        work = next_attempt(base / "exports" / entry / session)
        (work / "scope.txt").write_text("\n".join(names) + "\n")
        # Only already scanned theories supply contexts. Conditional or failed
        # sources must not be silently claimed as loaded/exported.
        scanned = set(record["scan"].get("theories", []))
        theory_names = [t["name"] for t in info["theories"] if t["path"] in scanned]
        (work / "theories.txt").write_text("\n".join(theory_names) + "\n")
        check = export_command(session, work, args, env)
        stage["runs"].append({"session": session, "directory": common.relative(work),
                              "command": check, "finished": (work / "finished.xml").is_file(),
                              "attempts": collect_attempts(work)})
    stage["candidates"] = resolve_candidates(names, stage["runs"])
    languages = {}
    for target in TARGETS:
        counts = collections.Counter(x[target]["status"] for x in stage["candidates"].values())
        languages[target] = ("blocked" if counts["blocked"] else
                             "passed" if counts["passed"] == len(names) else
                             "failed" if counts["failed"] == len(names) else "partial")
    stage.update(languages=languages, finished=common.timestamp(),
                 status="complete" if all(run["finished"] and run["command"]["status"] == "passed"
                                         for run in stage["runs"])
                 and all(x[t]["status"] in TERMINAL for x in stage["candidates"].values() for t in TARGETS)
                 else "blocked")
    # Keep every generated source; compilation uses this inventory rather than
    # assuming that a whole-entry aggregate produced exactly one Rust crate.
    stage["artifacts"] = [
        {"path": file, "sha256": digest((common.PROJECT / file).read_bytes()),
         "bytes": (common.PROJECT / file).stat().st_size}
        for file in sorted({file for run in stage["runs"] for attempt in run["attempts"]
                            if attempt["status"] == "passed" for file in attempt["files"]})]


def rust_manifests(record):
    return sorted({file for run in record.get("full_export", {}).get("runs", [])
                   for attempt in run.get("attempts", [])
                   if attempt.get("target") == "Rust" and attempt["status"] == "passed"
                   for file in attempt["files"] if file.endswith("/Cargo.toml")})


def export_checkpoint(base, data, result, exports):
    problems = []
    for entry in data["order"]:
        record = result["entries"][entry]
        stage = record.get("full_export", {})
        if stage.get("scan_sha256") != entry_scan_signature(record):
            problems.append({"entry": entry, "reason": "discovery context changed"})
        if stage.get("serializer_sha256") != serializer_signature():
            problems.append({"entry": entry, "reason": "serializer changed"})
        if stage.get("scope_sha256") != scope_digest(exports[entry]):
            problems.append({"entry": entry, "reason": "stale scope"})
        # A fully blocked original scan can have no candidates. It stays in
        # coverage with its upstream failure, rather than becoming a false empty pass.
        if common.candidates(exports[entry]) and stage.get("status") != "complete":
            problems.append({"entry": entry, "reason": "unresolved exports"})
        for run in stage.get("runs", []):
            if not run.get("finished") or run["command"]["status"] != "passed":
                problems.append({"entry": entry, "reason": "incomplete process",
                                 "command": run["command"]})
        for artifact in stage.get("artifacts", []):
            path = common.PROJECT / artifact["path"]
            if not path.is_file() or digest(path.read_bytes()) != artifact["sha256"]:
                problems.append({"entry": entry, "reason": "missing/changed export", "path": str(path)})
    identity = digest(json.dumps({e: r.get("full_export") for e, r in result["entries"].items()},
                                 sort_keys=True).encode())
    gate = {"phase": "export", "checked": common.timestamp(), "passed": not problems,
            "problems": problems, "export_signature": identity,
            "rust_crates": sum(len(rust_manifests(r)) for r in result["entries"].values())}
    common.write_json(base / "export-checkpoint.json", gate)
    return gate


def compile_entry(entry, record, base, args, env, optimizer):
    """Attempt optimization even if baseline Rust compilation failed.

    Stage-1 compiler failures do not imply that optimization or Stage-2 fails.
    No cargo test/run invocation and no generated executable is used.
    """
    compiled = record.setdefault("full_compile", {})
    for manifest in rust_manifests(record):
        if manifest in compiled and compiled[manifest].get("complete"):
            continue
        source = common.PROJECT / manifest
        key = digest(manifest.encode())[:20]
        logs = next_attempt(base / "compilation" / entry / key)
        out = base / "rust-stage2" / entry / key / logs.name
        item = compiled[manifest] = {"started": common.timestamp(), "stage2": common.relative(out)}
        item["stage1_compile"] = compile_crates([source], "stage1", args, env, logs)
        item["optimization"] = common.command(
            ["sh", str(common.PROJECT / "scripts/with-stack.sh"), "65536", str(optimizer),
             str(source.parent), "--out-dir", str(out)],
            logs / "optimization.log", args, env)
        if item["optimization"]["status"] == "passed" and (out / "Cargo.toml").is_file():
            item["stage2_compile"] = compile_crates([out / "Cargo.toml"], "stage2", args, env, logs)
        else:
            item["stage2_compile"] = {"status": "blocked", "reason": "optimization failed",
                                      "log": item["optimization"]["log"]}
        item.update(complete=True, finished=common.timestamp())


def fixture(base, args, env):
    """Test shared rejection, singleton isolation, six successes, and retained files."""
    work = next_attempt(base / "tooling" / "export-fixture")
    (work / "scope.txt").write_text("List.rev\nHilbert_Choice.Eps\n")
    (work / "theories.txt").write_text("Main\n")
    check = export_command("HOL", work, args, env)
    runs = [{"attempts": collect_attempts(work)}]
    outcome = resolve_candidates(["List.rev", "Hilbert_Choice.Eps"], runs)
    if check["status"] != "passed" or not (work / "finished.xml").is_file():
        raise ValueError("Export fixture failed; see " + check["log"])
    for target in TARGETS:
        assert outcome["List.rev"][target]["status"] == "passed", (target, outcome)
        assert outcome["Hilbert_Choice.Eps"][target]["status"] == "failed", (target, outcome)
    files = [common.PROJECT / f for a in runs[0]["attempts"] for f in a["files"]]
    assert files and all(f.is_file() for f in files)
    report = {"status": "passed", "checked": common.timestamp(), "command": check,
              "checks": ["all six language serializers ran", "failed aggregate was split",
                         "List.rev exported in all targets", "Eps failure has singleton witnesses",
                         "all successful generated files retained", "no generated program executed"],
              "outcomes": outcome}
    common.write_json(base / "tooling-validation.json", report)
    return report


def main():
    parser = common.arguments(__doc__)
    parser.add_argument("phase", choices=["scan-checkpoint", "export", "export-checkpoint",
                                         "compile", "fixture", "status"])
    parser.add_argument("--output-dir", type=Path, default=common.HERE / "full")
    parser.add_argument("--cargo", default="cargo +1.94.0")
    parser.set_defaults(timeout=0, max_heap_mb=4500)
    args = parser.parse_args()
    base = args.output_dir.resolve()
    if args.phase == "status":
        data, result, exports = load(base)
        print(json.dumps({"scan": dict(collections.Counter(r["scan"]["status"]
                           for r in result["entries"].values())),
                          "candidates": len({c for v in exports.values() for c in common.candidates(v)}),
                          "export": dict(collections.Counter(r.get("full_export", {}).get("status", "pending")
                                         for r in result["entries"].values()))}, indent=2))
        return 0
    if args.compiler_settings is None:
        args.compiler_settings = base / "compiler-settings.json"
    env, metadata = common.environment(args)
    env["CARGO"] = args.cargo
    env["RUSTFLAGS"] = (env.get("RUSTFLAGS", "") + " -Awarnings").strip()
    if args.phase == "fixture":
        print(json.dumps(fixture(base, args, env), ensure_ascii=False, indent=2))
        return 0
    with common.experiment_lock():
        data, result, exports = load(base)
        if args.skip_proofs:
            raise ValueError("The full experiment requires checked proofs")
        if args.phase == "scan-checkpoint":
            gate = scan_checkpoint(base, data, result, exports)
            gate["scan_signature"] = scan_signature(result, exports)
            common.write_json(base / "scan-checkpoint.json", gate)
            print(json.dumps({k: v for k, v in gate.items() if k != "entries"}, indent=2))
            return int(not gate["passed"])
        require_scan_gate(base, result, exports)
        if args.phase == "export-checkpoint":
            gate = export_checkpoint(base, data, result, exports)
            print(json.dumps(gate, indent=2))
            return int(not gate["passed"])
        selected = args.entries if args.entries else data["order"]
        if set(selected) - data["entries"].keys():
            raise ValueError("Unknown entry")
        result["environment"] = metadata
        if args.phase == "export":
            for i, entry in enumerate(selected, 1):
                record = result["entries"][entry]
                old = record.get("full_export", {})
                if (old.get("scope_sha256") == scope_digest(exports[entry])
                        and old.get("serializer_sha256") == serializer_signature()
                        and old.get("scan_sha256") == entry_scan_signature(record)) and old.get("status") in {
                        "complete", "no_candidates"}:
                    continue
                if old:
                    record.setdefault("full_export_history", []).append(copy.deepcopy(old))
                print(f"[export {i}/{len(selected)}] {entry}", flush=True)
                export_entry(entry, data["entries"][entry], record, exports[entry], base, args, env)
                save(base, result, exports)
                print("  " + json.dumps(record["full_export"]["languages"]), flush=True)
            return 0
        if args.phase == "compile":
            gate = export_checkpoint(base, data, result, exports)
            if not gate["passed"]:
                raise ValueError("Export checkpoint failed; inspect unresolved/environment failures first")
            env["CARGO_TARGET_DIR"] = str(base / "_build/cargo-target")
            optimizer_target = base / "_build/optimizer-target"
            preparation = common.command(
                [*shlex.split(args.cargo), "build", "--locked", "--offline",
                 "--manifest-path", str(common.PROJECT / "optimize/Cargo.toml"), "--bin", "cargo-opt",
                 "--target-dir", str(optimizer_target)],
                base / "optimizer-build.log", args, env)
            common.write_json(base / "optimizer-build.json", preparation)
            if preparation["status"] != "passed":
                raise ValueError("Optimizer preparation failed; see " + preparation["log"])
            optimizer = optimizer_target / "debug/cargo-opt"
            for i, entry in enumerate(selected, 1):
                print(f"[compile {i}/{len(selected)}] {entry}", flush=True)
                compile_entry(entry, result["entries"][entry], base, args, env, optimizer)
                save(base, result, exports)
            return 0
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, RuntimeError) as error:
        sys.exit(str(error))
    except KeyboardInterrupt:
        sys.exit(130)
