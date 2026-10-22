#!/usr/bin/env python3
"""Independently verify current AFP data and reports before declaring completion.

Counts alone cannot establish coverage. Each candidate result is checked against
its actual XML witness, every current Rust crate must have both stage outcomes,
and retained generated sources must match their recorded bytes.
"""
import argparse
import collections
import csv
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

import afp_common as common
import full


def audit_data(base, data, result, exports):
    issues = []
    checked = collections.Counter()
    failures = collections.Counter()
    def need(condition, reason, **detail):
        checked[reason] += 1
        if not condition:
            failures[reason] += 1
            # Incomplete previews can have hundreds of thousands of pending
            # cells. Count every violation, retaining a bounded set of examples.
            if len(issues) < 5000:
                issues.append(dict(reason=reason, **detail))
    need(len(data["entries"]) >= 800, "full AFP archive")
    need(set(data["entries"]) == set(result["entries"]) == set(exports), "all entry rows")
    need(set(data["order"]) == set(data["entries"]), "manifest traversal covers all entries")
    environment = result.get("environment", {})
    need(environment.get("proofs") == "checked", "proof checking enabled")
    need(environment.get("command_timeout_seconds") == 0, "unlimited scan and export configuration")
    source_manifest = common.read_json(base / "source-manifest.json", {})
    need(bool(source_manifest), "source inventory present")
    for name, checksum in source_manifest.items():
        path = common.PROJECT / name
        need(path.is_file() and full.file_digest(path) == checksum,
             "source file unchanged", path=name)
    gate = common.read_json(base / "scan-checkpoint.json", {})
    need(gate.get("passed") and gate.get("scan_signature") == full.scan_signature(result, exports),
         "current scan checkpoint")
    export_gate = common.read_json(base / "export-checkpoint.json", {})
    signature = full.digest(json.dumps({e: r.get("full_export") for e, r in result["entries"].items()},
                                       sort_keys=True).encode())
    need(export_gate.get("passed") and export_gate.get("export_signature") == signature,
         "current export checkpoint")
    # A state file is not evidence of a live process: compare Linux birth
    # identity against /proc before deciding whether a recorded writer is live.
    processes = common.read_json(base / "processes.json", {}).get("processes", {})
    for label, value in processes.items():
        actual = common.process_identity(value["pid"])
        old = value.get("identity")
        live = common.identity_matches(value)
        need(not live, "recorded upstream process finished", process=label, pid=value["pid"])
    messages = common.read_json(base / "scan-messages/index.json", {})
    for session, value in messages.items():
        if not value.get("current"):
            continue
        need(value.get("status") == "passed", "full failed-session messages available", session=session)
        need(value.get("origin_verified"), "session database matches failed build", session=session)
        if value.get("database"):
            database = common.PROJECT / value["database"]
            need(database.is_file() and full.file_digest(database) == value.get("database_sha256"),
                 "failed-session database retained", session=session)
            if database.is_file():
                origin = full.session_database_origin(database, session, value.get("references", []))
                need(origin["origin_verified"], "retained database matches failed command interval", session=session)
        if value.get("command", {}).get("log"):
            log = common.PROJECT / value["command"]["log"]
            need(log.is_file() and full.file_digest(log) == value.get("messages_sha256"),
                 "full session message bytes retained", session=session)
    for name, check, path, running in full.prerequisite_records(base):
        need(check.get("status") == "passed", "auxiliary prerequisite completed", prerequisite=name)
        log = common.PROJECT / check.get("log", "__missing__")
        need(log.is_file(), "auxiliary prerequisite log retained", prerequisite=name)
        identity = common.read_json(running, {})
        actual = common.process_identity(identity.get("pid", -1))
        old = identity.get("identity")
        need(not common.identity_matches(identity),
             "auxiliary prerequisite process finished", prerequisite=name)
    artifact_count = 0
    compiled = {"stage1_compile": set(), "stage2_compile": set()}
    known = set()
    serializer = full.serializer_signature()
    for entry in data["order"]:
        record = result["entries"][entry]
        witnesses = {}
        scan = record["scan"]
        names = common.candidates(exports[entry])
        known.update(names)
        need(scan.get("status") in {"passed", "failed", "blocked"}, "scan terminal", entry=entry)
        expected = {t["path"] for t in data["entries"][entry]["theories"]}
        if scan.get("status") == "passed":
            need(set(scan.get("theories", [])) == expected, "complete theory discovery", entry=entry)
        else:
            observed_failure = (scan.get("errors") or scan.get("dependencies") or scan.get("session_dependencies")
                                or any(x["status"] != "passed" for x in
                                       scan.get("loading", []) + scan.get("inspections", [])))
            need(bool(observed_failure), "scan failure has direct cause", entry=entry)
        for phase in ("loading", "inspections"):
            for check in scan.get(phase, []):
                if check.get("log"):
                    path = common.PROJECT / check["log"]
                    need(path.is_file(), "scan command log retained", entry=entry, path=check["log"])
                need(check.get("status") not in {"timeout", "memory_limit", "running"},
                     "scan resource failures resolved", entry=entry, phase=phase)
        for diagnostic in scan.get("certificate_errors", []) + scan.get("context_merge_errors", []):
            if diagnostic.get("truncated"):
                need((common.PROJECT / diagnostic.get("detail", "__missing__")).is_file(),
                     "full diagnostic beyond excerpt retained", entry=entry, constant=diagnostic.get("name"))
        stage = record.get("full_export", {})
        need(stage.get("scope_sha256") == full.scope_digest(exports[entry]), "current candidate scope", entry=entry)
        need(stage.get("scan_sha256") == full.entry_scan_signature(record), "current discovery context", entry=entry)
        need(stage.get("serializer_sha256") == serializer, "current serializer version", entry=entry)
        if not names:
            need(stage.get("status") == ("no_candidates" if scan["status"] == "passed" else "blocked"),
                 "empty and unknown scopes distinguished", entry=entry)
            need(set(stage.get("languages", {})) == set(full.TARGETS), "six target cells for empty scope", entry=entry)
            continue
        need(stage.get("status") == "complete", "export processing complete", entry=entry)
        need(set(stage.get("candidates", {})) == set(names), "every candidate has results", entry=entry)
        artifacts = {a["path"]: a for a in stage.get("artifacts", [])}
        for path, item in artifacts.items():
            file = common.PROJECT / path
            need(file.is_file() and full.file_digest(file) == item["sha256"],
                 "generated artifact bytes retained", entry=entry, path=path)
            artifact_count += 1
        for run in stage.get("runs", []):
            need(run["command"]["status"] == "passed" and run.get("finished"),
                 "export process finished normally", entry=entry, session=run["session"])
            need((common.PROJECT / run["command"]["log"]).is_file(), "export process log retained", entry=entry)
        for constant in names:
            outcomes = stage.get("candidates", {}).get(constant, {})
            need(set(outcomes) == set(full.TARGETS), "candidate has six target cells",
                 entry=entry, constant=constant)
            for target in full.TARGETS:
                value = outcomes.get(target, {})
                need(value.get("status") in full.TERMINAL, "candidate outcome terminal",
                     entry=entry, constant=constant, target=target)
                valid = False
                for evidence in value.get("evidence", []):
                    path = common.PROJECT / evidence
                    if not path.is_file():
                        continue
                    if evidence not in witnesses:
                        node = ET.parse(path).getroot()
                        cs = frozenset(x.attrib["name"] for x in node.findall("constant"))
                        files = node.findall("file")
                        files_ok = bool(files) or node.findtext("library_only") == "true"
                        directory = path.parents[3]
                        for child in files:
                            file = directory / child.text
                            files_ok &= file.is_file() and common.relative(file) in artifacts
                        witnesses[evidence] = {
                            "constants": cs, "target": node.attrib.get("target"),
                            "languages": frozenset(x.text for x in node.findall("language")),
                            "status": node.attrib.get("status"), "files_ok": files_ok,
                            "failure_ok": bool(node.findtext("error")) and (
                                len(cs) == 1 or node.attrib.get("stage") == "context_loading")}
                    witness = witnesses[evidence]
                    applicable = witness["target"] == target or (
                        witness["target"] in {"frontend", "context"} and target in witness["languages"])
                    if constant in witness["constants"] and applicable and witness["status"] == value.get("status"):
                        valid |= witness["files_ok"] if value["status"] == "passed" else witness["failure_ok"]
                need(valid, "candidate has direct applicable witness",
                     entry=entry, constant=constant, target=target)
        manifests = set(full.rust_manifests(record))
        for manifest in manifests:
            item = record.get("full_compile", {}).get(manifest, {})
            need(item.get("complete"), "every Rust crate processed", entry=entry, manifest=manifest)
            optimum = item.get("optimization", {})
            for phase in ("stage1_compile", "stage2_compile"):
                value = item.get(phase, {})
                if phase == "stage2_compile" and optimum.get("status") != "passed":
                    need(value.get("status") == "blocked" and optimum.get("status") == "failed"
                         and (common.PROJECT / optimum.get("log", "__missing__")).is_file(),
                         "stage2 blockage has optimizer failure evidence", entry=entry, manifest=manifest)
                    continue
                need(value.get("status") in full.TERMINAL and bool(value.get("checks")),
                     "stage compilation attempted", entry=entry, manifest=manifest, stage=phase)
                for check in value.get("checks", []):
                    need((common.PROJECT / check.get("log", "__missing__")).is_file(),
                         "complete compiler log retained", entry=entry, manifest=manifest, stage=phase)
                    need(check.get("status") not in {"timeout", "memory_limit", "running"},
                         "compiler resource failures resolved", entry=entry, manifest=manifest, stage=phase)
                build_checks = [c for c in value.get("checks", []) if "build" in c.get("command", [])]
                need(bool(build_checks), "actual Cargo build invoked", entry=entry, manifest=manifest, stage=phase)
                expected_manifest = (common.PROJECT / manifest if phase == "stage1_compile" else
                                     common.PROJECT / item.get("stage2", "__missing__") / "Cargo.toml")
                for check in build_checks:
                    command = check.get("command", [])
                    actual_manifest = (Path(command[command.index("--manifest-path") + 1])
                                       if "--manifest-path" in command else Path("__missing__"))
                    need(actual_manifest.resolve() == expected_manifest.resolve(),
                         "compiler used the recorded crate", entry=entry, manifest=manifest, stage=phase)
                if value.get("status") == "passed":
                    for run in stage["runs"]:
                        for attempt in run["attempts"]:
                            if manifest in attempt["files"] and attempt.get("target") == "Rust":
                                compiled[phase].update(attempt["constants"])
            need(optimum.get("status") in full.TERMINAL, "optimizer attempted", entry=entry, manifest=manifest)
            if optimum.get("status") == "passed":
                need(bool(item.get("stage2_artifacts")), "optimized sources inventoried", entry=entry, manifest=manifest)
                for artifact in item.get("stage2_artifacts", []):
                    file = common.PROJECT / artifact["path"]
                    need(file.is_file() and full.file_digest(file) == artifact["sha256"],
                         "optimized source bytes retained", entry=entry, path=artifact["path"])
    coverage = result.get("coverage", {})
    need(coverage.get("distinct_candidates") == len(known), "distinct discovery coverage")
    for phase in compiled:
        key = "distinct_" + phase.replace("_compile", "_compiled") + "_candidates"
        need(coverage.get(key) == len(compiled[phase]), "distinct compiled coverage", stage=phase)
    return {"passed": not issues, "checked": common.timestamp(), "issues": issues,
            "checks": dict(checked), "issue_counts": dict(failures), "retained_artifacts_checked": artifact_count,
            "input_sha256": full.inputs(base),
            "compiled_distinct_candidates": {p: len(cs) for p, cs in compiled.items()}}


