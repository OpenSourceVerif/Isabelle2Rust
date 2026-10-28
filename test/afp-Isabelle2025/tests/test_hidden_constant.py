#!/usr/bin/env python3
"""Opt-in native regression for exporting internally named hidden constants.

Run with AFP_TEST_HIDDEN_CONSTANT=1. A fully hidden boolean function must fail
Code.read_const's surface-name lookup while its internal declaration exports
through the current Thingol/target APIs in all six languages. Preserve the full
legacy diagnostic and generated sources without compiling or running them.
"""

import _paths  # Locate AFP tools independently of cwd and unittest discovery.
import os
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

import afp_common as common
import full


@unittest.skipUnless(os.environ.get("AFP_TEST_HIDDEN_CONSTANT") == "1",
                     "opt-in native hidden-constant export regression")
class HiddenConstantIntegration(unittest.TestCase):
    def test_internal_name_exports_after_surface_name_is_fully_hidden(self):
        # Use a read-only HOL heap and a separate output directory. This tiny
        # process neither rebuilds AFP sessions nor writes the main coverage
        # matrix, so it can run while the proof-building phase holds its lock.
        base = common.WORK / "regression"
        work = full.next_attempt(base / "tooling/hidden-constant-fixture")
        args = common.arguments(__doc__).parse_args([
            "--timeout", "0", "--max-heap-mb", "1000", "--java-heap-mb", "256",
            "--min-available-mb", "512"])
        env, metadata = common.environment(args)
        name = "Hidden_Constant.hidden_not"
        (work / "scope.txt").write_text(name + "\n")
        (work / "theories.txt").write_text("AFP-Scan-Fixture.Hidden_Constant\n")
        probe = work / "name-resolution.ML"
        probe.write_text(r"""
(* Internal names survive hide_const; only the external syntax lookup fails.
   Record the original exception before exercising the production exporter. *)
val hidden_thy = Thy_Info.get_theory "AFP-Scan-Fixture.Hidden_Constant";
val hidden_name = "Hidden_Constant.hidden_not";
val _ = if Sign.declared_const hidden_thy hidden_name then ()
        else error "Hidden internal declaration is missing";
val hidden_error =
  (case Exn.capture (Code.read_const hidden_thy) hidden_name of
    Exn.Res _ => error "Fully hidden name unexpectedly accessible"
  | Exn.Exn exn => if Exn.is_interrupt exn then Exn.reraise exn
                  else Runtime.exn_message exn);
val hidden_record = XML.Elem (("name_resolution",
  [("name", hidden_name), ("declared", "true"), ("surface_lookup", "failed")]),
  [XML.Elem (("error", []), [XML.Text hidden_error])]);
val _ = File.write (Path.explode (getenv_strict "AFP_FULL_OUTPUT")
          + Path.basic "name-resolution.xml") (XML.string_of hidden_record);
""")
        execute = common.command

        def with_fixture(argv, log, settings, actual):
            # Reuse the production command, adding only the independent theory
            # and an earlier ML observation. The actual serializer and its
            # internal-name entry point remain full_export.ML.
            argv = list(argv)
            first_theory = argv.index("-T")
            argv[first_theory:first_theory] = [
                "-d", str(common.EXPERIMENT / "tests/fixtures"),
                "-T", "AFP-Scan-Fixture.Hidden_Constant"]
            first_expression = argv.index("-e")
            argv[first_expression:first_expression] = [
                "-e", "ML_Context.eval_file ML_Compiler.flags (Path.explode "
                + common.quote(str(probe)) + ")"]
            return execute(argv, log, settings, actual)

        with patch.object(common, "command", side_effect=with_fixture):
            check = full.export_command("HOL", work, args, env)
        self.assertEqual(check["status"], "passed",
                         (work / "process.log").read_text())
        self.assertTrue((work / "finished.xml").is_file())
        observed = ET.parse(work / "name-resolution.xml").getroot()
        self.assertEqual(observed.attrib["declared"], "true")
        self.assertEqual(observed.attrib["surface_lookup"], "failed")
        self.assertIn("Inaccessible constant", observed.findtext("error", ""))
        attempts = full.collect_attempts(work)
        outcomes = full.resolve_candidates([name], [{"attempts": attempts}])
        for target in full.TARGETS:
            self.assertEqual(outcomes[name][target]["status"], "passed",
                             (target, outcomes))
            exported = [a for a in attempts if a["target"] == target]
            self.assertTrue(exported and all(a["files"] for a in exported))
        files = sorted({path for attempt in attempts for path in attempt["files"]})
        self.assertTrue(all((common.PROJECT / path).is_file() for path in files))
        common.write_json(base / "hidden-constant-validation.json",
            {"status": "passed", "checked": common.timestamp(),
             "directory": common.relative(work), "environment": metadata,
             "command": check, "outcomes": outcomes,
             "name_resolution_evidence": common.relative(work / "name-resolution.xml"),
             "artifacts": [{"path": path,
                            "sha256": full.file_digest(common.PROJECT / path),
                            "bytes": (common.PROJECT / path).stat().st_size}
                           for path in files],
             "checks": ["hidden internal declaration retained",
                        "surface name lookup rejected with complete diagnostic",
                        "current internal-name export succeeds in all six targets",
                        "all generated sources retained",
                        "generated programs neither compiled nor executed"]})


if __name__ == "__main__":
    unittest.main()
