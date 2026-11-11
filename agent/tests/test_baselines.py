import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from i2r_agent.baselines import acquire,measure_once,cached_outputs
from i2r_agent.common import Executor,Failure,read
from i2r_agent.validation import check_suite,reference_outputs


class BaselineTests(unittest.TestCase):
    def test_known_inputs_do_not_restart_references_and_candidates_still_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);binary=root/'ref'
            binary.write_text('#!/usr/bin/env python3\nimport sys\nfor line in sys.stdin:\n a=list(map(int,line.split())); print(a[1]+1)\n');binary.chmod(0o755)
            refs={k:{'binary':str(binary),'baseline_id':'test','outputs_path':str(root/'observations.json')} for k in ['ocaml','stage2']}
            ex=Executor(root/'commands');xs=[[0,0],[0,2],[0,0]]
            first=reference_outputs('ackermann',xs,refs,ex,5)
            self.assertEqual(ex.sequence,2)
            self.assertEqual(first['ocaml']['record']['new_unique_inputs'],2)
            second=reference_outputs('ackermann',xs,refs,ex,5)
            self.assertEqual(ex.sequence,2)
            self.assertEqual(second['stage2']['record']['reference_processes_started'],0)
            self.assertEqual(second['ocaml']['outputs'],[[1],[3],[1]])
            check=check_suite('ackermann',xs,str(binary),refs,ex,5,'candidate_regression')
            self.assertEqual(check['status'],'passed');self.assertEqual(ex.sequence,3)
            reference_outputs('ackermann',xs+[[0,3]],refs,ex,5)
            self.assertEqual(ex.sequence,5)

    def test_disagreeing_references_are_not_cached(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);refs={}
            for name,value in [('ocaml',1),('stage2',2)]:
                p=root/name;p.write_text('#!/usr/bin/env python3\nimport sys\nfor line in sys.stdin:print('+str(value)+')\n');p.chmod(0o755)
                refs[name]={'binary':str(p),'baseline_id':'test','outputs_path':str(root/'observations.json')}
            with self.assertRaises(Failure):reference_outputs('ackermann',[[0,0]],refs,Executor(root/'commands'),5)
            self.assertFalse((root/'observations.json').exists())

    def test_reference_build_reused_and_source_change_creates_new_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);binary=root/'executable';binary.write_text('binary');source=root/'source.rs';source.write_text('source')
            refs={k:{'binary':str(binary),'source':str(source)} for k in ['ocaml','stage1','stage2']}
            with patch('i2r_agent.baselines.identity',side_effect=lambda case,bundle,cfg:{'case':case,'sources':bundle}),patch('i2r_agent.references.prepare_references',return_value=refs) as prepare:
                a=acquire('case',root,{'x':'v1'},{},root/'work',None)
                b=acquire('case',root,{'x':'v1'},{},root/'work',None)
                self.assertEqual(a['id'],b['id']);self.assertEqual(b['acquisition'],'reused');self.assertEqual(prepare.call_count,1)
                c=acquire('case',root,{'x':'v2'},{},root/'work',None)
                self.assertNotEqual(a['id'],c['id']);self.assertEqual(prepare.call_count,2)
                Path(b['references']['ocaml']['binary']).write_text('changed')
                with self.assertRaises(Failure):acquire('case',root,{'x':'v1'},{},root/'work',None)

    def test_measurement_runs_once_per_workload(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);record={'id':'test','case':'test','references':{k:{'binary':k,'baseline_record':str(root/'baseline.json')} for k in ['ocaml','stage2']}}
            cfg={'performance':{'samples':7}}
            result={'summary':{},'raw_samples':[],'scope':'kernel','protocol':{'version':'kernel-v1','options':cfg['performance']}}
            with patch('i2r_agent.baselines.ROOT',root),patch('i2r_agent.baselines.benchmark_key',side_effect=lambda w,c:{'workload':w,'options':c['performance']}),patch('i2r_agent.performance.benchmark',return_value=result) as run:
                first=measure_once(record,[1],[1],cfg,None)
                second=measure_once(record,[1],[1],cfg,None)
                self.assertEqual(run.call_count,1);self.assertEqual(second['acquisition'],'reused')
                measure_once(record,[2],[2],cfg,None);self.assertEqual(run.call_count,2)

if __name__=='__main__':unittest.main()
