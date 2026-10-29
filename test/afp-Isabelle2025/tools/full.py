#!/usr/bin/env python3
"""Checkpointed AFP experiment: shared-frontend exports, then Rust compilation.

Scanning, exports and compilation share one current-state database. Native
evidence is retained only for current results and unfinished work. Generated
programs are never executed. A phase checkpoint must match the current inputs before the
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
import tempfile
import xml.etree.ElementTree as ET

import afp_common as common
import frontend_fault
from result_store import EntryStore
from state import State
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
    """Enumerate only current prerequisite results in this run."""
    state = State(base)
    names = {key.split("/")[1] for key in state.keys("prerequisites/") if key.endswith(("/result.json", "/running.json")) and len(key.split("/")) == 3}
    for name in sorted(names):
        result = base / "prerequisites" / name / "result.json"
        running = result.with_name("running.json")
        yield name, common.read_record(result, {"status": "unfinished"}), result, running


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
    """Bind checkpoints to current committed inputs/results, not audit metadata."""
    return {"state": State(base).signature(("run", "receipt/", "entry/", "units/", "exports/", "compilation/"))}


def load(base):
    from scan_store import load_snapshot
    state = State(base)
    run = state.get("run")
    if not run:
        raise ValueError("Initialize and scan the experiment first")
    result, exports = load_snapshot(base)
    result["entries"] = EntryStore(base, result["entries"], exports)
    result["updated"] = state.get("updated", run["created"])
    result["coverage"] = coverage(result, exports)
    return run["manifest"], result, exports


def entry_headers(result):
    entries = result["entries"]
    return entries.scans if isinstance(entries, EntryStore) else entries


def entry_compiled(record, scope, serializer):
    compiled = {phase: set() for phase in ("stage1_compile", "stage2_compile")}
    stage = record.get("full_export", {})
    if (stage.get("serializer_sha256") != serializer or stage.get("scope_sha256") != scope_digest(scope)
            or stage.get("scan_sha256") != entry_scan_signature(record) or stage.get("status") != "complete"):
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


def coverage(result, exports):
    compiled = {phase: set() for phase in ("stage1_compile", "stage2_compile")}
    serializer = serializer_signature()
    for entry, record in result["entries"].items():
        for phase, names in entry_compiled(record, exports[entry], serializer).items():
            compiled[phase].update(names)
    return {"entries": len(exports), "distinct_candidates": len({c for scope in exports.values() for c in common.candidates(scope)}),
            **{"distinct_" + p.replace("_compile", "_compiled") + "_candidates": len(v) for p, v in compiled.items()}}


def export_signature(result):
    checksum = hashlib.sha256()
    for entry, record in result["entries"].items():
        checksum.update(json.dumps((entry, record.get("full_export")), sort_keys=True).encode())
    return checksum.hexdigest()


def save(base, result, exports, entry=None):
    if isinstance(result["entries"], EntryStore):
        if entry is not None:
            result["entries"].commit(entry)
    else:
        # Small isolated fixtures can supply ordinary mappings; production uses
        # the lazy store and never materializes all export witnesses at once.
        for name, record in result["entries"].items():
            State(base).put("entry/" + name, record)
    if not isinstance(result["entries"], EntryStore):
        result["coverage"] = coverage(result, exports)
    result["updated"] = common.timestamp()
    State(base).put("updated", result["updated"])


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
    """Extract complete diagnostics from a checked temporary database copy.

    The console truncates errors. Retain its full build_log text and the source
    database identity, then discard the database copy once extraction completes.
    """
    needed, index = {}, {}
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
            index[session] = {"status": "unavailable", "current": True,
                              "reason": "No completed session database", "references": references}
            continue
        work = base / "scan-messages" / session
        work.mkdir(parents=True, exist_ok=True)
        # build_log sees a stable copy even if the shared heap is later rebuilt.
        # The copy is a temporary extraction input, never a retained result.
        with tempfile.TemporaryDirectory(prefix="afp-messages-") as temporary:
            heaps = Path(temporary)
            saved = heaps / env["ML_IDENTIFIER"] / "log" / (session + ".db")
            saved.parent.mkdir(parents=True)
            shutil.copy2(database, saved)
            origin = session_database_origin(saved, session, references)
            checksum = file_digest(saved)
            check = common.command([args.isabelle, "build_log", "-v", session],
                                   work / "messages.txt", args, dict(env, ISABELLE_HEAPS=str(heaps)))
        # Command metadata already has one authoritative database record.
        command_path = work / "messages.txt.json"
        common.write_record(command_path, check)
        index[session] = {
            "status": check["status"] if origin["origin_verified"] else "mismatched",
            "current": True, "command": common.relative(command_path), "references": references, **origin,
            "database_sha256": checksum, "messages_sha256": file_digest(work / "messages.txt")}
        common.write_record(base / "scan-messages/index.json", index)
    common.write_record(base / "scan-messages/index.json", index)
    return index


def scan_checkpoint(base, data, result, exports):
    from scan_frozen import checkpoint, make_units
    from scan_store import Store
    run = State(base).get("run")
    if not run:
        raise ValueError("Scan checkpoint requires an initialized run")
    gate = checkpoint(Store(base), data, make_units(data, run["sources"]), run["environment"])
    for name, check, _, _ in prerequisite_records(base):
        if check.get("status") != "passed":
            gate.setdefault("issues", []).append({"prerequisite": name, "status": check.get("status")})
            gate["passed"] = False
    common.write_record(base / "scan-checkpoint.json", gate)
    return gate


def scan_signature(result, exports):
    # Only semantic input/context facts and the retained scope bind exports.
    return digest(json.dumps({"scan": {e: entry_scan_signature(r)
                                      for e, r in entry_headers(result).items()},
                              "exports": exports}, sort_keys=True).encode())


def require_scan_gate(base, result, exports):
    gate = common.read_record(base / "scan-checkpoint.json", {})
    if not gate.get("passed") or gate.get("scan_signature") != scan_signature(result, exports):
        raise ValueError("A current passing scan-checkpoint is required; resolve scan failures first")


def maximal_sessions(info, scan):
    """Use loaded maximal sessions; a failed example cannot erase its usable core."""
    loaded = [x["session"] for x in scan.get("loading", []) if x.get("status") == "passed"]
    requirements = info.get("session_requirements", {})
    return [s for s in loaded if not any(s in requirements.get(other, []) for other in loaded if other != s)]


def next_attempt(root):
    # A replacement gets a fresh directory until its state has been committed.
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
             ("status", "semantic_identity", "policy", "theories", "missing_theories", "contexts", "unit_ids", "unit_states")}
    if not scan.get("semantic_identity"):
        # Fixtures without unit identities still bind their observed contexts.
        facts["observed_contexts"] = {
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
    registry = common.read_record(base / "frontend-fault-cases.json", {})
    cases = [case for case in registry.get("cases", [])
             if len(group) == 1 and case.get("entry") == entry and case.get("constant") == group[0]]
    if not cases:
        return None
    if (len(cases) != 1 or registry.get("schema") != 1
            or registry.get("serializer_sha256") != serializer_signature()
            or registry.get("candidate_scope_sha256") != scope_digest(scope)):
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
    if not common.has_record(base / "frontend-fault-cases.json"):
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


class UnrecordedExit(ValueError):
    """A dead request has no authoritative terminal command result."""


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
    check = common.read_record(work / "process.log.json", {})
    if common.identity_matches(check):
        raise ValueError("Export progress request is still live")
    if check.get("status") in {None, "running"} or "returncode" not in check:
        raise UnrecordedExit("Export progress request has no recorded process exit")
    if check.get("log") != common.relative(work / "process.log"):
        raise ValueError("Export progress sidecar belongs to another request")
    return {"session": item["session"], "directory": common.relative(work), "scope": item["scope"],
            "command": check, "finished": (work / "finished.xml").is_file(),
            "attempts": collect_attempts(work)}


def export_progress_item(run):
    """Seal all native diagnostic receipts used to resume a completed request."""
    work = common.resolve_path(run["directory"])
    paths = [work / "scope.txt", work / "theories.txt", work / "process.log"]
    paths += list(work.glob("contexts/*.xml")) + list(work.glob("attempts/**/*.xml"))
    paths += [common.resolve_path(file) for attempt in run["attempts"]
              if attempt["status"] == "passed" for file in attempt["files"]]
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
    state_db = State(base)
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
    progress = common.read_record(progress_path, {})
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
    record.pop("full_compile", None)
    stage = {"scope_sha256": identity["scope_sha256"], "serializer_sha256": identity["serializer_sha256"],
             "scan_sha256": identity["scan_sha256"], "started": progress["started"],
             "initial_batch_size": batch_size, "runs": runs}
    record["full_export"] = stage
    if not names:
        stage.update(status="no_candidates" if record["scan"]["status"] == "passed" else "blocked",
                     candidates={}, languages={t: "no_candidates" if record["scan"]["status"] == "passed"
                                               else "blocked" for t in TARGETS})
        return
    def persist():
        progress["owner"] = {"pid": os.getpid(), "identity": common.process_identity(os.getpid())}
        progress["updated"] = common.timestamp()
        common.write_record(progress_path, progress)
    def retire():
        keep = {common.resolve_path(r["directory"]) for r in
                [*previous.get("runs", []), *progress["runs"], *progress["retries"],
                 *([progress["active"]] if progress.get("active") else [])] if r.get("directory")}
        for attempt in (base / "exports" / entry).glob("*/attempt-*"):
            if attempt.resolve() not in keep:
                state_db.remove_tree(attempt)
    def accept(run):
        group = run["scope"]
        progress["pending"].pop(0)
        if len(group) > 1 and export_memory_failure(run):
            progress["retries"] = [export_progress_item(run)]
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
        # Publish the queue before retiring superseded native requests.
        retire()
    if progress.get("active"):
        # A crash after the child exited but before the checkpoint committed
        # consumes that same physical request once, without launching it again.
        try:
            accept(export_progress_run(progress["active"], entry, base, theory_names))
        except UnrecordedExit:
            from scan_frozen import active_children
            if active_children(base):
                raise ValueError("Export native children are still live") from None
            # Host loss can leave partial XML without an exit status. Keep the
            # pending scope and retry it; never adopt the partial files as a verdict.
            progress["active"] = None
            persist()
            retire()
    persist()
    retire()
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
        common.write_record(work / "request-resources.json", {
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
    common.write_record(base / "export-checkpoint.json", gate)
    return gate


def compile_phase_complete(value):
    """Resource limits and lost children remain retryable, even after a checkpoint."""
    checks = value.get("checks", [])
    return bool(checks) and value.get("status") in TERMINAL and all(c.get("status") in TERMINAL for c in checks)


def crate_complete(item):
    optimized = item.get("optimization", {}).get("status")
    second = item.get("stage2_compile", {})
    return (compile_phase_complete(item.get("stage1_compile", {})) and optimized in TERMINAL
            and (compile_phase_complete(second) if optimized == "passed" else
                 second.get("status") == "blocked" and second.get("reason") == "optimization failed"))


def compile_checkpoint(base, result):
    """Only complete current crates satisfy the boundary; a native failure is a result."""
    problems = []
    count = 0
    for entry, record in result["entries"].items():
        manifests = rust_manifests(record)
        compiled = record.get("full_compile", {})
        if set(compiled) - set(manifests):
            problems.append({"entry": entry, "reason": "compilation outside current exports"})
        for manifest in manifests:
            count += 1
            item = compiled.get(manifest, {})
            if not item.get("complete") or not crate_complete(item):
                problems.append({"entry": entry, "manifest": manifest, "reason": "incomplete crate"})
    gate = {"phase": "compile", "passed": not problems, "checked": common.timestamp(),
            "input_sha256": inputs(base), "rust_crates": count, "problems": problems}
    common.write_record(base / "compile-checkpoint.json", gate)
    return gate


def completed_command(argv, log, args, env):
    """Reuse a matching exited compiler/optimizer child after driver loss."""
    existing = common.read_record(log.with_suffix(log.suffix + ".json"), {})
    if common.identity_matches(existing):
        raise ValueError("A compiler or optimizer child is still running")
    if existing.get("command") == argv and existing.get("status") in TERMINAL and "returncode" in existing:
        return existing
    return common.command(argv, log, args, env)


def compile_entry(entry, record, base, args, env, optimizer, checkpoint=None):
    compiled = record.setdefault("full_compile", {})
    for manifest in rust_manifests(record):
        item = compiled.get(manifest, {})
        if item.get("complete") and crate_complete(item):
            continue
        source = common.resolve_path(manifest)
        key = digest(manifest.encode())[:20]
        logs = common.resolve_path(item["directory"]) if item.get("directory") else next_attempt(base / "compilation" / entry / key)
        out = common.resolve_path(item["stage2"]) if item.get("stage2") else base / "rust-stage2" / entry / key / logs.name
        if not item:
            item = compiled[manifest] = {"started": common.timestamp(), "directory": common.relative(logs), "stage2": common.relative(out)}
            if checkpoint:
                checkpoint()
        def persist():
            if checkpoint:
                checkpoint()
        if not compile_phase_complete(item.get("stage1_compile", {})):
            item["stage1_compile"] = compile_crates([source], "stage1", args, env, logs)
            persist()
        if item.get("optimization", {}).get("status") not in TERMINAL:
            command = ["sh", str(common.resolve_path("scripts/with-stack.sh")), "65536", str(optimizer),
                       str(source.parent), "--out-dir", str(out)]
            # A recorded terminal optimizer result can be adopted after driver
            # loss. Otherwise remove partial output before retrying that child.
            saved = common.read_record(logs / "optimization.log.json", {})
            if common.identity_matches(saved):
                raise ValueError("An optimizer child is still running")
            if saved.get("command") != command or saved.get("status") not in TERMINAL:
                State(base).remove_tree(out)
            item["optimization"] = completed_command(command, logs / "optimization.log", args, env)
            persist()
        if not compile_phase_complete(item.get("stage2_compile", {})):
            if item["optimization"]["status"] == "passed" and (out / "Cargo.toml").is_file():
                item["stage2_compile"] = compile_crates([out / "Cargo.toml"], "stage2", args, env, logs)
            else:
                item["stage2_compile"] = {"status": "blocked", "reason": "optimization failed", "log": item["optimization"]["log"]}
        item["stage2_artifacts"] = [{"path": common.relative(p), "sha256": file_digest(p), "bytes": p.stat().st_size}
                                    for p in sorted(out.rglob("*")) if p.is_file()] if out.is_dir() else []
        item.update(complete=crate_complete(item), finished=common.timestamp())
        persist()


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
    common.write_record(base / "tooling-validation.json", report)
    return report


def main():
    parser = common.arguments(__doc__)
    parser.add_argument("phase", choices=["scan-checkpoint", "export", "export-checkpoint", "compile", "compile-checkpoint", "fixture", "status"])
    parser.add_argument("--output-dir", type=Path, default=common.WORK)
    parser.add_argument("--cargo", default="cargo +1.94.0")
    parser.add_argument("--export-batch-size", type=int, default=0)
    parser.add_argument("--source-fault-heap-mb", type=int, default=0)
    args = parser.parse_args()
    base = args.output_dir.resolve()
    if args.phase == "status":
        data, result, exports = load(base)
        print(json.dumps({"scan": dict(collections.Counter(r["scan"]["status"] for r in result["entries"].values())),
                          "export": dict(collections.Counter(r.get("full_export", {}).get("status", "pending") for r in result["entries"].values())),
                          "coverage": result["coverage"]}, indent=2))
        return 0
    env, metadata = common.environment(args)
    env["CARGO"] = args.cargo
    env["RUSTFLAGS"] = (env.get("RUSTFLAGS", "") + " -Awarnings").strip()
    if args.phase == "fixture":
        print(json.dumps(fixture(base, args, env), ensure_ascii=False, indent=2))
        return 0
    with common.experiment_lock():
        from scan_frozen import validate_contract, active_children
        if active_children(base):
            raise ValueError("Native AFP children are still running")
        validate_contract(base, args, env)
        data, result, exports = load(base)
        if isinstance(result["entries"], EntryStore):
            for entry in result["entries"]:
                result["entries"].retire(entry, result["entries"][entry])
        if args.skip_proofs:
            raise ValueError("The full experiment requires checked proofs")
        if args.phase == "scan-checkpoint":
            gate = scan_checkpoint(base, data, result, exports)
            print(json.dumps(gate, indent=2))
            return int(not gate["passed"])
        require_scan_gate(base, result, exports)
        if args.phase == "compile-checkpoint":
            return int(not compile_checkpoint(base, result)["passed"])
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
            if preparation["status"] != "passed":
                raise ValueError("Optimizer preparation failed; see " + preparation["log"])
            optimizer = optimizer_target / "debug/cargo-opt"
            for i, entry in enumerate(selected, 1):
                print(f"[compile {i}/{len(selected)}] {entry}", flush=True)
                compile_entry(entry, result["entries"][entry], base, args, env, optimizer,
                              lambda entry=entry: save(base, result, exports, entry))
                save(base, result, exports, entry)
            return int(not compile_checkpoint(base, result)["passed"])
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, RuntimeError) as error:
        sys.exit(str(error))
    except KeyboardInterrupt:
        sys.exit(130)
