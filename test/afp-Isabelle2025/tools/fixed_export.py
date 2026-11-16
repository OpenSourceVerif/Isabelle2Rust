"""Execute and audit formal groups without adaptive requests or diagnostics."""
from pathlib import Path
import xml.etree.ElementTree as ET

import afp_common as common
import dependency_plan as dp
import fixed_plan
import frontend_rejection
from scan_store import Store, digest, file_digest
from state import State


def groups(plan):
    return {g["id"]: (ctx["context"], g) for ctx in plan["contexts"] for g in ctx["groups"]}


def seal(base, run):
    work = common.resolve_path(run["directory"])
    return Store(base).evidence([p for p in work.rglob("*") if p.is_file()])


def native_view(work):
    import full
    try:
        attempts = full.collect_attempts(work)
        for attempt in attempts:
            if (attempt.get("target") not in {*dp.TARGETS, "frontend", "context"}
                    or attempt.get("status") not in {"passed", "failed"}
                    or not attempt.get("constants")
                    or (attempt.get("target") in dp.TARGETS and attempt["status"] == "passed"
                        and not attempt["files"] and not attempt["library_only"])
                    or any(not common.resolve_path(p).is_relative_to(work / "artifacts")
                           for p in attempt["files"])):
                raise ValueError("Incomplete/inconsistent native attempt")
        finished = ET.parse(work / "finished.xml").getroot() if (work / "finished.xml").is_file() else None
        return attempts, finished, None
    except (ValueError, KeyError, OSError, ET.ParseError) as error:
        return [], None, repr(error)


def check_run(base, run, context, group, require_complete=False):
    import full
    work = common.resolve_path(run["directory"])
    root = Path(base).resolve() / "exports" / context["entry"] / group["id"]
    if work.parent != root or not work.name.startswith("attempt-"):
        raise ValueError("Foreign formal group directory")
    if (run.get("group") != group["id"] or run.get("scope") != group["entries"]
            or run.get("session") != group["session"] or run.get("context") != context["id"]):
        raise ValueError("Formal group request changed")
    if run.get("evidence") != seal(base, run):
        raise ValueError("Formal group evidence changed")
    request = ET.parse(work / "request.xml").getroot()
    expected = {"mode": "export", "context": context["id"], "group": group["id"], "module": dp.MODULE}
    if (request.tag != "request" or request.attrib != expected
            or any(set(n.attrib) != {"name"} or len(n) for n in request)
            or [n.get("name") for n in request.findall("parent")] != group["parents"]
            or [n.get("name") for n in request.findall("entry")] != group["entries"]
            or [n.get("name") for n in request.findall("target")] != list(dp.TARGETS)
            or any(n.tag not in {"parent", "entry", "target"} for n in request)):
        raise ValueError("Formal request differs from fixed plan")
    attempts, witness, error = native_view(work)
    if run.get("receipt_error") != error:
        raise ValueError("Formal receipt validation changed")
    if run.get("attempts", attempts) != attempts:
        raise ValueError("Formal attempt view differs from native XML")
    by_target = {}
    for attempt in attempts:
        target = attempt.get("target")
        if (target in by_target or target not in {*dp.TARGETS, "frontend", "context"}
                or attempt.get("context") != context["id"] or attempt.get("batch") != group["id"]
                or attempt["constants"] != group["entries"] or attempt["status"] not in full.TERMINAL):
            raise ValueError("Nonformal or changed six-language request")
        if target in {"frontend", "context"} and attempt["languages"] != list(dp.TARGETS):
            raise ValueError("Shared frontend request omitted a language")
        by_target[target] = attempt
        for file in attempt["files"]:
            if not common.resolve_path(file).is_relative_to(work / "artifacts"):
                raise ValueError("Artifact escapes its formal request")
    front = by_target.get("frontend", by_target.get("context"))
    complete = False
    if front:
        expected_targets = ({"frontend", *dp.TARGETS} if front["status"] == "passed"
                            else {front["target"]})
        complete = set(by_target) == expected_targets
        if front["status"] != "passed":
            complete = (complete and front["target"] == "frontend"
                        and len(group["entries"]) == 1
                        and frontend_rejection.export_failure(common.resolve_path(front["evidence"])) is not None)
    finished = work / "finished.xml"
    if witness is not None and (witness.tag != "finished" or len(witness) or witness.attrib != {
            "group": group["id"], "context": context["id"]}):
        complete = False
    check = common.read_record(work / "process.log.json", {})
    if digest(check) != digest(run["command"]):
        raise ValueError("Formal command receipt changed")
    complete = (complete and error is None and witness is not None and run.get("finished")
                and check.get("status") == "passed" and check.get("returncode") == 0
                and not any(full.infrastructure(ET.parse(common.resolve_path(a["evidence"])).
                            getroot().findtext("error", "")) for a in attempts if a["status"] == "failed"))
    if require_complete and not complete:
        raise ValueError("Unresolved formal group: " + group["id"])
    return bool(complete)


