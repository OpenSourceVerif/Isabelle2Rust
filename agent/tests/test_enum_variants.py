import tempfile
import unittest
from pathlib import Path
from i2r_agent import segmented_contract as contract
from i2r_agent.common import ROOT, config, merge, read, Executor
from i2r_agent.segmented_config import configure, rust_config, materialize, cargo_command


class EnumVariantsTest(unittest.TestCase):
    def test_variant_scope_and_test_interface_include_constructor_fields(self):
        source = '''pub mod a { pub enum E<T> { Empty, Tuple(T), Record { value: T } } }
pub mod b { pub enum E { Empty } }
pub fn hidden() -> u128 {987654321}'''
        index = contract.items({'src/lib.rs':source})
        for name in ['Empty','Tuple','Record']:
            row = contract.resolve(index,'crate::a::E::'+name)
            self.assertEqual(row['kind'],'enum_variant')
            self.assertEqual(row['module_scope'],['a'])
        self.assertEqual(contract.resolve(index,'crate::b::E::Empty')['scope'],['b','E'])
        api = contract.interfaces({'src/lib.rs':source})
        self.assertIn('value: T', api['crate::a::E::Record'][0]['declaration'])
        self.assertNotIn('987654321',str(api['crate::hidden']))

    def test_exact_variant_mapping_accepts_real_compilable_rust_constructors(self):
        files = {'src/lib.rs':'''pub enum Tree<T> { Leaf, Node { value: T, left: Box<Tree<T>> } }
pub fn make() -> Tree<u128> { Tree::Node { value: 1, left: Box::new(Tree::Leaf) } }'''}
        index = contract.items(files)
        for name in ['Leaf','Node']:
            row = {'source':'constant:Tree.tree.'+name,'kind':'direct','rust_item':'crate::Tree::'+name}
            self.assertEqual(contract.validate_item(index,row)['kind'],'enum_variant')
        cfg = configure(merge(config(),read(Path(__file__).parent/'fixtures/shared-workflow-config.json')['base']))
        rc = rust_config({},cfg)
        with tempfile.TemporaryDirectory() as d:
            crate = materialize(Path(d)/'crate',files,rc)
            result = Executor(Path(d)/'commands').run(cargo_command(rc,cfg,'build',crate,'--lib'),timeout=120)
            self.assertEqual(result['status'],'passed')
