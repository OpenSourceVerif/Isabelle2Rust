import tempfile
import unittest
from pathlib import Path
from i2r_agent.common import Failure
from i2r_agent.timing_v2 import Session, summarize, batch_cap, DEFAULTS

class TimingProtocolTests(unittest.TestCase):
    def fake(self, root, body):
        p=root/'fake';p.write_text('#!/usr/bin/env python3\n'+body);p.chmod(0o755);return p

    def test_rejects_microsecond_clock(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);binary=self.fake(root,'print("V2_CLOCK 1000 1000",flush=True)\n')
            with self.assertRaises(Failure) as error:Session(binary,root/'logs')
            self.assertEqual(error.exception.code,'clock_resolution_insufficient')

    def test_rejects_missing_results_and_zero_duration(self):
        for response in ['V2 123 1','V2 0 2']:
            with self.subTest(response=response),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp)
                binary=self.fake(root,'import sys\nprint("V2_CLOCK 42 42",flush=True)\nfor line in sys.stdin:\n sys.stdin.readline();sys.stdin.readline();print('+repr(response)+',flush=True)\n')
                with Session(binary,root/'logs') as session:
                    with self.assertRaises(Failure):session.batch(2,[1],[1],'sample')

    def test_one_process_serves_multiple_batches(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            binary=self.fake(root,'import sys\nprint("V2_CLOCK 42 83",flush=True)\nfor line in sys.stdin:\n n=int(line.split()[1]);x=sys.stdin.readline();y=sys.stdin.readline();assert x==y;print("V2 1000",n,flush=True)\n')
            with Session(binary,root/'logs') as session:
                pid=session.process.pid
                self.assertEqual(session.batch(4,[2],[2],'warmup')['output_checks'],4)
                self.assertEqual(session.batch(4,[3],[3],'sample')['per_call_ns'],250)
                self.assertEqual(session.process.pid,pid)

    def test_summary_weights_processes_equally(self):
        result=summarize([{'samples':[10,10,10],'warmup':{'stable':True}},
                          {'samples':[30],'warmup':{'stable':False}}])
        self.assertEqual(result['median_ns'],20)
        self.assertEqual(result['unstable_processes'],1)
        self.assertEqual(result['independent_processes'],2)

    def test_large_inputs_reduce_retained_batch_capacity(self):
        self.assertLess(batch_cap(list(range(1024)),DEFAULTS),batch_cap([1],DEFAULTS))
        self.assertGreaterEqual(batch_cap([2**100000],DEFAULTS),1)

class TimingPublicationTests(unittest.TestCase):
    def test_partial_publication_does_not_replace_default(self):
        from i2r_agent.common import save
        from i2r_agent.timing_v2_workbench import apply
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            save(root/'data/baselines/runs/timing-v2/active.json',{'status':'running','protocol':'kernel-v2'})
            self.assertIsNone(apply({},root))

    def test_changed_evidence_does_not_replace_default(self):
        from i2r_agent.common import save
        from i2r_agent.timing_v2_workbench import apply
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'result.json';save(source,{'status':'passed'})
            save(root/'data/baselines/runs/timing-v2/active.json',{'status':'complete','protocol':'kernel-v2',
                 'cases':[{'path':str(source),'sha256':'wrong'}]})
            self.assertIsNone(apply({},root))

    def test_new_measurement_is_separate_from_historical_view(self):
        from i2r_agent.common import save,digest
        from i2r_agent.timing_v2_workbench import apply
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);binary=root/'binary';binary.write_text('binary')
            build={'id':'b:ocaml','kind':'baseline','round_id':'baseline','numeric_profile':'shared',
                   'source_hashes':{},'artifact_hashes':{str(binary):digest(binary)},'binary':str(binary)}
            sample={'median_ns':10,'min_ns':8,'max_ns':14,'samples':[8,10,14],
                    'process_min_ns':8,'process_max_ns':14,'independent_processes':3,'unstable_processes':0,'mad_ns':2}
            result=root/'result.json';save(result,{'case':'case','status':'passed','protocol':{'version':'kernel-v2'},
                'builds':[build],'identity':{'binaries':{'b:ocaml':digest(binary)}},'workload':[1],
                'summary':{'b:ocaml':sample},'processes':{'b:ocaml':[{'warnings':[]}]},'measured_at':'new'})
            save(root/'data/baselines/runs/timing-v2/active.json',{'id':'v2','status':'complete','protocol':'kernel-v2',
                 'cases':[{'path':str(result),'sha256':digest(result)}]})
            old={'protocol':{'version':'kernel-v1'},'rows':[{'median_ns':1000}]}
            cases={'case':{'implementations':[{'implementation_id':'b:ocaml','kind':'baseline','measurement':{'median_ns':1000}}],
                           'performance_views':[old]}}
            self.assertEqual(apply(cases,root),'kernel-v2')
            self.assertEqual(cases['case']['performance_views'][0],old)
            self.assertEqual(cases['case']['performance_views'][1]['protocol']['version'],'kernel-v2')
            self.assertEqual(cases['case']['implementations'][0]['legacy_measurement']['median_ns'],1000)
            self.assertEqual(cases['case']['implementations'][0]['measurement']['median_ns'],10)

