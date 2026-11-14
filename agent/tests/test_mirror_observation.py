import json,tempfile,unittest,shutil
from pathlib import Path
from copy import deepcopy
from unittest.mock import Mock
from i2r_agent.common import read,Executor
from i2r_agent import observation_helpers as helpers,repair_controller
from i2r_agent.segmented_config import configure,materialize
from i2r_agent.translation_workflow import connection,compile_crate
from i2r_agent.segmented_support import execute as source_execute
from i2r_agent.validation import execute
from i2r_agent.test_connector import connect
from test_translation_workflow import cfg

FIXTURE=Path(__file__).parent/'fixtures/mirror-observation'

class MirrorObservation(unittest.TestCase):
    def setup_case(self):
        c=cfg();c['translation']['correctness_only']=True;c=configure(c)
        return c,read(FIXTURE/'candidate.json')

    def test_exact_helpers_and_interface_only_no_target_copy(self):
        c,s=self.setup_case();facts=helpers.material(FIXTURE,s['mapping'])
        self.assertEqual(facts['candidate_required_call'],'constant:Tree_Test.mirror')
        self.assertIn('x # preorder l @ preorder r',facts['external_observation_helpers'][0]['equations'])
        generated=helpers.generate(FIXTURE,s['files'],s['mapping'],c)
        self.assertEqual(generated['status'],'generated')
        self.assertIn('preorder(i2r_candidate::mirror(fixture(input)))',generated['files']['src/lib.rs'])
        self.assertNotIn('expected',generated['files']['src/lib.rs'])
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);shutil.copytree(FIXTURE,p/'project');project=p/'project'
            original=helpers.scenario_identity(project)
            (project/'Tree_Test.thy').write_text((project/'Tree_Test.thy').read_text().replace('x # preorder l @ preorder r','x # preorder r @ preorder l'))
            self.assertNotEqual(original,helpers.scenario_identity(project));self.assertFalse(helpers.material(project,s['mapping']))
            self.assertIsNone(helpers.generate(project,s['files'],s['mapping'],c))
        extra=s['mapping']+[{'source':'constant:Tree_Test.preorder','rust_item':'crate::preorder'}]
        self.assertFalse(helpers.material(FIXTURE,extra))
        bad={'src/lib.rs':s['files']['src/lib.rs'].replace('Node(Box<Tree<A>>, A, Box<Tree<A>>)','Node(A, Box<Tree<A>>, Box<Tree<A>>)')}
        self.assertIsNone(helpers.generate(FIXTURE,bad,s['mapping'],c))
        with tempfile.TemporaryDirectory() as d:
            provider=Mock()
            result,_=connect(FIXTURE,None,s['files'],s['mapping'],{'rust_config':s['rust_config']},c,provider,Path(d)/'connect')
            self.assertEqual(result,generated['files']);provider.call.assert_not_called()

    def test_real_candidate_source_tests_and_result_mutants(self):
        c,s=self.setup_case();frozen=read(FIXTURE/'frozen-tests.json')
        binding=helpers.generate(FIXTURE,s['files'],s['mapping'],c)['files']
        cases=[[],[0],[1,2,3],[7,0,7,2]]
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);ex=Executor(p/'commands')
            for label,code in [('original',s['files']['src/lib.rs']),
                ('identity','pub enum Tree<A>{Leaf,Node(Box<Tree<A>>,A,Box<Tree<A>>)} pub fn mirror<A>(t:Tree<A>)->Tree<A>{t}'),
                ('drop_result','pub enum Tree<A>{Leaf,Node(Box<Tree<A>>,A,Box<Tree<A>>)} pub fn mirror<A>(_t:Tree<A>)->Tree<A>{Tree::Leaf}')]:
                crate=materialize(p/label,{'src/lib.rs':code},s['rust_config'])
                support=source_execute(frozen,crate,s['rust_config'],c,ex)
                self.assertEqual(support['status'],'passed' if label=='original' else 'support_contract_failed')
                built=compile_crate(connection(crate,binding,s['rust_config'],c),s['rust_config'],c,ex,False)
                self.assertEqual(built['status'],'passed')
                for args in [(),('--i2r-kernel-check',)]:
                    outputs=execute(built['binary'],cases,ex,10,arguments=args)['outputs']
                    if label=='drop_result':self.assertNotEqual(outputs,cases)
                    else:self.assertEqual(outputs,cases) # Observation alone cannot reject identity; source tests do.

    def test_redirect_requires_actual_complete_current_evidence(self):
        s={'repair_issues':[],'connector_scenarios':{'Model.thy':'m','Tree_Test.thy':'t'},'connector':{'src/lib.rs':'binding'}}
        c,_=self.setup_case()
        issue=repair_controller.register(s,'compile',{'status':'connector_algorithm_defect'},{'roots':['mirror']},'compile')
        repair_controller.redirect_connector(s,'candidate1')
        suites=[{'kind':n,'status':'passed'} for n in ['fixed','kernel_fixed','generated_differential','kernel_generated_differential']]
        names=[x['kind'] for x in suites]
        for version,compiled,actual,scenarios in [('other',{'status':'passed'},suites,s['connector_scenarios']),
            ('candidate1',{'status':'compile_failed'},suites,s['connector_scenarios']),
            ('candidate1',{'status':'passed'},suites[:-1],s['connector_scenarios']),
            ('candidate1',{'status':'passed'},[{**x,'status':'failed'} for x in suites],s['connector_scenarios']),
            ('candidate1',{'status':'passed'},suites,{'Model.thy':'changed'})]:
            trial=deepcopy(s);trial['connector_scenarios']=scenarios
            repair_controller.close_redirected_connector(trial,version,compiled,actual,names,'evidence')
            self.assertEqual(trial['repair_issues'][0]['status'],'open')
        repair_controller.close_redirected_connector(s,'candidate1',{'status':'passed'},suites,names,'actual-test-attempt')
        self.assertEqual(issue['status'],'verified_passed')
        unrelated=deepcopy(s);unrelated['repair_issues'][0].update(status='open',original={'status':'plan_contract_failed'})
        repair_controller.close_redirected_connector(unrelated,'candidate1',{'status':'passed'},suites,names,'evidence')
        self.assertEqual(unrelated['repair_issues'][0]['status'],'open')
