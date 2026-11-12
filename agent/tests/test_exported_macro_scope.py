import subprocess
import tempfile
import unittest
from pathlib import Path
from i2r_agent.common import Failure
from i2r_agent.rust_index import build
from i2r_agent.segmented_contract import items, resolve
from i2r_agent import translation_workflow as runner
import test_shared_invalidation as fixtures


class ExportedMacroScopeTest(unittest.TestCase):
    def test_exported_macros_have_root_paths_in_files_modules_and_blocks(self):
        files={'src/lib.rs':'''mod helpers;
mod nested {#[macro_export] macro_rules! nested {()=>{2};}}
fn owner() {#[macro_export] macro_rules! local {()=>{3};}}
#[macro_export(local_inner_macros)] macro_rules! root {()=>{4};}
fn main() {assert_eq!((crate::in_file!(),crate::nested!(),crate::local!(),crate::root!()),(1,2,3,4));}
''','src/helpers.rs':'#[macro_export] macro_rules! in_file {()=>{1};}'}
        catalog=items(files)
        for name in ['in_file','nested','local','root']:
            self.assertEqual(resolve(catalog,'crate::'+name)['kind'],'macro_definition')
        self.assertNotIn('crate::helpers::in_file',catalog)
        self.assertNotIn('crate::nested::nested',catalog)
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)
            for name,text in files.items():(p/Path(name).name).write_text(text)
            c=subprocess.run(['rustc','--edition=2024',str(p/'lib.rs'),'-o',str(p/'probe')],capture_output=True,text=True)
            self.assertEqual(c.returncode,0,c.stderr)
            subprocess.run([str(p/'probe')],check=True)

    def test_unexported_and_conditional_exports_are_not_invented_paths(self):
        source='''macro_rules! local {()=>{1};}
mod nested {macro_rules! local {()=>{2};}}
fn f() {macro_rules! local {()=>{3};}}
#[cfg_attr(feature="export", macro_export)] macro_rules! conditional {()=>{4};}
'''
        index=build({'src/lib.rs':source})
        macros=[r for r in index['items'] if r['kind']=='macro_definition']
        self.assertEqual(len(macros),4)
        self.assertTrue(all(not r['path_addressable'] for r in macros))
        self.assertEqual(set(items({'src/lib.rs':source})),{'crate::f'})

    def test_duplicate_exports_remain_ambiguous(self):
        files={'src/lib.rs':'#[macro_export] macro_rules! same {()=>{1};}',
               'src/other.rs':'#[macro_export] macro_rules! same {()=>{2};}'}
        with self.assertRaises(Failure) as error:resolve(items(files),'crate::same')
        self.assertEqual(error.exception.evidence['matches'],2)

    def test_macro_addition_and_body_edit_invalidate_completed_reviews(self):
        state,cfg=fixtures.SharedInvalidationTest().make_state()
        macro='\n#[macro_export] macro_rules! helper {()=>{1};}\n'
        with tempfile.TemporaryDirectory() as directory:
            after=runner.apply_transaction(state,{'files':{'src/lib.rs':state['files']['src/lib.rs']+macro}},cfg,Path(directory))
            self.assertEqual(after['completed'],[])
            state['files']['src/lib.rs']+=macro
            after=runner.apply_transaction(state,{'files':{'src/lib.rs':state['files']['src/lib.rs'].replace('()=>{1}','()=>{2}')}},cfg,Path(directory))
            self.assertEqual(after['completed'],[])
