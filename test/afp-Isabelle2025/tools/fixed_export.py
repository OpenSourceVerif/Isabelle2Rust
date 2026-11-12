"""Execute and audit formal groups without adaptive requests or diagnostics."""
from pathlib import Path
import xml.etree.ElementTree as ET

import afp_common as common
import dependency_plan as dp
import fixed_plan
from scan_store import Store, digest, file_digest
from state import State


def groups(plan):
    return {g["id"]: (ctx["context"], g) for ctx in plan["contexts"] for g in ctx["groups"]}


def seal(base, run):
    work = common.resolve_path(run["directory"])
    return Store(base).evidence([p for p in work.rglob("*") if p.is_file()])


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
    if (request.attrib != expected
            or [n.get("name") for n in request.findall("parent")] != group["parents"]
            or [n.get("name") for n in request.findall("entry")] != group["entries"]
            or [n.get("name") for n in request.findall("target")] != list(dp.TARGETS)
            or any(n.tag not in {"parent", "entry", "target"} for n in request)):
        raise ValueError("Formal request differs from fixed plan")
    attempts = full.collect_attempts(work)
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
    finished = work / "finished.xml"
    if finished.is_file() and ET.parse(finished).getroot().attrib != {
            "group": group["id"], "context": context["id"]}:
        raise ValueError("Wrong formal completion witness")
    check = common.read_record(work / "process.log.json", {})
    if check != run["command"]:
        raise ValueError("Formal command receipt changed")
    complete = (complete and finished.is_file() and run.get("finished")
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
    if previous and (previous.get("mode") != "fixed-plan-v1" or previous.get("plan_id") != plan["id"]):
        raise ValueError("Existing dynamic/stale exports require a new work root")
    stage = {"mode": "fixed-plan-v1", "plan_id": plan["id"],
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
            if common.identity_matches(check) or active_children(base):
                raise ValueError("Formal group child is still live")
            if check.get("status") in {None, "running"} or "returncode" not in check:
                work = None
        if work is None:
            work = full.next_attempt(Path(base) / "exports" / plan["entry"] / gid)
            fixed_plan.write_request(work, "export", context, group=group)
            state.put(key, {"plan_id": plan["id"], "active": str(work.relative_to(base)),
                            "request_sha256": file_digest(work / "request.xml")})
            check = fixed_plan.native_command(group["session"], work, args, env, "fixed_export.ML")
        run = {"group": gid, "context": context["id"], "session": group["session"],
               "directory": common.relative(work), "scope": group["entries"], "command": check,
               "finished": (work / "finished.xml").is_file(), "attempts": full.collect_attempts(work)}
        run["evidence"] = seal(base, run)
        check_run(base, run, context, group)
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
                t: {"status": row["status"] if row["status"] != "retained" else "blocked",
                    "evidence": [], "coverage": []} for t in dp.TARGETS}}
        for group in ctx["groups"]:
            run = run_by_group.get(group["id"], {})
            attempts = {a["target"]: a for a in run.get("attempts", [])}
            group_results[group["id"]] = {}
            for t in dp.TARGETS:
                attempt = attempts.get(t)
                shared = attempts.get("frontend", attempts.get("context"))
                witness = attempt or (shared if shared and shared["status"] == "failed" else None)
                status = witness["status"] if witness else "blocked"
                group_results[group["id"]][t] = {"status": status, "evidence": witness["evidence"] if witness else None}
                for did in group["coverage"][t]["covered"]:
                    value = result[ctx["context"]["id"] + "/" + did]["targets"][t]
                    name = result[ctx["context"]["id"] + "/" + did]["declaration"]["name"]
                    state = "passed" if status == "passed" else "group_failed" if status == "failed" else "blocked"
                    if value["status"] != "passed":
                        value["status"] = state
                    if witness:
                        value["evidence"].append(witness["evidence"])
                    value["coverage"].append({"group": group["id"],
                        "kind": "printing" if dp.constant(name) in group["coverage"][t]["printing"] else "generated"})
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
    stage["languages"] = {t: ("no_candidates" if not group_results else
        "blocked" if any(g[t]["status"] == "blocked" for g in group_results.values()) else
        "passed" if all(g[t]["status"] == "passed" for g in group_results.values()) else
        "failed" if all(g[t]["status"] == "failed" for g in group_results.values()) else "partial")
        for t in dp.TARGETS}
    stage["status"] = ("complete" if set(group_results) == {r["group"] for r in stage["runs"]}
        and all(r["finished"] and r["command"]["status"] == "passed" for r in stage["runs"])
        and all(g[t]["status"] in full.TERMINAL for g in group_results.values() for t in dp.TARGETS)
        else "blocked")
    stage["artifacts"] = [{"path": p, "sha256": file_digest(common.resolve_path(p)),
                          "bytes": common.resolve_path(p).stat().st_size}
                         for p in sorted({p for r in stage["runs"] for a in r["attempts"]
                                          if a["status"] == "passed" for p in a["files"]})]
    stage["finished"] = common.timestamp()


def validate_stage(base, plan, stage):
    if stage.get("mode") != "fixed-plan-v1" or stage.get("plan_id") != plan["id"] or stage.get("plan") != plan:
        raise ValueError("Formal results use a different plan")
    expected = groups(plan)
    if sorted(expected) != sorted(r["group"] for r in stage.get("runs", [])):
        raise ValueError("Formal groups missing, repeated, or outside the plan")
    for run in stage["runs"]:
        context, group = expected[run["group"]]
        check_run(base, run, context, group, require_complete=True)
    for artifact in stage.get("artifacts", []):
        path = common.resolve_path(artifact["path"])
        if (not path.is_file() or file_digest(path) != artifact.get("sha256")
                or path.stat().st_size != artifact.get("bytes")):
            raise ValueError("Formal artifact changed: " + str(path))
    declarations, group_results = outcomes(stage)
    if declarations != stage.get("declarations") or group_results != stage.get("groups"):
        raise ValueError("Formal coverage/outcomes differ from native evidence")
