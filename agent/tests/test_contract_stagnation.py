import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from i2r_agent.common import config, Failure
from i2r_agent.pipeline import search


class ContractStagnationTests(unittest.TestCase):
    def run_search(self, changing_mapping):
        cfg=config();cfg['performance']['enabled']=False
        provider=Mock();provider.phase_calls={'generation':0};provider.usage={}
        plans=[{'id':'bad','strategy':'borrow'},{'id':'good','strategy':'move'}]
        seen=[]
        def generate(bundle,cfg,provider,directory,*args):
            provider.phase_calls['generation']+=1
            branch=bundle['ownership_plan']['id'];seen.append(branch)
            n=seen.count(branch)
            source='fixed' if not changing_mapping else str(n)
            return {'files':{'src/lib.rs':'pub fn f(){}'},'prompt':'test','crate':str(directory),
                    'translation_plan':{},'mapping':[{'source':source if branch=='bad' else 'valid'}],
                    'adaptation_usage':[],'ownership_changes':'','notes':''}
        def contract(plan,files,mapping,usage,bundle):
            if bundle['ownership_plan']['id']=='bad' and (not changing_mapping or seen.count('bad')<4):
                raise Failure('plan_contract_failed','Missing source correspondence',{'missing':['M.f']})
            return {'status':'passed'}
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp);updates=[]
            with patch('i2r_agent.generation.ownership_plans',return_value=plans), \
                 patch('i2r_agent.pipeline.generate',side_effect=generate), \
                 patch('i2r_agent.pipeline.candidate_contract',side_effect=contract), \
                 patch('i2r_agent.pipeline.compile_rust',return_value={'status':'passed','binary':'fake','checks':{}}):
                attempts,crate,binary=search({},None,cfg,provider,path,Mock(),None,[],[],path/'regressions.json',updates.append)
            branches=next(x['ownership_candidates'] for x in reversed(updates) if 'ownership_candidates' in x)
            return seen,branches,crate

    def test_identical_contract_failures_stop_without_discarding_passing_branch(self):
        seen,branches,crate=self.run_search(False)
        self.assertEqual(seen.count('bad'),3)
        self.assertEqual(seen.count('good'),1)
        self.assertEqual(branches[0]['status'],'stalled')
        self.assertEqual(branches[1]['status'],'passed')
        self.assertIsNotNone(crate)

    def test_changed_mapping_with_same_rust_keeps_repairing(self):
        seen,branches,crate=self.run_search(True)
        self.assertEqual(seen.count('bad'),4)
        self.assertTrue(all(b['status']=='passed' for b in branches))


if __name__=='__main__':unittest.main()
