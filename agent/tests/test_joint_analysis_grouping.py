import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock,patch
from i2r_agent import semantic_components as cp,segmented_context as ctx,prepared_identity,segmented_v8
from i2r_agent.common import Failure,read
from i2r_agent.segmented_config import configure
from test_segmented_workflow import source
from test_semantic_components import group
from test_v8_workflow import cfg


class JointAnalysisGrouping(unittest.TestCase):
    def conf(self):
        c=cfg();c['v8']['unit_policy']='semantic-components';return c

    def reply(self,p,components=None,boundaries=None):
        r={'opportunities':[],'boundaries':boundaries or [],'rust_config':{},
           'analysis_coverage':list(p['executable_graph']['edges']),
           'semantic_obligations':[{'source':'constant:A.h','operation':'source literal','rust_representation':'u128','conditions':['checked'],'boundary_cases':['one'],'verification':'source equation'}]}
        if components is not None:r['components']=components
        return r

    def test_observed_isort_reports_all_extras_without_filtering_groups(self):
        from i2r_agent.common import ROOT
        f=read(ROOT/'tests/fixtures/isort_grouping_extra_members.json');groups=deepcopy(f['components'])
        with self.assertRaises(Failure) as caught:cp.from_analysis(f['model'],f['boundaries'],groups,self.conf())
        feedback=caught.exception.evidence['membership_feedback']
        self.assertEqual(feedback['unknown_ids'],['class:Orderings.order','class:Orderings.preorder','constant:HOL.False','constant:HOL.True'])
        self.assertEqual(len(feedback['required_ids']),10);self.assertEqual(groups,f['components'])
        revised=[{**g,'members':[n for n in g['members'] if n in feedback['required_ids']]} for g in groups]
        good=cp.from_analysis(f['model'],f['boundaries'],revised,self.conf())
        self.assertEqual(set(good['owner']),set(feedback['required_ids']))
        revised[0]['members'].append(revised[-1]['members'][0]);revised[-1]['members'].pop()
        # Moving an item may be a valid group change. Duplicating and missing
        # identities must still be rejected, with all problems in one response.
        revised[0]['members'].append(revised[0]['members'][0]);removed=revised[1]['members'].pop()
        with self.assertRaises(Failure) as error:cp.from_analysis(f['model'],f['boundaries'],revised,self.conf())
        details=error.exception.evidence['membership_feedback']
        self.assertIn(removed,details['missing_ids']);self.assertTrue(details['duplicate_ids'])

    def test_inclusive_both_limits_and_one_over_require_model_components(self):
        m=source()['source_model'];c=self.conf();measured=cp.grouping_context(m,[],c)['measured']
        c['v8'].update(small_program_max_entities=measured['entities'],small_program_max_source_characters=measured['source_characters'])
        p=cp.from_analysis(m,[],None,c)
        self.assertEqual(p['grouping_decision']['method'],'program_single_group')
        self.assertEqual(set(p['owner']),set(m['entities']))
        for key in ['small_program_max_entities','small_program_max_source_characters']:
            x=deepcopy(c);x['v8'][key]-=1
            with self.assertRaises(Failure) as e:cp.from_analysis(m,[],None,x)
            self.assertEqual(e.exception.code,'invalid_component_plan')
            self.assertFalse(e.exception.evidence['grouping_context']['eligible_for_single_group'])
            self.assertEqual(cp.from_analysis(m,[],[group('all',*m['entities'])],x)['grouping_decision']['method'],'joint_analysis_components')

    def test_single_huge_entity_does_not_bypass_size_limit(self):
        m=source()['source_model'];m['entries']=['constant:A.h'];m['entities']={'constant:A.h':m['entities']['constant:A.h']}
        m['entities']['constant:A.h']['execution_equations']=[{'arguments':[],'rhs':{'text':'x'*17000}}]
        with self.assertRaises(Failure):cp.from_analysis(m,[],None,self.conf())
        context=cp.grouping_context(m,[],self.conf())
        self.assertEqual(context['measured']['entities'],1);self.assertGreater(context['measured']['source_characters'],16000)

    def test_adapted_closure_counts_type_class_and_shared_owner(self):
        m=source()['source_model'];m['entities']['constant:A.h']['dependencies']=['constant:Library.id']
        m['entities']['constant:A.f']['dependencies'].append('constant:Library.id')
        m['entities']['constant:Library.id']={'id':'constant:Library.id','name':'Library.id','kind':'constant','dependencies':['constant:Library.hidden'],
            'source_type':{'kind':'type','name':'Library.T','args':[]},'type_variables':[{'name':"'a",'sort':['Library.capability']}]}
        for name,kind in [('Library.T','type'),('Library.capability','class'),('Library.hidden','constant')]:
            m['entities'][kind+':'+name]={'id':kind+':'+name,'name':name,'kind':kind,'dependencies':[]}
        boundary={'source':'constant:Library.id','kind':'native','basis':'source identity','conditions':['all source instances']}
        p=cp.from_analysis(m,[boundary],None,self.conf())
        self.assertEqual(set(p['owner']),{'constant:A.h','constant:A.f','constant:Library.id','type:Library.T','class:Library.capability'})
        self.assertEqual(p['grouping_decision']['measured']['entities'],5)
        self.assertEqual(p['source_edges']['constant:Library.id'],['class:Library.capability','type:Library.T'])
        with self.assertRaises(Failure):cp.from_analysis(m,[{'source':'constant:A.h','kind':'native','basis':'hide business','conditions':['all']}],None,self.conf())

    def test_small_program_uses_deterministic_coverage_even_if_model_splits_it(self):
        m=source()['source_model'];p=cp.from_analysis(m,[],[group('partial','constant:A.h')],self.conf())
        self.assertEqual(len(p['units']),1);self.assertEqual(set(p['owner']),set(m['entities']))
        self.assertFalse(p['grouping_decision']['model_components_used'])

    def test_invalid_large_groups_reject_missing_duplicate_scc_split_and_group_cycle(self):
        c=self.conf();c['v8']['small_program_max_entities']=1;m=source()['source_model']
        for gs in [[group('missing','constant:A.h')],[group('a','constant:A.h'),group('b','constant:A.h','constant:A.f')]]:
            with self.assertRaises(Failure):cp.from_analysis(m,[],gs,c)
        cyc=deepcopy(m);cyc['entities']['constant:A.h']['dependencies']=['constant:A.f']
        with self.assertRaises(Failure):cp.from_analysis(cyc,[],[group('h','constant:A.h'),group('f','constant:A.f')],c)
        m['entities']['constant:A.g']={**deepcopy(m['entities']['constant:A.f']),'id':'constant:A.g','name':'A.g','dependencies':['constant:A.f']};m['entries']=['constant:A.g']
        with self.assertRaises(Failure):cp.from_analysis(m,[],[group('ends','constant:A.h','constant:A.g'),group('middle','constant:A.f')],c)

    def test_one_analysis_call_without_plan_call_and_feedback_stays_in_analysis(self):
        for bad_first,small in [(False,True),(False,False),(True,False)]:
            c=self.conf();c['v8']['small_program_max_entities']=12 if small else 1
            b=source();seen=[]
            def ask(pv,conf,path,p,analysis=False):
                self.assertTrue(analysis);self.assertNotEqual(p.get('task_kind'),'component_planning')
                seen.append(p)
                if bad_first and len(seen)==1:return self.reply(p)
                if bad_first:self.assertEqual(p['feedback']['status'],'invalid_component_plan')
                return self.reply(p,None if small else [group('all','constant:A.h','constant:A.f')])
            with tempfile.TemporaryDirectory() as d,patch.object(ctx,'ask',side_effect=ask):
                out,_=ctx.analyze(b,c,Mock(),Path(d));evidence=read(Path(d)/'reading-evidence.json')
            self.assertEqual(len(seen),2 if bad_first else 1)
            self.assertEqual(evidence['analysis_calls'],len(seen));self.assertEqual(evidence['separate_component_planning_calls'],0)
            self.assertEqual(len(out['segmentation']['units']),1)

    def test_incomplete_source_reading_cannot_finish_small_program(self):
        c=self.conf();c['segmented'].update(source_page_characters=50,initial_source_characters=50,no_progress_limit=2)
        seen=[]
        def ask(pv,conf,path,p,analysis=False):seen.append(p);return self.reply(p)
        with tempfile.TemporaryDirectory() as d,patch.object(ctx,'ask',side_effect=ask):
            with self.assertRaises(Failure) as e:ctx.analyze(source(),c,Mock(),Path(d))
        self.assertEqual(e.exception.code,'analysis_no_progress')
        self.assertEqual(seen[-1]['feedback']['status'],'incomplete_analysis')
        self.assertGreater(len(seen[-1]['page_catalog']),len(seen[-1]['source_pages']))

    def test_page_reads_are_counted_as_additional_analysis_calls(self):
        c=self.conf();c['segmented'].update(source_page_characters=80,initial_source_characters=80)
        calls=[]
        def ask(pv,conf,path,p,analysis=False):
            calls.append(p)
            supplied=p['source_pages']+p['requested_material'].get('pages',[])
            seen=set(p['read_pages'])|{r['id'] for r in supplied}
            remaining=[r['id'] for r in p['page_catalog'] if r['id'] not in seen]
            if remaining:
                return {'request_pages':[remaining[0]],'reading_notes':{r['id']:'Retained source fragment: '+r['text'] for r in supplied}}
            return self.reply(p)
        with tempfile.TemporaryDirectory() as d,patch.object(ctx,'ask',side_effect=ask):
            out,_=ctx.analyze(source(),c,Mock(),Path(d));evidence=read(Path(d)/'reading-evidence.json')
        self.assertGreater(len(calls),1)
        self.assertEqual(len(calls),evidence['analysis_calls'])
        self.assertEqual(len(evidence['read_pages']),len(calls[-1]['page_catalog']))
        self.assertEqual(evidence['separate_component_planning_calls'],0)
        self.assertEqual(out['segmentation']['grouping_decision']['method'],'program_single_group')

    def test_new_adapted_signature_dependency_must_be_read_and_classified(self):
        c=self.conf();b=source();m=b['source_model']
        m['entities']['constant:A.h']['dependencies']=['constant:Library.id']
        m['entities']['constant:Library.id']={'id':'constant:Library.id','name':'Library.id','kind':'constant','dependencies':[],
            'source_type':{},'type_variables':[{'name':"'a",'sort':['Library.capability']}]}
        m['entities']['class:Library.capability']={'id':'class:Library.capability','name':'Library.capability','kind':'class','dependencies':[]}
        boundary={'source':'constant:Library.id','kind':'native','basis':'source identity','conditions':['original capabilities']}
        calls=[]
        def ask(pv,conf,path,p,analysis=False):
            calls.append(p)
            if len(calls)==2:
                self.assertEqual(p['feedback']['status'],'incomplete_analysis')
                return {'request_pages':[r['id'] for r in p['page_catalog'] if r['source']=='class:Library.capability'],
                    'reading_notes':{r['id']:'Read original source facts: '+r['text'] for r in p['source_pages']}}
            r=self.reply(p,boundaries=[boundary])
            if len(calls)==3:r['analysis_coverage'].append('class:Library.capability')
            return r
        with tempfile.TemporaryDirectory() as d,patch.object(ctx,'ask',side_effect=ask):
            out,_=ctx.analyze(b,c,Mock(),Path(d));evidence=read(Path(d)/'reading-evidence.json')
        self.assertEqual(len(calls),3)
        self.assertIn('class:Library.capability',out['segmentation']['owner'])
        self.assertTrue(any(x.startswith('class:Library.capability#') for x in evidence['read_pages']))
        self.assertEqual(evidence['analysis_calls'],3)

    def test_threshold_and_decision_bind_config_plan_prepared_checkpoint_identity(self):
        c=self.conf();m=source()['source_model'];a=cp.from_analysis(m,[],None,c)
        changed=deepcopy(c);changed['v8']['small_program_max_entities']+=1
        b=cp.from_analysis(m,[],None,changed)
        self.assertNotEqual(a['version'],b['version']);self.assertEqual(a['owner'],b['owner'])
        bundle=source()
        self.assertNotEqual(segmented_v8.checkpoint_identity(bundle,c,{}),segmented_v8.checkpoint_identity(bundle,changed,{}))
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'A.thy').write_text('theory A imports Main begin end')
            self.assertNotEqual(prepared_identity.identity(p,c),prepared_identity.identity(p,changed))
        for value in [0,-1,True,'12']:
            x=deepcopy(c);x['v8']['small_program_max_entities']=value
            with self.assertRaises(Failure):configure(x)
        old=deepcopy(c)
        for key in cp.SMALL_PROGRAM_DEFAULTS:old['v8'].pop(key)
        default=configure(old)
        self.assertEqual(cp.grouping_policy(default),cp.SMALL_PROGRAM_DEFAULTS)
        self.assertIn('conservative',default['_configuration_sources']['origins']['v8.small_program_max_entities'])
