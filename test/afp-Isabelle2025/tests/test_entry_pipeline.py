"""Branch-local dispositions, publication and resumption."""
import _paths
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

import afp_common as common
import dependency_plan as dp
import entry_audit as checks
import entry_pipeline as pipeline
import fixed_export
import fixed_plan
import scan_frozen
from scan_store import digest
from state import State


DECLARATIONS = sorted([{"source": "Base.thy", "owner": "Fixture.Base", "name": "Base." + name}
                       for name in ("first", "second")], key=dp.declaration_id)


def inputs(theories=("Fixture.Left", "Fixture.Right")):
    return {"mode": dp.ENTRY_PIPELINE, "entry": "Fixture", "rules": dp.RULES,
            "scan_statuses": {"Fixture": "complete"}, "scan_receipts": {"Fixture": "sealed"},
            "sessions": ["Fixture"], "entry_theories": ["Fixture.Base", *theories],
            "declarations": DECLARATIONS, "branches": [
                {"session": "Fixture", "theory": theory, "declarations": DECLARATIONS} for theory in theories]}


def passed(work):
    log = work / "process.log"
    log.write_text("complete\n")
    command = {"status": "passed", "returncode": 0, "log": common.relative(log)}
    common.write_record(work / "process.log.json", command)
    return command


def analysis(work, response):
    request = ET.parse(work / "request.xml").getroot()
    parents = [n.get("name") for n in request.findall("parent")]
    rows = [node.attrib for node in request.findall("declaration")]
    failure = response(parents[0], [d["name"] for d in rows])
    result = ET.Element("analysis", schema=str(dp.SCHEMA), context=request.get("context"),
                        status="unresolved" if failure else "complete")
    for row in rows:
        ET.SubElement(result, "declaration", row if failure else dict(row, abstract_constructor="false"))
    if failure:
        node = ET.SubElement(result, "failure", phase="strict_frontend",
                             version="Isabelle2025", exception="ERROR")
        ET.SubElement(node, "message").text = failure
        ET.SubElement(node, "error").text = failure
    else:
        for row in rows:
            ET.SubElement(result, "node", id=dp.constant(row["name"]), name=row["name"],
                          kind="function", equations="ordinary", owner=row["owner"])
        for target in dp.TARGETS:
            ET.SubElement(result, "target", name=target)
    ET.ElementTree(result).write(work / "analysis.xml")
    return passed(work)


def export(work):
    request = ET.parse(work / "request.xml").getroot()
    context, group = request.get("context"), request.get("group")
    attempts = work / "attempts"
    attempts.mkdir()
    for target in ("frontend", *dp.TARGETS):
        attempt = ET.Element("attempt", status="passed", target=target, context=context, batch=group)
        for entry in request.findall("entry"):
            ET.SubElement(attempt, "constant", name=entry.get("name"))
        if target == "frontend":
            for name in dp.TARGETS:
                ET.SubElement(attempt, "language").text = name
        else:
            artifact = work / "artifacts" / target / ("Cargo.toml" if target == "Rust" else "code")
            artifact.parent.mkdir(parents=True)
            artifact.write_text("exported\n")
            ET.SubElement(attempt, "file").text = str(artifact.relative_to(work))
        ET.ElementTree(attempt).write(attempts / (target + ".xml"))
    ET.ElementTree(ET.Element("finished", context=context, group=group)).write(work / "finished.xml")
    return passed(work)


