import csv
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import target_compile as compilation
from dependency_plan import ENTRY_PIPELINE
from state import State


def sealed(path):
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


class TargetCompilationTest(unittest.TestCase):
    def test_inventory_reuses_identical_sources_but_records_every_scope(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            state = State(base)
            stage = {"mode": ENTRY_PIPELINE, "plan_id": "plan", "runs": []}
            contexts = []
            observations = {}
            for name in ("a", "b"):
                group = {"id": name, "session": "Session", "entries": ["Example.f"]}
                contexts.append({"context": {"id": "branch"}, "groups": [group]})
                work = base / "exports" / "Example" / name / "attempt-1"
                artifact = work / "artifacts" / "branch" / "code" / "OCaml" / (name + ".ocaml")
                request = work / "ocaml.xml"
                artifact.parent.mkdir(parents=True)
                artifact.write_text("let f () = 1\n")
                request.write_text("<attempt/>\n")
                stage["runs"].append({
                    "group": name, "context": "branch", "session": "Session", "scope": ["Example.f"],
                    "directory": str(work), "closed": True,
                    "evidence": {str(p.relative_to(base)): sealed(p) for p in (artifact, request)},
                })
                observations[work] = [{"target": "OCaml", "status": "passed", "context": "branch",
                                       "batch": name, "constants": ["Example.f"], "evidence": str(request),
                                       "files": [str(artifact)], "library_only": False}]
            state.put("entry/Example", {"full_export": stage})
            state.put("plan/Example", {"id": "plan", "contexts": contexts})
            with patch.object(compilation, "native_view", side_effect=lambda p: (observations[p], None, None)):
                rows, jobs = compilation.inventory(base, state, ["Example"], {"OCaml": "compiler"})
                self.assertEqual(len(jobs), 1)
                self.assertEqual(len(rows), 10)
                self.assertEqual({r.job for r in rows if r.status == "pending"}, set(jobs))
                self.assertEqual(sum(r.status == "not_exported" for r in rows), 8)
                artifact.write_text("let f () = 2\n")
                with self.assertRaisesRegex(ValueError, "Changed sealed export file"):
                    compilation.inventory(base, state, ["Example"], {"OCaml": "compiler"})

    def test_large_sml_sources_use_polyml_object_compilation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            file = ((Path("AFP_Code.sml"), root / "source.sml",
                     {"bytes": compilation.SML_LARGE_SOURCE_BYTES}),)
            job = compilation.compile_input("SML", file)
            command = compilation.arguments_for(job, ["poly"], root)
            self.assertEqual(command, ["poly", *compilation.SML_POLY_FLAGS])
            driver = (root / "compile_only.ML").read_text()
            self.assertIn('PolyML.export ("AFP_Code", artifact)', driver)
            self.assertIn("PolyML.Compiler.lowlevelOptimise := false", driver)
            self.assertFalse(compilation.compile_input("Go", file).large_sml)
            file[0][2]["bytes"] -= 1
            self.assertFalse(compilation.compile_input("SML", file).large_sml)

    def test_scoped_publication_preserves_the_full_report(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            state = State(base)
            report = base / "report"
            report.mkdir()
            (report / "summary.json").write_text('{"rust_crates": 2}')
            rows = [compilation.Request("First", "group", "branch", "Go", "library_only")]
            full = compilation.publish(base, state, rows, {}, {}, {}, ["First", "Second"],
                                       {"First", "Second"}, True)
            original = (report / "summary.json").read_bytes()
            scoped = compilation.publish(base, state, rows, {}, {}, {}, ["First"], {"First"}, False)
            self.assertNotEqual(full["table"], scoped["table"])
            self.assertEqual((report / "summary.json").read_bytes(), original)
            self.assertEqual(state.get(compilation.SUMMARY), full)
            self.assertIsNone(compilation.checkpoint_problem(base, ["First", "Second"]))
            (report / full["table"]).unlink()
            self.assertIsNone(compilation.checkpoint_problem(base, ["First"]))
            self.assertIsNotNone(compilation.checkpoint_problem(base, ["Second"]))

    def test_compilation_checkpoint_detects_changed_export_state_or_report(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            state = State(base)
            state.put("entry/Example", {"signature": "first"})
            rows = [compilation.Request("Example", "group", "branch", "Go", "pending", "job"),
                    compilation.Request("Example", "group", "branch", "Scala", "library_only")]
            receipts = {"job": {"status": "failed", "log": "compiler.log", "log_sha256": "hash"}}
            result = compilation.publish(base, state, rows, receipts, {"job": object()}, {},
                                         ["Example"], {"Example"}, True)
            self.assertTrue(result["complete"])
            self.assertIsNone(compilation.checkpoint_problem(base, ["Example"]))
            path = base / "report" / compilation.TABLE
            with path.open(newline="") as stream:
                self.assertEqual([row["status"] for row in csv.DictReader(stream)], ["failed", "library_only"])
            original = path.read_bytes()
            path.write_text("modified")
            self.assertIsNotNone(compilation.checkpoint_problem(base, ["Example"]))
            path.write_bytes(original)
            state.put("entry/Example", {"signature": "new export"})
            self.assertIsNotNone(compilation.checkpoint_problem(base, ["Example"]))


if __name__ == "__main__":
    unittest.main()
