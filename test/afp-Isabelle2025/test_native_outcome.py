#!/usr/bin/env python3
"""Opt-in native checks of outer export receipts, with no target execution.

AFP_NATIVE_OUTCOME_TEST=1 runs the ML facility fixtures and compares an actual
six-language export against the original direct invocation. All processes run
serially on an immutable HOL heap and retain their full evidence separately.
"""
import os
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

import afp_common as common
import full


@unittest.skipUnless(os.environ.get("AFP_NATIVE_OUTCOME_TEST") == "1",
                     "opt-in native export-outcome recorder regression")
class NativeOutcomeTests(unittest.TestCase):
    def setUp(self):
        self.work = full.next_attempt(common.HERE / "full/tooling/native-outcome-regression")
        self.args = common.arguments(__doc__).parse_args([
            "--timeout", "0", "--max-heap-mb", "1200", "--java-heap-mb", "128",
            "--stack-space-mb", "64", "--min-available-mb", "512",
            "--compiler-settings", str(common.HERE / "full/compiler-settings.json")])
        self.env, self.metadata = common.environment(self.args)

    def capture_fixture(self, source):
        # A facility fixture isolates evaluation from the exporter. In
        # particular, returning without finished.xml must remain distinct from
        # a completed export, and a source exception must still fail the process.
        fixture = self.work / "original-fixture.ML"
        fixture.write_text(source)
        checksum = full.file_digest(fixture)
        (self.work / "scope.txt").write_text("Native_Outcome.fixture\n")
        actual = dict(self.env, AFP_FULL_OUTPUT=str(self.work),
                      AFP_FULL_SCOPE=str(self.work / "scope.txt"),
                      AFP_ORIGINAL_EXPORT_ML=str(fixture))
        expression = (
            'Context.setmp_generic_context (SOME (Context.Theory (Thy_Info.get_theory "Main"))) '
            '(ML_Context.eval_file ML_Compiler.flags) (Path.explode '
            + common.quote(str(common.HERE / "full_capture.ML")) + ')')
        check = common.command([
            self.args.isabelle, "process", "-l", "HOL", "-o", "threads=1",
            "-o", "parallel_proofs=0", "-o", "timeout=0", "-o", "skip_proofs=false",
            "-e", expression], self.work / "process.log", self.args, actual)
        node = ET.parse(self.work / "native-request-outcome.xml").getroot()
        self.assertEqual(full.file_digest(fixture), checksum)
        self.assertEqual(node.tag, "native_request_outcome")
        self.assertEqual(node.attrib["origin"], "original_full_export_outer_capture")
        self.assertEqual([row.attrib["name"] for row in node.findall("constant")],
                         ["Native_Outcome.fixture"])
        self.assertEqual(node.findtext("original_script"), str(fixture))
        self.assertGreaterEqual(float(node.findtext("seconds")), 0)
        self.assertEqual(node.findtext("original_finished_exists"), "false")
        self.assertFalse((self.work / "finished.xml").exists())
        self.assertFalse(list(self.work.glob("attempts/**/*.xml")))
        common.write_json(self.work / "validation.json", {
            "command": check, "environment": self.metadata, "facility_fixture_only": True,
            "generated_program_run": False, "fixture_sha256": checksum,
            "outcome_sha256": full.file_digest(self.work / "native-request-outcome.xml")})
        return check, node

    def test_return_does_not_manufacture_frontend_or_finished_witnesses(self):
        # The evaluated source returns normally but supplies no exporter
        # witnesses. The outer receipt must say returned without asserting that
        # code generation completed or creating a synthetic frontend attempt.
        check, node = self.capture_fixture('val _ = ();\n')
        self.assertEqual(check["status"], "passed", check)
        self.assertEqual(node.attrib["status"], "returned")
        self.assertIsNone(node.find("exception_name"))
        self.assertIsNone(node.find("exception_message"))

    def test_unhandled_exception_is_retained_and_rethrown(self):
        # ML_Context.eval_file renders an ordinary source Fail through
        # ML_Compiler's error buffer, then raises ERROR. The recorder must keep
        # that actual outer exception and the original Fail payload, rather
        # than inventing an unwrapped inner exception or a candidate verdict.
        marker = "AFP native outcome fixture: deliberate source exception"
        check, node = self.capture_fixture('val _ = raise Fail ' + common.quote(marker) + ';\n')
        self.assertEqual(check["status"], "failed", check)
        self.assertEqual(node.attrib["status"], "exception")
        self.assertEqual(node.findtext("exception_name"), "ERROR")
        self.assertIn(marker, node.findtext("exception_message", ""))
        self.assertIn(marker, (self.work / "process.log").read_text())
        self.assertNotEqual(check["returncode"], 0)

    def test_actual_six_language_artifacts_match_direct_original_invocation(self):
        # Compare the same real List.rev request, original exporter, backends
        # and explicit module with and without the outer recorder. Both runs
        # must independently cover all six languages and retain identical bytes.
        # No exported source is compiled or executed by this regression.
        directories = [self.work / name for name in ("direct", "captured")]
        for directory in directories:
            directory.mkdir()
            (directory / "scope.txt").write_text("List.rev\n")
            (directory / "theories.txt").write_text("Main\n")
        execute = common.command

        def direct_original(argv, log, args, env):
            argv = list(argv)
            index = argv.index("-e") + 1
            old = str(common.HERE / "full_capture.ML")
            self.assertIn(old, argv[index])
            argv[index] = argv[index].replace(old, str(common.HERE / "full_export.ML"))
            return execute(argv, log, args, env)

        with patch.object(common, "command", side_effect=direct_original):
            direct = full.export_command("HOL", directories[0], self.args, self.env)
        captured = full.export_command("HOL", directories[1], self.args, self.env)
        for directory, command in zip(directories, (direct, captured)):
            self.assertEqual(command["status"], "passed", command)
            self.assertTrue((directory / "finished.xml").is_file())
            attempts = full.collect_attempts(directory)
            outcomes = full.resolve_candidates(["List.rev"], [{"attempts": attempts}])
            self.assertEqual({target: outcomes["List.rev"][target]["status"] for target in full.TARGETS},
                             {target: "passed" for target in full.TARGETS})
        def artifacts(directory):
            return {str(path.relative_to(directory / "artifacts")): path.read_bytes()
                    for path in sorted((directory / "artifacts").rglob("*")) if path.is_file()}
        original_files, captured_files = [artifacts(directory) for directory in directories]
        self.assertTrue(original_files)
        self.assertEqual(original_files, captured_files)
        outcome = ET.parse(directories[1] / "native-request-outcome.xml").getroot()
        self.assertEqual(outcome.attrib["status"], "returned")
        self.assertEqual(outcome.findtext("original_finished_exists"), "true")
        self.assertFalse((directories[0] / "native-request-outcome.xml").exists())
        common.write_json(self.work / "validation.json", {
            "direct": direct, "captured": captured, "environment": self.metadata,
            "artifact_count": len(original_files), "all_six_language_outcomes": "passed",
            "artifact_bytes_identical": True, "generated_program_run": False,
            "serializer_sha256": full.serializer_signature()})


if __name__ == "__main__":
    unittest.main()