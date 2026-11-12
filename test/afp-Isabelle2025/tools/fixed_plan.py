"""Native analysis receipts and the durable plan boundary in the run database."""
import os
from pathlib import Path
import xml.etree.ElementTree as ET

import afp_common as common
import dependency_plan as dp
from scan_store import Store, digest, file_digest
from state import State


def declaration_rows(info, scope):
    owners = {t["path"]: t["name"] for t in info["theories"]}
    return sorted(({"source": source, "owner": owners[source], "name": name}
                   for source, names in scope.items() for name in names), key=dp.declaration_id)


def identity(base, entry, info, record, scope):
    from full import maximal_sessions
    from scan_store import expected_theories
    run = State(base).get("run", {})
    sources = run.get("sources", {})
    # Machine paths, resource bounds, receipt timestamps and traversal order
    # are not semantic inputs. Source/compiler bytes and rule/tool versions are.
    source = {"afp": sources.get("afp", {}), "isabelle": sources.get("isabelle_src", {}),
              "settings": sorted(sources.get("settings", {}).values()),
              "conditions": {k: {"sha256": v.get("sha256"),
                                  "support": sorted(v.get("support", {}).values())}
                             for k, v in sources.get("conditions", {}).items()}}
    from scan_frozen import tools_identity
    return {"rules": dp.RULES, "entry": entry, "source": digest(source),
            "tools": digest(sorted(tools_identity().values())),
            "declarations": declaration_rows(info, scope),
            "sessions": sorted(maximal_sessions(info, record["scan"])),
            "theories": sorted(t["name"] for t in info["theories"]
                               if t["path"] in record["scan"].get("theories", [])),
             "entry_theories": sorted({t["name"] for t in info["theories"]}),
            "required": {s: expected_theories(info, s) for s in maximal_sessions(info, record["scan"])}}


def write_request(work, mode, context=None, declarations=(), theories=(), group=None):
    attrs = {"mode": mode}
    if context:
        attrs["context"] = context["id"]
    if group:
        attrs["group"] = group["id"]
        attrs["module"] = group["module"]
    root = ET.Element("request", attrs)
    for name in theories:
        ET.SubElement(root, "theory", name=name)
    if context:
        for name in context["parents"]:
            ET.SubElement(root, "parent", name=name)
    for row in declarations:
        ET.SubElement(root, "declaration", row)
    if group:
        for name in group["entries"]:
            ET.SubElement(root, "entry", name=name)
        for name in group["targets"]:
            ET.SubElement(root, "target", name=name)
    (work / "request.xml").write_bytes(ET.tostring(root, encoding="utf-8"))


def native_command(session, work, args, env, script="plan.ML"):
    expression = (
        'Context.setmp_generic_context (SOME (Context.Theory '
        '(Thy_Info.get_theory "Go.Go_Setup"))) (fn () => '
        '(ML_Context.eval_file ML_Compiler.flags (Path.explode '
        + common.quote(str(common.HERE / "plan_common.ML")) + '); '
        'ML_Context.eval_file ML_Compiler.flags (Path.explode '
        + common.quote(str(common.HERE / script)) + '))) ()')
    argv = [args.isabelle, "process", "-l", session, "-d", str(common.PROJECT),
            "-d", str(args.afp / "thys"), *common.process_options(args),
            "-o", "timeout=" + str(args.timeout), "-o", "skip_proofs=false",
            "-T", "Rust.Rust_BigInt_Setup", "-T", "Go.Go_Setup", "-e", expression]
    actual = dict(env, AFP_FULL_OUTPUT=str(work),
                  AFP_PLAN_REQUEST=str(work.resolve()))
    return common.command(argv, work / "process.log", args, actual)


def validate_evidence(base, receipt):
    store = Store(base)
    if not receipt.get("evidence"):
        raise ValueError("Analysis receipt has no sealed evidence")
    for name, item in receipt["evidence"].items():
        path = store.path(name)
        if not path.is_file() or path.stat().st_size != item["bytes"] or file_digest(path) != item["sha256"]:
            raise ValueError("Missing/changed analysis evidence: " + name)
    for field in ("xml", "request"):
        if receipt.get(field) not in receipt["evidence"]:
            raise ValueError("Unsealed analysis " + field)
    return store.path(receipt["xml"])


