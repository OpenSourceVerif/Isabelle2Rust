"""Native analysis receipts and the durable plan boundary in the run database."""
import os
from pathlib import Path
import xml.etree.ElementTree as ET

import afp_common as common
import dependency_plan as dp
import frontend_rejection
import plan_recovery
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


def request_xml(mode, context=None, declarations=(), theories=(), group=None):
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
    return root


def write_request(work, mode, context=None, declarations=(), theories=(), group=None):
    root = request_xml(mode, context, declarations, theories, group)
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



def run_native(session, work, args, env, script="plan.ML"):
    try:
        return native_command(session, work, args, env, script)
    except OSError:
        # A missing service/executable is an unresolved process result. Keep its
        # full traceback and the original command receipt; never prune a root.
        import traceback
        check = common.read_record(work / "process.log.json", {})
        check.update(status="failed", traceback=traceback.format_exc())
        check.setdefault("log", common.relative(work / "process.log"))
        if not (work / "process.log").exists():
            (work / "process.log").write_text(check["traceback"])
        common.write_record(work / "process.log.json", check)
        return check

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


class AnalysisFailure(ValueError):
    def __init__(self, receipt):
        self.receipt = receipt
        super().__init__(receipt["error"])


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
        raise AnalysisFailure(old)
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
        if common.identity_matches(check) or active_children(work, "AFP_PLAN_REQUEST"):
            raise ValueError("Analysis child is still live")
        if (check.get("status") in {None, "running", "interrupted", "cancelled"}
                or check.get("returncode") in {130, -2} or "returncode" not in check):
            active = None
    if not active:
        work = full.next_attempt(root)
        prepare(work)
        active = {"input": request_identity, "directory": str(work.relative_to(base)),
                  "request_sha256": file_digest(work / "request.xml")}
        state.put(active_key, active)
        check = run_native(session, work, args, env)
    if check.get("status") in {"interrupted", "cancelled"} or check.get("returncode") in {130, -2}:
        raise KeyboardInterrupt
    path = work / filename
    native_receipt = path.is_file()
    value, error, traceback_text = None, None, None
    if check.get("status") == "passed" and check.get("returncode") == 0 and path.is_file():
        try:
            value = parse(path)
        except Exception as exn:
            import traceback
            error = repr(exn)
            traceback_text = traceback.format_exc()
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
               "error": error, "traceback": traceback_text, "native_receipt": native_receipt, "phase": ("evidence_extraction" if check.get("status") == "passed"
                                            and check.get("returncode") == 0 else "native_process")}
    state.update({key: receipt}, remove=[active_key, "plan-checkpoint.json"])
    for attempt in root.glob("attempt-*"):
        if attempt != work:
            state.remove_tree(attempt)
    if error:
        raise AnalysisFailure(receipt)
    return value, receipt


