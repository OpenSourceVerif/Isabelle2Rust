import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
from copy import deepcopy
from i2r_agent.common import ROOT,config,merge,read,save,Executor,Failure
from i2r_agent.segmented_config import configure,materialize,rust_config
from i2r_agent import v8_repair as repair, v8_performance as perf
from i2r_agent.segmented_v8 import search,connector_identity
from i2r_agent.segmented_run import connection,compile_crate
from i2r_agent.v8_support import validate_obligations
from test_segmented_workflow import source,mapping,route_reviews


def cfg():
    c=configure(merge(config(),read(Path(__file__).parent/'fixtures/segmented-source-v8.json')['base']))
    c['testing']['transport']='native-u128';c['testing']['max_input_bits']=128
    c['testing']['clippy']='off';c['segmented']['development_performance']=False
    return c


def accept(p,c):
    return {'action':'accept','quality_review':'Source equations and actual interfaces checked',
            'reviewed_sources':p['required_review_sources'],'reviewed_pages':[x['id'] for x in p['page_catalog']],
            'reviewed_code_pages':[x['id'] for x in p['code_page_catalog']],
            'algorithm_routes':route_reviews(p),'review_checks':{k:'source comparison' for k in c['segmented']['review_categories']}}


CONNECTOR='''pub type WireInt=u128; pub type Prepared=Vec<u128>; pub type KernelResult=Vec<u128>;
pub fn observe(_: &[u128])->Vec<u128>{vec![2,2,2]}
pub fn benchmark_prepare(x:&[u128])->Prepared{x.to_vec()}
pub fn benchmark_run(_:Prepared)->KernelResult{vec![i2r_candidate::f();3]}
pub fn benchmark_encode(x:KernelResult)->Vec<u128>{x}
'''


