#!/usr/bin/env python3
"""Discover entry-owned executable HOL constants from loaded Isabelle theories."""

import sys
import re
import xml.etree.ElementTree as ET

from afp_common import (HERE, arguments, build_lock, build_options, candidates,
                        command, environment, experiment_lock, load_results, manifest, read_json,
                        relative, save_results, select, write_json)



def failed_sessions_in_log(text, status):
    """Identify actual failed prerequisites, including stock Isabelle sessions.

    The one-job build prints a start/finish lifecycle. For a watchdog timeout,
    the currently active session is the failure, not necessarily the requested
    AFP session. Completed prerequisites must never be marked as failed.
    """
    active = set()
    failed = set()
    for line in text.splitlines():
        started = re.match(r"^(?:Building|Running) (.+?) \.\.\.$", line)
        finished = re.match(r"^Finished (.+?) \(", line)
        error = re.match(r"^(.+?) FAILED(?:\s|$)", line)
        if started:
            active.add(started.group(1))
        if finished:
            active.discard(finished.group(1))
        if error:
            failed.add(error.group(1))
            active.discard(error.group(1))
    if status in ("timeout", "memory_limit"):
        failed.update(active)
    return sorted(failed)


def scan_entry(entry, info, args, env, exports):
    """Build all entry sessions; a bad certificate never removes its constant."""
    work = HERE / "_build" / entry
    work.mkdir(parents=True, exist_ok=True)
    logs = HERE / "logs" / entry
    loading = []
    inspections = []
    errors = []
    certificate_errors = []
    context_merge_errors = []
    theories = exports.setdefault(entry, {})
    # Explicit empty lists distinguish scanned theories without equations from
    # theories that have never loaded successfully (recorded in scan.theories).
    scanned = []
    discovered = {}
    failed_sessions = set()
    for session in info["sessions"]:
        blocked = sorted(failed_sessions.intersection(
            info.get("session_requirements", {}).get(session, [])))
        if blocked:
            loading.append({"session": session, "status": "blocked", "dependencies": blocked})
            continue
        load_log = logs / (session + ".load.log")
        with build_lock():
            # ROOT conditions are evaluated from the process environment,
            # not from source timestamps. Refresh a conditional session when
            # its external compiler is available, so an older heap which
            # skipped those theories cannot masquerade as a complete scan.
            refresh = any(
                theory["session"] == session and theory.get("conditions")
                and all(env.get(name) for name in theory["conditions"])
                for theory in info["theories"])
            built = command([args.isabelle, "build", "-b", *(["-c"] if refresh else []),
                             *build_options(args),
                             "-d", str(args.afp / "thys"), session],
                            load_log, args, env)
        built["session"] = session
        loading.append(built)
        if built["status"] != "passed":
            text = load_log.read_text(errors="replace") if load_log.exists() else ""
            built["failed_sessions"] = failed_sessions_in_log(text, built["status"])
            failed_sessions.update(built["failed_sessions"])
            continue
        # Later sessions may supply equations for constants from earlier
        # sessions of the same entry. The ML collector ignores not-yet-loaded
        # theories; successful contexts contribute a union of candidates.
        owned = info["theories"]
        names = work / (session + ".theories")
        output = work / (session + ".xml")
        names.write_text("\n".join(theory["name"] for theory in owned) + "\n")
        output.unlink(missing_ok=True)
        scan_env = dict(env, AFP_SCAN_THEORIES=str(names), AFP_SCAN_OUTPUT=str(output))
        with build_lock():
            inspected = command([args.isabelle, "process", "-l", session,
                                 "-d", str(args.afp / "thys"), "-f", str(HERE / "scan.ML"),
                                 "-o", "threads=1"],
                                logs / (session + ".scan.log"), args, scan_env)
        inspected["session"] = session
        inspected["data"] = relative(output)
        inspections.append(inspected)
        if inspected["status"] != "passed":
            continue
        try:
            document = ET.parse(output).getroot()
        except (OSError, ET.ParseError) as exn:
            inspected.update(status="failed", error=str(exn))
            continue
        # Incompatible independent branches are scanned in their own loaded
        # contexts. Their candidates are unioned below; a merge diagnostic does
        # not mean discovery failed, or that a joint export can import them all.
        context_merge_errors.extend(
            {"session": session, "message": (error.text or "")[:2000],
             "detail": relative(output), "truncated": len(error.text or "") > 2000}
            for error in document.findall("context_merge_error"))
        paths = {theory["name"]: theory["path"] for theory in owned}
        for theory in document.findall("theory"):
            name = theory.attrib["name"]
            path = paths[name]
            discovered.setdefault(path, set()).update(
                c.attrib["name"] for c in theory.findall("constant"))
            theories[path] = sorted(discovered[path])
            scanned.append(path)
        errors.extend({"name": error.attrib["name"], "message": error.text}
                      for error in document.findall("error"))
        certificate_errors.extend(
            {"name": error.attrib["name"], "message": (error.text or "")[:2000],
             "detail": relative(output), "truncated": len(error.text or "") > 2000}
            for theory in document.findall("theory") for error in theory.findall("error"))
    loaded = bool(loading) and all(item["status"] == "passed" for item in loading)
    complete = loaded and len(set(scanned)) == len(info["theories"])
    status = "passed" if complete and not errors else "failed"
    return {"status": status, "theories": sorted(set(scanned)), "loading": loading,
            "inspections": inspections, "errors": errors, "certificate_errors": certificate_errors,
            "context_merge_errors": context_merge_errors,
            "candidate_count": len(candidates(theories)),
            "theory_loading": {"status": "passed" if loaded else "failed"},
            "missing_theories": [
                {"path": theory["path"], "conditions": theory.get("conditions", []),
                 "missing_conditions": [name for name in theory.get("conditions", [])
                                        if not env.get(name)]}
                for theory in info["theories"] if theory["path"] not in scanned]}


