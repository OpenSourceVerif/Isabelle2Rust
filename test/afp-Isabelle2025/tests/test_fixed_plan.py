"""Deterministic dependency planning and fixed request invariants."""
import _paths
import copy
import tempfile
import unittest
from pathlib import Path

import dependency_plan as dp
import fixed_export
import native_patch
import afp_common as common


def graph(missing=()):
    nodes = {
        "CONST Main.f": {"id": "CONST Main.f", "name": "Main.f", "owner": "Main",
                         "kind": "function", "equations": "ordinary", "deps": ["CONST Main.u", "CONST Main.v"]},
        "CONST Main.u": {"id": "CONST Main.u", "name": "Main.u", "owner": "Main",
                         "kind": "none" if "u" in missing else "function",
                         "equations": "missing" if "u" in missing else "ordinary", "deps": []},
        "CONST Main.v": {"id": "CONST Main.v", "name": "Main.v", "owner": "Main",
                         "kind": "none" if "v" in missing else "function",
                         "equations": "missing" if "v" in missing else "ordinary", "deps": []},
        "CONST Main.left": {"id": "CONST Main.left", "name": "Main.left", "owner": "Main",
                            "kind": "function", "equations": "ordinary", "deps": []},
        "CONST Main.right": {"id": "CONST Main.right", "name": "Main.right", "owner": "Main",
                             "kind": "function", "equations": "ordinary", "deps": []},
    }
    return {"nodes": nodes, "declarations": [
        {"source": "Main.thy", "owner": "Main", "name": n, "abstract_constructor": "false"}
        for n in ("Main.f", "Main.u", "Main.v", "Main.left", "Main.right")
    ], "printings": {target: [] for target in dp.TARGETS}}


def context():
    return {"id": "ctx", "entry": "E", "session": "E", "parents": ["Main", *dp.SETUPS],
            "entry_theories": ["Main"], "input": {"source": "fixture"}}


class PlannerTests(unittest.TestCase):
    def test_complete_closure_is_required_per_target(self):
        value = dp.make_context_plan(context(), graph({"u", "v"}))
        rows = {r["name"]: r for r in value["classifications"]}
        self.assertEqual(rows["Main.f"]["status"], "excluded")
        self.assertEqual(rows["Main.u"]["status"], "excluded")
        self.assertEqual(rows["Main.left"]["status"], "retained")

    def test_explicit_empty_equation_is_not_treated_as_missing(self):
        value = graph()
        value["nodes"]["CONST Main.u"].update(kind="none", equations="empty")
        plan = dp.make_context_plan(context(), value)
        row = next(r for r in plan["classifications"] if r["name"] == "Main.u")
        self.assertEqual(row["status"], "retained")
        self.assertEqual(row["equations"], "empty")

    def test_one_target_printing_does_not_hide_frontend_dependency(self):
        value = graph({"u"})
        value["printings"]["Rust"] = ["CONST Main.u"]
        plan = dp.make_context_plan(context(), value)
        row = next(r for r in plan["classifications"] if r["name"] == "Main.f")
        self.assertEqual(row["status"], "retained")
        self.assertFalse(row["targets"]["Rust"]["blocked"])
        self.assertTrue(row["targets"]["SML"]["blocked"])
        self.assertIn("CONST Main.u", row["targets"]["SML"]["blockers"][0]["path"])

    def test_scc_and_entry_internal_computation_make_stable_groups(self):
        value = graph()
        value["nodes"]["CONST Main.left"]["deps"] = ["CONST Main.right"]
        value["nodes"]["CONST Main.right"]["deps"] = ["CONST Main.left"]
        a = dp.make_context_plan(context(), value)
        b = dp.make_context_plan(context(), dict(value, nodes=dict(reversed(list(value["nodes"].items())))))
        self.assertEqual(a["groups"], b["groups"])
        self.assertEqual(a["id"] if "id" in a else dp.assemble("E", {"input": "x"}, [a])["id"],
                         dp.assemble("E", {"input": "x"}, [b])["id"])

    def test_abstract_constructor_is_ineligible_and_structural_rows_are_kept(self):
        value = graph()
        value["declarations"][0]["abstract_constructor"] = "true"
        value["nodes"]["CONST Main.f"]["kind"] = "constructor"
        value["nodes"]["CONST Main.f"]["equations"] = "structural"
        value["nodes"]["CONST Main.f"]["structural_owner"] = "Main.t"
        plan = dp.make_context_plan(context(), value)
        row = next(r for r in plan["classifications"] if r["name"] == "Main.f")
        self.assertEqual(row["status"], "ineligible")
        self.assertIn("Main.left", {r["name"] for r in plan["classifications"]})

    def test_plan_rejects_unknown_or_inconsistent_native_facts(self):
        value = graph()
        value["nodes"]["CONST Main.u"]["deps"] = ["CONST missing"]
        with self.assertRaises(ValueError):
            dp.make_context_plan(context(), value)

    def test_native_patch_is_idempotent_and_pinned(self):
        home = Path(common.CONFIG.get("isabelle", "/missing")).resolve().parent.parent
        source_path = home / "src/Tools/Code/code_target.ML"
        if not source_path.is_file():
            self.skipTest("Isabelle2025 source is not installed")
        source = source_path.read_bytes()
        patched = native_patch.patched(source)
        self.assertEqual(native_patch.patched(patched), patched)
        self.assertEqual(native_patch.verify(home)["sha256"], native_patch.sha(patched))
        with self.assertRaises(ValueError):
            native_patch.patched(source.replace(b"Code_Target", b"Code_Target_X", 1))

    def test_tampered_plan_is_rejected_by_recomputation(self):
        expected = dp.assemble("E", {"input": "x"}, [dp.make_context_plan(context(), graph())])
        altered = copy.deepcopy(expected)
        altered["contexts"][0]["groups"][0]["entries"].append("Main.injected")
        with self.assertRaisesRegex(ValueError, "altered fixed dependency plan"):
            dp.verify_plan(altered, expected)

    def test_formal_plan_result_directory_cannot_escape(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            from state import State
            State(root)
            run = {"directory": str(root / "foreign"), "group": "g", "scope": [], "session": "E", "context": "c"}
            group = {"id": "g", "entries": [], "session": "E"}
            context_value = {"entry": "E", "id": "c"}
            with self.assertRaises(ValueError):
                fixed_export.check_run(root, run, context_value, group)

if __name__ == "__main__":
    unittest.main()
