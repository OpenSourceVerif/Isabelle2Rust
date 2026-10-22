#!/usr/bin/env python3
"""Opt-in checked native witness for frozen declaration/context coverage.

Run AFP_TEST_FROZEN_SCAN=1. This invokes the production collector in real theory
contexts including conflicting instance branches, never any target program.
"""
import os
from pathlib import Path
import unittest
from unittest.mock import patch

import afp_common as common
import scan
import scan_frozen as frozen
import scan_store as ss


@unittest.skipUnless(os.environ.get("AFP_TEST_FROZEN_SCAN") == "1",
                     "opt-in frozen native catalogue regression")
class CatalogueNative(unittest.TestCase):
    def test_all_owned_declarations_and_independent_contexts_are_retained(self):
        # A certificate-based scanner excludes target_only, token.Token,
        # abort_only and no_equation. Namespace discovery must retain all four,
        # alongside hidden, locale and abstract-code declarations. The independent
        # class-instance branches contain conflicting instances and cannot
        # be merged; their separate contexts must still be represented.
        base = common.HERE / "full/tooling/frozen-catalogue-fixture"
        n = 1
        while (base / f"attempt-{n:04d}").exists():
            n += 1
        work = base / f"attempt-{n:04d}"
        work.mkdir(parents=True)
        args = common.arguments(__doc__).parse_args([
            "--timeout", "0", "--max-heap-mb", "1000", "--java-heap-mb", "256",
            "--stack-space-mb", "128", "--min-available-mb", "512"])
        env, metadata = common.environment(args)
        names = ["AFP-Catalogue-Fixture.Catalogue_Coverage"] + [
            "AFP-Scan-Fixture." + n for n in ("Origin", "Later", "Branch_Base", "Branch_Left", "Branch_Right")]
        info = {"sessions": ["HOL"], "session_requirements": {"HOL": []},
                "theories": [{"name": name, "path": name + ".thy", "session": "HOL"}
                             for name in names]}
        unit = ss.unit_input("Fixture", "HOL", info, {"fixture": "native"})
        (work / "theories.txt").write_text("\n".join(names) + "\n")
        actual = dict(env, AFP_SCAN_POLICY=ss.POLICY, AFP_SCAN_UNIT=ss.digest(unit),
                      AFP_SCAN_THEORIES=str(work / "theories.txt"),
                      AFP_SCAN_OUTPUT=str(work / "catalogue.xml"))
        execute = scan.command
        def load_fixtures(argv, log, settings, inherited):
            argv = list(argv)
            first = argv.index("-T")
            argv[first:first] = [word for name in names for word in ("-T", name)]
            return execute(argv, log, settings, inherited)
        with common.build_lock(), patch.object(scan, "command", side_effect=load_fixtures):
            checked = scan.inspect_session("HOL", args, actual, work / "process.log",
                directories=[common.HERE / "fixtures", common.HERE / "fixtures/catalogue"])
        self.assertEqual(checked["status"], "passed", (work / "process.log").read_text())
        catalogue = ss.parse_catalogue(work / "catalogue.xml", unit)
        constants = set(common.candidates(catalogue["scope"]))
        for name in ("target_only", "target_wrapper", "abort_only", "ordinary",
                     "wrapped_empty", "no_equation", "hidden"):
            self.assertIn("Catalogue_Coverage." + name, constants)
        self.assertIn("Catalogue_Coverage.wrapped.unwrap", constants)
        self.assertTrue(any(name.endswith(".Token") for name in constants))
        self.assertTrue(any("local_plus" in name for name in constants))
        self.assertIn("Origin.no_equation", constants)
        self.assertIn("Origin.late_equation", constants)
        self.assertFalse(any("not_a_constant" in name for name in constants))
        self.assertTrue(any("not_a_constant" in name
                            for names in catalogue["abbreviations"].values() for name in names))
        self.assertIn("AFP-Scan-Fixture.Branch_Left", catalogue["contexts"])
        self.assertIn("AFP-Scan-Fixture.Branch_Right", catalogue["contexts"])
        common.write_json(work / "validation.json", {
            "status": "passed", "environment": metadata, "command": checked,
            "unit": unit, "candidate_count": len(constants), "catalogue": catalogue,
            "policy": ss.POLICY, "method": ss.METHOD, "tools": frozen.tools_identity()})
        print("Native catalogue evidence: " + str(work), flush=True)

    def test_real_session_receipt_resumes_without_a_second_native_command(self):
        # Exercise the complete build -> inspection -> durable receipt chain.
        # The second invocation only validates retained evidence and must not
        # call either original build or inspection again.
        root = common.HERE / "full/tooling/frozen-session-fixture"
        number = 1
        while (root / f"attempt-{number:04d}").exists():
            number += 1
        base = root / f"attempt-{number:04d}"
        base.mkdir(parents=True)
        args = common.arguments(__doc__).parse_args([
            "--timeout", "0", "--max-heap-mb", "1000", "--java-heap-mb", "256",
            "--stack-space-mb", "128", "--min-available-mb", "512"])
        env, metadata = common.environment(args)
        session = "AFP-Catalogue-Fixture"
        info = {"sessions": [session], "session_requirements": {session: []},
                "theories": [{"name": session + ".Catalogue_Coverage",
                              "path": "Catalogue_Coverage.thy", "session": session}]}
        unit = ss.unit_input("Fixture", session, info, {"fixture": "checked-native"})
        store = ss.Store(base)
        native = common.command
        commands = []
        def with_directory(argv, log, settings, actual):
            argv = list(argv)
            if argv[1] in {"build", "process"}:
                argv[2:2] = ["-d", str(common.HERE / "fixtures/catalogue")]
            commands.append(argv)
            return native(argv, log, settings, actual)
        with patch.object(common, "command", side_effect=with_directory), \
                patch.object(scan, "command", side_effect=with_directory):
            receipt = frozen.run_unit(store, unit, args, env, {"environment": metadata},
                                      frozen.tools_identity(), common.HERE)
        self.assertEqual(receipt["status"], "complete", receipt)
        self.assertEqual(len(commands), 2)
        with patch.object(common, "command", side_effect=AssertionError("must reuse")), \
                patch.object(scan, "command", side_effect=AssertionError("must reuse")):
            restored = ss.Store(base).recover(unit)
        self.assertEqual(ss.digest(restored), ss.digest(receipt))
        self.assertEqual(len(store.attempts(unit)), 1)
        common.write_json(base / "validation.json", {
            "status": "passed", "unit_id": ss.digest(unit), "native_commands": len(commands),
            "resume_native_commands": 0, "candidate_count": len(common.candidates(receipt["catalogue"]["scope"]))})


if __name__ == "__main__":
    unittest.main()
