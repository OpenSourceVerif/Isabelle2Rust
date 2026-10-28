#!/usr/bin/env python3
"""Checkpointed AFP experiment: shared-frontend exports, then Rust compilation.

The original scan.py remains the candidate collector. This driver consumes its
separate output directory, preserves every export attempt, and never executes
generated programs. A phase checkpoint must match the current inputs before the
following phase can start.
"""

import collections
from contextlib import closing
import copy
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import sqlite3
import sys
import xml.etree.ElementTree as ET

import afp_common as common
import frontend_fault
from result_store import EntryStore
from run import compile_crates

TARGETS = ("Rust", "SML", "OCaml", "Haskell", "Scala", "Go")
TERMINAL = {"passed", "failed"}


def digest(value):
    return hashlib.sha256(value).hexdigest()


def file_digest(path):
    """Hash large session databases without allocating another ML-sized buffer."""
    checksum = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(block)
    return checksum.hexdigest()


def prerequisite_records(base):
    """Read current auxiliary builds separately from archived repair attempts."""
    root = base / "prerequisites"
    if root.is_dir():
        for directory in sorted(p for p in root.iterdir() if p.is_dir()):
            result = directory / "result.json"
            running = directory / "running.json"
            if result.is_file() or running.is_file():
                yield directory.name, common.read_json(result, {"status": "unfinished"}), result, running


def session_database_origin(database, session, references):
    """Require the failed database to fall within each referenced build interval.

    A later rebuild may replace a session database while an older command log
    remains. Its messages cannot silently stand in for that earlier failure.
    """
    modified = database.stat().st_mtime
    unmatched = []
    for reference in references:
        try:
            start = datetime.fromisoformat(reference["started"]).timestamp()
            end = start + float(reference["seconds"])
            matches = start - 2 <= modified <= end + 2
        except (KeyError, TypeError, ValueError):
            matches = False
        if not matches:
            unmatched.append(reference)
    try:
        with closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)) as connection:
            row = connection.execute(
                "SELECT return_code, uuid FROM isabelle_session_info WHERE session_name = ?", (session,)).fetchone()
        failed = row is not None and row[0] is not None and row[0] != 0
        database_error = None
    except sqlite3.Error as error:
        row, failed, database_error = None, False, str(error)
    return {"origin_verified": not unmatched and failed,
            "unmatched_references": unmatched, "database_modified": modified,
            "session_returncode": row[0] if row else None,
            "session_uuid": row[1] if row else None, "database_error": database_error}


def scope_digest(scope):
    return digest("\n".join(common.candidates(scope)).encode())


def inputs(base):
    """Bind gates to both discovery results and the explicit candidate scope."""
    return {name: file_digest(base / name)
            for name in ("exports.json", "results.json")}


def load(base):
    # Continuations own their manifest so a later scan cannot reinterpret
    # already frozen candidate rows or silently change their source contexts.
    manifest = base / "manifest.json"
    data = common.read_json(manifest if manifest.is_file() else common.HERE / "_build/manifest.json")
    result = common.read_json(base / "results.json")
    exports = common.read_json(base / "exports.json")
    if not data or not result or exports is None:
        raise ValueError("Initialize the experiment and run scan.py first")
    if set(data["entries"]) != set(result["entries"]) or set(data["entries"]) != set(exports):
        raise ValueError("The manifest, result rows, and export rows must cover the same AFP entries")
    if result.get("result_storage") == "content-addressed-entries-v1":
        result["entries"] = EntryStore(base, result["entries"], result["entry_files"])
    return data, result, exports



def compact_results(base):
    """Migrate a terminal legacy checkpoint without changing any entry result."""
    data, result, exports = load(base)
    if isinstance(result["entries"], EntryStore):
        return {"status": "already_compact", "entries": len(result["entries"])}
    signature = scan_signature(result, exports)
    source = base / "results.json"
    archive = base / "result-history" / ("legacy-" + file_digest(source) + ".json")
    archive.parent.mkdir(parents=True, exist_ok=True)
    if not archive.exists():
        os.link(source, archive)
    original = result["entries"]
    store = EntryStore(base, {}, {})
    serializer = serializer_signature()
    checked = 0
    # Pop each migrated record so the old monolithic object shrinks while
    # immutable per-entry files are written and independently read back.
    for entry in data["order"]:
        record = original.pop(entry)
        store[entry] = record
        store.commit(entry, entry_compiled(record, exports[entry], serializer))
        path = common.resolve_path(store.files[entry]["path"])
        if common.read_json(path) != record:
            raise ValueError("Entry migration changed result: " + entry)
        checked += 1
    result["entries"] = store
    save(base, result, exports)
    _, actual, actual_exports = load(base)
    if (scan_signature(actual, actual_exports) != signature
            or set(actual["entries"]) != set(data["entries"])):
        raise ValueError("Result migration changed the frozen discovery boundary")
    report = {"status": "passed", "checked": common.timestamp(), "entries_checked": checked,
              "legacy": common.relative(archive), "legacy_bytes": archive.stat().st_size,
              "index_bytes": (base / "results.json").stat().st_size,
              "scan_signature": signature,
              "method": "every immutable payload independently read and compared to original entry"}
    common.write_json(base / "result-storage-migration.json", report)
    return report

def entry_headers(result):
    """Read discovery and stage identities without paging in large witnesses."""
    entries = result["entries"]
    return entries.summaries if isinstance(entries, EntryStore) else entries


def entry_compiled(record, scope, serializer):
    """Collect actual compiled Rust batches for one unchanged entry."""
    compiled = {phase: set() for phase in ("stage1_compile", "stage2_compile")}
    stage = record.get("full_export", {})
    if (stage.get("serializer_sha256") != serializer
            or stage.get("scope_sha256") != scope_digest(scope)
            or stage.get("scan_sha256") != entry_scan_signature(record)
            or stage.get("status") != "complete"):
        return compiled
    for run in stage.get("runs", []):
        for attempt in run["attempts"]:
            if attempt.get("target") != "Rust" or attempt["status"] != "passed":
                continue
            for manifest in (p for p in attempt["files"] if p.endswith("/Cargo.toml")):
                checks = record.get("full_compile", {}).get(manifest, {})
                for phase in compiled:
                    if checks.get(phase, {}).get("status") == "passed":
                        compiled[phase].update(attempt["constants"])
    return compiled


