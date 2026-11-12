import unittest
from i2r_agent.test_obligations import requirements

class OperationObligationTests(unittest.TestCase):
    def test_class_names_do_not_create_value_level_numeric_tests(self):
        names=['class:Rings.divide','class:Rings.semiring_modulo_trivial','type:Example.modulo_type',
               'constant:Euclidean_Rings.divide_nat_inst.divide_nat',
               'constant:Bit_Operations.semiring_bit_operations_nat_inst.push_bit_nat',
               'constant:Example.run']
        state={'mapping':[{'source':n,'rust_item':'crate::mapped'} for n in names],
               'bundle':{'source_model':{'entries':['constant:Example.run']}}}
        rows=requirements(state,names)
        self.assertEqual(rows,[{'source':names[4],'category':'zero_huge_count'},
                               {'source':names[4],'category':'nonzero_range_boundary'},
                               {'source':names[3],'category':'zero_divisor'},
                               {'source':names[3],'category':'division_signs'},
                               {'source':names[5],'category':'public_behavior'}])
