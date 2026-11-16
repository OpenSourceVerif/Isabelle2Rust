"""Failure-only pruning, frozen singleton execution and evidence replay."""
import _paths
import copy
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

import afp_common as common
import dependency_plan as dp
import fixed_export as fe
import fixed_plan as fp
import frontend_rejection as rejection
import plan_recovery as recovery
from scan_store import digest
from state import State
from test_fixed_plan import graph, context
import test_plan_selection_receipts as selection_fixture

WELL = "Wellsortedness error\n(in code equation bad x = x):\nType nat not of sort enum\nNo type arity nat :: enum"
UNKNOWN = {"phase": "strict_frontend", "version": "Isabelle2025", "exception": "OTHER",
           "message": "exception UNDEF raised", "error": "exception UNDEF raised"}


def failure(message=WELL, kind="ERROR", phase="strict_frontend"):
    return {"version": "Isabelle2025", "phase": phase, "exception": kind,
            "message": message, "error": message}


def fixture():
    g = graph()
    c = context()
    c["declarations"] = sorted([{k: d[k] for k in ("source", "owner", "name")}
                               for d in g["declarations"]], key=dp.declaration_id)
    return c, g


def subset(g, roots):
    return dict(g, declarations=[d for d in g["declarations"]
                                if dp.declaration_id(d) in {dp.declaration_id(r) for r in roots}])


class RejectionTests(unittest.TestCase):
    def test_every_allowlisted_native_format(self):
        examples = [
            (WELL, "ERROR", "wellsortedness"),
            ('"List.append" is not a constructor, on left hand side of equation, in theorem:\nf (xs @ ys) = xs', "ERROR", "code_equation_pattern"),
            ("Abstraction on left hand side of equation, in theorem:\nf (lambda x. x) = x", "ERROR", "code_equation_pattern"),
            ("Wrong head of code equation,\nexpected constant f\ng x = x", "ERROR", "wrong_equation_head"),
            ("Abstraction violation\n(in code equation f x = Abs x):\nconstant Abs", "ERROR", "abstraction_violation"),
            ("Type error in application: incompatible operand type\n\nOperator: f :: nat => nat\nOperand: True :: bool", "ERROR", "equation_type"),
            ("Type error in application: invalid type", "TYPE", "equation_type"),
            ("Proof failed.\n 1. P", "THM", "equation_proof"),
            ("Proof failed.\n 1. P\nThe error(s) above occurred for the goal statement:\nP", "ERROR", "equation_proof"),
            ("Tactic failed\nThe error(s) above occurred for the goal statement:\nP", "ERROR", "equation_tactic"),
        ]
        for text, kind, expected in examples:
            with self.subTest(text=text):
                self.assertEqual(rejection.classify(failure(text, kind)), expected)
                for phase in ("context_preparation", "evidence_extraction", "plan_processing", "log"):
                    self.assertIsNone(rejection.classify(failure(text, kind, phase)))
                self.assertIsNone(rejection.classify(failure("Log quote:\n" + text, kind)))

    def test_unknown_versions_kinds_resource_and_partial_messages_stay_unknown(self):
        for value in [UNKNOWN, failure("Run out of store"), failure("Wellsortedness error"),
                      failure("Proof failed."), failure("Type error in application: quoted"),
                      dict(failure(), version="Isabelle2026"), dict(failure(), exception="UNDEF")]:
            self.assertIsNone(rejection.classify(value))

    def test_failed_analysis_requires_exact_root_identity_and_envelope(self):
        c, _ = fixture()
        root = ET.Element("analysis", schema="2", context=c["id"], status="unresolved")
        for d in c["declarations"]:
            ET.SubElement(root, "declaration", d)
        add_failure(root, failure())
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "analysis.xml"
            ET.ElementTree(root).write(path)
            self.assertEqual(fp.parse_response(path, c)["failure"], failure())
            root.find("declaration").set("source", "foreign.thy")
            ET.ElementTree(root).write(path)
            with self.assertRaises(ValueError):
                fp.parse_response(path, c)