def export_signature(result):
    """Bind the gate to every entry's stage while retaining a bounded buffer."""
    entries = result["entries"]
    if isinstance(entries, EntryStore):
        value = {e: entries.files.get(e, {}).get("export_sha256") for e in entries}
    else:
        value = {e: r.get("full_export") for e, r in entries.items()}
    return digest(json.dumps(value, sort_keys=True).encode())


def save(base, result, exports, entry=None):
    # Entry payloads contain large XML inventories. Commit the modified entry
    # before a traversal can evict its working record, then aggregate headers.
    serializer = serializer_signature()
    entries = result["entries"]
    if isinstance(entries, EntryStore) and entry is not None:
        entries.commit(entry, entry_compiled(entries[entry], exports[entry], serializer))
    compiled = {phase: set() for phase in ("stage1_compile", "stage2_compile")}
    for name, record in entry_headers(result).items():
        if isinstance(entries, EntryStore):
            stage = record.get("full_export", {})
            if (stage.get("serializer_sha256") != serializer
                    or stage.get("scope_sha256") != scope_digest(exports[name])
                    or stage.get("scan_sha256") != entry_scan_signature(record)):
                continue
            coverage = record.get("_compiled_candidates", {})
        else:
            coverage = entry_compiled(record, exports[name], serializer)
        for phase in compiled:
            compiled[phase].update(coverage.get(phase, []))
    known = {c for scope in exports.values() for c in common.candidates(scope)}
    result["coverage"] = {"entries": len(entries), "distinct_candidates": len(known),
                          "distinct_stage1_compiled_candidates": len(compiled["stage1_compile"]),
                          "distinct_stage2_compiled_candidates": len(compiled["stage2_compile"])}
    result["updated"] = common.timestamp()
    common.write_json(base / "results.json",
                      entries.serialize(result) if isinstance(entries, EntryStore) else result)


def infrastructure(text):
    """Keep configuration failures out of backend defect statistics."""
    patterns = {
        "timeout": r"(?m)^timeout$|timed out|Timeout\.TIMEOUT|\*\*\*.*timeout|Timeout after",
        "interruption": r"(?m)^(?:interrupted|running|starting)$|host_restart",
        "memory_or_stack": r"memory_limit|out of memory|run out of store|unable to increase stack|Interrupt_Breakdown|cannot allocate|java heap space",
        "missing_dependency": r"command not found|no such file or directory|missing .*installation|missing .*compiler|cannot find.*(?:ocaml|ghc|sml|go)|Bad session",
        "tooling": r"Protocol_Message|has not been declared|Static Errors|ML error",
    }
    return [category for category, pattern in patterns.items()
            if re.search(pattern, text, re.IGNORECASE)]


def log_text(item):
    log = item.get("log")
    path = common.resolve_path(log) if log else None
    return path.read_text(errors="replace") if path and path.is_file() else item.get("error_excerpt", "")


def archive_scan_messages(base, result, args, env):
    """Keep complete failed-session messages before any environment repair.

    Isabelle's build console truncates long messages. The database and the
    unfiltered build_log output are separate immutable evidence, including
    warnings and error positions in the original theory.
    """
    index = common.read_json(base / "scan-messages/index.json", {})
    needed = {}
    for value in index.values():
        value["current"] = False
    for entry, record in result["entries"].items():
        for check in record.get("scan", {}).get("loading", []):
            if check.get("status") not in {"passed", "blocked"}:
                for session in check.get("failed_sessions", []):
                    needed.setdefault(session, []).append(
                        {"entry": entry, "command_log": check.get("log"), "started": check.get("started"),
                         "seconds": check.get("seconds")})
    heap_logs = Path(env["ISABELLE_HEAPS"]) / env["ML_IDENTIFIER"] / "log"
    for session, references in needed.items():
        database = heap_logs / (session + ".db")
        if not database.is_file():
            index[session] = {"status": "unavailable", "current": True, "reason": "No completed session database",
                              "references": references}
            continue
        checksum = file_digest(database)
        origin = session_database_origin(database, session, references)
        old = index.get(session, {})
        old.update(current=True, references=references, **origin)
        if (old.get("database_sha256") == checksum and old.get("status") == "passed"
                and origin["origin_verified"]):
            continue
        work = next_attempt(base / "scan-messages" / session)
        # Read build_log from the retained copy, not the mutable global heap
        # directory. Its environment points at a self-contained session database.
        saved_database = work / "heaps" / env["ML_IDENTIFIER"] / "log" / (session + ".db")
        saved_database.parent.mkdir(parents=True)
        shutil.copy2(database, saved_database)
        snapshot_env = dict(env, ISABELLE_HEAPS=str(work / "heaps"))
        check = common.command([args.isabelle, "build_log", "-v", session],
                               work / "messages.txt", args, snapshot_env)
        index[session] = {
            "status": check["status"] if origin["origin_verified"] else "mismatched",
            "current": True, "command": check, "references": references, **origin,
            "database": common.relative(saved_database), "database_sha256": checksum,
            "messages_sha256": file_digest(work / "messages.txt")}
        common.write_json(base / "scan-messages/index.json", index)
    common.write_json(base / "scan-messages/index.json", index)
    return index