def obtain(base, key, request_identity, session, args, env, prepare, filename, parse):
    """Recover a terminal child once; publish before retiring its predecessor."""
    import full
    from scan_frozen import active_children
    state, store = State(base), Store(base)
    old = state.get(key)
    if old:
        if old["input"] != request_identity:
            raise ValueError("Analysis inputs changed; start a new work root")
        path = validate_evidence(base, old)
        if old["status"] == "complete":
            return parse(path), old
    active_key = "analysis-active/" + digest(key)
    active = state.get(active_key)
    root = base / "analysis" / digest(key)
    if active:
        if active["input"] != request_identity:
            raise ValueError("Stale active analysis request")
        work = store.path(active["directory"])
        if work.parent != root or not work.name.startswith("attempt-"):
            raise ValueError("Foreign active analysis directory")
        if file_digest(work / "request.xml") != active["request_sha256"]:
            raise ValueError("Analysis request changed after interruption")
        check = common.read_record(work / "process.log.json", {})
        if common.identity_matches(check) or active_children(base):
            raise ValueError("Analysis child is still live")
        if check.get("status") in {None, "running"} or "returncode" not in check:
            active = None
    if not active:
        work = full.next_attempt(root)
        prepare(work)
        active = {"input": request_identity, "directory": str(work.relative_to(base)),
                  "request_sha256": file_digest(work / "request.xml")}
        state.put(active_key, active)
        check = native_command(session, work, args, env)
    path = work / filename
    value, error = None, None
    if check.get("status") == "passed" and check.get("returncode") == 0 and path.is_file():
        try:
            value = parse(path)
        except (ValueError, KeyError, ET.ParseError) as exn:
            error = str(exn)
    else:
        error = "Native analysis unresolved: " + check.get("status", "missing exit")
    # Keep incomplete XML as evidence as well; it is never interpreted as an
    # exclusion. A receipt without XML is sealed with an explicit placeholder.
    if not path.exists():
        path.write_text('<unresolved reason="no native receipt"/>')
    receipt = {"input": request_identity, "status": "complete" if error is None else "unresolved",
               "directory": str(work.relative_to(base)), "command": check,
               "xml": str(path.relative_to(base)), "request": str((work / "request.xml").relative_to(base)),
               "evidence": store.evidence([p for p in work.rglob("*") if p.is_file()]),
               "error": error}
    state.update({key: receipt}, remove=[active_key, "plan-checkpoint.json"])
    for attempt in root.glob("attempt-*"):
        if attempt != work:
            state.remove_tree(attempt)
    if error:
        raise ValueError(error)
    return value, receipt


def parse_selection(path, entry, session, expected):
    root = ET.parse(path).getroot()
    if root.tag != "selection" or root.get("schema") != "1":
        raise ValueError("Invalid context-selection receipt")
    loaded_nodes = root.findall("loaded")
    if any(set(n.attrib) != {"name"} or len(n) for n in loaded_nodes):
        raise ValueError("Invalid loaded-theory record")
    loaded = [n.get("name") for n in loaded_nodes]
    if (len(set(loaded)) != len(loaded) or not set(loaded) <= set(expected["theories"])
            or not set(expected["required"][session]) <= set(loaded)):
        raise ValueError("Invalid loaded-theory inventory")
    merges = root.findall("merge")
    if (len(merges) != 1 or set(merges[0].attrib) != {"status"}
            or merges[0].get("status") not in {"complete", "failed"} or len(merges[0])):
        raise ValueError("Invalid context merge record")
    contexts = []
    for node in root.findall("context"):
        if set(node.attrib) != {"status"} or node.get("status") != "complete":
            raise ValueError("Unresolved context selection: " + node.findtext("error", ""))
        parent_nodes = node.findall("parent")
        if any(set(n.attrib) != {"name"} or len(n) for n in parent_nodes):
            raise ValueError("Invalid selected context parent")
        parents = [n.get("name") for n in parent_nodes]
        declarations = sorted([dict(n.attrib) for n in node.findall("declaration")], key=dp.declaration_id)
        if (len(parents) <= len(dp.SETUPS) or
                parents[-len(dp.SETUPS):] != list(dp.SETUPS) or
                not set(parents[:-len(dp.SETUPS)]) <= set(loaded)
                or len(set(parents)) != len(parents)):
            raise ValueError("Invalid fixed parent order/backend setup")
        if any(d not in expected["declarations"] for d in declarations):
            raise ValueError("Foreign declaration in selected context")
        context = {"entry": entry, "session": session, "parents": parents,
                   "declarations": declarations, "entry_theories": expected["entry_theories"],
                   "input": digest(expected)}
        context["id"] = digest(context)
        contexts.append(context)
    if not contexts or len({c["id"] for c in contexts}) != len(contexts):
        raise ValueError("Missing/duplicate selected context")
    return sorted(contexts, key=lambda c: c["id"])