class TimingDriverConstructionTests(unittest.TestCase):
    def test_rust_batch_keeps_retention_and_encoding_outside_timer(self):
        from i2r_agent.test_connector import driver
        from i2r_agent.timing_drivers import rust
        text=rust(driver('native-u128'))
        batch=text.split('fn batch_v2_main()',1)[1]
        self.assertLess(batch.index('Vec::with_capacity(n)'),batch.index('let start='))
        self.assertLess(batch.index('for prepared in inputs.by_ref()'),batch.index('let elapsed='))
        self.assertGreater(batch.index('benchmark_encode(result)'),batch.index('let elapsed='))
        self.assertIn('std::hint::black_box(benchmark_run(prepared))',batch)
        self.assertIn('assert_eq!(words.join(" "),expected)',batch)

    def test_scala_single_line_result_signature(self):
        from i2r_agent.timing_drivers import scala
        text=scala('def kernel_run(p : (nat, nat)) : nat = { p._1 }')
        self.assertIn('new Array[nat](n)',text)
        self.assertNotIn('Array[nat =',text)


class TimingReuseTests(unittest.TestCase):
    def completed_measurement(self,root):
        from unittest.mock import patch
        from i2r_agent.timing_v2 import measure_group
        binary=TimingProtocolTests().fake(root,'import sys\nprint("V2_CLOCK 42 42",flush=True)\nfor line in sys.stdin:\n n=int(line.split()[1]);sys.stdin.readline();sys.stdin.readline();print("V2 1000",n,flush=True)\n')
        builds=[{'id':'candidate','work':str(root/'build'),'binary':str(binary)}]
        options={**DEFAULTS,'processes':1,'samples_per_process':1,'target_batch_ns':100,
                 'warmup_min_seconds':0,'warmup_max_seconds':0}
        with patch('builtins.print'):
            result=measure_group('sample',builds,[1],[1],options,root/'measurement')
        return builds,options,result

    def test_completed_measurement_keeps_its_date_and_does_not_restart(self):
        from unittest.mock import patch
        from i2r_agent.timing_v2 import measure_group
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);builds,options,first=self.completed_measurement(root)
            with patch('i2r_agent.timing_v2.Session',side_effect=AssertionError('must reuse')):
                second=measure_group('sample',builds,[1],[1],options,root/'measurement')
            self.assertEqual(first,second)

    def test_changed_expected_output_invalidates_resume(self):
        from i2r_agent.timing_v2 import measure_group
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);builds,options,_=self.completed_measurement(root)
            with self.assertRaises(Failure) as error:
                measure_group('sample',builds,[1],[2],options,root/'measurement')
            self.assertEqual(error.exception.code,'timing_resume_identity_changed')

    def test_campaign_reuses_original_timestamp_in_current_registry(self):
        from unittest.mock import patch
        from i2r_agent.common import save,read,config
        from i2r_agent.timing_v2_publish import register_reference_measurements
        from i2r_agent.baselines import measure_once
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'measurement-v2.json'
            cfg=config();cfg['performance']['protocol']='kernel-v2'
            base={'id':'sample','case':'sample','references':{lang:{'sha256':lang,
                  'baseline_record':str(root/'frozen/baseline.json')} for lang in ['ocaml','stage2']}}
            save(root/'data/baselines/sample/baseline.json',base)
            m={'scope':'kernel','protocol':{'version':'kernel-v2','options':{}},'workload':[1],
               'builds':[{'id':'sample:'+lang,'language':lang,'baseline_id':'sample'} for lang in ['ocaml','stage2']],
               'summary':{'sample:'+lang:{'median_ns':42} for lang in ['ocaml','stage2']},
               'processes':{'sample:'+lang:[] for lang in ['ocaml','stage2']},
               'raw_samples':[{'implementation':'sample:ocaml','batch_ns':42}],
               'measured_at':'original-time','identity':{'controller':'original-controller'}}
            save(source,m)
            with patch('i2r_agent.timing_v2_publish.ROOT',root),patch('i2r_agent.baselines.ROOT',root), \
                 patch('i2r_agent.baselines.benchmark_key',return_value={'key':'v2'}), \
                 patch('i2r_agent.timing_v2_publish.benchmark_key',return_value={'key':'v2'}), \
                 patch('i2r_agent.performance.benchmark',side_effect=AssertionError('must reuse')):
                paths=register_reference_measurements([(source,m)],cfg)
                result=measure_once(base,[1],[1],cfg,None)
            self.assertEqual(result['measured_at'],'original-time')
            self.assertEqual(result['acquisition'],'reused')
            self.assertEqual(result['campaign_identity']['controller'],'original-controller')
            self.assertEqual(set(result['summary']),{'ocaml','stage2'})
            self.assertEqual(read(paths[0])['raw_samples'][0]['implementation'],'ocaml')
            self.assertFalse((root/'frozen').exists())