class EntryPlanTests(unittest.TestCase):
    def test_same_declaration_rejected_in_left_and_exported_in_right(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            expected = inputs()
            bad = DECLARATIONS[0]["name"]
            calls = []

            def respond(branch, names):
                calls.append((branch, tuple(names)))
                return "Tactic failed" if branch == "Fixture.Left" and bad in names else None

            with patch.object(fixed_plan, "run_native", side_effect=lambda _, work, *_args: analysis(work, respond)):
                plan = checks.freeze(base, "Fixture", expected, None, {})
            self.assertEqual(len(calls), 4)
            self.assertEqual(len(set(calls)), len(calls))
            checks.validate_plan(base, plan, expected)
            with patch.object(fixed_plan, "run_native", side_effect=lambda _, work, *_args: export(work)):
                stage = fixed_export.execute(base, plan, {"scan": {}}, {}, None, {})
            fixed_export.validate_stage(base, plan, stage)
            by_branch = {item["context"]["id"]: item["context"]["scan_theory"] for item in plan["contexts"]}
            results = {by_branch[item["declaration"]["context"]]: item for item in stage["declarations"].values()
                       if item["declaration"]["name"] == bad}
            self.assertEqual({v["status"] for v in results["Fixture.Left"]["targets"].values()}, {"frontend_rejected"})
            self.assertEqual({v["status"] for v in results["Fixture.Right"]["targets"].values()}, {"passed"})
            rejected = results["Fixture.Left"]["declaration"]
            state = State(base)
            state.update({}, remove=[rejected["evidence"]])
            with self.assertRaisesRegex(ValueError, "plan receipt"):
                checks.validate_plan(base, plan, expected)
            common.resolve_path(stage["artifacts"][0]["path"]).write_text("modified\n")
            with self.assertRaisesRegex(ValueError, "evidence changed"):
                fixed_export.validate_stage(base, plan, stage)

    def test_slow_plan_cannot_delay_fast_entry_compilation(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            data = {"order": ["Slow", "Fast"], "entries": {entry: {"sessions": [entry]}
                                                           for entry in ("Slow", "Fast")}}
            units = {entry: {"entry": entry, "session": entry, "requirements": []}
                     for entry in data["order"]}
            options = SimpleNamespace(plan_workers=2, export_workers=1, compile_workers=1)
            slow_started, fast_published = threading.Event(), threading.Event()
            published = []

            def freeze(_base, entry, expected, args, env):
                if entry == "Slow":
                    slow_started.set()
                    self.assertTrue(fast_published.wait(15))
                else:
                    self.assertTrue(slow_started.wait(15))
                context = {"entry": entry, "id": entry}
                group = {"id": "request", "entries": ["constant"]}
                return {"id": entry, "entry": entry, "input": {}, "contexts": [
                    {"context": context, "groups": [group], "classifications": []}]}

            def export_job(_base, plan, context, group, args, env):
                run = {"closed": True, "attempts": [{"status": "passed", "target": "Rust",
                                                      "files": ["/generated/Cargo.toml"]}]}
                State(_base).put("fixed-progress/" + plan + "/request", {"plan_id": plan, "run": run})
                return run

            def publish(_base, plan, *_args):
                published.append(plan["entry"])
                if plan["entry"] == "Fast":
                    fast_published.set()

            with patch.object(scan_frozen.Store, "recover", return_value=None), \
                    patch.object(scan_frozen, "scan_session", return_value={"status": "complete"}), \
                    patch.object(checks, "scan_input", side_effect=lambda *args: ({"scan": {}}, {}, {"entry": args[-1]}, [])), \
                    patch.object(checks, "freeze", side_effect=freeze), \
                    patch.object(fixed_export, "execute_group", side_effect=export_job), \
                    patch.object(fixed_export, "check_run", return_value=True), \
                    patch.object(pipeline, "prepare_optimizer", return_value=base / "cargo-opt"), \
                    patch.object(pipeline.fixed_pipeline, "compile_group", return_value={"crates": 1, "closed": 1}) as compile_job, \
                    patch.object(pipeline.fixed_pipeline, "publish_entry", side_effect=publish):
                self.assertEqual(pipeline.execute(base, data, units, {}, data["order"], "run", options, {}), [])
            self.assertEqual(published, ["Fast", "Slow"])
            self.assertEqual([call.args[1]["entry"] for call in compile_job.call_args_list], ["Fast", "Slow"])

    def test_selected_scan_includes_real_prerequisites_in_order(self):
        data = {"entries": {"Child": {"sessions": ["child"]}, "Parent": {"sessions": ["parent"]}}}
        units = {"child": {"requirements": ["parent", "HOL"]}, "unrelated": {"requirements": []},
                 "parent": {"requirements": ["HOL"]}}
        self.assertEqual(scan_frozen.ordered_sessions(data, units, ["Child"]), ["parent", "child"])

    def test_joint_whitelist_match_without_singleton_match_uses_direct_requests(self):
        self.assert_fallback(lambda _, names: "Tactic failed" if len(names) > 1 else None, 3)

    def test_unknown_analysis_failure_freezes_every_scanned_root(self):
        self.assert_fallback(lambda *_: "Unknown native error", 1)

    def assert_fallback(self, response, calls):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            expected = inputs(("Fixture.Left",))
            with patch.object(fixed_plan, "run_native",
                              side_effect=lambda _, work, *_args: analysis(work, response)) as native:
                plan = checks.freeze(base, "Fixture", expected, None, {})
                self.assertEqual(native.call_count, calls)
            checks.validate_plan(base, plan, expected)
            context = plan["contexts"][0]
            self.assertEqual({r["status"] for r in context["classifications"]}, {"singleton_fallback"})
            self.assertEqual({tuple(g["entries"]) for g in context["groups"]}, {(d["name"],) for d in DECLARATIONS})
            self.assertTrue(all(g["targets"] == list(dp.TARGETS) and "coverage" not in g for g in context["groups"]))

    def test_interrupted_analysis_resumes_same_frozen_inputs(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            expected = inputs(("Fixture.Left",))
            with patch.object(fixed_plan, "run_native", side_effect=KeyboardInterrupt):
                with self.assertRaises(KeyboardInterrupt):
                    checks.freeze(base, "Fixture", expected, None, {})
            state = State(base)
            self.assertIsNone(state.get("plan/Fixture"))
            self.assertEqual(len(state.keys("analysis-active/")), 1)
            with patch.object(fixed_plan, "run_native",
                              side_effect=lambda _, work, *_args: analysis(work, lambda *_: None)):
                plan = checks.freeze(base, "Fixture", expected, None, {})
            self.assertEqual(dp.statistics(plan)["singleton_fallback"], 0)
            self.assertEqual(state.keys("analysis-active/"), [])
            checks.validate_plan(base, plan, expected)