def selection_key(entry, session):
    return "analysis-selection/" + entry + "/" + digest(session)


def analysis_key(context):
    return "analysis-context/" + context["id"]


def plan_entry(base, entry, info, record, scope, args, env):
    expected = identity(base, entry, info, record, scope)
    contexts, problems = [], []
    for session in expected["sessions"]:
        key = selection_key(entry, session)
        try:
            found, _ = obtain(base, key, expected, session, args, env,
                lambda work: write_request(work, "select", declarations=expected["declarations"],
                                           theories=expected["theories"]),
                "selection.xml", lambda path: parse_selection(path, entry, session, expected))
        except ValueError as error:
            problems.append(str(error))
            continue
        for context in found:
            try:
                graph, _ = obtain(base, analysis_key(context), context, session, args, env,
                    lambda work, c=context: write_request(work, "analyze", c, c["declarations"]),
                    "analysis.xml", lambda path, c=context: dp.parse_analysis(path, c))
                contexts.append(dp.make_context_plan(context, graph))
            except ValueError as error:
                problems.append(str(error))
    observed = {d["id"] for ctx in contexts for d in ctx["classifications"]}
    required = {dp.declaration_id(d) for d in expected["declarations"]}
    if observed != required:
        problems.append("Unresolved declaration contexts")
    state = State(base)
    if problems:
        state.update({"plan-status/" + entry: {"status": "unresolved", "problems": problems}},
                     remove=["plan/" + entry, "plan-checkpoint.json"])
        return {"status": "unresolved", "problems": problems}
    plan = dp.assemble(entry, expected, contexts)
    state.update({"plan/" + entry: plan, "plan-status/" + entry: {"status": "complete"}},
                 remove=["plan-checkpoint.json"])
    return {"status": "complete", "id": plan["id"], **dp.statistics(plan)}


def recheck_entry(base, entry, info, record, scope):
    state = State(base)
    expected = identity(base, entry, info, record, scope)
    contexts, evidence = [], {}
    for session in expected["sessions"]:
        receipt = state.get(selection_key(entry, session))
        if not receipt or receipt["input"] != expected or receipt["status"] != "complete":
            raise ValueError("Missing/current context selection: " + entry + "/" + session)
        found = parse_selection(validate_evidence(base, receipt), entry, session, expected)
        evidence.update(receipt["evidence"])
        for context in found:
            receipt = state.get(analysis_key(context))
            if not receipt or receipt["input"] != context or receipt["status"] != "complete":
                raise ValueError("Unresolved analysis context: " + context["id"])
            graph = dp.parse_analysis(validate_evidence(base, receipt), context)
            contexts.append(dp.make_context_plan(context, graph))
            evidence.update(receipt["evidence"])
    required = {dp.declaration_id(d) for d in expected["declarations"]}
    if {d["id"] for ctx in contexts for d in ctx["classifications"]} != required:
        raise ValueError("Not every declaration has native classification")
    plan = dp.assemble(entry, expected, contexts)
    saved = dp.verify_plan(state.get("plan/" + entry), plan)
    return saved, digest(evidence)


def checkpoint(base, data, result, exports, publish=True):
    problems, plans, seals = [], {}, {}
    for entry in sorted(data["order"]):
        try:
            plan, seal = recheck_entry(base, entry, data["entries"][entry],
                                       result["entries"][entry], exports[entry])
            plans[entry], seals[entry] = plan["id"], seal
        except (ValueError, OSError, KeyError, TypeError, ET.ParseError) as error:
            problems.append({"entry": entry, "reason": str(error)})
    gate = {"phase": "plan", "rules": dp.RULES, "passed": not problems,
            "plans": plans, "evidence": seals, "problems": problems}
    gate["signature"] = digest(gate)
    if publish:
        State(base).put("plan-checkpoint.json", gate)
    return gate


def require_gate(base, data, result, exports):
    state = State(base)
    saved = state.get("plan-checkpoint.json")
    actual = checkpoint(base, data, result, exports, publish=False)
    if not saved or not actual["passed"] or saved != actual:
        raise ValueError("A current passing plan-checkpoint and sealed evidence are required")
    return actual
