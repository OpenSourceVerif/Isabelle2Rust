import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
from copy import deepcopy
from i2r_agent.common import ROOT,config,merge,read,save,Executor,Failure
from i2r_agent.segmented_config import configure,materialize,rust_config
from i2r_agent import repair_controller as repair, performance_search as perf
from i2r_agent.translation_workflow import search,connector_identity
from i2r_agent.segmented_run import connection,compile_crate
from i2r_agent.test_obligations import validate_obligations
from test_segmented_workflow import source,mapping,route_reviews


def cfg():
    c=configure(merge(config(),read(Path(__file__).parent/'fixtures/translation-config.json')['base']))
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


class TranslationTests(unittest.TestCase):
    def test_changes_do_not_reset_original_failure_budget(self):
        c=cfg();c['translation']['repair_stall_limit']=3;s={}
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


if __name__=='__main__':unittest.main()
