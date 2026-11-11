import tempfile,unittest
from pathlib import Path
from copy import deepcopy
from i2r_agent.support_framework import build,inject,enum_layout_matches
from i2r_agent.common import Executor
from i2r_agent.segmented_config import materialize,rust_config
from i2r_agent.segmented_support import execute
from test_v8_workflow import cfg

CODE='pub enum List<T>{Nil,Cons(T,Box<List<T>>)} pub fn map<T,F:Fn(T)->T>(f:F,xs:List<T>)->List<T>{match xs{List::Nil=>List::Nil,List::Cons(x,t)=>List::Cons(f(x),Box::new(map(f,*t)))}}'
MAPPING=[{'source':'type:List.list','rust_item':'crate::List'},{'source':'constant:List.list.Nil','rust_item':'crate::List::Nil'},{'source':'constant:List.list.Cons','rust_item':'crate::List::Cons'}]

class SupportFramework(unittest.TestCase):
    def state(self):return {'files':{'src/lib.rs':CODE},'mapping':deepcopy(MAPPING),'bundle':{'source_model':{'entities':{'type:List.list':{}}}}}

    def test_enum_syntax_comments_do_not_hide_semantic_layout_changes(self):
        for kind,name,body in [('list','List','Nil,Cons(T,Box<List<T>>)'),('tree','Tree','Leaf,Node(Box<Tree<T>>,T,Box<Tree<T>>)')]:
            code=f'pub enum {name}<T>{{/// Source constructor.\n'+body.replace(',',',/* field note */',1)+',}'
            self.assertTrue(enum_layout_matches(code,name,kind))
            for bad in [code.replace('/// Source constructor.','#[cfg(any())]'),code.replace('<T>','<T:Clone>',1),code.replace('T,Box','u128,Box'),code.replace(',}',',Extra,}')]:
                self.assertFalse(enum_layout_matches(bad,name,kind),bad)
        state=self.state();state['files']['src/lib.rs']=CODE.replace('{Nil,','{/// Empty source list.\nNil,')
        self.assertIsNotNone(build(state))

    def test_scaffold_has_no_expectations_and_nonmatching_layout_is_not_guessed(self):
        s=self.state();a=build(s)
        self.assertIsNotNone(a);self.assertNotIn('#[test]',a['integration_source']);self.assertNotIn('map(',a['integration_source'])
        for code,mapping in [(CODE.replace('Cons(T,Box<List<T>>)','Cons(Box<List<T>>,T)'),MAPPING),
            (CODE,[*MAPPING[:-1],{**MAPPING[-1],'rust_item':'crate::List::Other'}])]:
            self.assertIsNone(build({**s,'files':{'src/lib.rs':code},'mapping':mapping}))
        s['files']['src/lib.rs']='pub type List<T> = Vec<T>;';b=build(s)
        self.assertIsNotNone(b);self.assertNotEqual(a['identity'],b['identity'])
        self.assertNotIn('i2r_candidate::',a['unit_source'])

    def test_reused_scaffold_runs_independent_business_cases_and_rejects_wrong_candidate(self):
        s=self.state();framework=build(s);c=cfg();rc=rust_config({},c)
        authored='''use i2r_test_support::{list_from_vec,list_into_vec};
struct NoTraits(i32);
#[test] fn source_map_nonclone(){
let result=i2r_candidate::map(|x:NoTraits|NoTraits(x.0+7),list_from_vec(vec![NoTraits(2),NoTraits(4)]));
let actual:Vec<i32>=list_into_vec(result).into_iter().map(|x|x.0).collect();
assert_eq!(actual,vec![9,11]);
}
#[test] fn source_empty(){assert!(list_into_vec(i2r_candidate::map(|x:u128|x+7,list_from_vec(vec![]))).is_empty());}
'''
        frozen={'identity':'exact-test-input','tests':[inject(authored,framework)],'unit_tests':[],
            'obligations':[{'source':'constant:List.map','category':'public_behavior','test_name':name,'case':name,'expected_basis':'map f (x#xs) = f x # map f xs; independent +7 literals'} for name in ['source_map_nonclone','source_empty']]}
        with tempfile.TemporaryDirectory() as d:
            w=Path(d);ex=Executor(w/'commands')
            for label,code in [('correct',CODE),('identity',CODE.replace('List::Cons(f(x),','List::Cons(x,'))]:
                crate=materialize(w/label,{'src/lib.rs':code},rc)
                r=execute(frozen,crate,rc,c,ex)
                self.assertEqual(r['status'],'passed' if label=='correct' else 'support_contract_failed')
            # The same scaffold carries a different immutable test expectation;
            # it does not cache or share expected values across tasks.
            wrong=deepcopy(frozen);wrong['tests']=[inject(authored.replace('vec![9,11]','vec![10,12]'),framework)]
            self.assertEqual(execute(wrong,w/'correct',rc,c,ex)['status'],'support_contract_failed')

    def test_inner_attributes_and_docs_remain_legal_in_integration_and_unit_modules(self):
        s=self.state();framework=build(s);c=cfg();rc=rust_config({},c)
        source='''//! Independent source cases.
#![allow(dead_code)]
#[test] fn preserved_header(){assert_eq!(i2r_test_support::list_into_vec(i2r_test_support::list_from_vec(vec![3u128,5])),vec![3,5]);}
'''
        for unit in [False,True]:
            with self.subTest(unit=unit),tempfile.TemporaryDirectory() as d:
                p=Path(d);crate=materialize(p/'candidate',s['files'],rc)
                frozen={'identity':'header-test','tests':[] if unit else [inject(source,framework)],
                    'unit_tests':[{'file':'src/lib.rs','module':[],'source':inject(source,framework,unit=True)}] if unit else [],
                    'obligations':[{'test_name':'preserved_header','source':'type:List.list','expected_basis':'representation only; targeted wrapper regression'}]}
                self.assertEqual(execute(frozen,crate,rc,c,Executor(p/'commands'))['status'],'passed')
