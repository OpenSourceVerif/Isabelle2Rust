"""Real driver checks keep kernel behavior without incidental measurement."""
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from i2r_agent import baselines, references, test_connector
from i2r_agent.common import config


class BehaviorOnly(unittest.TestCase):
    def test_real_candidate_driver_executes_all_kernel_functions_without_clock(self):
        library='''mod i2r_harness {
 pub fn observe(x:&[u128])->Vec<u128>{vec![x[0]+100]}
 pub fn benchmark_prepare(x:&[u128])->u128{x[0]+1}
 pub fn benchmark_run(x:u128)->u128{x+2}
 pub fn benchmark_encode(x:u128)->Vec<u128>{vec![x+3]}
}
'''
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for timing in (False,True):
                source=test_connector.driver('native-u128',timing=timing)
                self.assertEqual('Instant::now' in source,timing)
                (root/'main.rs').write_text(library+source)
                subprocess.run([str(Path(config()['tools']['cargo']).with_name('rustc')),str(root/'main.rs'),'-o',str(root/'driver')],check=True,capture_output=True)
                def run(*args):return subprocess.run([str(root/'driver'),*args],input='1\n',text=True,capture_output=True,check=True)
                ordinary=run();kernel=run('--i2r-kernel-check')
                self.assertEqual(ordinary.stdout,'101\n');self.assertEqual(kernel.stdout,'7\n')
                self.assertEqual(ordinary.stderr,'');self.assertEqual(kernel.stderr,'')
                if timing:
                    measured=run('--i2r-benchmark')
                    self.assertEqual(measured.stdout,'7\n');self.assertIn('I2R_KERNEL_NS ',measured.stderr)
                else:
                    self.assertNotIn('I2R_KERNEL_NS',source)
                    self.assertNotIn('--i2r-benchmark',source)

    def test_all_connection_materializers_propagate_correctness_mode(self):
        from i2r_agent import segmented_run, translation_workflow
        from i2r_agent.segmented_config import rust_config
        from test_segmented_workflow import cfg
        c=cfg();c['translation']={'correctness_only':True};c['testing']['transport']='native-u128';rc=rust_config({},c)
        files={'src/lib.rs':'// connector placeholder'}
        with tempfile.TemporaryDirectory() as tmp:
            for i,factory in enumerate([segmented_run.connection,translation_workflow.connection]):
                crate=Path(tmp)/str(i);crate.mkdir()
                harness=factory(crate,files,rc,c)
                text=(harness/'src/main.rs').read_text()
                self.assertNotIn('Instant',text)
                self.assertIn('--i2r-kernel-check',text)
            crate=Path(tmp)/'legacy';crate.mkdir()
            harness=test_connector.materialize(crate,files,{},c)
            self.assertNotIn('Instant',(harness/'src/main.rs').read_text())

    def test_real_ocaml_behavior_driver_has_no_timer_linkage(self):
        cfg=config()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'reference.ml').write_text('''module Candidate = struct
 let nat_of_integer x = x
 let integer_of_nat x = x
 let observe xs = List.map (fun x -> Z.add x (Z.of_int 100)) xs
 let kernel_prepare xs = List.map (fun x -> Z.add x Z.one) xs
 let kernel_run xs = List.map (fun x -> Z.add x (Z.of_int 2)) xs
 let kernel_encode xs = List.map (fun x -> Z.add x (Z.of_int 3)) xs
end
''')
            source=references.ocaml_driver('Candidate',timing=False)
            self.assertNotIn('timer_',source);self.assertNotIn('I2R_KERNEL_NS',source)
            self.assertNotIn('--i2r-benchmark',source)
            (root/'main.ml').write_text(source)
            import os
            env={**os.environ,'PATH':str(Path(cfg['tools']['ocamlfind']).parent)+os.pathsep+os.environ.get('PATH','')}
            subprocess.run([cfg['tools']['ocamlfind'],'ocamlopt','-package','zarith','-linkpkg','-o','driver','reference.ml','main.ml'],cwd=root,env=env,check=True,capture_output=True)
            for args,expected in [((),'101\n'),(('--i2r-kernel-check',),'7\n')]:
                r=subprocess.run([str(root/'driver'),*args],input='1\n',text=True,capture_output=True,check=True)
                self.assertEqual(r.stdout,expected);self.assertEqual(r.stderr,'')

    def test_rust_reference_clock_and_cache_identity_follow_mode(self):
        calls={name:('Candidate',False) for name in ['kernel_prepare','kernel_run','kernel_encode']}
        source=references.rust_driver('Candidate',True,kernel=True,kernel_modules=calls,timing=False)
        self.assertNotIn('Instant',source);self.assertNotIn('I2R_KERNEL_NS',source)
        self.assertNotIn('--i2r-benchmark',source);self.assertIn('--i2r-kernel-check',source)
        cfg=config()
        with patch('i2r_agent.baselines.tool_sources.manifest',return_value={}),patch('i2r_agent.baselines.implementation_identity',return_value={}):
            measured=baselines.identity('example',{'source_hashes':{}},cfg)
            cfg.setdefault('translation',{})['correctness_only']=True
            behavioral=baselines.identity('example',{'source_hashes':{}},cfg)
        self.assertTrue(measured['timing_enabled']);self.assertFalse(behavioral['timing_enabled'])
        self.assertNotEqual(baselines.fingerprint(measured),baselines.fingerprint(behavioral))

    def test_correctness_connector_request_preserves_source_contract_without_timing_review(self):
        cfg=config();cfg.setdefault('translation',{})['correctness_only']=True
        prompt=test_connector.system_prompt(cfg,knowledge=True)
        self.assertNotIn('Timing knowledge:',prompt)
        self.assertNotIn('before timing',prompt)
        self.assertNotIn('call/measurement',prompt)
        self.assertIn('source kernel_run',prompt)
        self.assertIn('algorithm_issue',prompt)
        self.assertIn('No long notes, boundary_review',prompt)


if __name__=='__main__':unittest.main()