class V8Tests(unittest.TestCase):
    def test_changes_do_not_reset_original_failure_budget(self):
        c=cfg();c['v8']['repair_stall_limit']=3;s={}
        issue=repair.register(s,'behavior',{'status':'mismatch'},{'inputs':[[1]],'arguments':['--i2r-benchmark']},'whole_review')
        for n in range(2):
            s['files']={'src/lib.rs':str(n)}
            self.assertFalse(repair.replay_result(s,{'status':'mismatch'},c))
        self.assertTrue(repair.needs_diagnostics(s,c))
        with self.assertRaises(Failure) as e:repair.replay_result(s,{'status':'mismatch'},c)
        self.assertEqual(e.exception.code,'repair_stalled');self.assertEqual(issue['reproducer']['inputs'],[[1]])

    def test_repeated_refuted_hypothesis_needs_evidence(self):
        s={};c=cfg();repair.register(s,'compile',{}, {'roots':[]},'refine')
        reply={'repair_hypothesis':{'cause':'wrong borrow','evidence':'E0502','change':'borrow scope','prediction':'compiles'}}
        repair.proposal(s,reply);repair.replay_result(s,{'status':'compile_failed'},c)
        with self.assertRaises(Failure):repair.proposal(s,reply)
        repair.active(s)['observations'].append({'path':'actually-executed-diagnostic'})
        repair.proposal(s,reply)

    def test_connector_identity_reuses_bodies_but_not_interfaces(self):
        s={'files':{'src/lib.rs':'pub fn f()->u128{1}'},'mapping':[],'rust_config':{}}
        first=connector_identity(s);s['files']['src/lib.rs']='pub fn f()->u128{2}'
        self.assertEqual(connector_identity(s),first)
        s['files']['src/lib.rs']='pub fn f()->i128{2}'
        self.assertNotEqual(connector_identity(s),first)

    def test_obligation_requires_real_enabled_test(self):
        req=[{'source':'constant:Nat.take_bit','category':'small_nonnegative_huge_count'}]
        p={'test_source':'#[test] fn huge(){assert_eq!(1,1);}', 'obligations':[{'source':req[0]['source'],'category':req[0]['category'],'test_name':'huge','expected_basis':'source equation'}]}
        validate_obligations(p,req)
        p['test_source']='#[test] #[ignore] fn huge(){assert_eq!(1,1);}'
        with self.assertRaises(Failure):validate_obligations(p,req)

    def test_source_optimization_true_cannot_be_silently_ignored(self):
        c=cfg();c['source_optimization']['enabled']=True
        with self.assertRaises(Failure) as e:configure(c)
        self.assertEqual(e.exception.code,'source_optimization_unimplemented')

    def test_perf_accepts_clear_gain_and_rejects_regression_or_noise(self):
        c=cfg()
        def m(a,b):return {'summary':{'parent':{'median_ns':sum(a)/len(a),'process_medians_ns':a},'candidate':{'median_ns':sum(b)/len(b),'process_medians_ns':b}}}
        self.assertTrue(perf.compare([m([100,101],[80,81])],c)['accept'])
        self.assertFalse(perf.compare([m([90,110],[85,105])],c)['accept'])
        self.assertFalse(perf.compare([m([100,101],[80,81]),m([100,101],[110,111])],c)['accept'])

    def test_workloads_cover_big_sqrt_and_respect_checked_domain(self):
        c=cfg();self.assertTrue(all(max(x).bit_length()<=128 for x in perf.workloads('karatsuba-sqrt',c)))
        c['testing']['max_input_bits']=0
        self.assertIn(4096,[max(x).bit_length() for x in perf.workloads('karatsuba-sqrt',c)])

    def test_actual_instrumentation_executes_and_reports_nested_calls(self):
        c=cfg();rc=rust_config({},c)
        files={'src/lib.rs':'pub fn h()->u128{1} pub fn f()->u128{h()+1} const fn unused()->u128{3}'}
        with tempfile.TemporaryDirectory() as d:
            w=Path(d);ex=Executor(w/'commands')
            reference=w/'reference';reference.write_text('#!/bin/sh\nwhile read x; do echo "2 2 2"; done\n');reference.chmod(0o755)
            s={'files':files,'mapping':[],'connector':{'src/lib.rs':CONNECTOR},'rust_config':rc,'bundle':{'case':'list-index'}}
            r=perf.profile(s,c,ex,{'ocaml':{'binary':str(reference)},'stage2':{'binary':str(reference)}},[[9,1,2]],w/'profile')
            self.assertEqual(r['status'],'measured',r)
            hotspots=r['workloads'][0]['hotspots'];self.assertEqual(len(hotspots),2)
            self.assertEqual(sorted(x['calls'] for x in hotspots),[3,3]);self.assertEqual(len(r['skipped']),1)
            self.assertEqual(files['src/lib.rs'],s['files']['src/lib.rs'])
            boundary=perf.boundaries(s,c,ex,{'ocaml':{'binary':str(reference)},'stage2':{'binary':str(reference)}},[[9,1,2]],w/'boundaries')
            self.assertEqual(boundary['status'],'measured',boundary)
            self.assertEqual(len(boundary['workloads'][0]['timings_ns']['PREPARE']),3)

    def test_kernel_failure_is_replayed_before_review_with_connector_reuse(self):
        c=cfg();c['segmented']['support_tests']=False;b=source();b['case']='list-index';b['workflow']='segmented-v8'
        provider=Mock();provider.calls=0;provider.usage={};seen=[];diagnosed=[]
        def ask(pv,conf,path,p,analysis=False):
            phase=p['controller_state']['phase'];seen.append(phase)
            if phase=='generate':
                n=p['unit']['members'][0].rsplit('.',1)[-1]
                return {'files':{'src/lib.rs':p['current_files']['src/lib.rs']+'\npub fn '+n+'()->u128{'+('1' if n=='h' else 'h()+0')+'}'},'mapping':[mapping(n)]}
            if phase=='repair':
                self.assertEqual(p['repair_issue']['reproducer']['arguments'],['--i2r-benchmark'])
                if not diagnosed:
                    diagnosed.append(True);return {'action':'request_diagnostics'}
                self.assertEqual(p['repair_issue']['observations'][0]['stdout'].strip(),'1 1 1')
                self.assertEqual(p['repair_issue']['observations'][0]['execution']['command'][-1],'--i2r-benchmark')
                return {'edits':[{'file':'src/lib.rs','old':'h()+0','new':'h()+1'}],
                        'repair_hypothesis':{'cause':'wrong offset in f','evidence':'kernel returns 1 instead of 2','change':'add source offset','prediction':'same kernel input returns 2'}}
            return accept(p,c)
        with tempfile.TemporaryDirectory() as d:
            w=Path(d);project=w/'testing';project.mkdir();(project/'Model.thy').write_text('test');(project/'Kernel.thy').write_text('test')
            reference=w/'reference';reference.write_text('#!/bin/sh\nwhile read x; do echo "2 2 2"; done\n');reference.chmod(0o755)
            refs={'ocaml':{'binary':str(reference)},'stage2':{'binary':str(reference)}}
            save(w/'regressions.json',[])
            with patch('i2r_agent.segmented_v8.ask',side_effect=ask),patch('i2r_agent.test_connector.connect',return_value=({'src/lib.rs':CONNECTOR},'fixture')) as connector:
                attempts,done=search(b,project,c,provider,w,Executor(w/'commands'),refs,[[9,1,2]],[],w/'regressions.json',lambda _:None)
            actions=[a['action_phase'] for a in attempts]
            i=max(i for i,a in enumerate(actions) if a=='repair');self.assertEqual(actions[i+1],'repair_replay')
            self.assertEqual(done[0]['status'],'passed');self.assertEqual(connector.call_count,1)
            self.assertEqual(done[0]['repair_issues'][0]['status'],'replayed_passed')

    def test_measured_non_improvement_restores_verified_incumbent(self):
        self.strategy_optimization(False)

    def test_measured_improvement_accepts_strategy_with_candidate(self):
        self.strategy_optimization(True)

    def strategy_optimization(self,accepted):
        c=cfg();c['segmented']['support_tests']=False;c['segmented']['development_performance']=True
        b=source();b['case']='list-index';b['workflow']='segmented-v8'
        provider=Mock();provider.calls=0;provider.usage={}
        def ask(pv,conf,path,p,analysis=False):
            phase=p['controller_state']['phase']
            if phase=='generate':
                n=p['unit']['members'][0].rsplit('.',1)[-1]
                return {'files':{'src/lib.rs':p['current_files']['src/lib.rs']+'\npub fn '+n+'()->u128{'+('1' if n=='h' else 'h()+1')+'}'},'mapping':[mapping(n)]}
            if phase=='performance_review':
                analysis={'classification':'rust_expression','evidence':'fixture measured hotspot','source_correspondence':'A.f','reason':'test a local implementation rewrite','next_step':'compare'}
                if p['optimization_attempts']:
                    return {'action':'finish_optimization','performance_analysis':analysis,'reason':'attempt had no measured benefit'}
                return {'action':'optimize','performance_analysis':analysis,
                        'optimization_hypothesis':{'cause':'temporary shape','evidence':'fixture','change':'local expression','prediction':'lower time'},
                        'strategy_version':p['controller_state']['strategy_version'],
                        'strategy_updates':[{'id':'optimized-ownership','expected_revision':0,'kind':'ownership','sources':['constant:A.f'],'choice':'local owned temporary','conditions':[],'reason':'equivalent local expression','status':'adopted','links':['mapping']}],
                        'edits':[{'file':'src/lib.rs','old':'h()+1','new':'{let value=h();value+1}'}]}
            return accept(p,c)
        def measure(*args,**kwargs):
            return [{'summary':{'parent':{'median_ns':100,'samples':[99,100,101]},'candidate':{'median_ns':105,'samples':[104,105,106]}}}]
        with tempfile.TemporaryDirectory() as d:
            w=Path(d);project=w/'testing';project.mkdir();(project/'Model.thy').write_text('test');(project/'Kernel.thy').write_text('test')
            reference=w/'reference';reference.write_text('#!/bin/sh\nwhile read x; do echo "2 2 2"; done\n');reference.chmod(0o755)
            refs={'ocaml':{'binary':str(reference)},'stage2':{'binary':str(reference)}};save(w/'regressions.json',[])
            with patch('i2r_agent.segmented_v8.ask',side_effect=ask),patch('i2r_agent.test_connector.connect',return_value=({'src/lib.rs':CONNECTOR},'fixture')),patch('i2r_agent.v8_performance.measure',side_effect=measure),patch('i2r_agent.v8_performance.compare',return_value={'accept':accepted,'reason':'mock paired comparison'}),patch('i2r_agent.v8_performance.profile',return_value={'status':'measured','workloads':[]}),patch('i2r_agent.v8_performance.boundaries',return_value={'status':'measured'}):
                attempts,done=search(b,project,c,provider,w,Executor(w/'commands'),refs,[[9,1,2]],[],w/'regressions.json',lambda _:None)
            self.assertEqual(done[0]['status'],'passed')
            self.assertIn('{let value=h();value+1}' if accepted else 'h()+1',done[0]['files']['src/lib.rs'])
            self.assertEqual(done[0]['optimization_attempts'][0]['status'],'accepted' if accepted else 'reverted')
            from i2r_agent.implementation_strategy import project
            self.assertEqual(any(r['id']=='optimized-ownership' for r in project(done[0])),accepted)
            if not accepted:self.assertTrue(done[0]['strategy_archives'])


if __name__=='__main__':unittest.main()
