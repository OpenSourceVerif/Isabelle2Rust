import unittest,tempfile
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock
from i2r_agent.common import ROOT,read,Executor,Failure
from i2r_agent.segmented_config import configure,rust_config,materialize
from i2r_agent.segmented_support import execute
from i2r_agent.segmented_test_audit import adjudicate,macro_separator_revision,revise,invariants
from test_v8_workflow import cfg

class MacroSeparator(unittest.TestCase):
    def test_original_compiler_failure_then_test_only_revision_and_wrong_branch_rejection(self):
        f=read(ROOT/'tests/fixtures/isort_support_macro_separator.json');c=cfg();c['v8']['correctness_only']=True;c=configure(c);rc=rust_config({},c)
        with tempfile.TemporaryDirectory() as tmp:
            w=Path(tmp);ex=Executor(w/'commands');crate=materialize(w/'candidate',f['files'],rc)
            original_materialized=(crate/'src/lib.rs').read_text()
            failed=execute(f['frozen'],crate,rc,c,ex)
            self.assertEqual(failed['status'],'support_test_compile_failed');self.assertIn('no rules expected `,`',failed['diagnostic'])
            pv=Mock();result=adjudicate(f['frozen'],failed,f,c,pv,w/'audit');pv.call.assert_not_called();fixed=result['frozen']
            self.assertEqual(fixed['obligations'],f['frozen']['obligations'])
            self.assertEqual(invariants(fixed['tests'][0]),invariants(f['frozen']['tests'][0]))
            self.assertEqual(len(f['frozen']['tests'][0])-len(fixed['tests'][0]),1)
            good=execute(fixed,crate,rc,c,ex);self.assertEqual(good['status'],'passed',good)
            self.assertEqual((crate/'src/lib.rs').read_text(),original_materialized)
            bad={'src/lib.rs':f['files']['src/lib.rs'].replace('if $condition {','if !$condition {')};materialize(crate,bad,rc)
            result=execute(fixed,crate,rc,c,ex);self.assertEqual(result['status'],'support_contract_failed')
            for change in [{'frozen_identity':'newer'},{'diagnostic':failed['diagnostic'].replace('tests/source_contract_0.rs','src/lib.rs')},{'immutable_test_sources':['different']}]:
                self.assertIsNone(macro_separator_revision(f['frozen'],{**failed,**change},f))
            old=f['frozen']['tests'][0]
            for new in [fixed['tests'][0].replace('22u32','23u32'),fixed['tests'][0].replace('assert_eq!(t, 11);','')]:
                with self.assertRaises(Failure):revise(f['frozen'],{'reason':'bad','repair_kind':'trailing_macro_separator','edits':[{'kind':'integration','index':0,'old':old,'new':new}]},f)