def scan_checkpoint(base, data, result, exports):
    """Inspect failed commands and conditions before permitting any exports."""
    if (base / "scan-contract.json").is_file():
        # Frozen stores derive completion from validated session receipts.
        # The compatibility pair must agree with that authoritative snapshot.
        from scan_frozen import checkpoint
        from scan_store import Store, aggregate
        units = common.read_json(base / "units.json")
        store = Store(base)
        actual, scope = aggregate(store, data, units, result["environment"])
        if scope != exports or any(
                actual["entries"][e]["scan"] != result["entries"][e]["scan"]
                for e in data["entries"]):
            raise ValueError("summary does not match frozen receipts; recover the joint snapshot")
        gate = checkpoint(store, data, units, result["environment"])
        gate["scan_signature"] = scan_signature(result, exports)
        common.write_json(base / "scan-checkpoint.json", gate)
        return gate
    problems = []
    rows = []
    for entry in data["order"]:
        record = result["entries"][entry]
        scan = record.get("scan", {})
        status = scan.get("status", "pending")
        if status not in {"passed", "failed", "blocked"}:
            problems.append({"entry": entry, "reason": "scan has not finished"})
        # A legacy status string alone is not evidence of loaded contexts.
        info = data["entries"][entry]
        if status == "passed":
            loaded = {c.get("session") for c in scan.get("loading", []) if c.get("status") == "passed"}
            inspected = {c.get("session") for c in scan.get("inspections", []) if c.get("status") == "passed"}
            if (set(scan.get("theories", [])) != {t["path"] for t in info["theories"]}
                    or loaded != set(info.get("sessions", [])) or inspected != loaded
                    or any(c.get("status") != "passed" for c in scan.get("inspections", []))):
                problems.append({"entry": entry, "reason": "unproven session/theory coverage"})
        elif status in {"failed", "blocked"} and not scan.get("source_review"):
            problems.append({"entry": entry, "reason": "failure requires explicit source/dependency review"})
        # Reused successful scans can still contain failed code certificates.
        # A truncated excerpt is insufficient when its original XML was cleaned.
        for diagnostic in scan.get("certificate_errors", []) + scan.get("context_merge_errors", []):
            if diagnostic.get("truncated") and not (
                    common.resolve_path(diagnostic.get("detail", "__missing__"))).is_file():
                problems.append({"entry": entry, "reason": "missing full diagnostic",
                                 "constant": diagnostic.get("name"), "detail": diagnostic.get("detail")})
        for missing in scan.get("missing_theories", []):
            if missing.get("missing_conditions"):
                problems.append({"entry": entry, "reason": "missing_conditions", "theory": missing})
        for check in scan.get("loading", []) + scan.get("inspections", []):
            if check.get("status") in {"passed", "blocked"}:
                continue
            message_index = common.read_json(base / "scan-messages/index.json", {})
            complete_logs = [log_text(message_index[session]["command"])
                             for session in check.get("failed_sessions", [])
                             if message_index.get(session, {}).get("status") == "passed"]
            issues = infrastructure(check.get("status", "") + "\n" + log_text(check)
                                    + "\n" + "\n".join(complete_logs))
            if issues:
                problems.append({"entry": entry, "session": check.get("session"),
                                 "issues": issues, "log": check.get("log")})
        rows.append({"entry": entry, "status": status,
                     "theories": len(scan.get("theories", [])),
                     "expected_theories": len(data["entries"][entry]["theories"]),
                     "candidates": len(common.candidates(exports[entry]))})
    # Auxiliary cache builds are part of environment preparation. A pending or
    # failed build must be reviewed before the main export stage begins.
    for name, check, path, running in prerequisite_records(base):
        if check.get("status") != "passed":
            problems.append({"prerequisite": name, "reason": "prerequisite build unresolved",
                             "status": check.get("status"), "result": common.relative(path)})
    gate = {"phase": "scan", "checked": common.timestamp(), "inputs": inputs(base),
            "passed": not problems, "infrastructure_failures": problems, "entries": rows,
            "phase_counts": dict(collections.Counter(row["status"] for row in rows))}
    common.write_json(base / "scan-checkpoint.json", gate)
    return gate


def scan_signature(result, exports):
    # Only semantic input/context facts and the retained scope bind exports.
    return digest(json.dumps({"scan": {e: entry_scan_signature(r)
                                      for e, r in entry_headers(result).items()},
                              "exports": exports}, sort_keys=True).encode())


