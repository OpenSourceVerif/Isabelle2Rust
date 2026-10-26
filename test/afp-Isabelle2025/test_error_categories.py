#!/usr/bin/env python3
"""Classify native abstraction, target namespace and literal diagnostics."""
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


    def test_pruned_target_symbol_is_not_source_declaration_visibility(self):
        # A generated partial_term_of expression asks Go for the ordinary
        # Code_Numeral.Pos constructor after numeral syntax has replaced it.
        # The hierarchical namespace reports a missing statement, while source
        # constant visibility has already been established by the frontend.
        key, _, explanation = full_report.category('Unknown statement name: "Code_Numeral.Pos"')
        self.assertEqual(key, "target_symbol_resolution")
        self.assertIn("code_printing", explanation)
        self.assertEqual(full_report.category('Unknown constant "Missing.c"')[0], "name_interface")
        self.assertEqual(full_report.category("exception Option raised")[0], "ml_exception")

    def test_dynamic_literal_rejection_preserves_its_printing_contract(self):
        # literal_of_asciis constructs a string from runtime character bits and
        # a recursive tail. Literal.add_code accepts only a closed static chain,
        # so this diagnostic should explain the target literal contract.
        message = (
            "Illegal string literal expression,\n"
            "in equation String.literal_of_asciis (?k # ?ks) \\<equiv>\n"
            "case char_of_integer ?k of Char b0 b1 b2 b3 b4 b5 b6 b7 \\<Rightarrow>\n"
            "String.Literal b0 b1 b2 b3 b4 b5 b6 (String.literal_of_asciis ?ks)"
        )
        key, _, explanation = full_report.category(message)
        self.assertEqual(key, "literal_adaptation")
        self.assertIn("动态", explanation)


if __name__ == "__main__":
    unittest.main()
