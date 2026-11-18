"""Entry-local evidence checks for fixed-plan-v3."""
from collections import Counter
import xml.etree.ElementTree as ET

import afp_common as common
import dependency_plan as dp
import fixed_export
import fixed_plan
import frontend_rejection
import full
from result_store import EntryStore
from scan_store import Store, aggregate, digest, file_digest
from state import State


TERMINAL_SCAN = {"complete", "failed_source", "blocked_dependency"}
EVIDENCE_ERRORS = (ValueError, KeyError, TypeError, OSError, ET.ParseError)


def scan_input(store, data, units, metadata, entry):
    info = data["entries"][entry]
    result, scopes = aggregate(store, data, units, metadata, [entry])
    record, scope = result["entries"][entry], scopes[entry]
    receipts = {s: store.read(units[s]) for s in info["sessions"]}
    statuses = record["scan"]["unit_states"]
    issues = [s + ": " + status for s, status in statuses.items() if status not in TERMINAL_SCAN]
    if not statuses or (set(statuses.values()) == {"complete"} and record["scan"]["missing_theories"]):
        issues.append("Missing required theory coverage")
    for session, receipt in receipts.items():
        if receipt and receipt["status"] == "failed_source":
            from scan_frozen import review_theory_failure
            index = common.read_record(store.path(receipt["directory"]) / "scan-messages/index.json", {})
            if review_theory_failure(store, receipt["build"], index) != receipt["source_review"]:
                issues.append(session + ": unverifiable source failure")
        if not receipt or receipt["status"] != "blocked_dependency":
            continue
        for blocker, cause in receipt["causes"].items():
            source = store.read(units[cause["session"]])
            if (not source or source["unit_id"] != cause["unit_id"]
                    or source["status"] != "failed_source" or blocker not in source["failed_sessions"]):
                issues.append(session + ": unresolved dependency " + blocker)
    if issues:
        return record, scope, None, issues
    paths = {t["name"]: t["path"] for t in info["theories"]}
    branches = []
    for session, receipt in receipts.items():
        if receipt["status"] != "complete":
            continue
        catalogue = receipt["catalogue"]
        for theory, covers in sorted(catalogue["contexts"].items()):
            branch_scope = {paths[owner]: catalogue["scope"][paths[owner]] for owner in covers}
            branches.append({"session": session, "theory": theory,
                             "declarations": fixed_plan.declaration_rows(info, branch_scope)})
    expected = {"mode": dp.ENTRY_PIPELINE, "entry": entry, "rules": dp.RULES,
                "scan_statuses": statuses, "scan_receipts": {s: digest(r) for s, r in receipts.items()},
                "sessions": [s for s in receipts if statuses[s] == "complete"],
                "entry_theories": sorted(paths), "declarations": fixed_plan.declaration_rows(info, scope),
                "branches": branches}
    return record, scope, expected, []


def freeze(base, entry, expected, args, env):
    state = State(base)
    key, seal_key = "plan/" + entry, "plan-seal/" + entry
    saved = state.get(key)
    if saved:
        if saved["input"] != expected or state.get(seal_key, {}).get("plan") != saved["id"]:
            raise ValueError("Frozen plan input or seal changed")
        return saved
    evidence = {}
    plan, _ = fixed_plan.build_entry(base, entry, expected, args, env, evidence_index=evidence)
    state.update({key: plan, seal_key: {"plan": plan["id"], "evidence": evidence}})
    return plan


