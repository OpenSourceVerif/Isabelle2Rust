import _paths
import tempfile
import unittest
from pathlib import Path
import xml.etree.ElementTree as ET
from unittest.mock import patch

import afp
import afp_common as common
import dependency_plan as dp
import rust_replay as replay


class RustReplayTests(unittest.TestCase):
    def test_rust_replay_keeps_frozen_roots_and_theory_branch(self):
        request = ET.Element("request", mode="export", context="branch", group="group", module="AFP_Code")
        for name in ("Entry.Branch", replay.OLD_PROFILE, dp.SETUPS[1]):
            ET.SubElement(request, "parent", name=name)
        for name in ("Theory.left", "Theory.right"):
            ET.SubElement(request, "entry", name=name)
        for name in dp.TARGETS:
            ET.SubElement(request, "target", name=name)
        exported = replay.rust_request(ET.tostring(request))
        self.assertEqual(exported.get("mode"), "rust-replay")
        self.assertEqual([exported.get(key) for key in ("context", "group", "module")],
                         ["branch", "group", "AFP_Code"])
        self.assertEqual([n.get("name") for n in exported.findall("parent")],
                         ["Entry.Branch", "Rust.Rust_Source_BigInt_Setup", "Go.Go_Setup"])
        self.assertEqual([n.get("name") for n in exported.findall("entry")], ["Theory.left", "Theory.right"])
        self.assertEqual([n.get("name") for n in exported.findall("target")], ["Rust"])
        with self.assertRaisesRegex(ValueError, "frozen six-target request"):
            replay.rust_request(ET.tostring(exported))

    def test_context_batches_never_share_distinct_theory_branches(self):
        jobs = [replay.Request("E", str(i), context, session, Path("request.xml"), "seal", False)
                for i, (session, context) in enumerate([("S", "left"), ("S", "right"),
                                                       ("S", "left"), ("U", "left")])]
        batches = list(replay.batches(jobs, 2))
        self.assertEqual([[job.group for job in batch] for batch in batches], [["0", "2"], ["1"], ["3"]])

    def test_cli_routes_rust_only_replay_to_an_independent_work_directory(self):
        with tempfile.TemporaryDirectory() as temporary, patch.object(afp, "call", return_value=0) as call:
            output = Path(temporary) / "new"
            original = Path(temporary) / "old"
            self.assertEqual(afp.main(["--work", str(output), "rust-replay", "--from-work", str(original),
                                       "--entries", "Buildings"]), 0)
            script, arguments, _ = call.call_args.args
            self.assertEqual(script, common.HERE / "rust_replay.py")
            self.assertIn(str(output), arguments)
            self.assertIn(str(original), arguments)
            self.assertEqual(arguments[-2:], ["--entries", "Buildings"])

    def test_compile_timeout_uses_real_command_status(self):
        item = {"stage1_compile": {"status": "failed", "checks": [{"status": "timeout"}]}}
        self.assertEqual(replay.phase_status(item, "stage1_compile"), "timeout")
        item["stage1_compile"]["checks"] = [{"status": "memory_limit"}]
        self.assertEqual(replay.phase_status(item, "stage1_compile"), "failed")

    def test_resume_adopts_only_complete_matching_slot_receipts(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            state = replay.State(base)
            worker = replay.State(base / "workers/1")
            inputs = {"Cargo.toml": "one", "src/lib.rs": "two"}
            key = "compile/" + replay.digest(inputs)
            completed = {"manifest": "Cargo.toml", "item": {
                "complete": True, "command_evidence": {"stage1.log": {"sha256": "seal"}},
                "stage1_inputs": inputs,
            }}
            worker.update({key: completed, "compile/foreign": completed,
                           "compile/incomplete": {"item": {"complete": False}}})
            replay.recover_compile_results(base, state)
            self.assertEqual(state.get(key), completed)
            self.assertEqual(state.keys("compile/"), [key])
