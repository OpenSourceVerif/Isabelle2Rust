import subprocess
import tempfile
import unittest
from pathlib import Path
from i2r_agent.rust_index import build
from i2r_agent.segmented_contract import items, interfaces, resolve
from i2r_agent.common import Failure
import test_shared_invalidation as fixtures


class LocalItemScopeTest(unittest.TestCase):
    def test_local_declarations_are_diagnostics_not_crate_paths(self):
        files={'src/lib.rs':'''const LIMIT:u128=1;
fn a()->u128 {const LIMIT:u128=2; struct Local; enum E {V} fn helper() {} LIMIT}
fn b()->u128 {const LIMIT:u128=3; LIMIT}
'''}
        catalog=items(files)
        self.assertEqual(len(catalog['crate::LIMIT']),1)
        self.assertEqual(set(catalog),{'crate::LIMIT','crate::a','crate::b'})
        local=[r for r in build(files)['items'] if not r['path_addressable']]
        self.assertEqual(len(local),6)
        self.assertTrue(all(r['lexical_scope'] for r in local))
        self.assertNotIn('crate::helper',interfaces(files))
        with self.assertRaises(Failure):resolve(catalog,'crate::Local')

    def test_nonlocal_impl_methods_remain_globally_addressable(self):
        source='''#![allow(dead_code, non_local_definitions)]
struct S;
fn owner() {impl S {fn m()->u8 {const C:u8=7; C}} struct L; impl L {fn hidden(){}}}
fn shadow() {struct S; impl S {fn private(){}}}
fn nested() {mod local {pub struct T; impl T {pub fn private(){}}}}
fn explicit() {struct S; impl crate::S {fn extra()->u8 {8}}}
fn main() {assert_eq!(S::m(),7); assert_eq!(S::extra(),8);}
'''
        catalog=items({'src/main.rs':source})
        self.assertIn('crate::main::S::m',catalog)
        self.assertIn('crate::main::S::extra',catalog)
        self.assertFalse(any(k.endswith(('::hidden','::private','::C')) for k in catalog))
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory);(p/'main.rs').write_text(source)
            result=subprocess.run(['rustc','--edition=2021',str(p/'main.rs'),'-o',str(p/'probe')],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            subprocess.run([str(p/'probe')],check=True)

    def test_same_named_local_constant_does_not_invalidate_other_units(self):
        helper=fixtures.SharedInvalidationTest();state,cfg=helper.make_state()
        source='pub fn f()->u128 {const TWO_POW_127:u128=1<<127; TWO_POW_127}\npub fn g()->u128 {0}\n'
        state['files']['src/lib.rs']=source
        added=source+'fn helper()->u128 {const TWO_POW_127:u128=1<<127; TWO_POW_127}\n'
        self.assertEqual(helper.change(state,cfg,added)['completed'],state['completed'])
        kept=[u for u,row in state['partition']['units'].items() if 'constant:A.g' in row['members']]
        self.assertEqual(helper.change(state,cfg,source.replace('1<<127','1<<126'))['completed'],kept)