def validate_plan(base, plan, expected):
    state = State(base)
    seal = state.get("plan-seal/" + expected["entry"], {})
    if not plan or plan["input"] != expected or seal.get("plan") != plan["id"]:
        raise ValueError("Missing or outdated frozen entry plan")
    dp.verify_plan(plan, plan)
    receipts, paths, root_ids = {}, {}, {}
    for key, checksum in seal["evidence"].items():
        receipt = state.get(key)
        if not receipt or digest(receipt) != checksum:
            raise ValueError("Missing or altered plan receipt: " + key)
        if key.startswith("analysis-context/"):
            paths[key] = fixed_plan.validate_evidence(base, receipt)
            command = common.read_record(paths[key].parent / "process.log.json")
            if digest(command) != digest(receipt["command"]):
                raise ValueError("Missing or altered native analysis command: " + key)
            receipts[key] = receipt
            root_ids[key] = {dp.declaration_id(d) for d in receipt["input"]["declarations"]}
    for item in plan["contexts"]:
        context = item["context"]
        for failure in item.get("analysis_failures", []):
            if receipts.get(failure["evidence"], {}).get("input", {}).get("id") != context["id"]:
                raise ValueError("Analysis failure lacks a sealed branch receipt")
        for row in item["classifications"]:
            key = row.get("evidence", item.get("analysis_evidence"))
            if row["status"] == "singleton_fallback":
                if not item.get("analysis_failures"):
                    raise ValueError("Fallback has no original analysis failure")
                continue
            receipt = receipts.get(key, {})
            inputs = receipt.get("input", {})
            if (inputs.get("id") != context["id"] or receipt.get("status") != "complete"
                    or row["id"] not in root_ids[key]):
                raise ValueError("Disposition lacks same-branch native analysis")
            if row["status"] == "frontend_rejected":
                failure = fixed_plan.parse_response(paths[key], inputs).get("failure")
                if (root_ids[key] != {row["id"]} or not failure or failure != row["failure"]
                        or frontend_rejection.classify(failure) != row["reason"]
                        or common.resolve_path(row["receipt_xml"]) != paths[key]):
                    raise ValueError("Rejection lacks same-branch singleton evidence")
    return seal


def command_evidence(base, item):
    commands = [item["optimization"], *item["stage1_compile"]["checks"],
                *item["stage2_compile"].get("checks", [])]
    logs = []
    for check in commands:
        path = common.resolve_path(check["log"])
        receipt = common.read_record(path.with_suffix(path.suffix + ".json"))
        if not receipt or any(receipt.get(field) != check.get(field)
                              for field in ("command", "log", "status", "returncode")):
            raise ValueError("Compilation command receipt changed: " + str(path))
        if (check.get("status") not in full.TERMINAL
                or not isinstance(check.get("returncode"), int)
                or (check["status"] == "passed") != (check["returncode"] == 0)
                or check["returncode"] < 0 or check["returncode"] in {130, 137, 143}
                or check["status"] == "failed" and full.infrastructure(full.log_text(check))):
            raise ValueError("Compilation command lacks a terminal receipt: " + str(path))
        logs.append(path)
    return Store(base).evidence(logs)


def validate_crate(base, manifest, item, optimizer):
    if not item.get("complete") or not full.crate_complete(item):
        raise ValueError("Rust crate has pending compilation")
    source = full.compilation_source(item, manifest)
    if not item.get("stage1_source") or source == common.resolve_path(manifest):
        raise ValueError("Rust compilation copy is missing")
    output = common.resolve_path(item["stage2"])
    if item["optimization"]["command"] != ["sh", str(common.PROJECT / "scripts/with-stack.sh"), "65536",
                                         str(optimizer), str(source.parent), "--out-dir", str(output)]:
        raise ValueError("Optimization request differs from the compiled source")
    targets = [("stage1_compile", source)]
    if item["optimization"]["status"] == "passed":
        targets.append(("stage2_compile", output / "Cargo.toml"))
    elif item["stage2_compile"].get("checks"):
        raise ValueError("Stage 2 evidence follows a failed optimizer")
    for phase, path in targets:
        checks = item[phase]["checks"]
        if (len(checks) != 1 or item[phase]["status"] != checks[0]["status"]
                or checks[0]["command"][-4:] != ["build", "--locked", "--manifest-path", str(path)]):
            raise ValueError("Cargo build does not match the requested Rust crate")
    artifacts = [{"path": common.relative(path), "sha256": file_digest(path), "bytes": path.stat().st_size}
                 for path in sorted(output.rglob("*")) if path.is_file()]
    if (artifacts != item["stage2_artifacts"]
            or (item["optimization"]["status"] == "passed" and not (output / "Cargo.toml").is_file())):
        raise ValueError("Optimized Rust artifact inventory changed")
    if item["command_evidence"] != command_evidence(base, item):
        raise ValueError("Rust compiler or optimizer log changed")


def validate_export(base, plan, record, scope):
    stage = record.get("full_export", {})
    signature = fixed_export.stage_for(plan, record, scope)
    if any(stage.get(key) != value for key, value in signature.items() if key != "runs"):
        raise ValueError("Export no longer matches entry inputs")
    fixed_export.validate_stage(base, plan, stage)


