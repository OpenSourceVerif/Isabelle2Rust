"""Synthetic full workflow across fresh database readers; no native verdicts are claimed."""
import _paths
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

import afp_common as common
import full
import full_audit
import full_report
import scan_frozen
from state import State
from test_scan_frozen import completed_fixture


class WorkflowRoundTripTests(unittest.TestCase):
    def test_scan_export_checkpoints_and_reports_share_one_current_store(self):
        # Each phase reloads from disk. This catches disagreement between the
        # database payload, native XML reconstruction and checkpoint signatures.
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            info = {"sessions": ["E"], "session_requirements": {"E": []},
                    "theories": [{"name": "E.A", "path": "A.thy", "session": "E"}]}
            data = {"order": ["E"], "entries": {"E": info}}
            sources = {"afp": {}, "isabelle_src": {}, "settings": {}, "conditions": {}}
            state = State(base)
            state.put("run", {"created": common.timestamp(), "manifest": data, "sources": sources,
                "tools": scan_frozen.tools_identity(),
                "environment": {"proofs": "checked", "command_timeout_seconds": 0}})
            unit = scan_frozen.make_units(data, sources)["E"]
            store, attempt, receipt = completed_fixture(base, unit)
            store.commit(attempt, receipt)
            data, result, exports = full.load(base)
            self.assertTrue(full.scan_checkpoint(base, data, result, exports)["passed"])
            full.require_scan_gate(base, result, exports)
            def export(session, work, args, env):
                (work / "process.log").write_text("synthetic successful native return")
                check = {"status": "passed", "returncode": 0, "log": str(work / "process.log")}
                common.write_record(work / "process.log.json", check)
                (work / "finished.xml").write_text("<finished/>")
                node = ET.Element("attempt", status="failed", target="frontend", stage="frontend")
                ET.SubElement(node, "constant", name="A.f")
                for target in full.TARGETS:
                    ET.SubElement(node, "language").text = target
                ET.SubElement(node, "error").text = "synthetic singleton rejection"
                path = work / "attempts/merged/all/frontend.xml"
                path.parent.mkdir(parents=True)
                path.write_text(ET.tostring(node, encoding="unicode"))
                return check
            with patch.object(full, "export_command", side_effect=export):
                full.export_entry("E", info, result["entries"]["E"], exports["E"], base,
                                  SimpleNamespace(export_batch_size=0, source_fault_heap_mb=0), {})
            full.save(base, result, exports, "E")
            data, result, exports = full.load(base)
            self.assertTrue(full.export_checkpoint(base, data, result, exports)["passed"])
            self.assertTrue(full.compile_checkpoint(base, result)["passed"])
            audited = full_audit.audit_data(base, data, result, exports)
            # The sole archive-wide failure is intentional: this fixture has
            # one entry. Every current-state/evidence predicate must pass.
            self.assertEqual(audited["issue_counts"], {"full AFP archive": 1})
            full_report.build_report(base, data, result, exports, verified=True)
            report_audit = {"passed": True, "issues": [], "checks": {}, "issue_counts": {}}
            full_audit.audit_reports(base, data, result, exports, report_audit)
            self.assertTrue(report_audit["passed"], report_audit["issues"])
            self.assertEqual(list(base.glob("*.json")), [])
            self.assertFalse(state.keys("export-progress/"))
            packed = state.get("entry/E")["full_export"]
            self.assertNotIn("candidates", packed)
            self.assertNotIn("attempts", packed["runs"][0])
            self.assertIn("@command", packed["runs"][0]["command"])