def execute(base, plan, record, scope, args, env, checkpoint=None):
    import full
    from scan_frozen import active_children
    state = State(base)
    previous = record.get("full_export", {})
    if previous and (previous.get("mode") != "fixed-plan-v2" or previous.get("plan_id") != plan["id"]):
        raise ValueError("Existing dynamic/stale exports require a new work root")
    stage = {"mode": "fixed-plan-v2", "plan_id": plan["id"],
             "scope_sha256": full.scope_digest(scope), "scan_sha256": full.entry_scan_signature(record),
             "serializer_sha256": full.serializer_signature(), "plan": plan, "runs": []}
    old_runs = {r["group"]: r for r in previous.get("runs", [])}
    for gid, old in old_runs.items():
        key = "fixed-progress/" + plan["entry"] + "/" + gid
        if not state.get(key):
            state.put(key, {"plan_id": plan["id"], "run": old})
    for gid, (context, group) in sorted(groups(plan).items()):
        key = "fixed-progress/" + plan["entry"] + "/" + gid
        saved = state.get(key, {})
        if saved and saved.get("plan_id") != plan["id"]:
            raise ValueError("Stale formal group progress")
        run = saved.get("run") or old_runs.get(gid)
        if run and check_run(base, run, context, group):
            stage["runs"].append(run)
            continue
        work = None
        if saved.get("active"):
            work = Store(base).path(saved["active"])
            if work.parent != Path(base) / "exports" / plan["entry"] / gid:
                raise ValueError("Foreign active formal request")
            if file_digest(work / "request.xml") != saved["request_sha256"]:
                raise ValueError("Interrupted formal request changed")
            check = common.read_record(work / "process.log.json", {})
            if common.identity_matches(check) or active_children(work, "AFP_PLAN_REQUEST"):
                raise ValueError("Formal group child is still live")
            if check.get("status") in {None, "running"} or "returncode" not in check:
                work = None
        if work is None:
            work = full.next_attempt(Path(base) / "exports" / plan["entry"] / gid)
            fixed_plan.write_request(work, "export", context, group=group)
            state.put(key, {"plan_id": plan["id"], "active": str(work.relative_to(base)),
                            "request_sha256": file_digest(work / "request.xml")})
            check = fixed_plan.run_native(group["session"], work, args, env, "fixed_export.ML")
        if check.get("status") in {"interrupted", "cancelled"} or check.get("returncode") in {130, -2}:
            raise KeyboardInterrupt
        attempts, _, receipt_error = native_view(work)
        run = {"group": gid, "context": context["id"], "session": group["session"],
               "directory": common.relative(work), "scope": group["entries"], "command": check,
               "finished": (work / "finished.xml").is_file(), "attempts": attempts, "receipt_error": receipt_error}
        run["evidence"] = seal(base, run)
        run["closed"] = check_run(base, run, context, group)
        state.put(key, {"plan_id": plan["id"], "run": run})
        stage["runs"].append(run)
        # Commit resumable results before deleting any obsolete attempt.
        record.pop("full_compile", None)
        record["full_export"] = stage
        finish(stage)
        if checkpoint:
            checkpoint()
        keep = {common.resolve_path(r["directory"]) for r in stage["runs"] + previous.get("runs", [])}
        for attempt in work.parent.glob("attempt-*"):
            if attempt.resolve() not in keep:
                state.remove_tree(attempt)
    record["full_export"] = stage
    finish(stage)
    if checkpoint:
        checkpoint()
    state.update({}, remove=state.keys("fixed-progress/" + plan["entry"] + "/"))
    return stage


