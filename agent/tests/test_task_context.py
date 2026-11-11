import json
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from i2r_agent.common import config, Failure
from i2r_agent import task_context as tc
from i2r_agent.knowledge import apply_files, analyze, requested, material
from i2r_agent.knowledge_run import search


def bundle():
    return {'programs':[{'entries':['constant:A.main'],'nodes':[
        {'id':'constant:A.main','dependencies':['constant:A.helper'],'statement':{'kind':'function','signature':{'variables':[]},'equations':['ORIGINAL_MAIN']}},
        {'id':'constant:A.helper','dependencies':[],'statement':{'kind':'function','signature':{'variables':[]},'equations':['ORIGINAL_HELPER']}}]}],
        'sources':{'Algorithm.thy':'line one\nline two'},'numeric_policy':{'mode':'checked'}}


def managed_config():
    cfg=config();cfg['context_management']['enabled']=True;cfg['testing']['transport']='native-u128'
    return cfg


class ContextTests(unittest.TestCase):
    def test_same_symbol_reads_exact_graph_version_and_original_survives(self):
        b=bundle();b['original_programs']=deepcopy(b['programs']);b['programs'][0]['nodes'][0]['statement']['equations']=['ADAPTED']
        with tempfile.TemporaryDirectory() as d:
            tc.register(b,d)
            original=requested({'request_nodes':[{'graph_version':'G0','id':'constant:A.main'}]},b)
            current=requested({'request_nodes':['constant:A.main']},b)
            self.assertEqual(original['nodes'][0]['statement']['equations'],['ORIGINAL_MAIN'])
            self.assertEqual(current['nodes'][0]['statement']['equations'],['ADAPTED'])
            b['programs']=[{'entries':[],'nodes':[]}];tc.register(b,d)
            self.assertIn('ORIGINAL_HELPER',json.dumps(requested({'request_nodes':[{'graph_version':'G0','id':'constant:A.helper'}]},b)))
            with self.assertRaises(Failure):requested({'request_nodes':['constant:A.helper']},b)

    def test_sources_are_frozen_and_tampering_is_detected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'External.thy';p.write_text('original')
            b=bundle();b['source_catalog']=[{'path':str(p),'available':True}]
            tc.register(b,Path(d)/'archive');p.write_text('changed externally')
            got=requested({'request_sources':[{'path':str(p)}]},b)
            self.assertEqual(got['sources'][0]['text'],'original')
            version=b['source_versions'][str(p)]
            (Path(d)/'archive'/(version+'.json')).write_text('"tampered"')
            with self.assertRaises(Failure):requested({'request_sources':[{'path':str(p)}]},b)

    def test_reading_merge_preserves_versions_and_references(self):
        first={'references':{'topic':'knowledge'},'nodes':[{'id':'same','graph_version':'g0','body':1}]}
        second={'nodes':[{'id':'same','graph_version':'g1','body':2}]}
        merged=tc.merge_material(first,second)
        self.assertEqual(len(merged['nodes']),2);self.assertEqual(merged['references']['topic'],'knowledge')
        self.assertEqual(tc.merge_material(merged,second),merged)

    def test_stale_and_partial_patch_never_change_original(self):
        original={'src/lib.rs':'one two'}
        with self.assertRaises(Failure):apply_files(original,{'base_code_version':'code-'+('0'*64),'edits':[{'file':'src/lib.rs','old':'one','new':'ONE'}]})
        with self.assertRaises(Failure):apply_files(original,{'edits':[{'file':'src/lib.rs','old':'one','new':'ONE'},{'file':'src/lib.rs','old':'absent','new':'X'}]})
        self.assertEqual(original,{'src/lib.rs':'one two'})

    def test_conversation_resume_and_phase_change_remove_old_graph(self):
        cfg=managed_config();provider=Mock();provider.call.return_value={'action':'generate','files':{'src/lib.rs':'code'}}
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'session.json';session=tc.Conversation(path,cfg);session.enter('generation')
            session.call(provider,'rules',{'program':{'thingol':'BIG_GRAPH'}},d)
            restored=tc.Conversation(path,cfg);restored.enter('generation')
            restored.call(provider,'rules',{'requested_material':{'x':'NEW_EVIDENCE'}},d)
            messages=provider.call.call_args.kwargs['messages']
            self.assertEqual(sum('BIG_GRAPH' in m['content'] for m in messages),0)
            archived=list(restored.archive.directory.glob('turn-*.json'))
            self.assertTrue(any('BIG_GRAPH' in p.read_text() for p in archived))
            self.assertTrue(restored.has_graph())
            self.assertTrue(any(m['role']=='assistant' for m in messages))
            restored.enter('repair');restored.call(provider,'rules',{'current_files':{'src/lib.rs':'code'},'feedback':'error'},d)
            self.assertNotIn('BIG_GRAPH',json.dumps(provider.call.call_args.kwargs['messages']))

    def test_context_budget_covers_system_and_history(self):
        cfg=managed_config();cfg['preprocessing']['max_context_chars']=50
        with tempfile.TemporaryDirectory() as d:
            session=tc.Conversation(Path(d)/'session.json',cfg);session.enter('repair')
            with self.assertRaises(Failure):session.call(Mock(),'x'*51,{},d)

    def test_generation_handoff_keeps_original_evidence_with_empty_g1(self):
        b=bundle();b['original_programs']=deepcopy(b['programs']);b['programs']=[{'entries':[],'nodes':[]}];b['loaded_adapter']={'support':{'files':{}},'bindings':{}}
        branch={'id':'candidate-1','bundle':b,'files':{'src/lib.rs':'fn main(){}'},'mode':'generate','feedback':{'status':'compile_failed'},'extra':{'references':{'topic':'retained'}},'pending_material':{}}
        with tempfile.TemporaryDirectory() as d:
            out=tc.prepare_generation(branch,{'program':material(b),'available_actions':[]},managed_config(),d)
            self.assertNotIn('thingol',out['program']);self.assertIn('ORIGINAL_MAIN',json.dumps(out['program']['original_evidence']))
            self.assertEqual(out['program']['retained_references']['topic'],'retained')
            self.assertTrue(out['code_version'].startswith('code-'))

    def test_analysis_reading_survives_stage_handoff(self):
        p=Mock();p.phase_calls={'preprocessing':0};p.calls=0
        replies=[{'request_references':['semantic-adaptation/references/numeric-semantics.md']},{'request_nodes':['constant:A.helper']},{'opportunities':[]}]
        def call(*args,**kwargs):
            p.phase_calls['preprocessing']+=1;p.calls+=1
            return replies[p.calls-1]
        p.call.side_effect=call
        with tempfile.TemporaryDirectory() as d:
            result,_=analyze(bundle(),managed_config(),p,d)
            self.assertIn('semantic-adaptation/references/numeric-semantics.md',result['knowledge_material']['references'])
            self.assertEqual(result['knowledge_material']['nodes'][0]['id'],'constant:A.helper')
            self.assertNotIn('thingol',json.loads(p.call.call_args.args[1])['program'])

    def test_managed_local_repair_and_review_do_not_reupload_full_graph(self):
        b=bundle();b['loaded_adapter']={'support':{'files':{}},'bindings':{}}
        cfg=managed_config();p=Mock();p.phase_calls={'generation':0};p.calls=0;p.usage={};requests=[]
        replies=[{'action':'generate','files':{'src/lib.rs':'pub fn main(){}'},'mapping':[{'source':n['id'],'rust':'main'} for n in b['programs'][0]['nodes']]},
                 {'action':'generate','files':{'src/lib.rs':'pub fn main(){ let _x=1; }'}},{'action':'accept','quality_review':'checked original definitions'}]
        def respond(*args):
            requests.append(args[-1]);p.calls+=1;p.phase_calls['generation']+=1;return replies[p.calls-1]
        with tempfile.TemporaryDirectory() as d,patch('i2r_agent.knowledge_run.call',side_effect=respond),patch('i2r_agent.knowledge_run.compile_library',side_effect=[{'status':'compile_failed','checks':{}},{'status':'passed'}]):
            attempts,survivors=search(b,None,cfg,p,d,Mock(),None,[],[],Path(d)/'r.json',lambda x:None)
            self.assertEqual(len(survivors),1)
            self.assertTrue((Path(d)/'candidate-02/changes.diff').exists())
        self.assertIn('thingol',requests[0]['program'])
        self.assertNotIn('thingol',requests[1]['program']);self.assertNotIn('thingol',requests[2]['program'])


    def test_behavior_repair_reuses_connector_then_reviews_validated_code(self):
        b=bundle();b['case']='list-index';b['loaded_adapter']={'support':{'files':{}},'bindings':{}}
        p=Mock();p.calls=0;p.phase_calls={'generation':0};p.usage={};requests=[]
        replies=[{'action':'generate','files':{'src/lib.rs':'pub fn main(){}'},'mapping':[{'source':n['id'],'rust':'main'} for n in b['programs'][0]['nodes']]},
                 {'action':'generate','files':{'src/lib.rs':'pub fn main(){let _fixed=1;}'}},{'action':'accept','quality_review':'source and connector checked'}]
        def respond(*args):
            requests.append(args[-1]);p.calls+=1;p.phase_calls['generation']+=1;return replies[p.calls-1]
        checks=[]
        def suite(*args,**kwargs):
            checks.append(args)
            return {'status':'mismatch' if len(checks)==1 else 'passed','kind':args[6],'count':1,'failures':1 if len(checks)==1 else 0,
                    'counterexamples':[{'input':[1],'expected':[1],'actual':[0]}] if len(checks)==1 else []}
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);project=root/'testing';project.mkdir()
            for name in ['Model.thy','Kernel.thy']:(project/name).write_text('original scenario')
            with patch('i2r_agent.knowledge_run.call',side_effect=respond),patch('i2r_agent.knowledge_run.compile_library',return_value={'status':'passed'}),patch('i2r_agent.knowledge_run.compile_rust',return_value={'status':'passed','binary':'binary','checks':{}}),patch('i2r_agent.knowledge_run.check_suite',side_effect=suite),patch('i2r_agent.knowledge_run.test_connector.connect',return_value=({'src/lib.rs':'connector'},'boundary notes')) as connector:
                attempts,survivors=search(b,project,managed_config(),p,root,Mock(),{},[[1]],[],root/'regressions.json',lambda x:None)
            self.assertEqual(len(survivors),1);self.assertEqual(connector.call_count,1)
            self.assertEqual(p.calls,3);self.assertIn('behavior_failure',requests[1]['feedback'])
            self.assertIn('connection_review',requests[2]);self.assertNotIn('thingol',requests[2]['program'])
            self.assertGreaterEqual(len(checks),4)



    def test_extra_rust_callable_parameter_has_specific_mapping_diagnostic(self):
        from i2r_agent.export_contract import check_exports
        b=bundle();b['programs'][0]['nodes'][0]['statement']['signature']['variables']=[['a',[]]]
        mapping=[{'source':'constant:A.main','rust':'main','type_parameters':{'a':'T','p':'P'}}]
        with self.assertRaises(Failure) as caught:check_exports(b,{'src/lib.rs':'pub fn main<T,P>(){}'},mapping)
        problem=caught.exception.evidence[0]
        self.assertEqual(problem['extra_keys'],['p']);self.assertEqual(problem['expected_keys'],['a'])
        mapping[0]['type_parameters']={'a':'T'}
        self.assertEqual(len(check_exports(b,{'src/lib.rs':'pub fn main<T,P>(){}'},mapping)['checked_exports']),1)


if __name__=='__main__':unittest.main()