def failure_key(value):
    """Identify a failure occurrence without relying on its summary category."""
    return (value.get("entry"), value.get("phase"), value.get("stage"),
            value.get("status"), value.get("target"), value.get("manifest"),
            tuple(value.get("constants", [])), tuple(value.get("evidence", []))[:1])


def required_failure_inventory(base, data, result):
    """Independently enumerate every current command/diagnostic occurrence.

    This does not reuse the report generator's event iterator: missing a whole
    loop there must remain detectable even when its summary totals agree.
    """
    expected = collections.Counter()
    def add(entry, phase, stage, status, evidence, constants=(), target=None, manifest=None):
        expected[failure_key(dict(entry=entry, phase=phase, stage=stage, status=status,
                                  evidence=evidence, constants=constants, target=target, manifest=manifest))] += 1
    root = base / "prerequisites"
    for path in sorted(root.glob("**/result.json")):
        check = common.read_json(path, {})
        if check.get("status") not in {"passed", None}:
            add("@prerequisite/" + path.relative_to(root).parts[0], "scan", "prerequisite",
                check["status"], [check["log"]] if check.get("log") else [common.relative(path)])
    for path in sorted((base / "recovery").glob("*/result.json")):
        check = common.read_json(path, {})
        if check.get("status") not in {"passed", None}:
            add(check.get("entry", "@execution"), check.get("phase", "scan"),
                "process_interruption", check["status"], [check["log"]])
    for entry in data["order"]:
        record = result["entries"][entry]
        scan = record["scan"]
        for phase in ("loading", "inspections"):
            for check in scan.get(phase, []):
                if check["status"] not in {"passed", "blocked"}:
                    add(entry, "scan", phase, check["status"], [check["log"]] if check.get("log") else [])
        for kind in ("certificate_errors", "context_merge_errors", "errors"):
            for value in scan.get(kind, []):
                diagnostic = value if isinstance(value, dict) else {}
                detail = diagnostic.get("detail")
                # Complete short messages can survive solely in results.json;
                # the catalog must reference those bytes, not a cleaned XML.
                evidence = detail if detail and (common.PROJECT / detail).is_file() else common.relative(
                    base / "results.json")
                add(entry, "scan", kind, "failed", [evidence],
                    [diagnostic["name"]] if diagnostic.get("name") else [])
        if scan["status"] == "blocked":
            add(entry, "scan", "dependency", "blocked", [common.relative(base / "results.json")])
        for run in record.get("full_export", {}).get("runs", []):
            if run["command"]["status"] != "passed":
                add(entry, "export", "process", run["command"]["status"], [run["command"]["log"]])
            for attempt in run["attempts"]:
                if attempt["status"] == "failed":
                    add(entry, "export", attempt["stage"], "failed", [attempt["evidence"]],
                        attempt["constants"], attempt["target"])
        for manifest in full.rust_manifests(record):
            item = record.get("full_compile", {}).get(manifest, {})
            for phase in ("stage1_compile", "optimization", "stage2_compile"):
                value = item.get(phase, {})
                checks = ([value] if value else []) if phase == "optimization" else value.get("checks", [])
                for check in checks:
                    if check["status"] != "passed":
                        add(entry, "compile", phase, check["status"], [check["log"]], target="Rust", manifest=manifest)
    return expected


