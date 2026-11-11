import unittest
from i2r_agent.common import Failure
from i2r_agent.export_contract import check_exports, generic_function_parameters

class ExportContractTests(unittest.TestCase):
    def test_observation_specialization_does_not_count_as_generic_export(self):
        bundle={'programs':[{'entries':['constant:M.index'],'nodes':[{'id':'constant:M.index',
            'statement':{'kind':'function','signature':{'variables':[['a',['HOL.equal']]]}}}]}]}
        mapping=[{'source':'constant:M.index','rust':'index','type_parameters':{'a':'T'}}]
        with self.assertRaises(Failure):
            check_exports(bundle,{'src/lib.rs':'// fn index<T>() {}\npub fn index(xs: &[u128]) -> usize { xs.len() }'},mapping)
        checked=check_exports(bundle,{'src/lib.rs':'pub fn index<T: PartialEq>(xs: &[T], x: &T) -> usize { xs.iter().position(|a| a==x).unwrap_or(xs.len()) }'},mapping)
        self.assertEqual(len(checked['checked_exports']),1)
    def test_function_trait_bounds_and_lifetimes(self):
        self.assertEqual(generic_function_parameters("pub fn find<'a, T, F: Fn(&T) -> bool>(p: F, xs: &'a [T]) {}",'find'),[{'T','F'}])

if __name__=='__main__':unittest.main()