def validate_compile(base, record, optimizer):
    compiled = record.get("full_compile", {})
    manifests = full.rust_manifests(record)
    if sorted(compiled) != manifests:
        raise ValueError("Rust compilation inventory does not match closed exports")
    for manifest in manifests:
        validate_crate(base, manifest, compiled[manifest], optimizer)


def publication(base, plan, expected, record, optimizer, compiled):
    validate_plan(base, plan, expected)
    stage = record["full_export"]
    problems = []
    if stage["status"] != "complete":
        problems.append("Unresolved export request")
    if compiled:
        try:
            validate_compile(base, record, optimizer)
        except EVIDENCE_ERRORS as error:
            problems.append(str(error))
    return {"published/" + plan["entry"]: {"plan": plan["id"], "export": stage["status"],
            "complete": compiled and not problems, "problems": problems}}


def reconcile(store, data, units, metadata, selected, phase, optimizer):
    scans, scopes, problems, facts = {}, {}, [], {}
    counts = {column: Counter() for column in ("scan", *dp.TARGETS,
              "stage1_compile", "optimization", "stage2_compile")}
    entries = EntryStore(store.base, scans, scopes)
    state = store.state
    context_rows = rust_crates = 0
    for entry in selected:
        expected = None
        try:
            scans[entry], scopes[entry], expected, issues = scan_input(store, data, units, metadata, entry)
            problems.extend({"entry": entry, "reason": issue} for issue in issues)
        except EVIDENCE_ERRORS as error:
            scans[entry] = {"scan": {"status": "evidence_invalid", "errors": [str(error)]}}
            scopes[entry] = {}
            problems.append({"entry": entry, "reason": str(error)})
        if phase == "scan":
            continue
        try:
            plan = state.get("plan/" + entry)
            if expected is not None:
                seal = validate_plan(store.base, plan, expected)
                facts[entry] = {"plan": plan["id"], "seal": digest(seal)}
            if phase == "plan":
                continue
            record = entries[entry]
            if expected is not None:
                validate_export(store.base, plan, record, scopes[entry])
                if phase in {"compile", "all"}:
                    validate_compile(store.base, record, optimizer)
            if phase == "all":
                published = state.get("published/" + entry, {})
                if not published.get("complete") or published.get("plan") != (plan or {}).get("id"):
                    raise ValueError("Entry has no complete publication")
        except EVIDENCE_ERRORS as error:
            problems.append({"entry": entry, "reason": str(error)})
        if phase == "all":
            try:
                record = entries[entry]
            except EVIDENCE_ERRORS as error:
                problems.append({"entry": entry, "reason": str(error)})
                entries.invalid.add(entry)
                record = scans[entry]
            stage = record.get("full_export", {})
            counts["scan"][record["scan"]["status"]] += 1
            for target in dp.TARGETS:
                counts[target][stage.get("languages", {}).get(target, "pending")] += 1
            context_rows += len(stage.get("declarations", {}))
            for item in record.get("full_compile", {}).values():
                rust_crates += 1
                for column in ("stage1_compile", "optimization", "stage2_compile"):
                    counts[column][item.get(column, {}).get("status", "pending")] += 1
    if phase == "all":
        if set(selected) != set(data["entries"]) or len(data["order"]) != len(data["entries"]):
            problems.append({"reason": "Incomplete manifest inventory"})
        for prefix in ("analysis-active/", "fixed-progress/", "compile-group/"):
            pending = state.keys(prefix)
            if pending:
                problems.append({"reason": prefix + " pending", "count": len(pending)})
        if set(state.keys("entry/")) != {"entry/" + entry for entry in data["entries"]}:
            problems.append({"reason": "Published entry inventory differs from manifest"})
    gate = {"phase": phase, "checked": common.timestamp(), "passed": not problems,
            "entries": list(selected), "problems": problems, "facts": facts}
    result = {"entries": entries, "environment": metadata, "updated": state.get("updated", "")}
    return gate, result, scopes, {"phase_counts": {k: dict(v) for k, v in counts.items()},
                                  "published_context_declarations": context_rows, "rust_crates": rust_crates}
