import tempfile
import unittest
from pathlib import Path
from i2r_agent.common import Failure
from i2r_agent.kernel_timing import Session, summarize, batch_cap, DEFAULTS

class TimingProtocolTests(unittest.TestCase):
    def test_williams_order_balances_positions_and_predecessors(self):
        from collections import Counter
        from i2r_agent.kernel_timing import process_order
        for n in [2,3,4,6]:
            with self.subTest(implementations=n):
                rounds=n if n%2==0 else 2*n
                orders=[process_order(list(range(n)),r,'williams') for r in range(rounds)]
                for pos in range(n):
                    self.assertEqual(Counter(row[pos] for row in orders),Counter({i:rounds//n for i in range(n)}))
                pairs=Counter((a,b) for row in orders for a,b in zip(row,row[1:]))
                self.assertEqual(pairs,Counter({(a,b):rounds//n for a in range(n) for b in range(n) if a!=b}))

    def test_final_round_count_completes_balanced_cycles_after_aliases(self):
        from i2r_agent.kernel_timing import balanced_rounds
        self.assertEqual([balanced_rounds(n) for n in range(1,7)],[6,6,6,8,10,6])

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
    def completed_measurement(self,root,overrides=None):
        from unittest.mock import patch
        from i2r_agent.kernel_timing import measure_group
        binary=TimingProtocolTests().fake(root,'import sys\nprint("V2_CLOCK 42 42",flush=True)\nfor line in sys.stdin:\n n=int(line.split()[1]);sys.stdin.readline();sys.stdin.readline();print("V2 1000",n,flush=True)\n')
        builds=[{'id':'candidate','work':str(root/'build'),'binary':str(binary)}]
        options={**DEFAULTS,'processes':1,'samples_per_process':1,'target_batch_ns':100,
                 'warmup_min_seconds':0,'warmup_max_seconds':0,**(overrides or {})}
        with patch('builtins.print'):
            result=measure_group('sample',builds,[1],[1],options,root/'measurement')
        return builds,options,result

    def test_short_batches_use_fixed_extra_samples_and_retain_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            _,_,result=self.completed_measurement(Path(tmp),{'short_batch_samples':40})
            measured=result['processes']['candidate'][0]
            self.assertEqual(measured['sample_count'],40)
            self.assertEqual(len(measured['raw_samples']),40)
            self.assertIn('batch_too_close_to_clock_resolution',measured['warnings'])
            self.assertGreater(measured['timer_probe_fraction'],.01)

    def test_completed_measurement_keeps_its_date_and_does_not_restart(self):
        from unittest.mock import patch
        from i2r_agent.kernel_timing import measure_group
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);builds,options,first=self.completed_measurement(root)
            with patch('i2r_agent.kernel_timing.Session',side_effect=AssertionError('must reuse')):
                second=measure_group('sample',builds,[1],[1],options,root/'measurement')
            self.assertEqual(first,second)

    def test_changed_expected_output_invalidates_resume(self):
        from i2r_agent.kernel_timing import measure_group
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);builds,options,_=self.completed_measurement(root)
            with self.assertRaises(Failure) as error:
                measure_group('sample',builds,[1],[2],options,root/'measurement')
            self.assertEqual(error.exception.code,'timing_resume_identity_changed')