def outcomes(stage):
    """Keep per-context declaration results, including group_failed.

    A planned exclusion is a classification, never a fabricated export failure.
    Coverage fulfilled by target printing remains separately labelled.
    """
    run_by_group = {r["group"]: r for r in stage["runs"]}
    result, group_results = {}, {}
    for ctx in stage["plan"]["contexts"]:
        for row in ctx["classifications"]:
            key = ctx["context"]["id"] + "/" + row["id"]
            result[key] = {"declaration": row, "targets": {
                t: {"status": row["status"] if row["status"] in {"excluded", "ineligible", "frontend_rejected"} else "blocked",
                    "evidence": [], "coverage": []} for t in dp.TARGETS}}
        for group in ctx["groups"]:
            run = run_by_group.get(group["id"], {})
            attempts = {a["target"]: a for a in run.get("attempts", [])}
            group_results[group["id"]] = {}
            for t in dp.TARGETS:
                attempt = attempts.get(t)
                shared = attempts.get("frontend", attempts.get("context"))
                witness = attempt or (shared if shared and shared["status"] == "failed" else None)
                status = witness["status"] if witness and run.get("closed") else "blocked"
                group_results[group["id"]][t] = {"status": status, "evidence": witness["evidence"] if witness else None}
                direct = group.get("kind") == "singleton_fallback"
                covered = [group["declaration"]] if direct else group["coverage"][t]["covered"]
                for did in covered:
                    value = result[ctx["context"]["id"] + "/" + did]["targets"][t]
                    name = result[ctx["context"]["id"] + "/" + did]["declaration"]["name"]
                    state = ("passed" if status == "passed" else
                             ("failed" if direct else "group_failed") if status == "failed" else "blocked")
                    if direct and status == "failed" and witness.get("target") == "frontend":
                        state = "frontend_rejected"
                    if value["status"] != "passed":
                        value["status"] = state
                    if witness:
                        value["evidence"].append(witness["evidence"])
                    value["coverage"].append({"group": group["id"],
                        "kind": "direct" if direct else
                                "printing" if dp.constant(name) in group["coverage"][t]["printing"] else "generated"})
    return result, group_results


def finish(stage):
    import full
    declarations, group_results = outcomes(stage)
    stage["declarations"], stage["groups"] = declarations, group_results
    # Legacy name-level cells are only a report view. Source/context records
    # above remain the authoritative unit, including repeated internal names.
    names = {}
    for item in declarations.values():
        name = item["declaration"]["name"]
        for target, value in item["targets"].items():
            cell = names.setdefault(name, {}).setdefault(target, {"status": value["status"], "evidence": []})
            if cell["status"] != value["status"]:
                cell["status"] = "mixed_contexts"
            cell["evidence"] = sorted(set(cell["evidence"] + value["evidence"]))
    stage["candidates"] = names
    stage["languages"] = {t: ("blocked" if stage["plan"].get("unresolved_contexts") else
        "no_candidates" if not group_results else
        "blocked" if any(g[t]["status"] == "blocked" for g in group_results.values()) else
        "passed" if all(g[t]["status"] == "passed" for g in group_results.values()) else
        "failed" if all(g[t]["status"] == "failed" for g in group_results.values()) else "partial")
        for t in dp.TARGETS}
    stage["status"] = ("complete" if set(group_results) == {r["group"] for r in stage["runs"]}
        and not stage["plan"].get("unresolved_contexts")
        and all(r.get("closed") for r in stage["runs"])
        and all(g[t]["status"] in full.TERMINAL for g in group_results.values() for t in dp.TARGETS)
        else "blocked")
    stage["artifacts"] = [{"path": p, "sha256": file_digest(common.resolve_path(p)),
                          "bytes": common.resolve_path(p).stat().st_size}
                         for p in sorted({p for r in stage["runs"] for a in r["attempts"]
                                          if a["status"] == "passed" for p in a["files"]})]
    stage["finished"] = common.timestamp()


