#!/usr/bin/env python3
"""Classify actual abstraction diagnostics at their shared code-generation stage."""
import unittest
import full_report


class ErrorCategoryTests(unittest.TestCase):
    def test_abstract_constructor_export_uses_the_interface_category(self):
        # PQ declares an executable abstract representation. Directly exporting
        # its Abs_pq constructor is rejected before a target printer is invoked;
        # the distinct rejection must not become an unexplained backend error.
        message = "Cannot export abstract constructor(s): pq.Abs_pq"
        key, label, explanation = full_report.category(message)
        self.assertEqual(key, "abstraction")
        self.assertIn("Thingol", explanation)

    def test_equation_abstraction_and_missing_equations_remain_distinct(self):
        # Both original equation checks and direct export checks describe the
        # abstract interface, while an absent BNF helper implementation is a
        # separate target-projection prerequisite.
        self.assertEqual(full_report.category("Abstraction violation in code equation")[0], "abstraction")
        self.assertEqual(full_report.category("No code equations for AVL.tree.Abs_tree")[0], "code_equations")


if __name__ == "__main__":
    unittest.main()
