#!/usr/bin/env python3
"""Native regression for the common explicit export-module configuration."""

import _paths  # Locate AFP tools independently of cwd and unittest discovery.
import os
from pathlib import Path
import unittest

import afp_common as common
import full


@unittest.skipUnless(os.environ.get("AFP_NATIVE_MODULE_TEST") == "1",
                     "requires the checked AVL-Trees heap")
class ExportModuleTests(unittest.TestCase):
    def test_executable_avl_predicate_exports_in_all_six_targets(self):
        # AVL.avl depends on numeric code adaptations. Default source-based
        # module splitting creates a Go dependency cycle; a common explicit
        # module preserves the executable dependency graph for every target.
        # This checks native serialization only and never runs target code.
        parser = common.arguments("Export module regression")
        args = parser.parse_args([
            "--compiler-settings", str(common.EXPERIMENT / "setup/compiler-settings.local.json"),
            "--timeout", "0", "--max-heap-mb", "2000"])
        env, _ = common.environment(args)
        base = common.WORK / "regression/tooling/module-configuration-regression"
        work = full.next_attempt(base)
        (work / "scope.txt").write_text("AVL.avl\n")
        (work / "theories.txt").write_text("AVL-Trees.AVL\nAVL-Trees.AVL2\n")
        check = full.export_command("AVL-Trees", work, args, env)
        self.assertEqual(check["status"], "passed", check)
        self.assertTrue((work / "finished.xml").is_file())
        attempts = full.collect_attempts(work)
        outcomes = full.resolve_candidates(["AVL.avl"], [{"attempts": attempts}])
        self.assertEqual({t: outcomes["AVL.avl"][t]["status"] for t in full.TARGETS},
                         {t: "passed" for t in full.TARGETS})
        common.write_json(work / "validation.json", {"command": check, "outcomes": outcomes})


if __name__ == "__main__":
    unittest.main()
