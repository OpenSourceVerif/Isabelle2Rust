"""Regression cases for native context-selection evidence."""
import _paths
import copy
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

import dependency_plan as dp
import fixed_plan


class SelectionReceiptTests(unittest.TestCase):
    def setUp(self):
        self.expected = {
            "theories": ["E.Left", "E.Right"],
            "required": {"E": ["E.Left", "E.Right"]},
            "entry_theories": ["E.Left", "E.Right"],
            "declarations": [
                {"name": "Left.f", "owner": "E.Left", "source": "Left.thy"},
                {"name": "Right.g", "owner": "E.Right", "source": "Right.thy"},
            ],
        }

    def receipt(self, failed=True):
        root = ET.Element("selection", schema="1")
        for name in self.expected["theories"]:
            ET.SubElement(root, "loaded", name=name)
        merge = ET.SubElement(root, "merge", status="failed" if failed else "complete")
        if failed:
            ET.SubElement(merge, "error").text = "Clash of specifications for equal_class.equal"
        groups = [[name] for name in self.expected["theories"]] if failed else [self.expected["theories"]]
        for parents in groups:
            node = ET.SubElement(root, "context", status="complete")
            for name in list(parents) + list(dp.SETUPS):
                ET.SubElement(node, "parent", name=name)
            for declaration in self.expected["declarations"]:
                if declaration["owner"] in parents:
                    ET.SubElement(node, "declaration", declaration)
        return root

    def parse(self, root):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "selection.xml"
            ET.ElementTree(root).write(path, encoding="utf-8")
            return fixed_plan.parse_selection(path, "E", "E", self.expected)

    def test_failed_merge_with_native_error_accepts_complete_branches(self):
        result = self.parse(self.receipt())
        self.assertEqual(len(result), 2)
        self.assertEqual({d["name"] for c in result for d in c["declarations"]},
                         {"Left.f", "Right.g"})
        self.assertTrue(all(c["parents"][-2:] == list(dp.SETUPS) for c in result))

    def test_successful_merge_has_one_context_without_error(self):
        result = self.parse(self.receipt(failed=False))
        self.assertEqual(result[0]["parents"], ["E.Left", "E.Right", *dp.SETUPS])

    def test_failed_merge_requires_exact_text_error(self):
        for mode in ("absent", "empty", "duplicate", "attributes", "nested", "unknown"):
            with self.subTest(mode=mode):
                root = self.receipt()
                merge = root.find("merge")
                error = merge.find("error")
                if mode == "absent":
                    merge.remove(error)
                elif mode == "empty":
                    error.text = "  "
                elif mode == "duplicate":
                    merge.append(copy.deepcopy(error))
                elif mode == "attributes":
                    error.set("ignored", "true")
                elif mode == "nested":
                    ET.SubElement(error, "nested")
                else:
                    error.tag = "unknown"
                with self.assertRaisesRegex(ValueError, "Invalid context merge record"):
                    self.parse(root)

    def test_successful_merge_cannot_include_error(self):
        root = self.receipt(failed=False)
        ET.SubElement(root.find("merge"), "error").text = "conflict"
        with self.assertRaisesRegex(ValueError, "Invalid context merge record"):
            self.parse(root)

    def test_failed_branch_remains_unresolved(self):
        root = self.receipt()
        node = root.find("context")
        node.set("status", "unresolved")
        ET.SubElement(node, "error").text = "branch failed"
        with self.assertRaisesRegex(ValueError, "Unresolved context selection: branch failed"):
            self.parse(root)

    def test_missing_required_loaded_theory_is_rejected(self):
        root = self.receipt()
        root.remove(root.find("loaded"))
        with self.assertRaisesRegex(ValueError, "Invalid loaded-theory inventory"):
            self.parse(root)

    def test_duplicate_setup_parent_is_rejected(self):
        root = self.receipt()
        root.find("context").insert(0, ET.Element("parent", name=dp.SETUPS[-1]))
        with self.assertRaisesRegex(ValueError, "Invalid fixed parent order/backend setup"):
            self.parse(root)

    def test_setup_only_entry_uses_each_backend_parent_once(self):
        self.expected = {"theories": [dp.SETUPS[-1]], "required": {"E": [dp.SETUPS[-1]]},
                         "entry_theories": [dp.SETUPS[-1]], "declarations": []}
        root = self.receipt(failed=False)
        node = root.find("context")
        node.remove(node.find("parent"))
        self.assertEqual(self.parse(root)[0]["parents"], list(dp.SETUPS))

    def test_setup_only_context_cannot_drop_entry_theories(self):
        root = self.receipt(failed=False)
        node = root.find("context")
        for parent in node.findall("parent")[:2]:
            node.remove(parent)
        with self.assertRaisesRegex(ValueError, "Invalid fixed parent order/backend setup"):
            self.parse(root)

    def test_duplicate_declaration_is_rejected(self):
        root = self.receipt()
        node = root.find("context")
        node.append(copy.deepcopy(node.find("declaration")))
        with self.assertRaisesRegex(ValueError, "Duplicate selected declaration"):
            self.parse(root)

    def test_unknown_evidence_is_not_silently_ignored(self):
        for scope in ("root", "context", "declaration"):
            with self.subTest(scope=scope):
                root = self.receipt()
                node = root if scope == "root" else root.find("context")
                if scope == "declaration":
                    node = node.find("declaration")
                ET.SubElement(node, "unknown")
                with self.assertRaises(ValueError):
                    self.parse(root)


if __name__ == "__main__":
    unittest.main()
