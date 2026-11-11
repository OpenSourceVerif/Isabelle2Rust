import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from i2r_agent.common import config, Failure
from i2r_agent.rust_index import build, select
from i2r_agent.source_context import coverage, payload
from i2r_agent.source_run import search


def bundle():
    entity={'id':'constant:A.f','name':'A.f','kind':'constant','dependencies':[],
        'source_type':{},'callers':[],'execution_equations':[]}
    model={'kind':'isabelle2rust-program','schema_version':1,'entries':['constant:A.f'],
        'entities':{'constant:A.f':entity},'uses':[],'recursive_groups':[],'provenance':{}}
    return {'workflow':'source-v6','source_model':model,'original_source_model':model,
        'programs':[{'entries':model['entries'],'nodes':[],'sccs':[]}],
        'sources':{},'source_catalog':[],'numeric_policy':{'mode':'checked'}}


def mapping():
    return [{'source':'constant:A.f','rust':'f','rust_item':'f','kind':'replacement',
        'basis':'f returns the original constant','conditions':['all inputs']}]


class SourceWorkflowTests(unittest.TestCase):
    def test_syntax_index_handles_nested_braces_and_keeps_related_items(self):
        files={'src/lib.rs':'pub fn a(){ let s="}"; b(); }\nfn b(){ if true { c(); } }\nfn c(){}\nfn unrelated(){}'}
        index=build(files)
        self.assertFalse(index['parse_error_files'])
        self.assertIn('c();',next(r['text'] for r in index['items'] if r['name']=='b'))
        chosen=select(index,{'message':'error in b'})
        self.assertEqual({r['name'] for r in chosen},{'a','b','c'})

    def test_boundary_requires_existing_implementation_and_contract(self):
        b=bundle();files={'src/lib.rs':'pub fn f()->u128 { 1 }'}
        self.assertEqual(coverage(b,files,mapping())['status'],'passed')
        bad=mapping();bad[0]['rust_item']='absent'
        with self.assertRaises(Failure):coverage(b,files,bad)
        bad=mapping();bad[0].pop('conditions')
        with self.assertRaises(Failure):coverage(b,files,bad)

    def test_direct_mapping_does_not_silently_cover_missing_dependency(self):
        b=bundle();b['source_model']['entities']['constant:A.f']['dependencies']=['constant:A.helper']
        rows=mapping();rows[0]['kind']='direct'
        with self.assertRaises(Failure) as e:coverage(b,{'src/lib.rs':'pub fn f(){}'},rows)
        self.assertEqual(e.exception.evidence['missing'],['constant:A.helper'])

    def test_refine_precedes_compiler_and_compiler_failure_uses_repair(self):
        cfg=config();cfg['generation']['workflow']='source-v6'
        provider=Mock();provider.phase_calls={'generation':0};provider.calls=0;provider.usage={}
        phases=[];compiled=[]
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);out=root/'out';out.write_text('');err=root/'err';err.write_text('error[E0308]: wrong type')
            record={'stdout':str(out),'stderr':str(err),'status':'failed'}
            def ask(provider,cfg,path,stage,p):
                phases.append(p['controller_state']['phase']);provider.phase_calls['generation']+=1;provider.calls+=1
                phase=phases[-1]
                if phase=='generate':return {'action':'generate','files':{'src/lib.rs':'pub fn f()->u128 { false }'},'mapping':mapping()}
                if phase in {'quick_refine','review'}:return {'action':'accept','quality_review':'No structural change required','quality_resolutions':[]}
                self.assertIn('structured_diagnostics',p['feedback'])
                self.assertTrue(p['current_mapping'])
                return {'action':'generate','base_code_version':p['code_version'],
                    'edits':[{'file':'src/lib.rs','old':'false','new':'1'}],'diagnosis':'The source result is natural one'}
            def compile_one(crate,*args):
                compiled.append((list(phases),(crate/'src/lib.rs').read_text()))
                if len(compiled)==1:return {'status':'compile_failed','checks':{'build':record},'diagnostics':[{'code':{'code':'E0308'},'message':'wrong type'}]}
                return {'status':'passed','checks':{},'diagnostics':[]}
            with patch('i2r_agent.source_run.call',side_effect=ask),patch('i2r_agent.source_run.compile_library',side_effect=compile_one):
                attempts,survivors=search(bundle(),None,cfg,provider,root,Mock(),None,[],[],root/'regressions.json',lambda x:None)
            self.assertEqual(phases,['generate','quick_refine','repair','review'])
            self.assertEqual(compiled[0][0],['generate','quick_refine'])
            self.assertIn('{ 1 }',compiled[1][1]);self.assertEqual(len(survivors),1)
            self.assertTrue(survivors[0]['closed_issues'])
            self.assertFalse(survivors[0].get('loaded_adapter'))

    def test_parse_error_file_is_never_hidden_by_retrieval(self):
        with tempfile.TemporaryDirectory() as d:
            b={'bundle':bundle(),'files':{'src/lib.rs':'pub fn f( {'},'mapping':mapping(),
                'plan':{'dependencies':{}},'mode':'repair','feedback':{'message':'some error'},'decisions':[]}
            p=payload(b,config(),d)
            self.assertIn('src/lib.rs',p['current_files'])
            self.assertEqual(p['rust_index']['parse_error_files'],['src/lib.rs'])
            self.assertNotIn('backend_obligations',p['program'])


if __name__=='__main__':unittest.main()
