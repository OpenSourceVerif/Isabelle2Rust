from workflow_fixture import compile_until_source
import tempfile,unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock,patch
from i2r_agent import semantic_components as cpt,translation_workflow as runner
from i2r_agent.common import Failure,Executor,save
from test_segmented_workflow import source,mapping
from test_translation_workflow import cfg,accept


def group(name,*members):return {'name':name,'purpose':'coherent '+name,'members':list(members)}

class SemanticComponentTests(unittest.TestCase):
    def test_component_grouping_is_validated_from_same_global_adaptation_reply(self):
        from i2r_agent.segmented_context import analyze
        conf=cfg();conf['translation'].update(unit_policy='semantic-components',small_program_max_entities=1)
        bundle=source();bundle['workflow']='source-translation';seen=[]
        def ask(pv,c,path,p,analysis=False):
            seen.append(p.get('task_kind','global_analysis'))
            self.assertEqual(p['component_grouping']['mode'],'joint_analysis')
            return {'opportunities':[],'boundaries':[],'rust_config':{},'analysis_coverage':list(p['executable_graph']['edges']),
                    'components':[group('algorithm','constant:A.h','constant:A.f')],
                    'semantic_obligations':[{'source':'constant:A.h','operation':'constant one','rust_representation':'u128','conditions':['checked'],'boundary_cases':['one'],'verification':'source literal'}]}
        with tempfile.TemporaryDirectory() as d,patch('i2r_agent.segmented_context.ask',side_effect=ask):
            out,record=analyze(bundle,conf,Mock(),Path(d))
        self.assertEqual(seen,['global_analysis'])
        self.assertEqual(out['segmentation']['grouping_decision']['method'],'joint_analysis_components')
        self.assertEqual(len(out['segmentation']['units']),1);self.assertEqual(record['units'],1)

    def test_groups_preserve_every_entity_and_dependency_order(self):
        model=source()['source_model'];plan=cpt.compose(model,[],[group('algorithm','constant:A.h','constant:A.f')])
        self.assertEqual(len(plan['units']),1)
        self.assertEqual(set(plan['owner']),set(model['entities']))
        self.assertEqual(plan['source_edges']['constant:A.f'],['constant:A.h'])
        self.assertEqual(len(plan['atomic_units']),2)

    def test_missing_duplicate_unknown_and_cycle_split_are_rejected(self):
        model=source()['source_model']
        for gs in [[group('missing','constant:A.h')],[group('one','constant:A.h'),group('two','constant:A.h','constant:A.f')],
                   [group('unknown','constant:A.h','constant:A.f','constant:Unknown')]]:
            with self.assertRaises(Failure):cpt.compose(model,[],gs)
        model['entities']['constant:A.h']['dependencies']=['constant:A.f']
        with self.assertRaises(Failure):cpt.compose(model,[],[group('h','constant:A.h'),group('f','constant:A.f')])

    def test_grouping_cannot_introduce_cycle_in_acyclic_source(self):
        model=source()['source_model'];model['entities']['constant:A.g']={**deepcopy(model['entities']['constant:A.f']),'id':'constant:A.g','name':'A.g','dependencies':['constant:A.f']};model['entries']=['constant:A.g']
        with self.assertRaises(Failure):cpt.compose(model,[],[group('ends','constant:A.h','constant:A.g'),group('middle','constant:A.f')])

    def test_adapted_helper_has_exactly_one_explicit_owner(self):
        model=source()['source_model'];model['entities']['constant:Library.add']={'id':'constant:Library.add','name':'Library.add','kind':'constant','dependencies':[],'source_type':{}}
        model['entities']['constant:A.h']['dependencies']=['constant:Library.add']
        boundary={'source':'constant:Library.add','kind':'native','basis':'exact arithmetic','conditions':['all inputs']}
        plan=cpt.compose(model,[boundary],[group('numeric','constant:Library.add'),group('algorithm','constant:A.h','constant:A.f')])
        numeric=plan['owner']['constant:Library.add'];business=plan['owner']['constant:A.h']
        self.assertEqual(plan['units'][business]['dependencies'],[numeric])
        self.assertEqual(plan['order'],[numeric,business]);self.assertEqual(plan['units'][business]['boundary_sources'],[])

    def test_local_repair_retains_sibling_evidence_and_only_dirties_actual_consumers(self):
        b=source();model=b['source_model'];model['entities']['constant:A.g']={**deepcopy(model['entities']['constant:A.h']),'id':'constant:A.g','name':'A.g'}
        model['entries'].append('constant:A.g')
        p=cpt.compose(model,[],[group('helpers','constant:A.h','constant:A.g'),group('entry','constant:A.f')]);b['segmentation']=p
        s={'bundle':b,'partition':p,'files':{'src/lib.rs':'pub fn h()->u128{1}\npub fn g()->u128{7}\npub fn f()->u128{h()+1}\n'},'mapping':[mapping(x) for x in ['h','g','f']],
           'rust_config':b['rust_config'],'completed':p['order'],'reviews':{u:{'version':'old'} for u in p['order']},'source_reviews':{n:{'evidence':'original-'+n} for n in p['owner']},'transactions':[],'phase':'repair','unit':p['owner']['constant:A.h']}
        conf=cfg()
        with tempfile.TemporaryDirectory() as d:
            after=runner.apply_transaction(s,{'files':{'src/lib.rs':s['files']['src/lib.rs'].replace('{1}','{2}')}},conf,Path(d))
        self.assertEqual(set(after['source_reviews']),{'constant:A.g'})
        self.assertEqual(after['dirty_sources'][p['owner']['constant:A.h']],['constant:A.h'])
        self.assertEqual(after['dirty_sources'][p['owner']['constant:A.f']],['constant:A.f'])
        after.update(phase='refine',unit=p['owner']['constant:A.h'])
        self.assertNotIn('constant:A.g',runner.review_required(after,'refine',conf)[0])
        # A second failed repair can touch a sibling after its component was
        # removed from completed. Its earlier evidence must still be invalidated.
        after['phase']='repair'
        with tempfile.TemporaryDirectory() as d:
            again=runner.apply_transaction(after,{'files':{'src/lib.rs':after['files']['src/lib.rs'].replace('{7}','{8}')}},conf,Path(d))
        self.assertEqual(again['source_reviews'],{})
        self.assertEqual(again['dirty_sources'][p['owner']['constant:A.h']],['constant:A.g','constant:A.h'])

    def test_real_component_compile_repair_reviews_only_changed_member(self):
        conf=cfg();conf['translation']['unit_policy']='semantic-components';conf['segmented']['support_tests']=False
        b=source();b['workflow']='source-translation';b['segmentation']=cpt.compose(b['source_model'],[],[group('pair','constant:A.h','constant:A.f')])
        provider=Mock();provider.calls=0;provider.usage={};reviews=[]
        def ask(pv,c,path,p,analysis=False):
            phase=p['controller_state']['phase']
            if phase=='generate':return {'files':{'src/lib.rs':'pub fn h()->u128{1}\npub fn f()->u128{missing()+1}\n'},'mapping':[mapping('h'),mapping('f')]}
            if phase=='repair':return {'files':{'src/lib.rs':p['current_files']['src/lib.rs'].replace('missing()','h()')},'repair_hypothesis':{'cause':'wrong function name','evidence':'compiler unresolved missing','change':'call h','prediction':'original build passes'}}
            if phase=='refine':reviews.append(p['review_scope']['members_to_review'])
            return accept(p,conf)
        with tempfile.TemporaryDirectory() as d:
            w=Path(d);save(w/'regressions.json',[])
            with patch('i2r_agent.translation_workflow.ask',side_effect=ask):
                attempts,done=compile_until_source(b,None,conf,provider,w,Executor(w/'commands'),None,[],[],w/'regressions.json',lambda _:None)
            self.assertEqual(done[0]['status'],'active')
            self.assertEqual(reviews,[['constant:A.f','constant:A.h'],['constant:A.f']])
            self.assertEqual(len([a for a in attempts if a['action_phase']=='generate']),1)
            self.assertEqual(next(a for a in attempts if a['action_phase']=='repair_replay')['original_replay']['status'],'passed')
