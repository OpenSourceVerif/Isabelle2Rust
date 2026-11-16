"""A failed export checkpoint emits an explicitly incomplete report."""
import _paths
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import afp
import afp_common as common


class IncompleteReportTests(unittest.TestCase):
    def run_pipeline(self, failure=None):
        calls = []
        def call(script, arguments, config_path=None):
            calls.append((Path(script).name, arguments))
            return int(Path(script).name == "afp.py" and failure in arguments)
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            with patch.object(common, "configure", return_value={}), \
                    patch.object(afp, "call", side_effect=call):
                result = afp.main(["--work", str(base), "run"])
            return result, calls, str(base)

    def test_failed_export_reports_incomplete_without_compilation(self):
        result, calls, base = self.run_pipeline("export-checkpoint")
        self.assertEqual(result, 1)
        self.assertEqual(calls[-1],
                         ("full_report.py", ["--output-dir", base, "--preview"]))
        phases = [args[-1] for name, args in calls if name == "afp.py"]
        self.assertNotIn("compile", phases)
        self.assertNotIn("audit", phases)
        self.assertNotIn("report", phases)

    def test_success_keeps_final_report_and_completion_audits(self):
        result, calls, _ = self.run_pipeline()
        self.assertEqual(result, 0)
        self.assertTrue(all(name == "afp.py" for name, _ in calls))
        self.assertTrue(all("--preview" not in args for _, args in calls))
        self.assertEqual([args[-1] for _, args in calls][-4:],
                         ["compile-checkpoint", "audit", "report", "--with-report"])


if __name__ == "__main__":
    unittest.main()