def main():
    parser = arguments(__doc__)
    args = parser.parse_args()
    env, metadata = environment(args)
    data = manifest(args, env)
    exports = read_json(HERE / "exports.json", {})
    result = load_results(metadata, data["entries"])
    for entry in data["entries"]:
        exports.setdefault(entry, {})
    selected = select(args, data, result, "scan")
    # Dependencies precede dependents; the first smoke entries can also be
    # requested explicitly without silently expanding the export scope.
    failed_sessions = set()
    processed = set()
    for index, entry in enumerate(selected, 1):
        info = data["entries"][entry]
        record = result["entries"][entry]
        # Session requirements distinguish a usable core session from failed
        # examples/tests in the same AFP entry. With that complete graph,
        # entry-wide failures must not block consumers of only the usable core.
        # Retain the conservative fallback for manifests without session data.
        failed_dependencies = [] if "required_sessions" in info else [
            dep for dep in info["dependencies"]
            if dep in processed and result["entries"][dep].get("scan", {}).get("theory_loading", {}).get("status")
            in ("failed", "blocked")]
        print(f"[scan {index}/{len(selected)}] {entry}", flush=True)
        failed_session_dependencies = sorted(failed_sessions.intersection(
            info.get("required_sessions", [])))
        if failed_session_dependencies:
            scan = {"status": "blocked", "session_dependencies": failed_session_dependencies,
                    "theory_loading": {"status": "blocked"}}
        elif failed_dependencies:
            scan = {"status": "blocked", "dependencies": failed_dependencies,
                    "theory_loading": {"status": "blocked"}}
        elif info["source_errors"]:
            scan = {"status": "failed", "errors": info["source_errors"],
                    "theory_loading": {"status": "failed"}}
        else:
            try:
                scan = scan_entry(entry, info, args, env, exports)
            except (OSError, ValueError) as error:
                scan = {"status": "failed", "errors": [str(error)],
                        "theory_loading": {"status": "failed"}}
        failed_sessions.update(session for check in scan.get("loading", [])
                               for session in check.get("failed_sessions", []))
        processed.add(entry)
        record["scan"] = scan
        record["candidate_count"] = len(candidates(exports[entry]))
        record["theory_count"] = len(info["theories"])
        # Re-scanning invalidates downstream coverage until the changed scope
        # has been exported and compiled again. Semantic checks likewise belong
        # to the previous generated crate, so invalidate their pass while keeping
        # their diagnostics available for comparison with the new scope.
        record["status"] = "pending" if scan["status"] == "passed" else scan["status"]
        for phase in ("rust_export", "stage1_compile", "optimization", "stage2_compile",
                      "runtime_validation"):
            if phase in record:
                record[phase]["status"] = "stale"
        write_json(HERE / "exports.json", exports)
        save_results(result, exports)
        print(f"  {scan['status']}: {record['candidate_count']} candidates", flush=True)
    return int(any(result["entries"][entry]["scan"]["status"] != "passed"
                   for entry in selected))


if __name__ == "__main__":
    try:
        with experiment_lock():
            sys.exit(main())
    except (ValueError, RuntimeError) as error:
        sys.exit(str(error))
    except KeyboardInterrupt:
        sys.exit(130)
