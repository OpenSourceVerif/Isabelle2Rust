"""Explicit analysis deferral and bounded export/compile continuation."""
import _paths
import copy
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch

import afp_common as common
import continuation as cont
import dependency_plan as dp
import fixed_export as fe
import fixed_pipeline as pipeline
import fixed_plan as fp
import full
from result_store import EntryStore
from scan_store import Store, digest, file_digest
from state import State
import test_plan_recovery as recovery_tests
from test_plan_recovery import fake_native, failure, add_failure


def authorize(base, entries=("E",), tools=None):
    state = State(base)
    origin = {"tools": tools or {}, "parent_run": "parent", "record_signature": "snapshot"}
    policy = {"schema": 1, "parent": "/original", "cutoff": "2026-11-18",
              "deferred_entries": list(entries), "reason": "User requested singleton continuation",
              "allow_partial_compile": True, "origin": digest(origin)}
    state.update({"run": {"experiment": "fixed-plan-v2", "tools": tools or {}, "continuation": digest(policy)},
                  "continuation-origin": origin, "continuation-policy": policy})
    return policy


class DeferredPlanTests(unittest.TestCase):
    def test_replay_preserves_singleton_rejections_and_defers_only_missing_requests(self):
        fixture = recovery_tests.PlanEvidenceTests()
        expected, calls = fixture.expected(), []
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            def interrupted(*args):
                work = args[1]
                request = ET.parse(work / "request.xml").getroot()
                calls.append(request.get("mode"))
                if len(calls) == 5:
                    raise KeyboardInterrupt
                check = fixture.native(*args)
                if request.get("mode") == "analyze":
                    root = ET.parse(work / "analysis.xml").getroot()
                    root.remove(root.find("failure"))
                    add_failure(root, failure())
                    ET.ElementTree(root).write(work / "analysis.xml")
                return check
            with patch.object(fp, "native_command", side_effect=interrupted), self.assertRaises(KeyboardInterrupt):
                fp.build_entry(base, "E", expected, None, {})
            authorize(base)
            with patch.object(fp, "native_command", side_effect=AssertionError("no new native analysis")):
                plan, seal = fp.build_entry(base, "E", expected, replay=True, defer_missing=True)
                replay, reseal = fp.build_entry(base, "E", expected, replay=True)
            self.assertEqual((plan, seal), (replay, reseal))
            rows = plan["contexts"][0]["classifications"]
            self.assertTrue(any(d["status"] == "frontend_rejected" for d in rows))
            self.assertTrue(any(d["status"] == "singleton_fallback" for d in rows))
            self.assertEqual(len(rows), len(expected["declarations"]))
            self.assertTrue(all(g.get("coverage") is None for g in plan["contexts"][0]["groups"]))
            state = State(base)
            key = state.keys("analysis-deferred/")[0]
            state.update({}, remove=[key])
            with self.assertRaises(ValueError):
                fp.build_entry(base, "E", expected, replay=True)

    def test_deferred_identity_authorization_and_conflicting_native_receipt_are_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            authorize(base)
            expected = {"declarations": [{"source": "A.thy", "owner": "A", "name": "A.f"}]}
            key = "analysis-context/c"
            first = cont.deferred_request(base, "E", key, expected, create=True)
            self.assertEqual(first["failure"]["phase"], "user_deferred")
            for changed in (dict(expected, parents=["changed"]), {}):
                with self.assertRaises(ValueError):
                    cont.deferred_request(base, "E", key, changed)
            with self.assertRaises(ValueError):
                cont.deferred_request(base, "Other", key, expected, create=True)
            State(base).put(key, {"status": "complete"})
            with self.assertRaises(ValueError):
                cont.deferred_request(base, "E", key, expected)

    def test_missing_selection_cannot_be_fabricated_for_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            authorize(base)
            with self.assertRaises(ValueError):
                fp.build_entry(base, "E", recovery_tests.PlanEvidenceTests().expected(), replay=True, defer_missing=True)
            self.assertFalse(State(base).keys("analysis-deferred/"))

    def test_native_tool_change_or_changed_authorization_blocks_reuse(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            old = {"native.ML": "original"}
            authorize(base, tools=old)
            self.assertEqual(cont.analysis_tools(base, old), old)
            with self.assertRaises(ValueError):
                cont.analysis_tools(base, {"native.ML": "changed"})
            state = State(base)
            changed = state.get("continuation-policy")
            changed["reason"] = "tampered"
            state.put("continuation-policy", changed)
            with self.assertRaises(ValueError):
                cont.policy(base)


class SnapshotTests(unittest.TestCase):
    def test_indexed_prefix_keeps_literal_metacharacters_and_unicode(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = State(Path(tmp))
            keys = ["a/x", "a/y", "ab/x", "a%/x", "a[/x", "?/x"]
            state.update(dict.fromkeys(keys, {}))
            for prefix in ["", "a/", "a%", "a[", "?/", "missing"]:
                self.assertEqual(state.keys(prefix), sorted(k for k in keys if k.startswith(prefix)))

    def test_snapshot_copies_only_sealed_files_and_never_reuses_live_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            parent, child = Path(tmp) / "parent", Path(tmp) / "child"
            state = State(parent)
            state.put("run", {"experiment": "fixed-plan-v2", "tools": {}, "created": "earlier",
                             "manifest": {"entries": {"E": {}}}})
            sealed = parent / "analysis/k/attempt-0001/result.xml"
            sealed.parent.mkdir(parents=True)
            sealed.write_text("<sealed/>")
            mutable = parent / "analysis/live/attempt-0001/process.log"
            mutable.parent.mkdir(parents=True)
            mutable.write_text("running")
            state.put("analysis-context/k", {"evidence": Store(parent).evidence([sealed])})
            state.put("analysis-active/live", {"directory": str(mutable.parent.relative_to(parent))})
            state.put(str(mutable.relative_to(parent)) + ".json", {"status": "running"})
            state.put("plan/Other", {"id": "frozen"})
            before = state.signature(("",))
            cont.snapshot(parent, child, ["E"], "Keep process, defer analysis", {})
            self.assertEqual(state.signature(("",)), before)
            self.assertEqual(State(child).get("plan/Other"), {"id": "frozen"})
            self.assertFalse(State(child).keys("analysis-active/"))
            self.assertFalse((child / mutable.relative_to(parent)).exists())
            self.assertIsNone(State(child).get(str(mutable.relative_to(parent)) + ".json"))
            copied = child / sealed.relative_to(parent)
            sealed.write_text("<later/>")
            self.assertEqual(copied.read_text(), "<sealed/>")
            with self.assertRaises(ValueError):
                cont.snapshot(parent, child, ["E"], "again", {})

    def test_corrupt_sealed_file_and_nested_destination_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp) / "parent"
            state = State(parent)
            state.put("run", {"experiment": "fixed-plan-v2", "tools": {},
                             "manifest": {"entries": {"E": {}}}})
            file = parent / "sealed.xml"
            file.write_text("<sealed/>")
            state.put("analysis-context/k", {"evidence": Store(parent).evidence([file])})
            file.write_text("<changed/>")
            with self.assertRaises(ValueError):
                cont.snapshot(parent, Path(tmp) / "child", ["E"], "defer", {})
            with self.assertRaises(ValueError):
                cont.snapshot(parent, parent / "nested", ["E"], "defer", {})


class PipelineTests(unittest.TestCase):
    def test_round_robin_preserves_fixed_requests_and_does_not_starve_entries(self):
        a = recovery_tests.ExecutionTests().plan(3)
        b = copy.deepcopy(a)
        b["entry"] = "Other"
        stream = list(pipeline.jobs({"E": a, "Other": b}))
        self.assertEqual([x[0] for x in stream], ["E", "Other"] * 3)
        self.assertEqual({x[2]["id"] for x in stream}, set(fe.groups(a)))

    def test_compilation_overlaps_exports_and_unknown_group_does_not_block_healthy_crates(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            plan = recovery_tests.ExecutionTests().plan(3)
            authorize(base)
            State(base).put("plan/E", plan)
            scans, scopes = {"E": {"scan": {}}}, {"E": {}}
            result = {"entries": EntryStore(base, scans, scopes)}
            data = {"order": ["E"], "entries": {"E": {}}}
            began_compile, lock = threading.Event(), threading.Lock()
            calls, active, peak = [], 0, 0
            def native(*args):
                nonlocal active, peak
                with lock:
                    index = len(calls)
                    calls.append(index)
                    active += 1
                    peak = max(peak, active)
                try:
                    if index == 2:
                        self.assertTrue(began_compile.wait(5), "compilation waited for the full export phase")
                        return fake_native("unknown")(*args)
                    check = fake_native("passed")(*args)
                    work = args[1]
                    crate = work / "artifacts/Rust"
                    crate.mkdir(parents=True)
                    manifest = crate / "Cargo.toml"
                    manifest.write_text("[package]\nname='fixture'\nversion='0.0.0'\n")
                    rust = next((work / "attempts").rglob("Rust.xml"))
                    root = ET.parse(rust).getroot()
                    root.remove(root.find("library_only"))
                    ET.SubElement(root, "file").text = str(manifest.relative_to(work))
                    ET.ElementTree(root).write(rust)
                    return check
                finally:
                    with lock:
                        active -= 1
            def compile_entry(entry, record, base, args, env, optimizer, checkpoint):
                began_compile.set()
                for manifest in full.rust_manifests(record):
                    terminal = {"status": "passed", "checks": [{"status": "passed"}]}
                    record["full_compile"][manifest] = {"complete": True,
                        "stage1_compile": terminal, "optimization": {"status": "passed"},
                        "stage2_compile": terminal}
                checkpoint()
            options = SimpleNamespace(export_workers=2, compile_workers=1)
            with patch.object(fp, "require_gate"), patch.object(fp, "native_command", side_effect=native), \
                    patch.object(full, "compile_entry", side_effect=compile_entry):
                counts = pipeline.execute(base, data, result, scopes, options, {}, Path("optimizer"))
            self.assertEqual(counts["export_attempted"], 3)
            self.assertEqual(counts["export_unresolved"], 1)
            self.assertEqual(counts["compiled_crates"], 2)
            self.assertLessEqual(peak, 2)
            record = EntryStore(base, scans, scopes)["E"]
            self.assertEqual(record["full_export"]["status"], "blocked")
            self.assertEqual(len(record["full_compile"]), 2)
            with self.assertRaises(ValueError):
                fe.validate_stage(base, plan, record["full_export"])
            self.assertFalse(State(base).keys("fixed-progress/"))
            self.assertFalse(State(base).keys("compile-group/"))
            observed = full.entry_compiled(record, scopes["E"], full.serializer_signature())
            self.assertEqual(len(observed["stage1_compile"]), 2)
            # Resume reuses both completed export/compile results; only the
            # unknown third request is retried in this second invocation.
            calls = []
            with patch.object(fp, "require_gate"), patch.object(fp, "native_command",
                    side_effect=fake_native("passed", calls)), patch.object(common, "command",
                    side_effect=AssertionError("completed compiler must not repeat")):
                second = pipeline.execute(base, data, result, scopes, options, {}, Path("optimizer"))
            self.assertEqual(len(calls), 1)
            self.assertEqual(second["export_closed"], 3)
            self.assertEqual(second["compiled_crates"], 2)

    def test_compilation_never_adds_lockfiles_to_sealed_exports(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = base / "exports/crate/Cargo.toml"
            source.parent.mkdir(parents=True)
            source.write_text("[package]\\n")
            rust = source.parent / "src/lib.rs"
            rust.parent.mkdir()
            rust.write_text("pub fn healthy() {}")
            record = {"full_export": {"mode": "fixed-plan-v2", "runs": [{"attempts": [
                {"target": "Rust", "status": "passed", "files": [str(source)]}]}]}}
            def compile_crates(manifests, phase, args, env, logs):
                for path in manifests:
                    (path.parent / "Cargo.lock").write_text("pinned")
                return {"status": "passed", "checks": [{"status": "passed"}]}
            def optimize(argv, log, args, env):
                out = Path(argv[-1])
                out.mkdir(parents=True)
                (out / "Cargo.toml").write_text("optimized")
                return {"status": "passed", "log": str(log)}
            with patch.object(full, "compile_crates", side_effect=compile_crates), \
                    patch.object(full, "completed_command", side_effect=optimize):
                full.compile_entry("E", record, base, None, {}, Path("optimizer"))
            self.assertFalse((source.parent / "Cargo.lock").exists())
            self.assertEqual(rust.read_text(), "pub fn healthy() {}")
            item = record["full_compile"][str(source)]
            copied = common.resolve_path(item["stage1_source"])
            self.assertEqual((copied / "Cargo.lock").read_text(), "pinned")
            self.assertTrue(full.compile_checkpoint(base, {"entries": {"E": record}})["passed"])
            (copied / "src/lib.rs").write_text("tampered")
            self.assertFalse(full.compile_checkpoint(base, {"entries": {"E": record}})["passed"])

    def test_unknown_export_cannot_enter_compilation(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = recovery_tests.ExecutionTests().plan(1)
            context, group = next(iter(fe.groups(plan).values()))
            with patch.object(full, "compile_entry", side_effect=AssertionError("not admitted")):
                with self.assertRaises(ValueError):
                    pipeline.compile_group(Path(tmp), plan, context, group, {"closed": False},
                                           None, {}, Path("optimizer"))


if __name__ == "__main__":
    unittest.main()