def initialize_candidates(base, source):
    """Freeze an explicitly selected current-candidate experiment, without rescanning.

    This contract accepts the existing discovery boundary, including upstream
    failures. It never marks the original scan checkpoint as passed. The joint
    receipt snapshot, full scan records and all 893 rows remain reviewable.
    """
    if base.exists() and any(base.iterdir()):
        raise ValueError("Candidate continuation requires an empty work directory")
    pointer = common.read_json(source / "scan-current.json", {})
    snapshot = source / pointer.get("snapshot", "__missing__")
    if not snapshot.resolve().is_relative_to(source.resolve()) or not snapshot.is_file() or file_digest(snapshot) != pointer.get("sha256"):
        raise ValueError("Current scan snapshot is missing or has changed")
    joint = common.read_json(snapshot)
    original_result, exports = joint["results"], joint["exports"]
    data = common.read_json(source / "manifest.json")
    if (set(data["entries"]) != set(original_result["entries"])
            or set(data["entries"]) != set(exports)):
        raise ValueError("Candidate snapshot does not cover the complete manifest")
    baseline = base / "baseline"
    baseline.mkdir(parents=True)
    files = {}
    for name, path in (("snapshot.json", snapshot), ("manifest.json", source / "manifest.json"),
                       ("scan-checkpoint.json", source / "scan-checkpoint.json"),
                       ("source-inputs.json", source / "source-inputs.json")):
        shutil.copy2(path, baseline / name)
        files[name] = file_digest(baseline / name)
    shutil.copy2(baseline / "manifest.json", base / "manifest.json")
    result = copy.deepcopy(original_result)
    # Export and compile results belong to this run, not an earlier experiment.
    for record in result["entries"].values():
        for key in list(record):
            if key.startswith("full_export") or key.startswith("full_compile"):
                del record[key]
    contract = {
        "mode": "current_candidates", "created": common.timestamp(),
        "source": common.relative(source), "snapshot": common.relative(snapshot),
        "snapshot_sha256": pointer["sha256"], "baseline_files": files,
        "scan_signature": scan_signature(result, exports),
        "scan_complete": bool(common.read_json(source / "scan-checkpoint.json").get("passed")),
        "scan_counts": dict(collections.Counter(r["scan"]["status"] for r in result["entries"].values())),
        "entries": len(data["entries"]),
        "candidate_references": sum(len(common.candidates(v)) for v in exports.values()),
        "distinct_candidate_names": len({c for v in exports.values() for c in common.candidates(v)}),
        "scope": "All candidates in the selected current scan; upstream unknown scopes remain blocked"}
    # Receipt validation errors and dependency-only blocks are distinct from
    # native command failures. Preserve their causes for the downstream reports.
    from candidate_scope import freeze_receipts
    freeze_receipts(base, source, result, files)
    result["scope_contract"] = {"mode": "current_candidates", "source": contract["source"]}
    common.write_json(base / "results.json", result)
    common.write_json(base / "exports.json", exports)
    common.write_json(base / "candidate-baseline.json", contract)
    # Bind the actual files used during this continuation separately from the
    # frozen scanner's historical inventory and any documented source repairs.
    afp = common.resolve_path(result["environment"]["afp_root"]) / "thys"
    source_inputs = common.read_json(baseline / "source-inputs.json")
    paths = [afp / name for name in source_inputs["afp"]]
    paths += list((common.resolve_path("translate")).glob("*.ML"))
    paths += list((common.resolve_path("translate")).glob("*.thy"))
    paths += [common.HERE / name for name in
              ("full.py", "full_export.ML", "run.py", "afp_common.py", "candidate_scope.py", "result_store.py")]
    common.write_json(base / "source-manifest.json",
                      {common.relative(p): file_digest(p) for p in paths if p.is_file()})
    return contract


def candidate_baseline_matches(base, result, exports):
    """Verify the selected snapshot without upgrading incomplete discovery."""
    contract = common.read_json(base / "candidate-baseline.json", {})
    if contract.get("mode") != "current_candidates":
        return False
    for name, checksum in contract.get("baseline_files", {}).items():
        path = base / "baseline" / name
        if not path.is_file() or file_digest(path) != checksum:
            return False
    baseline = common.read_json(base / "baseline/snapshot.json", {})
    original = baseline.get("results", {}).get("entries", {})
    return (baseline.get("exports") == exports and set(original) == set(result["entries"])
            and all(original[e]["scan"] == r["scan"] for e, r in entry_headers(result).items())
            and file_digest(base / "manifest.json") ==
                contract.get("baseline_files", {}).get("manifest.json")
            and contract.get("scan_signature") == scan_signature(result, exports))


def require_scan_gate(base, result, exports):
    # An explicit current-candidate contract is a separate authorized scope.
    # It preserves failed discovery rows instead of forging a passing scan gate.
    if (base / "candidate-baseline.json").exists():
        if candidate_baseline_matches(base, result, exports):
            return
        raise ValueError("Selected current-candidate baseline changed")
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
        '(Path.explode ' + common.quote(str(common.HERE / "full_capture.ML")) + ')')
    argv = [args.isabelle, "process", "-l", session, "-d", str(common.PROJECT),
            "-d", str(args.afp / "thys"), "-o", "threads=1", "-o", "parallel_proofs=0",
            "-o", "timeout=" + str(args.timeout), "-o", "skip_proofs=false",
            "-T", "Rust.Rust_BigInt_Setup", "-T", "Go.Go_Setup", "-e", expression]
    # The outer recorder evaluates the unchanged exporter, then re-raises its
    # original exception. Its separate receipt cannot establish a completed
    # frontend or alter candidate verdicts when the request is interrupted.
    actual = dict(env, AFP_FULL_OUTPUT=str(work), AFP_FULL_SCOPE=str(work / "scope.txt"),
                  AFP_FULL_THEORIES=str(work / "theories.txt"),
                  AFP_ORIGINAL_EXPORT_ML=str(common.HERE / "full_export.ML"))
    # These raw processes only read existing heaps. The full experiment lock
    # serializes the main phases; the fixture may use a separate immutable HOL heap.
    check = common.command(argv, work / "process.log", args, actual)
    common.write_json(work / "process.json", check)
    return check


def collect_attempts(work):
    records = []
    files = sorted(work.glob("attempts/**/*.xml"))
    if (work / "context-merge.xml").is_file():
        files.append(work / "context-merge.xml")
    for file in files:
        node = ET.parse(file).getroot()
        value = dict(node.attrib, evidence=common.relative(file),
                     constants=[c.attrib["name"] for c in node.findall("constant")],
                     languages=[c.text for c in node.findall("language")],
                     files=[common.relative(work / c.text) for c in node.findall("file")],
                     error=(node.findtext("error", "")[:2000]),
                     error_sha256=digest(node.findtext("error", "").encode()),
                     error_truncated=len(node.findtext("error", "")) > 2000,
                     library_only=node.findtext("library_only") == "true")
        if file.name == "context-merge.xml":
            # This aggregate import failure is diagnostic even when every
            # candidate exports successfully in an independent valid branch.
            value.update(target="aggregate_context", stage="context_merge")
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
                        outcome.pop("source_fault", None)
                        outcome["evidence"].append(attempt["evidence"])
                    elif (len(cs) == 1 or attempt.get("stage") == "context_loading") and outcome["status"] != "passed":
                        # Full exception text lives in immutable XML; do not duplicate it
                        # six times per constant in the coverage matrix.
                        outcome.update(status="failed", stage=attempt["stage"],
                                       error_excerpt=attempt["error"][:500])
                        outcome["evidence"].append(attempt["evidence"])
        # This is a derived review of an actual failed singleton request,
        # not a synthetic native frontend XML. Successful independent contexts
        # still win; the independent audit rechecks the complete source proof.
        fault = run.get("source_fault")
        if fault:
            cs = run.get("scope", [])
            if len(cs) != 1 or cs[0] != fault.get("constant") or cs[0] not in outcomes:
                raise ValueError("Source failure review requires its original singleton scope")
            for target in TARGETS:
                value = outcomes[cs[0]][target]
                if value["status"] != "passed":
                    value.update(status="failed", stage="frontend_source_algorithm",
                                 source_fault=fault["review"],
                                 error_excerpt="Verified shared frontend source algorithm failure: " + fault["family"])
                    value["evidence"].append(fault["review"])
    return outcomes


