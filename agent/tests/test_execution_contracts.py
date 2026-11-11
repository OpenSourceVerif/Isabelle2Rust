import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from i2r_agent.common import Executor, Failure, config
from i2r_agent.generation import generate
from i2r_agent.performance import benchmark
from i2r_agent.planning import manifest, candidate_contract
from i2r_agent.provider import Provider
from i2r_agent.references import compile_rust, rust_driver
from test_planning import fixture


class ExecutionContracts(unittest.TestCase):
    def test_compiler_feedback_keeps_root_error_before_long_cascade(self):
        from i2r_agent.pipeline import feedback_for
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'out').write_text('');(root/'err').write_text('error[E0255]: root cause\n'+'cascade\n'*8000)
            result=feedback_for({'compilation':{'checks':{'build':{'stdout':str(root/'out'),'stderr':str(root/'err')}}}})
            self.assertTrue(result['compiler_diagnostics']['build'].startswith('error[E0255]'))
            self.assertEqual(result['compiler_diagnostics']['build'],(root/'err').read_text())
            self.assertIn('error[E0255]',result['first_compiler_errors']['build'])

    def test_resumed_provider_counts_interrupted_request_against_same_budget(self):
        raw={'choices':[{'finish_reason':'stop','message':{'content':'{}'}}],'usage':{'total_tokens':7}}
        with tempfile.TemporaryDirectory() as tmp, patch('i2r_agent.provider.credential',return_value='test'), patch('urllib.request.urlopen',return_value=io.BytesIO(json.dumps(raw).encode())):
            cfg=config();cfg['preprocessing']['max_plan_attempts']=1
            first=Provider(cfg,tmp);first.call('s','p',phase='preprocessing')
            resumed=Provider(cfg,tmp)
            self.assertEqual(resumed.calls,1);self.assertEqual(resumed.usage['total_tokens'],7)
            with self.assertRaises(Failure):resumed.call('s','p',phase='preprocessing')

    def test_ffi_support_and_echoed_root_survive_generation_contract(self):
        bundle,plan=fixture();support={'files':{'build.rs':'fn main() {}','native/a.c':'int f(void) {return 1;}','src/native.rs':'pub fn f() {}'},'root':'pub mod native;\n'}
        bundle.update(translation_plan=plan,loaded_adapter={'support':support,'before_target':{},'after_target':{}})
        reply={'files':{'src/lib.rs':'#![allow(dead_code)]\npub mod native;\npub fn observe() {}',**support['files']},
               'mapping':[{'source':'constant:M.observe','rust':'observe'},{'source':'type:Nat.nat','rust':'u128'}],
               'adaptation_usage':[{'decision':'nat','locations':['src/lib.rs'],'implementation':'native'}]}
        provider=Mock();provider.call.return_value=reply
        with tempfile.TemporaryDirectory() as tmp:
            out=generate(bundle,config(),provider,tmp)
            self.assertEqual(out['files']['src/lib.rs'].count('pub mod native;'),1)
            self.assertEqual(candidate_contract(plan,out['files'],out['mapping'],out['adaptation_usage'],bundle)['status'],'recorded')
            out['files'].pop('build.rs')
            with self.assertRaises(Failure):candidate_contract(plan,out['files'],out['mapping'],out['adaptation_usage'],bundle)

    def test_class_operation_uses_actual_reachable_instance_binding(self):
        from i2r_agent.adapters import instance_bindings
        instance={'id':'instance:nat:ord','statement':{'kind':'instance','type':'nat',
            'parameters':[{'name':'ord.less_eq','const':{'symbol':'constant:nat.less_eq'}}],'super_parameters':[]}}
        graph={'nodes':[instance]}
        direct={'operations':[{'source':'constant:nat.less_eq','application':{'status':'rendered','rust':'le(a,b)'}}]}
        rows,resolved=instance_bindings(graph,direct)
        self.assertEqual(resolved,{'constant:ord.less_eq'})
        self.assertEqual(rows[0]['implementation'],'constant:nat.less_eq')
        self.assertEqual(instance_bindings(graph,{'operations':[]})[1],set())

    def test_syntax_feedback_preserves_argument_holes_and_original_text(self):
        from i2r_agent.adapters import syntax_hints
        source='constant f (Rust) "!crate::Numeric::less_eq\'(_, _\')"'
        hints=syntax_hints(source)
        self.assertEqual(hints[0]['suggested_template'],"!crate::Numeric::less'_eq'(_, _')")
        self.assertIn('less_eq',source)
        self.assertEqual(syntax_hints('constant f (Rust) "!f\'(_, _\')"'),[])

    def test_stage_budgets_share_one_total_without_reset(self):
        raw={'choices':[{'finish_reason':'stop','message':{'content':'{}'}}]}
        with tempfile.TemporaryDirectory() as tmp, patch('i2r_agent.provider.credential',return_value='test'), patch('urllib.request.urlopen',side_effect=lambda *a,**k:io.BytesIO(json.dumps(raw).encode())):
            provider=Provider(config(),tmp)
            for _ in range(20):provider.call('s','p',phase='preprocessing')
            with self.assertRaises(Failure):provider.call('s','p',phase='preprocessing')
            for _ in range(50):provider.call('s','p',phase='generation')
            with self.assertRaises(Failure):provider.call('s','p',phase='source_optimization')
            self.assertEqual(provider.calls,70)
            self.assertEqual(provider.phase_calls['preprocessing'],20)

    def test_loaded_support_is_written_and_cannot_be_silently_changed(self):
        bundle,plan=fixture();support={'files':{'src/numbers.rs':'pub type Nat = u128;'},'root':'pub mod numbers;'}
        bundle.update(translation_plan=plan,loaded_adapter={'support':support,'before_target':{},'after_target':{}})
        provider=Mock();provider.call.return_value={'files':{'src/lib.rs':'#![allow(dead_code)]\npub fn observe() {}'}}
        with tempfile.TemporaryDirectory() as tmp:
            out=generate(bundle,config(),provider,tmp)
            self.assertTrue(out['files']['src/lib.rs'].startswith('#![allow(dead_code)]'))
            self.assertEqual((Path(tmp)/'src/numbers.rs').read_text(),support['files']['src/numbers.rs'])
            self.assertIn('dashu-int',(Path(tmp)/'Cargo.toml').read_text())
        provider.call.return_value['files']['src/numbers.rs']='pub type Nat = u64;'
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(Failure) as error:
            generate(bundle,config(),provider,tmp)
        self.assertEqual(error.exception.code,'plan_contract_failed')

    def test_no_wall_clock_fallback_when_kernel_marker_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);binary=root/'candidate'
            binary.write_text('#!/usr/bin/env python3\nimport sys\nfor line in sys.stdin:print(1)\n');binary.chmod(0o755)
            cfg=config();cfg['performance'].update(protocol='kernel-v1',warmups=0,samples=1,iterations=1)
            with self.assertRaises(Failure) as error:
                benchmark({'candidate':str(binary)},[1],[1],cfg,Executor(root/'commands'),root)
            self.assertEqual(error.exception.code,'kernel_timing_missing')

    def test_real_rust_timer_excludes_slow_preparation_and_encoding(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'src').mkdir();cfg=config();executor=Executor(root/'commands')
            (root/'Cargo.toml').write_text(manifest({}))
            (root/'src/lib.rs').write_text('''use dashu_int::UBig;
pub fn observe(x: &[UBig]) -> Vec<UBig> { x.to_vec() }
pub fn benchmark_prepare(x: &[UBig]) -> Vec<UBig> {
    std::thread::sleep(std::time::Duration::from_millis(60)); x.to_vec()
}
pub fn benchmark_run(x: Vec<UBig>) -> Vec<UBig> {
    std::thread::sleep(std::time::Duration::from_millis(1)); x
}
pub fn benchmark_encode(x: Vec<UBig>) -> Vec<UBig> {
    std::thread::sleep(std::time::Duration::from_millis(60)); x
}
''')
            (root/'src/main.rs').write_text(rust_driver('',kernel=True))
            compiled=compile_rust(root,cfg,executor)
            self.assertEqual(compiled['status'],'passed')
            cfg['performance'].update(protocol='kernel-v1',warmups=0,samples=1,iterations=2)
            # An integer larger than u128 verifies UBig transport independently.
            value=2**300+3
            result=benchmark({'candidate':compiled['binary']},[value],[value],cfg,executor,root)
            sample=result['raw_samples'][0]
            self.assertGreater(sample['execution']['seconds'],0.20)
            self.assertLess(sample['per_call_ns'],30_000_000)
            self.assertEqual(result['scope'],'kernel')
            # The batch protocol must exclude the same slow preparation and
            # encoding, including for values that cannot fit in u128.
            import time
            cfg['performance']['protocol']='kernel-v2'
            cfg['performance']['v2']={'processes':1,'samples_per_process':2,'max_batch':2,
                                     'target_batch_ns':10000000,'warmup_min_seconds':0,'warmup_max_seconds':0}
            started=time.monotonic()
            result=benchmark({'candidate':compiled['binary']},[value],[value],cfg,executor,root/'v2')
            self.assertGreater(time.monotonic()-started,0.6)
            self.assertEqual(result['protocol']['version'],'kernel-v2')
            self.assertTrue(all(s['per_call_ns']<30_000_000 for s in result['raw_samples']))
            self.assertTrue(all(s['output_checks']==2 for s in result['raw_samples']))


if __name__=='__main__':unittest.main()
