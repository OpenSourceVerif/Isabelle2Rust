"""Opt-in native acceptance of scanned branches, six targets and Rust compilation."""
import _paths
import os
from pathlib import Path
import unittest
from unittest.mock import patch

import afp
import afp_common as common
import dependency_plan as dp
import entry_audit as checks
import entry_pipeline as pipeline
import scan
from scan_store import Store, unit_input
from state import State


@unittest.skipUnless(os.environ.get("AFP_ENTRY_TEST") == "1", "opt-in native entry pipeline acceptance")
class EntryPipelineNativeTests(unittest.TestCase):
    def test_scanned_branches_keep_both_native_outcomes_and_compile(self):
        base = Path(os.environ["AFP_ENTRY_WORK"]).resolve()
        self.assertFalse(base.exists())
        options = common.arguments(__doc__).parse_args(afp.runtime_arguments(common.CONFIG))
        options.cargo = "cargo +1.94.0"
        options.plan_workers, options.export_workers, options.compile_workers = 2, 2, 2
        env, metadata = common.environment(options)
        env.update(CARGO=options.cargo, RUSTFLAGS="-Awarnings")
        entry, session = "Fixture", "AFP-Entry-Fixture"
        theories = [{"name": session + "." + name, "path": name + ".thy", "session": session}
                    for name in ("Entry_Base", "Entry_Left", "Entry_Right")]
        info = {"sessions": [session], "theories": theories, "session_requirements": {session: ["HOL", "Rust", "Go"]}}
        data = {"order": [entry], "entries": {entry: info}}
        units = {session: unit_input(entry, session, info, {"fixture": "native"})}
        state = State(base)
        state.put("run", {"experiment": dp.ENTRY_PIPELINE, "manifest": data, "environment": metadata})
        native = common.command
        fixture_dir = common.EXPERIMENT / "tests/fixtures/entry_pipeline"

        def with_fixture(argv, log, settings, actual):
            if argv[1] in {"build", "process"}:
                directories = ["-d", str(fixture_dir)]
                if str(common.PROJECT) not in argv:
                    directories += ["-d", str(common.PROJECT)]
                argv = [*argv[:2], *directories, *argv[2:]]
            return native(argv, log, settings, actual)

        with common.experiment_lock(), patch.object(common, "command", side_effect=with_fixture), \
                patch.object(scan, "command", side_effect=with_fixture):
            errors = pipeline.execute(base, data, units, metadata, [entry], "run", options, env)
        self.assertEqual(errors, [])
        gate, result, _, totals = checks.reconcile(Store(base), data, units, metadata, [entry], "all",
                                                    pipeline.optimizer_path(base))
        self.assertTrue(gate["passed"], gate["problems"])
        record = result["entries"][entry]
        stage = record["full_export"]
        contexts = {c["context"]["id"]: c["context"]["scan_theory"] for c in stage["plan"]["contexts"]}
        probe = {contexts[v["declaration"]["context"]].rsplit(".", 1)[-1]: v["targets"]
                 for v in stage["declarations"].values() if v["declaration"]["name"] == "Entry_Base.probe"}
        self.assertEqual(set(probe), {"Entry_Left", "Entry_Right"})
        self.assertEqual({v["status"] for v in probe["Entry_Left"].values()}, {"frontend_rejected"})
        self.assertEqual(set(probe["Entry_Right"]), set(dp.TARGETS))
        self.assertEqual({v["status"] for v in probe["Entry_Right"].values()}, {"passed"})
        self.assertGreater(totals["rust_crates"], 0)
        for item in record["full_compile"].values():
            for phase in ("stage1_compile", "optimization", "stage2_compile"):
                self.assertEqual(item[phase]["status"], "passed", item[phase])
        self.assertEqual(pipeline.finalize(base, data, units, metadata), 0)
        state.put("acceptance", {"left": "frontend_rejected", "right": "passed",
                                 "targets": list(dp.TARGETS), **totals})
        print("Native entry pipeline acceptance:", base, flush=True)