def entry_scan_signature(record):
    """Ignore timings/PIDs/diagnostic text without discarding source identity."""
    scan = record["scan"]
    facts = {key: scan.get(key) for key in
             ("semantic_identity", "policy", "theories", "contexts", "unit_ids", "unit_states")}
    if not scan.get("semantic_identity"):
        # Preserve the weaker historical evidence as historical evidence.
        facts["legacy_contexts"] = {
            phase: [(c.get("session"), c.get("status")) for c in scan.get(phase, [])]
            for phase in ("loading", "inspections")}
    return digest(json.dumps(facts, sort_keys=True).encode())


def serializer_signature():
    paths = sorted(list((common.resolve_path("translate")).glob("*.ML"))
                   + list((common.resolve_path("translate")).glob("*.thy"))
                   + [common.HERE / "full_export.ML"])
    return digest(b"".join(str(p.relative_to(common.PROJECT)).encode() + b"\0" + p.read_bytes()
                            for p in paths))


def export_memory_failure(run):
    """Distinguish resource exhaustion from a completed logical rejection."""
    if (run["command"].get("status") == "memory_limit"
            or "memory_or_stack" in infrastructure(log_text(run["command"]))):
        return True
    for attempt in run.get("attempts", []):
        if attempt.get("status") != "failed":
            continue
        node = ET.parse(common.resolve_path(attempt["evidence"])).getroot()
        if "memory_or_stack" in infrastructure(node.findtext("error", "")):
            return True
    return False


def registered_source_fault(base, entry, scope, group):
    """Require an explicit, input-bound case; resource exhaustion alone is insufficient."""
    registry = common.read_json(base / "frontend-fault-cases.json", {})
    cases = [case for case in registry.get("cases", [])
             if len(group) == 1 and case.get("entry") == entry and case.get("constant") == group[0]]
    if not cases:
        return None
    if (len(cases) != 1 or registry.get("schema") != 1
            or registry.get("serializer_sha256") != serializer_signature()
            or registry.get("candidate_scope_sha256") != file_digest(base / "exports.json")):
        raise ValueError("Stale or ambiguous source algorithm registry")
    # Repeated internal names need each source owner's own context witness.
    # Keep those declarations on the ordinary path until their source-specific
    # rejection evidence is supported; never borrow another owner's diagnosis.
    if sum(group[0] in names for names in scope.values()) != 1:
        raise ValueError("Source algorithm review requires an unambiguous source declaration")
    return cases[0]


def annotate_source_faults(entry, record, scope, stage, base):
    """Attach derived reviews while leaving all original native evidence intact."""
    changed = False
    for run in stage.get("runs", []):
        if run.get("source_fault"):
            frontend_fault.validate_record(run, stage["serializer_sha256"])
            continue
        if run["command"].get("status") != "failed" or run.get("finished"):
            continue
        case = registered_source_fault(base, entry, scope, run.get("scope", []))
        if case is None:
            continue
        run["source_fault"] = frontend_fault.prepare_record(
            run, common.resolve_path(case["observation"]), case["family"], stage["serializer_sha256"])
        changed = True
    return changed


def review_source_faults(base, data, result, exports):
    """Adjudicate only current source cases under the caller's experiment lock."""
    changed = []
    if not (base / "frontend-fault-cases.json").is_file():
        return changed
    for entry in data["order"]:
        record = result["entries"][entry]
        stage = record.get("full_export", {})
        if (stage.get("scope_sha256") != scope_digest(exports[entry])
                or stage.get("scan_sha256") != entry_scan_signature(record)
                or stage.get("serializer_sha256") != serializer_signature()):
            continue
        if annotate_source_faults(entry, record, exports[entry], stage, base):
            finish_export(stage, common.candidates(exports[entry]))
            # EntryStore keeps one payload. Commit this entry before another
            # read can evict it; every original failed command stays recorded.
            save(base, result, exports, entry)
            changed.append(entry)
    return changed


def export_progress_identity(entry, record, scope, sessions, theories):
    """Bind request recovery to the exact checked input context and exporter."""
    return {"entry": entry, "scope_sha256": scope_digest(scope),
            "scan_sha256": entry_scan_signature(record), "serializer_sha256": serializer_signature(),
            "original_export_script_sha256": file_digest(common.HERE / "full_export.ML"),
            "outer_capture_sha256": file_digest(common.HERE / "full_capture.ML"),
            "sessions": sessions, "theories": theories}


def export_progress_run(item, entry, base, theories):
    """Recover only original terminal process bytes; never infer an exception.

    The request sidecar, scope and theory inventory must belong to this entry.
    Native XML is reread instead of trusting cached candidate outcomes. A live
    or incompletely recorded process cannot be started a second time.
    """
    work = (common.resolve_path(item["directory"])).resolve()
    root = (base / "exports" / entry / item["session"]).resolve()
    if work.parent != root or not work.name.startswith("attempt-"):
        raise ValueError("Export progress refers to a foreign request directory")
    if ((work / "scope.txt").read_text().splitlines() != item["scope"]
            or (work / "theories.txt").read_text().splitlines() != theories):
        raise ValueError("Export progress request input changed")
    for relative, checksum in item.get("evidence_sha256", {}).items():
        path = (common.resolve_path(relative)).resolve()
        if not path.is_relative_to(work) or not path.is_file() or file_digest(path) != checksum:
            raise ValueError("Export progress native evidence changed")
    check = common.read_json(work / "process.log.json", {})
    if common.identity_matches(check):
        raise ValueError("Export progress request is still live")
    if check.get("status") in {None, "running"} or "returncode" not in check:
        raise ValueError("Export progress request has no recorded process exit")
    if check.get("log") != common.relative(work / "process.log"):
        raise ValueError("Export progress sidecar belongs to another request")
    return {"session": item["session"], "directory": common.relative(work), "scope": item["scope"],
            "command": check, "finished": (work / "finished.xml").is_file(),
            "attempts": collect_attempts(work)}


