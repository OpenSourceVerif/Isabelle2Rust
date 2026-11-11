import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock,patch
from i2r_agent.common import Failure,Executor
from i2r_agent.segmented_config import materialize,rust_config
from i2r_agent.segmented_support import prepare,execute
from i2r_agent.v8_support import validate_records,validate_obligations
from test_segmented_workflow import source,mapping
from test_v8_workflow import cfg


class V8SupportRecords(unittest.TestCase):
    def test_nonterminating_contract_uses_execution_timeout_not_build_budget(self):
        c=cfg();c['testing']['process_timeout']=1;c['budgets']['build_seconds']=60
        rc=rust_config({},c)
        frozen={'identity':'hang-reproducer','tests':['#[test] fn must_finish(){i2r_candidate::run();}'],
                'unit_tests':[],'obligations':[]}
        with tempfile.TemporaryDirectory() as d:
            w=Path(d);crate=materialize(w/'crate',{'src/lib.rs':'pub fn run(){loop{std::hint::spin_loop();}}'},rc)
            result=execute(frozen,crate,rc,c,Executor(w/'commands'))
            self.assertEqual(result['compilation']['status'],'passed')
            self.assertEqual(result['compilation']['timeout_seconds'],60)
            self.assertEqual(result['record']['status'],'timeout')
            self.assertEqual(result['record']['timeout_seconds'],1)
            self.assertLess(result['record']['seconds'],10)
            self.assertEqual(result['status'],'support_contract_failed')

    def test_omissions_are_records_not_fake_executions_or_implicit_coverage(self):
        row={'source':'constant:A.f','category':'public_behavior','disposition':'inaccessible',
             'source_basis':'source entry exists','api_basis':'entry not translated in this prefix',
             'expected_basis':'no result is claimed'}
        proposal={'test_source':'#[test] fn other(){}','obligations':[row]}
        validate_records(proposal,{row['source']})
        with self.assertRaises(Failure):validate_obligations(proposal,[{'source':row['source'],'category':row['category']}])
        row['disposition']='not_applicable'
        validate_records(proposal,{row['source']})
        validate_obligations(proposal,[{'source':row['source'],'category':row['category']}])
        row.pop('api_basis')
        with self.assertRaises(Failure) as e:validate_records(proposal,{row['source']})
        self.assertIn('api_basis',e.exception.evidence['record_errors'][0]['missing_fields'])

    def test_executing_record_and_unknown_source_report_the_actual_field(self):
        row={'source':'constant:A.f','expected_basis':'source equation','test_name':'check'}
        with self.assertRaises(Failure) as e:validate_records({'obligations':[row]},{row['source']})
        self.assertEqual(e.exception.evidence['record_errors'][0]['missing_fields'],['case'])
        row['case']='f()';row['source']='constant:invented'
        with self.assertRaises(Failure) as e:validate_records({'obligations':[row]},{'constant:A.f'})
        self.assertEqual(e.exception.evidence['record_errors'][0]['error'],'unknown source ID')
        row['source']=['constant:A.f']
        with self.assertRaises(Failure):validate_records({'obligations':[row]},{'constant:A.f'})
        row['source']='constant:A.f'
        for case in [0,False,[]]:
            row['case']=case;validate_records({'obligations':[row]},{'constant:A.f'})

    def test_whole_scope_supplies_all_export_sources_and_executes_them(self):
        c=cfg();rc=rust_config({},c);b=source();model=b['source_model']
        g=deepcopy(model['entities']['constant:A.f']);g.update(id='constant:A.g',name='A.g')
        model['entities']['constant:A.g']=g;model['entries'].append('constant:A.g');b['numeric_policy']={'mode':'checked'}
        s={'bundle':b,'files':{'src/lib.rs':'pub fn h()->u128{1} pub fn f()->u128{2} pub fn g()->u128{3}'},
           'mapping':[mapping('h'),mapping('f'),mapping('g')],'rust_config':rc}
        def review(p,source_pages,*args,**kwargs):
            self.assertEqual(p['test_scope']['implemented_exports'],['constant:A.f','constant:A.g'])
            self.assertEqual(p['test_scope']['kind'],'whole_program')
            self.assertEqual(p['test_scope']['pending_exports'],[])
            self.assertEqual({'constant:A.h','constant:A.f','constant:A.g'},{r['source'] for r in source_pages})
            if p['task'].startswith('Review'):return {'action':'accept','review':'All public source values independently checked'}
            return {'test_source':'#[test] fn values(){assert_eq!(i2r_candidate::h(),1);assert_eq!(i2r_candidate::f(),2);assert_eq!(i2r_candidate::g(),3);}',
                    'obligations':[{'source':'constant:A.f','category':'public_behavior','test_name':'values','case':'f()','expected_basis':'source f=2'},
                    {'source':'constant:A.g','category':'public_behavior','test_name':'values','case':'g()','expected_basis':'source g=3'}]}
        with tempfile.TemporaryDirectory() as d,patch('i2r_agent.segmented_support.source_review',side_effect=review):
            work=Path(d);frozen=prepare(s,c,Mock(),work/'tests')
            self.assertEqual(frozen['obligations'][1]['source'],'constant:A.g')
            crate=materialize(work/'candidate',s['files'],rc)
            self.assertEqual(execute(frozen,crate,rc,c,Executor(work/'commands'))['status'],'passed')

    def test_strategy_test_focus_and_cache_do_not_supply_candidate_expectations(self):
        from i2r_agent import implementation_strategy as strategy
        c=cfg();rc=rust_config({},c);b=source();b['numeric_policy']={'mode':'checked'}
        s={'bundle':b,'files':{'src/lib.rs':'pub fn h()->u128{99}'},'mapping':[mapping('h')],'rust_config':rc}
        s['implementation_strategy']=strategy.initialize({'semantic_obligations':[{'source':'constant:A.h','rust_representation':'secret algorithm','conditions':['zero boundary']}]})
        def review(p,*args,**kwargs):
            self.assertIn('zero boundary',str(p['strategy_test_focus']))
            self.assertNotIn('secret algorithm',str(p))
            self.assertNotIn('return 99',str(p))
            self.assertIn('exclusively from source equations',p['expectation_rule'])
            if p['task'].startswith('Review'):return {'action':'accept','review':'Source h=1, irrespective of strategy'}
            return {'test_source':'#[test] fn frozen(){assert_eq!(i2r_candidate::h(),1);}',
                    'obligations':[{'source':'constant:A.h','test_name':'frozen','case':'h()','expected_basis':'source h=1'}]}
        with tempfile.TemporaryDirectory() as d,patch('i2r_agent.segmented_support.source_review',side_effect=review) as author:
            work=Path(d);first=prepare(s,c,Mock(),work/'tests')
            original=deepcopy(first)
            s['implementation_strategy']['decisions'][0]['reason']='Unrelated explanatory wording'
            reused=prepare(s,c,Mock(),work/'tests')
            self.assertEqual(author.call_count,2);self.assertEqual(first['identity'],reused['identity'])
            s['implementation_strategy']['decisions'][0]['conditions'].append('additional range condition')
            rebound=prepare(s,c,Mock(),work/'tests')
            self.assertEqual(author.call_count,4);self.assertNotEqual(first['identity'],rebound['identity'])
            self.assertEqual(first,original)
            crate=materialize(work/'candidate',s['files'],rc)
            self.assertEqual(execute(first,crate,rc,c,Executor(work/'commands'))['status'],'support_contract_failed')

    def test_mapping_change_rebinds_tests_even_with_identical_rust_interfaces(self):
        c=cfg();rc=rust_config({},c);b=source();b['numeric_policy']={'mode':'checked'}
        s={'bundle':b,'files':{'src/lib.rs':'pub fn h()->u128{1} pub fn f()->u128{2}'},'mapping':[mapping('h')],'rust_config':rc}
        def review(p,*args,**kwargs):
            if p['task'].startswith('Review'):return {'action':'accept','review':'Source h=1 unchanged; actual mapped owner checked'}
            item=p['mapping'][0]['rust_item'].rsplit('::',1)[-1]
            return {'test_source':'#[test] fn original(){assert_eq!(i2r_candidate::'+item+'(),1);}',
                    'obligations':[{'source':'constant:A.h','test_name':'original','case':'mapped h()','expected_basis':'source h=1'}]}
        with tempfile.TemporaryDirectory() as d,patch('i2r_agent.segmented_support.source_review',side_effect=review) as author:
            work=Path(d);crate=materialize(work/'candidate',s['files'],rc);ex=Executor(work/'commands')
            first=prepare(s,c,Mock(),work/'tests')
            self.assertEqual(execute(first,crate,rc,c,ex)['status'],'passed')
            s['mapping'][0].update(rust='crate::f',rust_item='crate::f')
            rebound=prepare(s,c,Mock(),work/'tests')
            self.assertNotEqual(first['identity'],rebound['identity']);self.assertEqual(author.call_count,4)
            self.assertEqual(execute(rebound,crate,rc,c,ex)['status'],'support_contract_failed')


if __name__=='__main__':unittest.main()
