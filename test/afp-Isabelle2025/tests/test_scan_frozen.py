#!/usr/bin/env python3
"""Independent regressions for candidate preservation and transactional resume.

Fixtures exercise real parsing/receipt/queue code. SIGKILL tests use an actual
subprocess at each publication boundary, never a simulated successful restart.
"""

import _paths  # Locate AFP tools independently of cwd and unittest discovery.
from contextlib import nullcontext
import copy
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

import afp_common as common
import full
import scan
import scan_frozen as frozen
import scan_store as ss


def fixture_unit(session="E"):
    info = {"sessions": [session], "session_requirements": {session: []},
            "theories": [{"name": "E.A", "path": "A.thy", "session": session, "conditions": []}],
            "dependencies": [], "source_errors": []}
    return ss.unit_input("E", session, info, {"source": "fixed"})


def fixture_xml(unit, constants=("A.f",), *, owner="E.A"):
    root = ET.Element("scan", schema="2", policy=ss.POLICY, method=ss.METHOD, unit=ss.digest(unit))
    ET.SubElement(root, "requested", name="E.A")
    ET.SubElement(root, "loaded", name="E.A")
    context = ET.SubElement(root, "context", name="E.A")
    ET.SubElement(context, "covers", theory="E.A")
    theory = ET.SubElement(root, "theory", name="E.A", context="E.A", declared=str(len(constants)))
    for c in constants:
        ET.SubElement(theory, "constant", name=c, owner=owner)
    return ET.tostring(root, encoding="unicode")


def completed_fixture(base, unit, constants=("A.f",)):
    store = ss.Store(base)
    attempt = store.next_attempt(unit)
    run = {"unit_id": ss.digest(unit), "tool_generation": "fixture-method", "runtime": {"proofs": "checked"}}
    common.write_record(attempt / "attempt.json", run)
    (attempt / "theories.txt").write_text("E.A\n")
    (attempt / "catalogue.xml").write_text(fixture_xml(unit, constants))
    checks = []
    for name in ("load", "scan"):
        log = attempt / (name + ".log")
        log.write_text("Independent fixture command completed.\n")
        check = {"status": "passed", "returncode": 0, "log": common.relative(log)}
        common.write_record(log.with_suffix(".log.json"), check)
        checks.append(check)
    return store, attempt, ss.completed_receipt(store, attempt, unit, run, *checks)