def validate_stage(base, plan, stage):
    if stage.get("mode") != "fixed-plan-v2" or stage.get("plan_id") != plan["id"] or stage.get("plan") != plan:
        raise ValueError("Formal results use a different plan")
    expected = groups(plan)
    if sorted(expected) != sorted(r["group"] for r in stage.get("runs", [])):
        raise ValueError("Formal groups missing, repeated, or outside the plan")
    for run in stage["runs"]:
        context, group = expected[run["group"]]
        closed = check_run(base, run, context, group, require_complete=True)
        if run.get("closed") != closed:
            raise ValueError("Formal closure differs from native evidence")
    if plan.get("unresolved_contexts"):
        raise ValueError("Unresolved declaration contexts")
    for artifact in stage.get("artifacts", []):
        path = common.resolve_path(artifact["path"])
        if (not path.is_file() or file_digest(path) != artifact.get("sha256")
                or path.stat().st_size != artifact.get("bytes")):
            raise ValueError("Formal artifact changed: " + str(path))
    if stage.get("status") != "complete":
        raise ValueError("Formal disposition results are not closed")
    declarations, group_results = outcomes(stage)
    if declarations != stage.get("declarations") or group_results != stage.get("groups"):
        raise ValueError("Formal coverage/outcomes differ from native evidence")


def disposition_summary(plan, stage):
    """Count source identities and context obligations separately."""
    runs = {r["group"]: r for r in stage.get("runs", [])}
    unresolved = {dp.declaration_id(d) for u in plan.get("unresolved_contexts", []) for d in u["declarations"]}
    rows = [d for ctx in plan["contexts"] for d in ctx["classifications"]]
    counts = {}
    for status in ("retained", "excluded", "ineligible", "frontend_rejected", "singleton_fallback"):
        selected = [d for d in rows if d["status"] == status]
        counts[status] = {"candidates": len({d["id"] for d in selected}), "contexts": len(selected)}
    fallback_closed = fallback_unresolved = 0
    for ctx in plan["contexts"]:
        for group in ctx["groups"]:
            direct = group.get("kind") == "singleton_fallback"
            if runs.get(group["id"], {}).get("closed"):
                fallback_closed += int(direct)
            else:
                fallback_unresolved += int(direct)
                unresolved.update([group["declaration"]] if direct else
                    {d for t in dp.TARGETS for d in group["coverage"][t]["covered"]})
    fallback_results = [d for d in stage.get("declarations", {}).values()
                        if d["declaration"]["status"] == "singleton_fallback"]
    rejection_reasons = {}
    for d in rows:
        if d["status"] == "frontend_rejected":
            rejection_reasons[d["reason"]] = rejection_reasons.get(d["reason"], 0) + 1
    return {"dispositions": counts, "rejection_reasons": rejection_reasons,
            "fallback_rejected": sum(all(v["status"] == "frontend_rejected" for v in d["targets"].values())
                                     for d in fallback_results),
            "fallback_successful": sum(all(v["status"] == "passed" for v in d["targets"].values())
                                       for d in fallback_results),
            "direct_success": {t: sum(d["targets"][t]["status"] == "passed" for d in fallback_results)
                               for t in dp.TARGETS},
            "fallback_closed": fallback_closed,
            "fallback_unresolved": fallback_unresolved, "unresolved_candidates": len(unresolved),
            "unresolved_contexts": len(plan.get("unresolved_contexts", [])),
            "results_closed": stage.get("status") == "complete" and not unresolved}