def audit_reports(base, data, result, exports, audit):
    """Verify every CSV row and failure occurrence against experiment evidence."""
    report = base / "report"
    issues = audit["issues"]
    def need(condition, reason, **detail):
        audit["checks"][reason] = audit["checks"].get(reason, 0) + 1
        if not condition:
            audit["issue_counts"][reason] = audit["issue_counts"].get(reason, 0) + 1
            if len(issues) < 5000:
                issues.append(dict(reason=reason, **detail))
    for name in ("README.md", "scan-failures.md", "export-failures.md", "compile-failures.md",
                 "entries.csv", "candidates.csv", "compilation.csv", "failures.jsonl",
                 "summary.json", "failure-categories.csv"):
        need((report / name).is_file(), "required report exists", path=name)
    if not (report / "summary.json").is_file():
        audit["passed"] = False
        return
    summary = common.read_json(report / "summary.json")
    need(summary.get("completion_verified") and summary.get("input_sha256") == full.inputs(base),
         "final report matches current completed data")
    need(summary.get("missing_full_messages") == 0, "no missing full diagnostics in report")
    if (report / "entries.csv").is_file():
        with (report / "entries.csv").open() as stream:
            rows = list(csv.DictReader(stream))
        need(collections.Counter(r["entry"] for r in rows) == collections.Counter(data["entries"].keys()),
             "exactly one report row per entry")
        for row in rows:
            entry = row["entry"]
            record = result["entries"].get(entry, {})
            scan = record.get("scan", {})
            expected = {
                "scan": scan.get("status"), "scanned_theories": str(len(scan.get("theories", []))),
                "expected_theories": str(len(data["entries"].get(entry, {}).get("theories", []))),
                "candidates": str(len(common.candidates(exports.get(entry, {})))),
                **{t: record.get("full_export", {}).get("languages", {}).get(t, "pending") for t in full.TARGETS}}
            need(all(row.get(k) == v for k, v in expected.items()),
                 "entry report matches phase evidence", entry=entry)
        for target in ("scan",) + full.TARGETS:
            need(dict(collections.Counter(r[target] for r in rows)) == summary.get("phase_counts", {}).get(target),
                 "entry phase totals consistent", target=target)
    if (report / "candidates.csv").is_file():
        actual = collections.Counter()
        with (report / "candidates.csv").open() as stream:
            for row in csv.DictReader(stream):
                actual[(row["entry"], row["constant"])] += 1
                outcomes = result["entries"].get(row["entry"], {}).get("full_export", {}).get(
                    "candidates", {}).get(row["constant"], {})
                for target in full.TARGETS:
                    expected = outcomes.get(target, {})
                    need(row[target] == expected.get("status")
                         and row[target + "_evidence"] == ";".join(expected.get("evidence", [])),
                         "candidate report matches evidence", entry=row["entry"],
                         constant=row["constant"], target=target)
        expected = collections.Counter((e, c) for e, scope in exports.items() for c in common.candidates(scope))
        need(actual == expected, "exactly one report row per candidate reference")
    if (report / "compilation.csv").is_file():
        actual = collections.Counter()
        states = {p: collections.Counter() for p in ("stage1_compile", "optimization", "stage2_compile")}
        with (report / "compilation.csv").open() as stream:
            for row in csv.DictReader(stream):
                key = row["entry"], row["manifest"]
                actual[key] += 1
                item = result["entries"].get(row["entry"], {}).get("full_compile", {}).get(row["manifest"], {})
                need(row["stage2"] == item.get("stage2", "")
                     and all(row[p] == item.get(p, {}).get("status", "not_run") for p in states),
                     "compilation report matches crate evidence", entry=row["entry"], manifest=row["manifest"])
                for phase in states:
                    states[phase][row[phase]] += 1
        expected = collections.Counter((e, m) for e, r in result["entries"].items() for m in full.rust_manifests(r))
        need(actual == expected, "exactly one compilation row per successful Rust crate")
        for phase, counts in states.items():
            need(dict(counts) == summary.get("phase_counts", {}).get(phase),
                 "compilation totals consistent", stage=phase)
    if (report / "failures.jsonl").is_file():
        actual, categories = collections.Counter(), collections.Counter()
        events = 0
        historical = 0
        with (report / "failures.jsonl").open() as stream:
            for line in stream:
                value = json.loads(line)
                events += 1
                historical += bool(value.get("historical"))
                actual[failure_key(value)] += 1
                categories[(value["phase"], value["category"], value.get("target") or "", value["status"])] += 1
                need(value.get("error_sha256") == full.digest(value["error"].encode()),
                     "failure catalog full message digest matches", entry=value["entry"])
                need(all((common.PROJECT / p).is_file() for p in value["evidence"]),
                     "failure catalog original evidence retained", entry=value["entry"])
                need(value.get("full_message_available") is not False,
                     "failure catalog has full diagnostics", entry=value["entry"])
        need(actual == required_failure_inventory(base, data, result),
             "failure catalog covers every actual failed command and diagnostic")
        need(events == summary.get("failure_events"), "failure event count consistent")
        need(historical == summary.get("historical_failure_events", 0)
             and events - historical == summary.get("current_failure_events", events),
             "historical and current failure counts consistent")
        if (report / "failure-categories.csv").is_file():
            with (report / "failure-categories.csv").open() as stream:
                rows = list(csv.DictReader(stream))
            reported = collections.Counter()
            for row in rows:
                reported[(row["phase"], row["category"], row["target"], row["status"])] += int(row["events"])
            need(reported == categories, "failure category totals consistent")
    audit["passed"] = not issues and not audit["issue_counts"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=common.HERE / "full")
    parser.add_argument("--data-only", action="store_true")
    parser.add_argument("--preview", action="store_true", help="inspect incomplete data without waiting on writer lock")
    args = parser.parse_args()
    base = args.output_dir.resolve()
    def perform():
        data, result, exports = full.load(base)
        audit = audit_data(base, data, result, exports)
        if args.preview:
            audit["issues"].append({"reason": "preview is not a final quiescent audit"})
            audit["passed"] = False
        elif not args.data_only:
            audit_reports(base, data, result, exports, audit)
        name = "audit-preview.json" if args.preview else "data-audit.json" if args.data_only else "completion-audit.json"
        common.write_json(base / name, audit)
        print(json.dumps({"passed": audit["passed"], "issues": len(audit["issues"]), "checks": audit["checks"]}, indent=2))
        return int(not audit["passed"])
    if args.preview:
        return perform()
    with common.experiment_lock():
        return perform()


if __name__ == "__main__":
    raise SystemExit(main())
