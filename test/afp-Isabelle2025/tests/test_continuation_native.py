"""Opt-in native singleton continuation through both Rust compilation stages."""
import _paths
import os
from pathlib import Path
import unittest
from unittest.mock import patch

import afp
import afp_common as common
import continuation as cont
import dependency_plan as dp
import fixed_pipeline
import fixed_plan as fp
import full
from result_store import EntryStore
from scan_store import digest
from state import State


@unittest.skipUnless(os.environ.get("AFP_CONTINUATION_TEST") == "1", "opt-in native continuation acceptance")
class ContinuationNativeTests(unittest.TestCase):
    def test_deferred_singletons_export_and_compile_with_an_unresolved_peer(self):
        base = Path(os.environ["AFP_CONTINUATION_WORK"]).resolve()
        self.assertFalse(base.exists(), "requires a fresh native evidence root")
        state = State(base)
        options = common.arguments(__doc__).parse_args(afp.runtime_arguments(common.CONFIG))
        options.cargo = "cargo +1.94.0"
        options.export_workers, options.compile_workers = 2, 1
        env, _ = common.environment(options)
        env["CARGO"] = options.cargo
        env["RUSTFLAGS"] = "-Awarnings"
        owner = "AFP-Recovery-Fixture.Recovery_Prune"
        expected = {"sessions": ["HOL"], "theories": [owner], "entry_theories": [owner],
                    "required": {"HOL": [owner]},
                    "declarations": sorted([{"name": "Recovery_Prune." + n, "owner": owner,
                        "source": "Recovery_Prune.thy"} for n in ("healthy", "bad_sort", "unknown")],
                        key=dp.declaration_id)}
        native = common.command
        def with_fixture(argv, log, args, inherited):
            argv = list(argv)
            if argv[:2] == [options.isabelle, "process"]:
                argv[2:2] = ["-d", str(common.EXPERIMENT / "tests/fixtures/recovery")]
                index = argv.index("-e")
                argv[index:index] = ["-T", owner]
            return native(argv, log, args, inherited)
        with patch.object(common, "command", side_effect=with_fixture):
            fp.obtain(base, fp.selection_key("Fixture", "HOL"), expected, "HOL", options, env,
                lambda work: fp.write_request(work, "select", declarations=expected["declarations"],
                                               theories=expected["theories"]),
                "selection.xml", lambda path: fp.parse_selection(path, "Fixture", "HOL", expected, partial=True))
            origin = {"tools": {}, "parent_run": "native-acceptance"}
            policy = {"schema": 1, "parent": "native-selection-only", "cutoff": common.timestamp(),
                      "deferred_entries": ["Fixture"], "reason": "Native acceptance of explicit deferral",
                      "allow_partial_compile": True, "origin": digest(origin)}
            state.update({"run": {"experiment": "fixed-plan-v2", "continuation": digest(policy)},
                          "continuation-origin": origin, "continuation-policy": policy})
            plan, seal = fp.build_entry(base, "Fixture", expected, replay=True, defer_missing=True)
            self.assertEqual((plan, seal), fp.build_entry(base, "Fixture", expected, replay=True))
            state.put("plan/Fixture", plan)
            self.assertEqual(dp.statistics(plan)["singleton_fallback"], 3)
            target = base / "_build/optimizer-target"
            build = common.command(["cargo", "+1.94.0", "build", "--locked", "--offline",
                "--manifest-path", str(common.PROJECT / "optimize/Cargo.toml"), "--bin", "cargo-opt",
                "--target-dir", str(target)], base / "optimizer.log", options, env)
            self.assertEqual(build["status"], "passed", build)
            scans, scopes = {"Fixture": {"scan": {}}}, {"Fixture": {}}
            result = {"entries": EntryStore(base, scans, scopes)}
            # This tiny fixture has no AFP manifest; request admission and all
            # native evidence checks still run without mocks.
            with patch.object(fp, "require_gate"):
                counts = fixed_pipeline.execute(base, {"order": ["Fixture"]}, result, scopes,
                    options, env, target / "debug/cargo-opt")
            record = EntryStore(base, scans, scopes)["Fixture"]
            self.assertEqual(counts["export_attempted"], 3)
            self.assertEqual(counts["export_closed"], 2)
            self.assertEqual(counts["export_unresolved"], 1)
            self.assertEqual(counts["compiled_crates"], 1)
            item = next(iter(record["full_compile"].values()))
            for phase in ("stage1_compile", "optimization", "stage2_compile"):
                self.assertEqual(item[phase]["status"], "passed", (phase, item[phase]))
            self.assertEqual(record["full_export"]["status"], "blocked")
            state.put("acceptance", dict(counts, stage1="passed", optimization="passed", stage2="passed",
                                         global_export_closed=False))
        print("Native continuation acceptance:", base, flush=True)


if __name__ == "__main__":
    unittest.main()
