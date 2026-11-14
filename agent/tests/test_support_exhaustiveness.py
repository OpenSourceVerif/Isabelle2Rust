import tempfile,unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock,patch
from i2r_agent.common import ROOT,read,Executor,Failure
from i2r_agent.segmented_config import configure,rust_config,materialize
from i2r_agent.segmented_support import execute
from i2r_agent.segmented_test_audit import adjudicate,exhaustiveness_revision,revise,invariants
from i2r_agent.response_protocol import normalize
from test_translation_workflow import cfg

class SupportExhaustiveness(unittest.TestCase):
    def setUp(self):
        self.f=read(ROOT/'tests/fixtures/map_support_e0004.json')
        c=cfg();c['translation']['correctness_only']=True;self.c=configure(c);self.rc=rust_config({},self.c)

    def test_real_original_e0004_then_same_oracle_passes_and_rejects_wrong_results(self):
        f=self.f;pv=Mock()
        with tempfile.TemporaryDirectory() as tmp:
            w=Path(tmp);crate=materialize(w/'candidate',f['files'],self.rc);ex=Executor(w/'commands')
            failed=execute(f['frozen'],crate,self.rc,self.c,ex)
            self.assertEqual(failed['status'],'support_test_compile_failed');self.assertIn('E0004',failed['diagnostic'])
            result=adjudicate(f['frozen'],failed,f,self.c,pv,w/'audit');fixed=result['frozen']
            pv.call.assert_not_called();self.assertEqual(result['action'],'binding_fix')
            self.assertEqual(fixed['oracle_identity'],f['frozen']['identity'])
            self.assertEqual(fixed['obligations'],f['frozen']['obligations'])
            self.assertEqual(invariants(fixed['tests'][0]),invariants(f['frozen']['tests'][0]))
            good=execute(fixed,crate,self.rc,self.c,ex)
            self.assertEqual(good['status'],'passed');self.assertEqual(good['tests_passed'],5)
            original=f['files']['src/lib.rs']
            # Keep the generic signature and production enum; change only the
            # returned semantics. All frozen tests/expectations stay identical.
            start=original.index('    match xs {')
            for name,body in [('empty','List::Nil'),('wrong_head','match xs { List::Nil => List::Nil, List::Cons(x, _) => List::Cons(f(x), Box::new(List::Nil)) }')]:
                bad=original[:start]+'    '+body+'\n}\n'
                materialize(w/name,{'src/lib.rs':bad},self.rc)
                observed=execute(fixed,w/name,self.rc,self.c,ex)
                self.assertEqual(observed['status'],'support_contract_failed',observed)

    def test_wrong_head_and_empty_results_fail_with_fixed_singleton_test(self):
        frozen={'identity':'singleton','tests':['#[test] fn singleton(){match i2r_candidate::value(){Some(42)=>(),None=>panic!(),}}'],
                'unit_tests':[],'obligations':[{'test_name':'singleton'}]}
        with tempfile.TemporaryDirectory() as tmp:
            w=Path(tmp);ex=Executor(w/'commands');files={'src/lib.rs':'pub fn value()->Option<i32>{Some(42)}'}
            crate=materialize(w/'candidate',files,self.rc);failure=execute(frozen,crate,self.rc,self.c,ex)
            fixed=exhaustiveness_revision(frozen,failure,{'files':files})
            self.assertIsNotNone(fixed)
            for value,status in [('Some(42)','passed'),('Some(43)','support_contract_failed'),('None','support_contract_failed')]:
                materialize(crate,{'src/lib.rs':'pub fn value()->Option<i32>{'+value+'}'},self.rc)
                self.assertEqual(execute(fixed,crate,self.rc,self.c,ex)['status'],status)


    def test_only_matching_frozen_identity_exact_source_e0004_span(self):
        f=self.f
        self.assertIsNotNone(exhaustiveness_revision(f['frozen'],f['failure'],f))
        for key,value in [('status','support_contract_failed'),('frozen_identity','stale'),('immutable_test_sources',['different']),('diagnostic',f['failure']['diagnostic'].replace('E0004','E0308')),('diagnostic',f['failure']['diagnostic'].replace('source_contract_0.rs:51:11','src/lib.rs:51:11')),('diagnostic',f['failure']['diagnostic'].replace(':51:11',':50:11'))]:
            with self.subTest(key=key,value=value):
                failure={**f['failure'],key:value};self.assertIsNone(exhaustiveness_revision(f['frozen'],failure,f))

    def test_panic_accepting_tests_are_not_mechanically_completed(self):
        from i2r_agent.segmented_test_audit import rejecting_match_extensions
        for marker in ['#[should_panic]', '// catch_unwind']:
            self.assertEqual(rejecting_match_extensions(marker+'\n'+self.f['frozen']['tests'][0]),[])

    def test_strict_extension_cannot_change_expectation_or_pass_missing_cases(self):
        f=self.f;old=f['frozen']['tests'][0];fixed=exhaustiveness_revision(f['frozen'],f['failure'],f)['tests'][0]
        for new in [fixed.replace('Cons(42, tail)','Cons(43, tail)'),fixed.replace('_ => ::core::panic!(),','_ => (),'),fixed.replace('_ => ::core::panic!(),','_ => return,'),fixed.replace('#[test]','#[test]\n#[ignore]',1),fixed.replace('assert_eq!(called.get(), 1);','')]:
            with self.subTest(new=new),self.assertRaises(Failure):
                revise(f['frozen'],{'repair_kind':'rejecting_exhaustiveness','reason':'bad','edits':[{'kind':'integration','index':0,'old':old,'new':new}]},f)

    def test_real_binding_response_uses_test_schema_not_production_file_schema(self):
        proposal=self.f['proposal'];self.assertEqual(normalize(proposal)[0],proposal)
        for extra in [{'files':{}},{'mapping':[]},{'rust_config':{}},{'edits':[{'kind':'integration','index':True,'old':'x','new':'y'}]},{'edits':[{'file':'src/lib.rs','old':'x','new':'y'}]}]:
            with self.subTest(extra=extra),self.assertRaises(Failure):normalize({**proposal,**extra})
        with self.assertRaises(Failure):normalize({'action':'repair','edits':proposal['edits']})

if __name__=='__main__':unittest.main()