class IsolationTests(unittest.TestCase):
    def test_success_is_exact_existing_algorithm_with_one_request(self):
        c, g = fixture()
        calls = []
        def analyze(roots):
            calls.append(roots)
            return {"graph": subset(g, roots), "evidence": "success"}
        result = recovery.recover(c, analyze)
        self.assertEqual(result, dp.make_context_plan(c, g))
        self.assertEqual(calls, [c["declarations"]])
        self.assertNotIn("analysis_failures", result)

    def test_mixed_roots_are_rejected_only_by_singleton_evidence(self):
        c, g = fixture()
        calls = []
        bad = {"Main.u", "Main.f"}  # shared bad dependency
        def analyze(roots):
            calls.append(tuple(d["name"] for d in roots))
            if any(d["name"] in bad for d in roots):
                return {"failure": failure(), "evidence": digest(calls[-1])}
            return {"graph": subset(g, roots), "evidence": digest(calls[-1])}
        result = recovery.recover(c, analyze)
        self.assertEqual({d["name"] for d in result["classifications"]
                          if d["status"] == "frontend_rejected"}, bad)
        for d in result["classifications"]:
            if d["status"] == "frontend_rejected":
                self.assertIn((d["name"],), calls)
        self.assertFalse(any(g.get("kind") == "singleton_fallback" for g in result["groups"]))
        self.assertLessEqual(len(calls), 2 * len(c["declarations"]) + 1)

    def test_singletons_succeed_joint_failure_never_retries_unchanged_request(self):
        c, g = fixture()
        calls = []
        def analyze(roots):
            calls.append(tuple(d["name"] for d in roots))
            return ({"failure": failure(), "evidence": "joint"} if len(roots) > 1 else
                    {"graph": subset(g, roots), "evidence": "single"})
        result = recovery.recover(c, analyze)
        self.assertEqual(calls.count(tuple(d["name"] for d in c["declarations"])), 1)
        self.assertEqual(len(result["groups"]), len(c["declarations"]))
        self.assertTrue(all(d["status"] == "singleton_fallback" for d in result["classifications"]))

    def test_unknown_initial_error_falls_back_without_diagnostic_requests(self):
        c, _ = fixture()
        calls = []
        def analyze(roots):
            calls.append(roots)
            return {"failure": UNKNOWN, "evidence": "initial"}
        result = recovery.recover(c, analyze)
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(result["groups"]), len(c["declarations"]))
        self.assertTrue(all("coverage" not in g for g in result["groups"]))

    def test_unknown_subrequest_stops_splitting_and_preserves_unanalyzed_candidates(self):
        c, g = fixture()
        calls = []
        def analyze(roots):
            calls.append(roots)
            if len(calls) == 1:
                return {"failure": failure(), "evidence": "initial"}
            return {"failure": UNKNOWN, "evidence": "unknown"}
        result = recovery.recover(c, analyze)
        self.assertEqual(len(calls), 3)
        self.assertEqual(len(result["groups"]), len(c["declarations"]))

    def test_group_fallback_includes_entrances_removed_by_dependency_coverage(self):
        c, g = fixture()
        planned = dp.make_context_plan(c, g)
        group = next(g for g in planned["groups"] if "Main.f" in g["entries"])
        frozen = recovery.singleton_requests(c, c["declarations"], [{"error": "failure"}], group)
        self.assertEqual({g["entries"][0] for g in frozen}, {"Main.f", "Main.u", "Main.v"})
        self.assertNotIn("Main.left", {g["entries"][0] for g in frozen})
        self.assertTrue(all(g["affected"]["id"] == group["id"] for g in frozen))

    def test_known_exclusions_survive_unknown_other_half(self):
        c, g = fixture()
        ordered = c["declarations"]
        selected = ordered[:len(ordered)//2]
        missing = {d["name"] for d in selected}
        for d in selected:
            g["nodes"][dp.constant(d["name"])].update(kind="none", equations="missing")
        calls = []
        def analyze(roots):
            calls.append(roots)
            if len(calls) == 1:
                return {"failure": failure(), "evidence": "initial"}
            if roots == selected:
                return {"graph": subset(g, roots), "evidence": "success"}
            return {"failure": UNKNOWN, "evidence": "unknown"}
        result = recovery.recover(c, analyze)
        self.assertEqual({d["name"] for d in result["classifications"] if d["status"] == "excluded"}, missing)
        self.assertTrue(missing.isdisjoint(g["entries"][0] for g in result["groups"]))

    def test_rejection_is_not_propagated_across_contexts_or_polymorphic_roots(self):
        c, g = fixture()
        bad = recovery.recover(c, lambda roots: {"failure": failure(), "evidence": "bad"})
        other = dict(c, id="other", parents=["Other", *dp.SETUPS])
        good = recovery.recover(other, lambda roots: {"graph": subset(g, roots), "evidence": "good"})
        self.assertTrue(all(d["status"] == "frontend_rejected" for d in bad["classifications"]))
        self.assertTrue(all(d["status"] == "retained" for d in good["classifications"]))
        self.assertEqual(bad["groups"], [])

    def test_recursive_graph_and_plan_processing_fault_preserve_full_scope(self):
        c, g = fixture()
        g["nodes"]["CONST Main.u"]["deps"] = ["CONST Main.f"]
        expected = dp.make_context_plan(c, g)
        self.assertEqual(recovery.recover(c, lambda roots: {"graph": g, "evidence": "graph"}), expected)
        with patch.object(dp, "make_context_plan", side_effect=RuntimeError("Wellsortedness error")):
            result = recovery.recover(c, lambda roots: {"graph": g, "evidence": "graph"})
        self.assertEqual(len(result["groups"]), len(c["declarations"]))
        self.assertEqual(result["analysis_failures"][0]["phase"], "plan_processing")

    def test_interrupt_propagates_without_scheduling_fallback(self):
        c, _ = fixture()
        with self.assertRaises(KeyboardInterrupt):
            recovery.recover(c, lambda roots: (_ for _ in ()).throw(KeyboardInterrupt()))


def add_failure(root, value):
    n = ET.SubElement(root, "failure", {k: value[k] for k in ("phase", "version", "exception")})
    for key in ("message", "error"):
        ET.SubElement(n, key).text = value[key]


def fake_native(mode="passed", commands=None):
    def native(session, work, args, env, script):
        if commands is not None:
            commands.append(work)
        request = ET.parse(work / "request.xml").getroot()
        context_id, gid = request.get("context"), request.get("group")
        targets = ["frontend"] + list(dp.TARGETS) if mode in {"passed", "target_failed"} else ["frontend"]
        for target in targets:
            root = ET.Element("attempt", context=context_id, batch=gid, target=target,
                              stage="frontend" if target == "frontend" else "target_preparation_or_serialization",
                              seconds="0", status="passed")
            for n in request.findall("entry"):
                ET.SubElement(root, "constant", name=n.get("name"))
            if target == "frontend":
                for t in dp.TARGETS:
                    ET.SubElement(root, "language").text = t
                if mode not in {"passed", "target_failed"}:
                    root.set("status", "failed")
                    value = failure() if mode == "rejected" else UNKNOWN
                    ET.SubElement(root, "error").text = value["error"]
                    add_failure(root, value)
            elif mode == "target_failed" and target == "Rust":
                root.set("status", "failed")
                ET.SubElement(root, "error").text = "deterministic serializer failure"
            else:
                ET.SubElement(root, "library_only").text = "true"
            path = work / "attempts" / context_id / gid / (target + ".xml")
            path.parent.mkdir(parents=True, exist_ok=True)
            ET.ElementTree(root).write(path)
        ET.ElementTree(ET.Element("finished", group=gid, context=context_id)).write(work / "finished.xml")
        check = {"status": "passed", "returncode": 0, "identity": ("boot", 123, "start")}
        common.write_record(work / "process.log.json", check)
        (work / "process.log").write_text("native fixture")
        return check
    return native


class ExecutionTests(unittest.TestCase):
    def plan(self, count=2):
        c, _ = fixture()
        c["declarations"] = c["declarations"][:count]
        recovered = recovery.recover(c, lambda roots: {"failure": UNKNOWN, "evidence": "initial"})
        return dp.assemble("E", {"declarations": c["declarations"]}, [recovered])

    def test_direct_success_and_deterministic_failures_close_without_structural_claim(self):
        for mode in ("passed", "target_failed", "rejected"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                base, plan, record = Path(tmp), self.plan(), {"scan": {}}
                with patch.object(fp, "native_command", side_effect=fake_native(mode)):
                    stage = fe.execute(base, plan, record, {}, None, {})
                fe.validate_stage(base, plan, stage)
                self.assertEqual(stage["status"], "complete")
                self.assertEqual(fe.disposition_summary(plan, stage)["fallback_closed"], 2)
                self.assertEqual(dp.statistics(plan)["structural_coverage"], dict.fromkeys(dp.TARGETS, 0))
                self.assertTrue(all(v["coverage"][0]["kind"] == "direct"
                                    for d in stage["declarations"].values() for v in d["targets"].values()))
                with patch.object(fp, "native_command", side_effect=AssertionError("must reuse")):
                    fe.execute(base, plan, record, {}, None, {})

    def test_unknown_failure_runs_once_then_is_resumable(self):
        with tempfile.TemporaryDirectory() as tmp:
            base, plan, record, calls = Path(tmp), self.plan(), {"scan": {}}, []
            with patch.object(fp, "native_command", side_effect=fake_native("unknown", calls)):
                stage = fe.execute(base, plan, record, {}, None, {})
            self.assertEqual(len(calls), 2)
            self.assertEqual(stage["status"], "blocked")
            with self.assertRaises(ValueError):
                fe.validate_stage(base, plan, stage)
            with patch.object(fp, "native_command", side_effect=fake_native("passed", calls)):
                fe.execute(base, plan, record, {}, None, {})
            self.assertEqual(len(calls), 4)
            fe.validate_stage(base, plan, record["full_export"])

    def test_interruption_reuses_already_committed_singleton(self):
        with tempfile.TemporaryDirectory() as tmp:
            base, plan, record, calls = Path(tmp), self.plan(), {"scan": {}}, []
            real = fake_native("passed", calls)
            def interrupt(*args):
                if calls:
                    common.write_record(args[1] / "process.log.json",
                                        {"status": "interrupted", "returncode": -2})
                    raise KeyboardInterrupt
                return real(*args)
            with patch.object(fp, "native_command", side_effect=interrupt), self.assertRaises(KeyboardInterrupt):
                fe.execute(base, plan, record, {}, None, {})
            with patch.object(fp, "native_command", side_effect=real):
                stage = fe.execute(base, plan, record, {}, None, {})
            self.assertEqual(len(calls), 2)
            self.assertEqual(stage["status"], "complete")

    def test_sqlite_lazy_store_restores_v2_plan_and_direct_outcomes(self):
        from result_store import EntryStore
        with tempfile.TemporaryDirectory() as tmp:
            base, plan = Path(tmp), self.plan(1)
            state = State(base)
            state.put("plan/E", plan)
            scans, scopes = {"E": {"scan": {}}}, {"E": {}}
            writer = EntryStore(base, scans, scopes)
            with patch.object(fp, "native_command", side_effect=fake_native()):
                original = fe.execute(base, plan, writer["E"], {}, None, {},
                                      checkpoint=lambda: writer.commit("E"))
            stored = state.get("entry/E")["full_export"]
            self.assertNotIn("plan", stored)
            self.assertNotIn("declarations", stored)
            restored = EntryStore(base, scans, scopes)["E"]["full_export"]
            self.assertEqual(restored["declarations"], original["declarations"])
            fe.validate_stage(base, plan, restored)

    def test_changed_or_missing_evidence_blocks_reuse(self):
        for change in ("modify", "remove"):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as tmp:
                base, plan, record = Path(tmp), self.plan(1), {"scan": {}}
                with patch.object(fp, "native_command", side_effect=fake_native()):
                    stage = fe.execute(base, plan, record, {}, None, {})
                evidence = common.resolve_path(stage["runs"][0]["attempts"][0]["evidence"])
                evidence.write_text("<tampered/>") if change == "modify" else evidence.unlink()
                with self.assertRaises(ValueError):
                    fe.validate_stage(base, plan, stage)

    def test_unresolved_context_does_not_block_executable_scope_but_blocks_final_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            base, plan, record, calls = Path(tmp), self.plan(1), {"scan": {}}, []
            plan["unresolved_contexts"] = [{"status": "unresolved_context", "declarations": [],
                                           "error": "true branch conflict"}]
            with patch.object(fp, "native_command", side_effect=fake_native(commands=calls)):
                stage = fe.execute(base, plan, record, {}, None, {})
            self.assertEqual(len(calls), 1)
            self.assertEqual(stage["status"], "blocked")
            with self.assertRaisesRegex(ValueError, "Unresolved declaration contexts"):
                fe.validate_stage(base, plan, stage)

    def test_empty_and_fully_rejected_scope_do_not_report_export_success(self):
        c, _ = fixture()
        for declarations in ([], c["declarations"]):
            ctx = dict(c, declarations=declarations)
            recovered = (recovery.recover(ctx, lambda roots: {"failure": failure(), "evidence": "e"})
                         if declarations else {"context": ctx, "classifications": [], "groups": [], "sccs": []})
            plan = dp.assemble("E", {"declarations": declarations}, [recovered])
            with tempfile.TemporaryDirectory() as tmp, patch.object(fp, "native_command", side_effect=AssertionError):
                stage = fe.execute(Path(tmp), plan, {"scan": {}}, {}, None, {})
            self.assertEqual(set(stage["languages"].values()), {"no_candidates"})


class PartialSelectionTests(unittest.TestCase):
    def test_native_failed_branch_keeps_healthy_branch(self):
        fixture = selection_fixture.SelectionReceiptTests()
        fixture.setUp()
        root = fixture.receipt()
        node = root.find("context")
        node.set("status", "unresolved")
        for d in node.findall("declaration"):
            node.remove(d)
        ET.SubElement(node, "error").text = "true conflict"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "selection.xml"
            ET.ElementTree(root).write(path)
            value = fp.parse_selection(path, "E", "E", fixture.expected, partial=True)
        self.assertEqual(len(value["contexts"]), 1)
        self.assertEqual(len(value["unresolved"]), 1)



class PlanEvidenceTests(unittest.TestCase):
    def expected(self):
        c, _ = fixture()
        return {"sessions": ["E"], "theories": ["Main"], "entry_theories": ["Main"],
                "required": {"E": ["Main"]}, "declarations": c["declarations"]}

    def native(self, session, work, args, env, script="plan.ML"):
        request = ET.parse(work / "request.xml").getroot()
        if request.get("mode") == "select":
            root = ET.Element("selection", schema="1")
            ET.SubElement(root, "loaded", name="Main")
            ET.SubElement(root, "merge", status="complete")
            context = ET.SubElement(root, "context", status="complete")
            for name in ["Main", *dp.SETUPS]:
                ET.SubElement(context, "parent", name=name)
            for node in request.findall("declaration"):
                context.append(copy.deepcopy(node))
            path = work / "selection.xml"
        else:
            root = ET.Element("analysis", schema="2", context=request.get("context"), status="unresolved")
            for node in request.findall("declaration"):
                root.append(copy.deepcopy(node))
            add_failure(root, UNKNOWN)
            path = work / "analysis.xml"
        ET.ElementTree(root).write(path)
        (work / "process.log").write_text("sealed fixture")
        check = {"status": "passed", "returncode": 0, "identity": ("boot", 123, "start")}
        common.write_record(work / "process.log.json", check)
        return check

    def test_fallback_plan_replays_without_frontend_success_and_detects_plan_tampering(self):
        with tempfile.TemporaryDirectory() as tmp:
            base, expected = Path(tmp), self.expected()
            with patch.object(fp, "native_command", side_effect=self.native) as native:
                plan, seal = fp.build_entry(base, "E", expected, None, {})
                self.assertEqual(native.call_count, 2)
            State(base).put("plan/E", plan)
            with patch.object(fp, "native_command", side_effect=AssertionError("no retry")):
                replay, replay_seal = fp.build_entry(base, "E", expected, replay=True)
            self.assertEqual((plan, seal), (replay, replay_seal))
            self.assertEqual(len(plan["contexts"][0]["groups"]), len(expected["declarations"]))
            changed = copy.deepcopy(plan)
            changed["contexts"][0]["groups"].pop()
            with self.assertRaises(ValueError):
                dp.verify_plan(changed, replay)
            with patch.object(fp, "identity", return_value=expected):
                gate = fp.checkpoint(base, {"order": ["E"], "entries": {"E": {}}},
                                     {"entries": {"E": {}}}, {"E": {}})
            self.assertTrue(gate["passed"])
            self.assertEqual(gate["meaning"], "disposition_inventory_valid")

    def test_missing_changed_resealed_request_and_missing_database_receipt_are_rejected(self):
        for change in ("missing", "changed", "resealed_request", "database"):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as tmp:
                base = Path(tmp)
                with patch.object(fp, "native_command", side_effect=self.native):
                    fp.build_entry(base, "E", self.expected(), None, {})
                state = State(base)
                key = state.keys("analysis-context/")[0]
                receipt = state.get(key)
                path = base / receipt["xml"]
                if change == "missing":
                    path.unlink()
                elif change == "changed":
                    path.write_text("<bad/>")
                elif change == "database":
                    state.update({}, remove=[key])
                else:
                    request = base / receipt["request"]
                    root = ET.parse(request).getroot()
                    root.remove(root.find("declaration"))
                    ET.ElementTree(root).write(request)
                    from scan_store import Store
                    receipt["evidence"] = Store(base).evidence([p for p in path.parent.rglob("*") if p.is_file()])
                    state.put(key, receipt)
                with self.assertRaises((ValueError, OSError)):
                    fp.build_entry(base, "E", self.expected(), replay=True)

    def test_report_and_independent_audit_keep_original_failure_and_direct_counts(self):
        import collections
        import json
        import full_report
        import full_audit
        with tempfile.TemporaryDirectory() as tmp:
            base, inputs = Path(tmp), self.expected()
            with patch.object(fp, "native_command", side_effect=self.native):
                plan, _ = fp.build_entry(base, "E", inputs, None, {})
            state = State(base)
            state.put("run", {"experiment": "fixed-plan-v2"})
            state.put("plan/E", plan)
            state.put("plan-checkpoint.json", {"passed": True})
            scope = {"Main.thy": [d["name"] for d in inputs["declarations"]]}
            record = {"scan": {"status": "passed", "theories": ["Main.thy"]}}
            with patch.object(fp, "native_command", side_effect=fake_native()):
                stage = fe.execute(base, plan, record, scope, None, {})
            result = {"entries": {"E": record}}
            data = {"order": ["E"], "entries": {"E": {"theories": [{"path": "Main.thy", "name": "Main"}]}}}
            summary = full_report.build_report(base, data, result, {"E": scope}, verified=True)
            self.assertEqual(summary["fallback_closed"], len(inputs["declarations"]))
            self.assertEqual(summary["final_unresolved_candidates"], 0)
            self.assertEqual(summary["structural_coverage"], dict.fromkeys(dp.TARGETS, 0))
            events = list(full_report.failure_events(base, data, result))
            self.assertEqual(collections.Counter(map(full_audit.failure_key, events)),
                             full_audit.required_failure_inventory(base, data, result))
            audit = {"passed": True, "issues": [], "checks": {}, "issue_counts": {}}
            full_audit.audit_reports(base, data, result, {"E": scope}, audit)
            self.assertTrue(audit["passed"], audit)
            path = base / "report/plan-dispositions.jsonl"
            rows = path.read_text().splitlines()
            path.write_text("\n".join(rows[1:]) + "\n")
            full_audit.audit_reports(base, data, result, {"E": scope}, audit)
            self.assertIn("fixed disposition inventory matches sealed plan", audit["issue_counts"])

    def test_persisted_analysis_interruption_restarts_only_the_unfinished_request(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            def interrupt(session, work, *args):
                common.write_record(work / "process.log.json", {"status": "interrupted", "returncode": -2})
                raise KeyboardInterrupt
            with patch.object(fp, "native_command", side_effect=interrupt), self.assertRaises(KeyboardInterrupt):
                fp.build_entry(base, "E", self.expected(), None, {})
            with patch.object(fp, "native_command", side_effect=self.native) as native:
                plan, _ = fp.build_entry(base, "E", self.expected(), None, {})
            self.assertEqual(native.call_count, 2)
            self.assertEqual(len(plan["contexts"]), 1)
            self.assertEqual(State(base).keys("analysis-active/"), [])

    def test_processing_failure_is_frozen_and_replayed_even_when_processor_recovers(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            def native(*args):
                check = self.native(*args)
                work = args[1]
                request = ET.parse(work / "request.xml").getroot()
                if request.get("mode") == "analyze":
                    _, g = fixture()
                    root = ET.Element("analysis", schema="2", context=request.get("context"), status="complete")
                    for d in request.findall("declaration"):
                        ET.SubElement(root, "declaration", dict(d.attrib, abstract_constructor="false"))
                    for key, value in g["nodes"].items():
                        n = ET.SubElement(root, "node", {k: v for k, v in value.items() if k != "deps"})
                        for dep in value["deps"]:
                            ET.SubElement(n, "edge", to=dep)
                    for t in dp.TARGETS:
                        ET.SubElement(root, "target", name=t)
                    ET.ElementTree(root).write(work / "analysis.xml")
                return check
            with patch.object(fp, "native_command", side_effect=native), \
                    patch.object(dp, "make_context_plan", side_effect=RuntimeError("transient planner failure")):
                plan, seal = fp.build_entry(base, "E", self.expected(), None, {})
            replay, other = fp.build_entry(base, "E", self.expected(), replay=True)
            self.assertEqual((plan, seal), (replay, other))
            state = State(base)
            key = state.keys("analysis-processing/")[0]
            receipt = state.get(key)
            receipt["input"]["context"] = "tampered"
            state.put(key, receipt)
            with self.assertRaisesRegex(ValueError, "Changed plan-processing"):
                fp.build_entry(base, "E", self.expected(), replay=True)

    def test_missing_native_service_is_unresolved_context_not_rejection(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(fp, "native_command", side_effect=FileNotFoundError("isabelle service missing")):
                plan, _ = fp.build_entry(Path(tmp), "E", self.expected(), None, {})
            self.assertEqual(plan["contexts"], [])
            self.assertEqual(plan["unresolved_contexts"][0]["status"], "unresolved_context")

    def test_python_evidence_error_and_missing_native_receipt_do_not_prune(self):
        for mode in ("python", "missing"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                base = Path(tmp)
                def native(*args):
                    check = self.native(*args)
                    work = args[1]
                    if mode == "missing" and (work / "analysis.xml").exists():
                        (work / "analysis.xml").unlink()
                    return check
                patches = [patch.object(fp, "native_command", side_effect=native)]
                if mode == "python":
                    patches.append(patch.object(fp, "parse_response", side_effect=RuntimeError(WELL)))
                from contextlib import ExitStack
                with ExitStack() as stack:
                    for p in patches:
                        stack.enter_context(p)
                    plan, seal = fp.build_entry(base, "E", self.expected(), None, {})
                    replay, other = fp.build_entry(base, "E", self.expected(), replay=True)
                self.assertEqual((plan, seal), (replay, other))
                self.assertTrue(all(d["status"] == "singleton_fallback"
                                    for d in plan["contexts"][0]["classifications"]))

if __name__ == "__main__":
    unittest.main()