class FrozenTests(unittest.TestCase):
    def test_xml_contract_rejects_wrong_scope_schema_owner_and_missing_context(self):
        # A syntactically valid document must not become a completion fact
        # when it belongs to another input, policy, owner or incomplete context.
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "candidate.xml"
            unit = fixture_unit()
            good = fixture_xml(unit)
            cases = [good.replace('schema="2"', 'schema="1"'),
                     good.replace('policy="owned-constants-v1"', 'policy="old"'),
                     good.replace('owner="E.A"', 'owner="Foreign.A"'),
                     good.replace(ss.digest(unit), "wrong"),
                     good.replace('<covers theory="E.A" />', ""),
                     good.replace('declared="1"', 'declared="2"')]
            for xml in cases:
                path.write_text(xml)
                with self.subTest(xml=xml), self.assertRaises(ValueError):
                    ss.parse_catalogue(path, unit)
            path.write_text(good)
            self.assertEqual(ss.parse_catalogue(path, unit)["scope"], {"A.thy": ["A.f"]})

    def test_failed_inspection_cannot_be_committed_complete(self):
        # Coverage rows cannot turn a killed inspection into a successful unit.
        with tempfile.TemporaryDirectory() as temporary, patch.object(common, "PROJECT", Path(temporary)):
            store, attempt, receipt = completed_fixture(Path(temporary) / "run", fixture_unit())
            receipt["inspect"]["status"] = "failed"
            receipt["inspect"]["returncode"] = -9
            with self.assertRaises(ValueError):
                store.commit(attempt, receipt)
            self.assertIsNone(store.state.get("receipt/" + ss.digest(fixture_unit())))

    def test_complete_receipt_is_reused_and_cannot_be_reopened(self):
        # Resume invokes no Isabelle command for a completed unit. Repaired
        # diagnostics and resource values do not grant replacement permission.
        with tempfile.TemporaryDirectory() as temporary, patch.object(common, "PROJECT", Path(temporary)):
            unit = fixture_unit()
            store, attempt, receipt = completed_fixture(Path(temporary) / "run", unit)
            store.commit(attempt, receipt)
            with patch.object(frozen, "run_unit", side_effect=AssertionError("must not execute")):
                resumed = ss.Store(store.base).recover(unit)
            self.assertEqual(resumed["catalogue"]["scope"], {"A.thy": ["A.f"]})
            altered = copy.deepcopy(receipt)
            altered["runtime"] = {"heap": 8000}
            with self.assertRaises(ValueError):
                store.commit(store.next_attempt(unit), altered)

    def test_successful_xml_recovers_without_publishing_old_summary_pair(self):
        # The driver can die after the successful scan sidecar but before its
        # session receipt. Recovery validates and commits the existing XML.
        with tempfile.TemporaryDirectory() as temporary, patch.object(common, "PROJECT", Path(temporary)):
            unit = fixture_unit()
            store, attempt, receipt = completed_fixture(Path(temporary) / "run", unit)
            (store.base / "exports.json").write_text('{"stale": true}')
            recovered = ss.Store(store.base).recover(unit)
            self.assertEqual(recovered["catalogue"], receipt["catalogue"])
            self.assertIsNotNone(store.state.get("receipt/" + ss.digest(unit)))
            self.assertEqual(len(store.attempts(unit)), 1)

    def test_evidence_tampering_blocks_recovery_instead_of_rescanning(self):
        # A missing original log is an unresolved integrity failure, never a
        # cache miss that silently schedules completed sessions again.
        with tempfile.TemporaryDirectory() as temporary, patch.object(common, "PROJECT", Path(temporary)):
            unit = fixture_unit()
            store, attempt, receipt = completed_fixture(Path(temporary) / "run", unit)
            store.commit(attempt, receipt)
            (attempt / "scan.log").write_text("changed")
            with self.assertRaises(ValueError):
                ss.Store(store.base).recover(unit)

    def test_sigkill_before_after_transaction_and_retirement_recovers_same_candidates(self):
        # Kill a real writer before the receipt, after the receipt, and after
        # retirement starts. Every boundary recovers one identical candidate.
        for boundary in ("receipt-before", "receipt-after", "retirement-before"):
            with self.subTest(boundary=boundary), tempfile.TemporaryDirectory() as temporary, \
                    patch.object(common, "PROJECT", Path(temporary)):
                unit = fixture_unit()
                store, attempt, receipt = completed_fixture(Path(temporary) / "run", unit)
                payload = Path(temporary) / "payload.json"
                common.write_record(payload, {"unit": unit, "receipt": receipt,
                                           "base": str(store.base), "attempt": str(attempt)})
                script = """
import json, os, signal, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import afp_common as c
import scan_store as s
c.PROJECT = Path(sys.argv[2])
p = json.loads(Path(sys.argv[3]).read_text())
boundary = sys.argv[4]
original = s.State.update
def update(self, values, remove=()):
    receipt = any(key.startswith('receipt/') for key in values)
    if receipt and boundary == 'receipt-before':
        os.kill(os.getpid(), signal.SIGKILL)
    original(self, values, remove)
    if receipt and boundary == 'receipt-after':
        os.kill(os.getpid(), signal.SIGKILL)
s.State.update = update
prune = s.Store.prune
def retire(self, unit, attempt):
    if boundary == 'retirement-before':
        os.kill(os.getpid(), signal.SIGKILL)
    prune(self, unit, attempt)
s.Store.prune = retire
s.Store(Path(p['base'])).commit(Path(p['attempt']), p['receipt'])
"""
                run = subprocess.run([sys.executable, "-B", "-c", script,
                                      str(common.HERE), temporary, str(payload), boundary])
                self.assertEqual(run.returncode, -signal.SIGKILL)
                recovered = ss.Store(store.base).recover(unit)
                self.assertEqual(recovered["catalogue"]["scope"], {"A.thy": ["A.f"]})
                self.assertEqual(len(store.attempts(unit)), 1)

    def test_multi_record_publication_rolls_back_as_one_transaction(self):
        # A failed publication must not mix generations of result and checkpoint.
        with tempfile.TemporaryDirectory() as temporary:
            store = ss.Store(temporary)
            store.state.update({"result": {"version": 1}, "gate": {"version": 1}})
            with self.assertRaises(RuntimeError):
                with store.state.connect() as db:
                    db.execute("UPDATE records SET value=? WHERE key=?", ('{"version":2}', "result"))
                    raise RuntimeError("injected interruption")
            self.assertEqual(store.state.get("result"), {"version": 1})
            self.assertEqual(store.state.get("gate"), {"version": 1})


    def test_partial_legacy_retry_preserves_later_session_candidates(self):
        # Earlier success followed by later failure is the deletion counterexample.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            args = SimpleNamespace(isabelle="isabelle", afp=root, timeout=0, skip_proofs=False)
            info = {"sessions": ["E", "Later"], "theories": [
                {"name": "E.A", "path": "A.thy", "session": "E"}]}
            exports = {"E": {"A.thy": ["A.f", "A.late"]}}
            def execute(argv, log, args, env):
                if argv[-1] == "Later":
                    return {"status": "failed"}
                if argv[1] == "process":
                    Path(env["AFP_SCAN_OUTPUT"]).write_text(
                        '<scan><theory name="E.A"><constant name="A.f"/></theory></scan>')
                return {"status": "passed"}
            with patch.object(scan, "HERE", root), patch.object(common, "PROJECT", root), \
                    patch.object(scan, "build_lock", nullcontext), patch.object(scan, "command", side_effect=execute):
                receipt = scan.scan_entry("E", info, args, {}, exports)
            self.assertEqual(receipt["status"], "failed")
            self.assertEqual(exports["E"]["A.thy"], ["A.f", "A.late"])

    def test_failed_second_inspection_cannot_pass_by_theory_path_count(self):
        # Both builds pass and the early inspection lists every theory. A later
        # failed inspection is still missing a required context.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            info = {"sessions": ["E", "Later"], "theories": [
                {"name": "E.A", "path": "A.thy", "session": "E"}]}
            args = SimpleNamespace(isabelle="isabelle", afp=root, timeout=0, skip_proofs=False)
            def execute(argv, log, args, env):
                if argv[1] == "process":
                    if argv[argv.index("-l") + 1] == "Later":
                        return {"status": "failed"}
                    Path(env["AFP_SCAN_OUTPUT"]).write_text('<scan><theory name="E.A"/></scan>')
                return {"status": "passed"}
            with patch.object(scan, "HERE", root), patch.object(common, "PROJECT", root), \
                    patch.object(scan, "build_lock", nullcontext), patch.object(scan, "command", side_effect=execute):
                self.assertEqual(scan.scan_entry("E", info, args, {}, {})["status"], "failed")

    def test_manifest_key_changes_when_root_changes_but_roots_does_not(self):
        # A consistent prior manifest cannot survive changing a session ROOT.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "thys/E").mkdir(parents=True)
            (root / "thys/ROOTS").write_text("E\n")
            (root / "thys/E/ROOT").write_text("session Before = HOL +\n")
            args = SimpleNamespace(afp=root)
            before = common.manifest_identity(args)
            (root / "thys/E/ROOT").write_text("session After = HOL +\n")
            self.assertNotEqual(before, common.manifest_identity(args))

    def test_metadata_and_diagnostics_do_not_change_candidate_signature(self):
        # PID, elapsed time and normalization diagnostics are separate facts.
        record = {"scan": {"semantic_identity": "source-context", "theories": ["A.thy"],
                           "loading": [{"session": "E", "pid": 1, "seconds": 1}],
                           "certificate_context": "old"}}
        changed = copy.deepcopy(record)
        changed["scan"]["loading"][0].update(pid=2, seconds=500)
        changed["scan"]["certificate_context"] = "new"
        self.assertEqual(full.entry_scan_signature(record), full.entry_scan_signature(changed))

    def test_killed_active_prerequisite_is_identified(self):
        # A non-timeout crash still makes the active prerequisite unavailable.
        text = "Building Done ...\nFinished Done (0:00:01 elapsed time)\nBuilding Parent ...\nKilled\n"
        self.assertEqual(scan.failed_sessions_in_log(text, "failed"), ["Parent"])

    def test_missing_receipt_and_unknown_kill_are_blocked_by_gate(self):
        # Only committed validated receipts establish completion, regardless of
        # any claimed summary. A killed command is still an unresolved outcome.
        for killed in (False, True):
            with tempfile.TemporaryDirectory() as temporary:
                store = ss.Store(temporary); unit = fixture_unit()
                data = {"order": ["E"], "entries": {"E": {"sessions": ["E"], "theories": unit["theories"]}}}
                if killed:
                    receipt = {"schema": ss.SCHEMA, "unit": unit, "unit_id": ss.digest(unit),
                               "status": "unresolved_infrastructure", "build": {"status": "failed", "returncode": -9}, "evidence": {}}
                    store.commit(store.next_attempt(unit), receipt)
                self.assertFalse(frozen.checkpoint(store, data, {"E": unit}, {})["passed"])


    def test_condition_build_uses_cache_validation_without_clean(self):
        # A compiler condition is already in Isabelle's meta_digest. Repeating
        # -c would remove unrelated descendant heaps during an otherwise local retry.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            info = {"sessions": ["E"], "theories": [
                {"name": "E.A", "path": "A.thy", "session": "E", "conditions": ["ISABELLE_CC"]}]}
            args = SimpleNamespace(isabelle="isabelle", afp=root, timeout=0, skip_proofs=False)
            with patch.object(scan, "HERE", root), patch.object(scan, "build_lock", nullcontext), \
                    patch.object(scan, "command", return_value={"status": "failed"}) as execute:
                scan.scan_entry("E", info, args, {"ISABELLE_CC": "/usr/bin/cc"}, {})
            self.assertNotIn("-c", execute.call_args.args[0])

    def test_driver_resume_executes_only_uncommitted_session(self):
        # Interrupt the actual driver after First has committed. Re-entering
        # main must schedule Second alone, even without --retry-failed.
        with tempfile.TemporaryDirectory() as temporary, patch.object(common, "PROJECT", Path(temporary)):
            base = Path(temporary) / "run"
            info = {"sessions": ["First", "Second"], "session_requirements": {"First": [], "Second": ["First"]},
                    "theories": [{"name": "E.A", "path": "A.thy", "session": "First"}]}
            data = {"order": ["E"], "entries": {"E": info}}
            units = {s: ss.unit_input("E", s, info, {}) for s in info["sessions"]}
            contract = {"tools": frozen.tools_identity()}
            calls = []
            interrupted = [False]
            def execute(store, unit, *args):
                calls.append(unit["session"])
                if unit["session"] == "Second" and not interrupted[0]:
                    interrupted[0] = True
                    raise KeyboardInterrupt
                inner, attempt, receipt = completed_fixture(base, unit)
                return inner.commit(attempt, receipt)
            with patch.object(sys, "argv", ["scan_frozen.py", "--output-dir", str(base)]), \
                    patch.object(common, "environment", return_value=({}, {"proofs": "checked"})), \
                    patch.object(frozen, "validate_contract", return_value=(contract, data, units)), \
                    patch.object(frozen, "run_unit", side_effect=execute):
                with self.assertRaises(KeyboardInterrupt):
                    frozen.main()
                self.assertEqual(frozen.main(), 0)
            self.assertEqual(calls, ["First", "Second", "Second"])
            self.assertEqual(len(ss.Store(base).attempts(units["First"])), 1)

    def test_failed_parent_does_not_block_independent_session_in_same_entry(self):
        # The real queue must isolate the dependent session; entry-wide
        # required_sessions used to suppress the independent sibling as well.
        with tempfile.TemporaryDirectory() as temporary, patch.object(common, "PROJECT", Path(temporary)):
            base = Path(temporary) / "run"
            parent = {"sessions": ["Parent"], "session_requirements": {"Parent": []},
                      "theories": [{"name": "E.A", "path": "A.thy", "session": "Parent"}]}
            child = {"sessions": ["Child", "Independent"],
                     "session_requirements": {"Child": ["Parent"], "Independent": []},
                     "theories": [{"name": "E.A", "path": "A.thy", "session": "Independent"}]}
            data = {"order": ["P", "E"], "entries": {"P": parent, "E": child}}
            units = {s: ss.unit_input(e, s, i, {}) for e, i in data["entries"].items() for s in i["sessions"]}
            contract = {"tools": frozen.tools_identity()}
            calls = []
            def execute(store, unit, *args):
                calls.append(unit["session"])
                if unit["session"] == "Parent":
                    receipt = {"schema": ss.SCHEMA, "unit": unit, "unit_id": ss.digest(unit),
                               "status": "unresolved_infrastructure", "failed_sessions": ["Parent"],
                               "build": {"status": "failed"}, "evidence": {}}
                    return store.commit(store.next_attempt(unit), receipt)
                inner, attempt, receipt = completed_fixture(base, unit)
                return inner.commit(attempt, receipt)
            with patch.object(sys, "argv", ["scan_frozen.py", "--output-dir", str(base)]), \
                    patch.object(common, "environment", return_value=({}, {"proofs": "checked"})), \
                    patch.object(frozen, "validate_contract", return_value=(contract, data, units)), \
                    patch.object(frozen, "run_unit", side_effect=execute):
                self.assertEqual(frozen.main(), 1)
            self.assertEqual(calls, ["Parent", "Independent"])
            self.assertEqual(ss.Store(base).read(units["Child"])["status"], "blocked_dependency")

    def test_reparenting_does_not_change_process_identity(self):
        # PPID is deliberately absent from the new identity tuple.
        identity = common.process_identity(os.getpid())
        self.assertEqual(identity[1], os.getpid())
        self.assertEqual(len(identity), 3)
        old = {"pid": os.getpid(), "identity": list(identity), "ppid": -123}
        self.assertTrue(common.identity_matches(old))


if __name__ == "__main__":
    unittest.main()