def parse_selection(path, entry, session, expected, partial=False):
    root = ET.parse(path).getroot()
    if root.tag != "selection" or root.attrib != {"schema": "1"}:
        raise ValueError("Invalid context-selection receipt")
    loaded_nodes = root.findall("loaded")
    if any(set(n.attrib) != {"name"} or len(n) for n in loaded_nodes):
        raise ValueError("Invalid loaded-theory record")
    loaded = [n.get("name") for n in loaded_nodes]
    if (len(set(loaded)) != len(loaded) or not set(loaded) <= set(expected["theories"])
            or not set(expected["required"][session]) <= set(loaded)):
        raise ValueError("Invalid loaded-theory inventory")
    if any(n.tag not in {"loaded", "merge", "context"} for n in root):
        raise ValueError("Unknown context-selection record")
    merges = root.findall("merge")
    if (len(merges) != 1 or set(merges[0].attrib) != {"status"}
            or merges[0].get("status") not in {"complete", "failed"}):
        raise ValueError("Invalid context merge record")
    merge = merges[0]
    if merge.get("status") == "complete":
        valid_merge = len(merge) == 0
    else:
        valid_merge = (len(merge) == 1 and merge[0].tag == "error"
                       and not merge[0].attrib and not len(merge[0])
                       and bool((merge[0].text or "").strip()))
    if not valid_merge:
        raise ValueError("Invalid context merge record")
    contexts, unresolved = [], []
    for node in root.findall("context"):
        if set(node.attrib) != {"status"} or node.get("status") not in {"complete", "unresolved"}:
            raise ValueError("Invalid context selection status")
        if node.get("status") == "unresolved":
            if not partial:
                raise ValueError("Unresolved context selection: " + node.findtext("error", ""))
            if (any(n.tag not in {"parent", "error"} for n in node)
                    or len(node.findall("error")) != 1 or not (node.findtext("error") or "").strip()
                    or node.find("error").attrib or len(node.find("error"))
                    or any(set(n.attrib) != {"name"} or len(n) for n in node.findall("parent"))):
                raise ValueError("Invalid unresolved context record")
            parents = [n.get("name") for n in node.findall("parent")]
            if (parents[-len(dp.SETUPS):] != list(dp.SETUPS) or len(parents) != len(set(parents))
                    or not set(parents[:-len(dp.SETUPS)]) <= set(loaded)):
                raise ValueError("Invalid unresolved context parents")
            unresolved.append({"status": "unresolved_context", "session": session,
                               "parents": [n.get("name") for n in node.findall("parent")],
                               "error": node.findtext("error"), "declarations": expected["declarations"]})
            continue
        if any(n.tag not in {"parent", "declaration"} for n in node):
            raise ValueError("Unknown selected context record")
        parent_nodes = node.findall("parent")
        if any(set(n.attrib) != {"name"} or len(n) for n in parent_nodes):
            raise ValueError("Invalid selected context parent")
        parents = [n.get("name") for n in parent_nodes]
        declaration_nodes = node.findall("declaration")
        if any(set(n.attrib) != {"source", "owner", "name"} or len(n)
               for n in declaration_nodes):
            raise ValueError("Invalid selected declaration record")
        declarations = sorted([dict(n.attrib) for n in declaration_nodes], key=dp.declaration_id)
        if len({dp.declaration_id(d) for d in declarations}) != len(declarations):
            raise ValueError("Duplicate selected declaration")
        if len({d["name"] for d in declarations}) != len(declarations):
            raise ValueError("Ambiguous declaration ownership in selected context")
        if (len(parents) < len(dp.SETUPS) or
                parents[-len(dp.SETUPS):] != list(dp.SETUPS) or
                not set(parents[:-len(dp.SETUPS)]) <= set(loaded)
                or len(set(parents)) != len(parents)
                or (len(parents) == len(dp.SETUPS) and not set(loaded) <= set(dp.SETUPS))):
            raise ValueError("Invalid fixed parent order/backend setup")
        if any(d not in expected["declarations"] for d in declarations):
            raise ValueError("Foreign declaration in selected context")
        context = {"entry": entry, "session": session, "parents": parents,
                   "declarations": declarations, "entry_theories": expected["entry_theories"],
                   "input": digest(expected)}
        context["id"] = digest(context)
        contexts.append(context)
    if (not contexts and not unresolved) or len({c["id"] for c in contexts}) != len(contexts):
        raise ValueError("Missing/duplicate selected context")
    contexts = sorted(contexts, key=lambda c: c["id"])
    return {"contexts": contexts, "unresolved": unresolved} if partial else contexts


def selection_key(entry, session):
    return "analysis-selection/" + entry + "/" + digest(session)


def analysis_key(context):
    return "analysis-context/" + context["id"]


def parse_response(path, context):
    root = ET.parse(path).getroot()
    if root.get("status") == "complete":
        return {"graph": dp.parse_analysis(path, context)}
    if (root.tag != "analysis" or root.attrib !=
            {"schema": str(dp.SCHEMA), "context": context["id"], "status": "unresolved"}
            or any(n.tag not in {"declaration", "failure"} for n in root)):
        raise ValueError("Invalid failed analysis identity")
    rows = root.findall("declaration")
    if (any(set(n.attrib) != {"source", "owner", "name"} or len(n) for n in rows)
            or sorted([dict(n.attrib) for n in rows], key=dp.declaration_id) !=
               sorted(context["declarations"], key=dp.declaration_id)):
        raise ValueError("Failed analysis request roots changed")
    return {"failure": frontend_rejection.native_failure(root)}