def export_progress_item(run):
    """Seal all native diagnostic receipts used to resume a completed request."""
    work = common.resolve_path(run["directory"])
    paths = [work / "scope.txt", work / "theories.txt", work / "process.log", work / "process.log.json"]
    paths += list(work.glob("contexts/*.xml")) + list(work.glob("attempts/**/*.xml"))
    paths += [common.resolve_path(file) for attempt in run["attempts"]
              if attempt["status"] == "passed" for file in attempt["files"]]
    paths += [work / "request-resources.json"] if (work / "request-resources.json").is_file() else []
    paths += [work / name for name in ["finished.xml", "context-merge.xml", "native-request-outcome.xml"]
              if (work / name).is_file()]
    return {"session": run["session"], "directory": run["directory"], "scope": run["scope"],
            "evidence_sha256": {common.relative(path): file_digest(path) for path in paths if path.is_file()}}


def validate_export_progress(progress, identity, names):
    """Require an exact disjoint partition for every original export context."""
    if progress.get("schema") != 1 or progress.get("identity") != identity:
        raise ValueError("Stale export progress input identity")
    owner = progress.get("owner", {})
    if common.identity_matches(owner) and owner.get("pid") != os.getpid():
        raise ValueError("Export progress still has a live scheduler")
    expected = collections.Counter((session, name) for session in identity["sessions"] for name in names)
    actual = collections.Counter((item["session"], name)
                                 for item in progress.get("runs", []) + progress.get("pending", [])
                                 for name in item["scope"])
    if actual != expected or any(not item["scope"] for item in progress.get("pending", [])):
        raise ValueError("Export progress does not partition the original candidate contexts")
    if any(not item.get("evidence_sha256") for item in progress.get("runs", []) + progress.get("retries", [])):
        raise ValueError("Export progress completed request has no evidence digests")
    directories = [item["directory"] for item in progress.get("runs", []) + progress.get("retries", [])]
    if len(directories) != len(set(directories)):
        raise ValueError("Export progress repeats a native request")
    active = progress.get("active")
    if active and (not progress.get("pending")
                   or any(active[key] != progress["pending"][0][key] for key in ["session", "scope"])
                   or active["directory"] in directories):
        raise ValueError("Export progress active request differs from the pending queue")


