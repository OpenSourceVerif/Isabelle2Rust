"""Opt-in server acceptance; retain evidence only under AFP_RECOVERY_WORK."""
import _paths
import os
from pathlib import Path
import unittest
from unittest.mock import patch

import afp_common as common
import afp
import dependency_plan as dp
import fixed_plan as fp
import fixed_export as fe
from scan_store import digest
from state import State


@unittest.skipUnless(os.environ.get("AFP_RECOVERY_TEST") == "1", "opt-in server native recovery acceptance")
class RecoveryNativeTests(unittest.TestCase):
    def test_pruning_and_unknown_fallback_use_original_native_equations(self):
        root = Path(os.environ["AFP_RECOVERY_WORK"]).resolve()
        self.assertFalse(root.exists(), "native acceptance requires a fresh evidence root")
        root.mkdir(parents=True)
        options = common.arguments(__doc__).parse_args(afp.runtime_arguments(common.CONFIG))
        env, _ = common.environment(options)
        native = common.command
        calls = []
        def with_fixture(argv, log, args, inherited):
            argv = list(argv)
            argv[2:2] = ["-d", str(common.EXPERIMENT / "tests/fixtures/recovery")]
            index = argv.index("-e")
            argv[index:index] = ["-T", "AFP-Recovery-Fixture.Recovery_Prune"]
            calls.append(argv)
            return native(argv, log, args, inherited)
        def expected(names):
            owner = "AFP-Recovery-Fixture.Recovery_Prune"
            return {"sessions": ["HOL"], "theories": [owner], "entry_theories": [owner],
                    "required": {"HOL": [owner]},
                    "declarations": sorted([{"name": "Recovery_Prune." + n, "owner": owner,
                        "source": "Recovery_Prune.thy"} for n in names], key=dp.declaration_id)}
        summary = {}
        with patch.object(common, "command", side_effect=with_fixture):
            for mode, names in (("pruning", ["healthy", "bad_sort"]),
                                ("fallback", ["healthy", "unknown"])):
                base = root / mode
                State(base)
                inputs = expected(names)
                plan, seal = fp.build_entry(base, "Fixture", inputs, options, env)
                State(base).put("plan/Fixture", plan)
                replay, second_seal = fp.build_entry(base, "Fixture", inputs, replay=True)
                self.assertEqual(plan, replay)
                self.assertEqual(seal, second_seal)
                rows = {d["name"]: d for c in plan["contexts"] for d in c["classifications"]}
                if mode == "pruning":
                    self.assertEqual(rows["Recovery_Prune.bad_sort"]["status"], "frontend_rejected", rows)
                    self.assertEqual(rows["Recovery_Prune.healthy"]["status"], "retained")
                else:
                    self.assertEqual({d["status"] for d in rows.values()}, {"singleton_fallback"}, rows)
                record = {"scan": {}}
                stage = fe.execute(base, plan, record, {}, options, env)
                healthy = next(d for d in stage["declarations"].values()
                               if d["declaration"]["name"] == "Recovery_Prune.healthy")
                self.assertEqual({v["status"] for v in healthy["targets"].values()}, {"passed"}, healthy)
                if mode == "pruning":
                    fe.validate_stage(base, plan, stage)
                    count = len(calls)
                    fe.execute(base, plan, record, {}, options, env)
                    self.assertEqual(len(calls), count)
                else:
                    self.assertEqual(stage["status"], "blocked")
                    with self.assertRaises(ValueError):
                        fe.validate_stage(base, plan, stage)
                    self.assertTrue(all(g.get("coverage") is None for c in plan["contexts"] for g in c["groups"]))
                summary[mode] = {"plan": dp.statistics(plan), **fe.disposition_summary(plan, stage)}
        State(root).put("acceptance", dict(summary, native_commands=len(calls)))
        print("Native recovery acceptance: " + str(root), flush=True)


if __name__ == "__main__":
    unittest.main()