def build_entry(base, entry, expected, args=None, env=None, replay=False):
    state = State(base)
    contexts, unresolved, evidence = [], [], {}

    def request(key, inputs, session, prepare, filename, parse):
        if replay:
            receipt = state.get(key)
            if not receipt or receipt["input"] != inputs:
                raise ValueError("Missing/current plan evidence: " + key)
        else:
            try:
                _, receipt = obtain(base, key, inputs, session, args, env, prepare, filename, parse)
            except AnalysisFailure as error:
                receipt = error.receipt
        path = validate_evidence(base, receipt)
        evidence.update(receipt["evidence"])
        actual_request = ET.parse(Store(base).path(receipt["request"])).getroot()
        expected_request = (request_xml("select", declarations=inputs["declarations"], theories=inputs["theories"])
                            if filename == "selection.xml" else
                            request_xml("analyze", inputs, inputs["declarations"]))
        def tree(node):
            return (node.tag, sorted(node.attrib.items()), (node.text or "").strip(),
                    [tree(n) for n in node])
        if tree(actual_request) != tree(expected_request):
            raise ValueError("Sealed analysis request differs from its frozen identity")
        check = common.read_record(path.parent / "process.log.json", {})
        if digest(check) != digest(receipt["command"]):
            raise ValueError("Analysis command receipt changed")
        error, value = None, None
        if check.get("status") == "passed" and check.get("returncode") == 0 and receipt["native_receipt"]:
            try:
                value = parse(path)
            except Exception as exn:
                error = repr(exn)
        else:
            error = "Native analysis unresolved: " + check.get("status", "missing exit")
        if (receipt["error"] != error
                or receipt["status"] != ("complete" if error is None else "unresolved")):
            raise ValueError("Analysis disposition differs from sealed native evidence")
        if error is not None:
            raise AnalysisFailure(receipt)
        return value, receipt

    for session in expected["sessions"]:
        key = selection_key(entry, session)
        try:
            found, receipt = request(key, expected, session,
                lambda work: write_request(work, "select", declarations=expected["declarations"],
                                           theories=expected["theories"]),
                "selection.xml", lambda path: parse_selection(path, entry, session, expected, partial=True))
        except AnalysisFailure as error:
            evidence.update(error.receipt["evidence"])
            unresolved.append({"status": "unresolved_context", "session": session,
                               "declarations": expected["declarations"], "evidence": key,
                               "error": str(error)})
            continue
        for issue in found["unresolved"]:
            unresolved.append(dict(issue, evidence=key))
        for context in found["contexts"]:
            def analyze(roots):
                subset = dict(context, declarations=roots)
                key = analysis_key(context)
                if roots != context["declarations"]:
                    key += "/" + digest(roots)
                try:
                    value, receipt = request(key, subset, session,
                        lambda work: write_request(work, "analyze", context, roots),
                        "analysis.xml", lambda path: parse_response(path, subset))
                    return dict(value, evidence=key)
                except AnalysisFailure as error:
                    evidence.update(error.receipt["evidence"])
                    return {"evidence": key, "failure": {"phase": error.receipt["phase"],
                            "error": str(error), "message": str(error)}}
            def process(value):
                key = "analysis-processing/" + digest(value["evidence"])
                receipt = state.get(value["evidence"])
                inputs = {"context": context["id"], "request": value["evidence"],
                          "evidence": digest(receipt["evidence"])}
                saved = state.get(key)
                if saved:
                    if saved.get("input") != inputs or saved.get("failure", {}).get("phase") != "plan_processing":
                        raise ValueError("Changed plan-processing failure evidence")
                    evidence[key] = digest(saved)
                    return {"failure": saved["failure"]}
                try:
                    return {"plan": dp.make_context_plan(context, value["graph"])}
                except Exception as error:
                    if replay:
                        raise ValueError("Missing original plan-processing failure receipt") from error
                    import traceback
                    failed = {"phase": "plan_processing", "error": repr(error),
                              "message": str(error), "traceback": traceback.format_exc()}
                    saved = {"input": inputs, "failure": failed}
                    state.put(key, saved)
                    evidence[key] = digest(saved)
                    return {"failure": failed}
            contexts.append(plan_recovery.recover(context, analyze, process))
    observed = {d["id"] for ctx in contexts for d in ctx["classifications"]}
    observed.update(dp.declaration_id(d) for u in unresolved for d in u["declarations"])
    missing = [d for d in expected["declarations"] if dp.declaration_id(d) not in observed]
    if missing:
        unresolved.append({"status": "unresolved_context", "declarations": missing,
                           "error": "Unresolved declaration ownership", "sessions": expected["sessions"]})
    plan = dp.assemble(entry, expected, contexts, unresolved)
    dp.verify_plan(plan, plan)
    return plan, digest(evidence)


def plan_entry(base, entry, info, record, scope, args, env):
    expected = identity(base, entry, info, record, scope)
    state = State(base)
    # Once published, a plan is frozen. Replaying validates its dispositions;
    # it never repeats failed analysis or modifies export requests.
    plan, _ = build_entry(base, entry, expected, args, env, replay=state.get("plan/" + entry) is not None)
    if state.get("plan/" + entry):
        dp.verify_plan(state.get("plan/" + entry), plan)
    state.update({"plan/" + entry: plan, "plan-status/" + entry:
                  {"status": "complete", "meaning": "disposition_inventory_valid"}},
                 remove=["plan-checkpoint.json"])
    return {"status": "complete", "meaning": "disposition_inventory_valid",
            "id": plan["id"], **dp.statistics(plan)}


def recheck_entry(base, entry, info, record, scope):
    expected = identity(base, entry, info, record, scope)
    plan, seal = build_entry(base, entry, expected, replay=True)
    return dp.verify_plan(State(base).get("plan/" + entry), plan), seal


def checkpoint(base, data, result, exports, publish=True):
    problems, plans, seals = [], {}, {}
    for entry in sorted(data["order"]):
        try:
            plan, seal = recheck_entry(base, entry, data["entries"][entry],
                                       result["entries"][entry], exports[entry])
            plans[entry], seals[entry] = plan["id"], seal
        except (ValueError, OSError, KeyError, TypeError, ET.ParseError) as error:
            problems.append({"entry": entry, "reason": str(error)})
    gate = {"phase": "plan", "rules": dp.RULES, "meaning": "disposition_inventory_valid", "passed": not problems,
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