def export_entry(entry, info, record, scope, base, args, env):
    names = common.candidates(scope)
    previous = record.get("full_export", {})
    batch_size = getattr(args, "export_batch_size", 0)
    if batch_size < 0:
        raise ValueError("export-batch-size must be nonnegative")
    if not batch_size and any(export_memory_failure(run) for run in previous.get("runs", [])):
        batch_size = max(1, min(32, previous.get("initial_batch_size", len(names)) // 2))
    batch_size = batch_size or max(1, len(names))
    sessions = maximal_sessions(info, record["scan"])
    scanned = set(record["scan"].get("theories", []))
    theory_names = [t["name"] for t in info["theories"] if t["path"] in scanned]
    identity = export_progress_identity(entry, record, scope, sessions, theory_names)
    progress_path = base / "export-progress" / (entry + ".json")
    progress = common.read_json(progress_path, {})
    # A terminal journal can precede the atomic entry publication. If the
    # saved entry already equals that terminal stage, a blocked retry is fresh;
    # otherwise consume the completed journal rather than repeat every child.
    previous_digest = digest(json.dumps(previous, sort_keys=True).encode())
    resuming = (progress.get("status") == "running" or (
        progress.get("status") in {"complete", "blocked"}
        and progress.get("final_stage_sha256") != previous_digest))
    if resuming:
        validate_export_progress(progress, identity, names)
        # Native logs are immutable recovery inputs. A changed file is a hard
        # error rather than permission to reuse an old reported verdict.
        runs = [export_progress_run(item, entry, base, theory_names) for item in progress["runs"]]
        retries = [export_progress_run(item, entry, base, theory_names) for item in progress["retries"]]
        if any(len(run["scope"]) < 2 or not export_memory_failure(run) for run in retries):
            raise ValueError("Export progress retry lacks its original aggregate resource failure")
        batch_size = progress["initial_batch_size"]
    else:
        runs, retries = [], []
        pending = [{"session": session, "scope": names[index:index + batch_size]}
                   for session in sessions for index in range(0, len(names), batch_size)]
        progress = {"schema": 1, "identity": identity, "status": "running",
                    "started": common.timestamp(), "initial_batch_size": batch_size,
                    "runs": [], "retries": [], "pending": pending, "active": None}
    if record.get("full_compile"):
        record.setdefault("full_compile_history", []).append(record.pop("full_compile"))
    stage = {"scope_sha256": identity["scope_sha256"], "serializer_sha256": identity["serializer_sha256"],
             "scan_sha256": identity["scan_sha256"], "started": progress["started"],
             "initial_batch_size": batch_size, "runs": runs}
    record["full_export"] = stage
    if not names:
        stage.update(status="no_candidates" if record["scan"]["status"] == "passed" else "blocked",
                     candidates={}, languages={t: "no_candidates" if record["scan"]["status"] == "passed"
                                               else "blocked" for t in TARGETS})
        return
    def retain_retry(run):
        record.setdefault("full_export_history", []).append({
            "scope_sha256": stage["scope_sha256"], "scan_sha256": stage["scan_sha256"],
            "serializer_sha256": stage["serializer_sha256"], "runs": [run],
            "status": "resource_retry", "reason": "memory_partition",
            "started": run["command"].get("started"), "finished": run["command"].get("finished")})
    for run in retries:
        retain_retry(run)
    def persist():
        progress["owner"] = {"pid": os.getpid(), "identity": common.process_identity(os.getpid())}
        progress["updated"] = common.timestamp()
        common.write_json(progress_path, progress)
    def accept(run):
        group = run["scope"]
        progress["pending"].pop(0)
        if len(group) > 1 and export_memory_failure(run):
            retain_retry(run)
            progress["retries"].append(export_progress_item(run))
            # Registered observations only choose smaller request scopes here;
            # they do not determine outcomes without their own native failure.
            if any(registered_source_fault(base, entry, scope, [name]) for name in group):
                groups = [[name] for name in group]
            else:
                middle = len(group) // 2
                groups = [group[:middle], group[middle:]]
            progress["pending"][0:0] = [{"session": run["session"], "scope": part} for part in groups]
            print(f"  [memory retry] {entry}/{run['session']}: {len(group)} -> "
                  + " + ".join(str(len(part)) for part in groups), flush=True)
        else:
            stage["runs"].append(run)
            progress["runs"].append(export_progress_item(run))
        progress["active"] = None
        persist()
    if progress.get("active"):
        # A crash after the child exited but before the checkpoint committed
        # consumes that same physical request once, without launching it again.
        accept(export_progress_run(progress["active"], entry, base, theory_names))
    persist()
    for run in stage["runs"]:
        if len(run["scope"]) == 1:
            annotate_source_faults(entry, record, scope, {"runs": [run],
                                   "serializer_sha256": stage["serializer_sha256"]}, base)
    while progress["pending"]:
        job = progress["pending"][0]
        session, group = job["session"], job["scope"]
        work = next_attempt(base / "exports" / entry / session)
        (work / "scope.txt").write_text("\n".join(group) + "\n")
        (work / "theories.txt").write_text("\n".join(theory_names) + "\n")
        progress["active"] = dict(job, directory=common.relative(work))
        persist()
        request_env = dict(env)
        cap = getattr(args, "source_fault_heap_mb", 0)
        if cap < 0:
            raise ValueError("source-fault-heap-mb must be nonnegative")
        if cap and registered_source_fault(base, entry, scope, group):
            # This is a memory bound, not a timer or a synthetic rejection.
            # The unchanged native script still has to exit naturally, and its
            # source invariant is independently checked before adjudication.
            request_env["ML_OPTIONS"] = re.sub(r"(--maxheap\s+)\d+",
                lambda match: match[1] + str(min(cap, args.max_heap_mb)), request_env["ML_OPTIONS"])
        common.write_json(work / "request-resources.json", {
            "ML_OPTIONS": request_env.get("ML_OPTIONS"),
            "registered_source_fault_heap_mb": cap if request_env != env else None,
            "command_timeout_seconds": getattr(args, "timeout", 0)})
        check = export_command(session, work, args, request_env)
        run = {"session": session, "directory": common.relative(work), "scope": group,
               "command": check, "finished": (work / "finished.xml").is_file(),
               "attempts": collect_attempts(work)}
        accept(run)
        if len(group) == 1:
            annotate_source_faults(entry, record, scope, {"runs": [run],
                                   "serializer_sha256": stage["serializer_sha256"]}, base)
    annotate_source_faults(entry, record, scope, stage, base)
    finish_export(stage, names)
    progress.update(status=stage["status"], finished=common.timestamp(),
                    final_stage_sha256=digest(json.dumps(stage, sort_keys=True).encode()))
    persist()


def finish_export(stage, names):
    """Finish adjudicating coverage, retaining failed native process fields.

    A source-fault review is prepared only from a real singleton exception and
    a checked recursive invariant. The gate and independent audit recompute it;
    processing complete never changes that process's status or finished flag.
    """
    stage["candidates"] = resolve_candidates(names, stage["runs"])
    languages = {}
    for target in TARGETS:
        counts = collections.Counter(x[target]["status"] for x in stage["candidates"].values())
        languages[target] = ("blocked" if counts["blocked"] else
                             "passed" if counts["passed"] == len(names) else
                             "failed" if counts["failed"] == len(names) else "partial")
    stage.update(languages=languages, finished=common.timestamp(),
                 status="complete" if all((run["finished"] and run["command"]["status"] == "passed")
                                         or run.get("source_fault") for run in stage["runs"])
                 and all(x[t]["status"] in TERMINAL for x in stage["candidates"].values() for t in TARGETS)
                 else "blocked")
    # Keep every generated source; compilation uses this inventory rather than
    # assuming that a whole-entry aggregate produced exactly one Rust crate.
    stage["artifacts"] = [
        {"path": file, "sha256": file_digest(common.resolve_path(file)),
         "bytes": (common.resolve_path(file)).stat().st_size}
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
            reviewed = False
            if run.get("source_fault"):
                try:
                    frontend_fault.validate_record(run, stage["serializer_sha256"])
                    reviewed = True
                except (ValueError, OSError, KeyError, TypeError, ET.ParseError) as error:
                    problems.append({"entry": entry, "reason": "invalid source algorithm evidence",
                                     "error": str(error), "command": run["command"]})
            if not reviewed and (not run.get("finished") or run["command"]["status"] != "passed"):
                problems.append({"entry": entry, "reason": "incomplete process",
                                 "command": run["command"]})
        for run in stage.get("runs", []):
            for attempt in run.get("attempts", []):
                if attempt.get("status") == "failed":
                    # Serializer errors can exceed the summary excerpt. Inspect
                    # the immutable complete exception for environment blockers.
                    evidence = common.resolve_path(attempt["evidence"])
                    message = ET.parse(evidence).getroot().findtext("error", "")
                    issues = infrastructure(message)
                    if issues:
                        problems.append({"entry": entry, "reason": "export infrastructure failure",
                                         "issues": issues, "evidence": attempt["evidence"]})
        for artifact in stage.get("artifacts", []):
            path = common.resolve_path(artifact["path"])
            if not path.is_file() or file_digest(path) != artifact["sha256"]:
                problems.append({"entry": entry, "reason": "missing/changed export", "path": str(path)})
    identity = export_signature(result)
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
        source = common.resolve_path(manifest)
        key = digest(manifest.encode())[:20]
        logs = next_attempt(base / "compilation" / entry / key)
        out = base / "rust-stage2" / entry / key / logs.name
        item = compiled[manifest] = {"started": common.timestamp(), "stage2": common.relative(out)}
        item["stage1_compile"] = compile_crates([source], "stage1", args, env, logs)
        item["optimization"] = common.command(
            ["sh", str(common.resolve_path("scripts/with-stack.sh")), "65536", str(optimizer),
             str(source.parent), "--out-dir", str(out)],
            logs / "optimization.log", args, env)
        if item["optimization"]["status"] == "passed" and (out / "Cargo.toml").is_file():
            item["stage2_compile"] = compile_crates([out / "Cargo.toml"], "stage2", args, env, logs)
        else:
            item["stage2_compile"] = {"status": "blocked", "reason": "optimization failed",
                                      "log": item["optimization"]["log"]}
        # Snapshot optimized sources after Cargo has supplied its lockfile.
        # Global CARGO_TARGET_DIR keeps build caches outside the retained tree.
        item["stage2_artifacts"] = [
            {"path": common.relative(p), "sha256": file_digest(p), "bytes": p.stat().st_size}
            for p in sorted(out.rglob("*")) if p.is_file()] if out.is_dir() else []
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
    files = [common.resolve_path(f) for a in runs[0]["attempts"] for f in a["files"]]
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
    parser.add_argument("phase", choices=["init", "compact-results", "scan-checkpoint", "export", "export-checkpoint",
                                         "compile", "fixture", "status"])
    parser.add_argument("--output-dir", type=Path, default=common.WORK)
    parser.add_argument("--cargo", default="cargo +1.94.0")
    parser.add_argument("--export-batch-size", type=int, default=0,
                        help="maximum initial constants per process; 0 adapts prior memory failures")
    parser.add_argument("--source-fault-heap-mb", type=int, default=0,
                        help="optional native heap cap for explicitly registered source observations; 0 keeps the normal heap")
    parser.add_argument("--candidate-baseline", type=Path,
                        help="init only: freeze the selected current scan, preserving its upstream failures")
    parser.set_defaults(timeout=0, max_heap_mb=4500)
    args = parser.parse_args()
    base = args.output_dir.resolve()
    if args.phase == "compact-results":
        with common.experiment_lock():
            print(json.dumps(compact_results(base), indent=2))
        return 0
    if args.phase == "init":
        if args.candidate_baseline is None:
            raise ValueError("init requires --candidate-baseline")
        with common.experiment_lock():
            print(json.dumps(initialize_candidates(base, args.candidate_baseline.resolve()), indent=2))
        return 0
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
            messages = archive_scan_messages(base, result, args, env)
            gate = scan_checkpoint(base, data, result, exports)
            gate["full_session_messages"] = common.relative(base / "scan-messages/index.json")
            gate["message_archive_failures"] = [
                session for session, item in messages.items()
                if item.get("current") and item["status"] != "passed"]
            if gate["message_archive_failures"]:
                gate["passed"] = False
            gate["scan_signature"] = scan_signature(result, exports)
            common.write_json(base / "scan-checkpoint.json", gate)
            print(json.dumps({k: v for k, v in gate.items() if k != "entries"}, indent=2))
            return int(not gate["passed"])
        require_scan_gate(base, result, exports)
        if args.phase == "export-checkpoint":
            review_source_faults(base, data, result, exports)
            gate = export_checkpoint(base, data, result, exports)
            print(json.dumps(gate, indent=2))
            return int(not gate["passed"])
        selected = args.entries if args.entries else data["order"]
        if set(selected) - data["entries"].keys():
            raise ValueError("Unknown entry")
        result["environment"] = metadata
        if args.phase == "export":
            # Recheck retained singleton evidence before deciding which entries
            # need fresh processes; a verified source failure need not recur.
            review_source_faults(base, data, result, exports)
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
                save(base, result, exports, entry)
                print("  " + json.dumps(record["full_export"]["languages"]), flush=True)
            return 0
        if args.phase == "compile":
            review_source_faults(base, data, result, exports)
            gate = export_checkpoint(base, data, result, exports)
            if not gate["passed"]:
                raise ValueError("Export checkpoint failed; inspect unresolved/environment failures first")
            env["CARGO_TARGET_DIR"] = str(base / "_build/cargo-target")
            optimizer_target = base / "_build/optimizer-target"
            preparation = common.command(
                [*shlex.split(args.cargo), "build", "--locked", "--offline",
                 "--manifest-path", str(common.resolve_path("optimize/Cargo.toml")), "--bin", "cargo-opt",
                 "--target-dir", str(optimizer_target)],
                base / "optimizer-build.log", args, env)
            common.write_json(base / "optimizer-build.json", preparation)
            if preparation["status"] != "passed":
                raise ValueError("Optimizer preparation failed; see " + preparation["log"])
            optimizer = optimizer_target / "debug/cargo-opt"
            for i, entry in enumerate(selected, 1):
                print(f"[compile {i}/{len(selected)}] {entry}", flush=True)
                compile_entry(entry, result["entries"][entry], base, args, env, optimizer)
                save(base, result, exports, entry)
            return 0
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, RuntimeError) as error:
        sys.exit(str(error))
    except KeyboardInterrupt:
        sys.exit(130)
