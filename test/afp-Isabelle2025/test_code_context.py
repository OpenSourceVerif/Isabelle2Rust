#!/usr/bin/env python3
"""Opt-in native regression for candidate certificate preprocessing.

Run with AFP_TEST_CODE_CONTEXT=1. The ordinary HOL simpset rejects an integer
numeral pattern; the production scanner must accept the same registered code
equation with the code preprocessor simpset. Preserve the complete old exception
and new candidate XML. No target program is generated, compiled or run.
"""
import os
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

import afp_common as common
import full
import scan


@unittest.skipUnless(os.environ.get("AFP_TEST_CODE_CONTEXT") == "1",
                     "opt-in native code-certificate context regression")
class CodeContextIntegration(unittest.TestCase):
    def test_registered_numeral_pattern_uses_code_preprocessing_rules(self):
        # A small checked theory isolates the distinction between logical simp
        # rules and code-equation normalization. A separate output directory
        # retains both witnesses across repeated invocations.
        base = common.HERE / "full"
        work = full.next_attempt(base / "tooling/code-context-fixture")
        args = common.arguments(__doc__).parse_args([
            "--timeout", "0", "--max-heap-mb", "1000", "--java-heap-mb", "256",
            "--min-available-mb", "512"])
        env, metadata = common.environment(args)
        theory = "AFP-Scan-Fixture.Code_Context"
        name = "Code_Context.integer_one"
        (work / "theories.txt").write_text(theory + "\n")
        legacy = work / "legacy.ML"
        legacy.write_text(r"""
local
  val thy = Thy_Info.get_theory "AFP-Scan-Fixture.Code_Context";
  val ctxt = Proof_Context.init_global thy;
  val result = Exn.capture (fn () =>
    Code.get_cert ctxt [] "Code_Context.integer_one"
      |> Code.conclude_cert |> Code.equations_of_cert thy) ();
  val message = (case result of
      Exn.Res _ => error "Expected ordinary HOL normalization to reject the numeral pattern"
    | Exn.Exn exn => if Exn.is_interrupt exn then Exn.reraise exn
                     else Runtime.exn_message exn);
in
  val _ = File.write (Path.explode (getenv_strict "AFP_CONTEXT_LEGACY"))
    (XML.string_of (XML.Elem (("legacy", []), [XML.Text message])));
end;
""")
        actual = dict(env, AFP_SCAN_THEORIES=str(work / "theories.txt"),
                      AFP_SCAN_OUTPUT=str(work / "scan.xml"),
                      AFP_CONTEXT_LEGACY=str(work / "legacy.xml"))
        execute = scan.command

        def with_fixture(argv, log, settings, inherited):
            # Add only the independent fixture and a preceding legacy
            # observation. The candidate collector remains production scan.ML.
            argv = list(argv)
            first_theory = argv.index("-T")
            argv[first_theory:first_theory] = [
                "-d", str(common.HERE / "fixtures"), "-T", theory]
            first_expression = argv.index("-e")
            expression = (
                'Context.setmp_generic_context (SOME (Context.Theory '
                '(Thy_Info.get_theory "' + theory + '"))) '
                '(ML_Context.eval_file ML_Compiler.flags) (Path.explode '
                + common.quote(str(legacy)) + ')')
            argv[first_expression:first_expression] = ["-e", expression]
            return execute(argv, log, settings, inherited)

        with common.build_lock(), patch.object(scan, "command", side_effect=with_fixture):
            check = scan.inspect_session("HOL", args, actual, work / "process.log")
        self.assertEqual(check["status"], "passed",
                         (work / "process.log").read_text())
        old = ET.parse(work / "legacy.xml").getroot().text or ""
        self.assertIn("not a constructor", old)
        self.assertIn("one_integer", old)
        document = ET.parse(work / "scan.xml").getroot()
        self.assertEqual(document.attrib["certificate_context"], scan.CERTIFICATE_CONTEXT)
        constants = [n.attrib["name"] for n in document.findall(".//constant")]
        self.assertIn(name, constants)
        self.assertFalse(document.findall(".//error"))
        common.write_json(base / "code-context-validation.json",
            {"status": "passed", "checked": common.timestamp(),
             "directory": common.relative(work), "environment": metadata,
             "command": check, "constant": name,
             "certificate_context": scan.CERTIFICATE_CONTEXT,
             "legacy_error_evidence": common.relative(work / "legacy.xml"),
             "candidate_evidence": common.relative(work / "scan.xml"),
             "checks": ["ordinary HOL normalization rejects the integer numeral pattern",
                        "production scanner accepts the registered equation with code rules",
                        "original candidate and full diagnostic retained",
                        "no target program generated, compiled or run"]})


if __name__ == "__main__":
    unittest.main()
