import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from i2r_agent.common import Executor
from i2r_agent.segmented_config import configure,materialize,rust_config
from i2r_agent.segmented_v8 import connection,compile_crate
from i2r_agent.validation import execute
from i2r_agent.connector_templates import KERNEL,identity
from i2r_agent.list_connector_templates import generate
from test_v8_workflow import cfg

LIST='pub enum List<T>{Nil,Cons(T,Box<List<T>>)}'
MAPPING=[{'source':'type:List.list','rust_item':'crate::List'},{'source':'constant:List.list.Cons','rust_item':'crate::List::Cons'}]
def model(theory,term):return f'theory Model imports {theory} begin definition observe :: "nat list \\<Rightarrow> nat list" where "observe input = {term}" end'

class ListConnectorTemplates(unittest.TestCase):
    def config(self):
        c=cfg();c['v8']['correctness_only']=True;return configure(c)

    def test_list_shape_spans_source_targets_and_observes_real_result(self):
        c=self.config();rc=rust_config({},c)
        for theory in ['Listprog_Test','Other_Source']:
            code=LIST+' pub fn push<T>(x:T,xs:List<T>)->List<T>{List::Cons(x,Box::new(xs))}'
            mapping=MAPPING+[{'source':'constant:'+theory+'.push','rust_item':'crate::push'}]
            source=model(theory,theory+'.push 0 input');binding=generate(source,KERNEL,{'src/lib.rs':code},mapping,c)
            self.assertIsNotNone(binding)
            with tempfile.TemporaryDirectory() as d:
                p=Path(d);ex=Executor(p/'commands')
                for name,text in [('good',code),('wrong',code.replace('{List::Cons(x,Box::new(xs))}','{xs}'))]:
                    crate=materialize(p/name,{'src/lib.rs':text},rc);built=compile_crate(connection(crate,binding['files'],rc,c),rc,c,ex,False)
                    self.assertEqual(built['status'],'passed')
                    for args in [(),('--i2r-kernel-check',)]:
                        out=execute(built['binary'],[[],[4,2]],ex,10,arguments=args)['outputs']
                        self.assertEqual(out,[[0],[0,4,2]] if name=='good' else [[],[4,2]])
            self.assertIsNone(generate(source.replace('push 0','push 1'),KERNEL,{'src/lib.rs':code},mapping,c))
            self.assertIsNone(generate(source,KERNEL.replace('kernel_prepare x = x','kernel_prepare x = rev x'),{'src/lib.rs':code},mapping,c))

    def test_map_checked_callback_preserves_overflow_and_wrong_results_fail(self):
        c=self.config();rc=rust_config({},c)
        code=LIST+' pub fn map<A,B,F:Fn(A)->B>(f:F,xs:List<A>)->List<B>{match xs{List::Nil=>List::Nil,List::Cons(x,t)=>List::Cons(f(x),Box::new(map(f,*t)))}}'
        mapping=MAPPING+[{'source':'constant:H.map','rust_item':'crate::map'}]
        source=model('H',r'H.map (\<lambda>x. x+1) input');binding=generate(source,KERNEL,{'src/lib.rs':code},mapping,c)
        self.assertIsNotNone(binding)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);ex=Executor(p/'commands');crate=materialize(p/'candidate',{'src/lib.rs':code},rc)
            built=compile_crate(connection(crate,binding['files'],rc,c),rc,c,ex,False);self.assertEqual(built['status'],'passed')
            self.assertEqual(execute(built['binary'],[[0,7]],ex,10)['outputs'],[[1,8]])
            self.assertEqual(execute(built['binary'],[[2**128-1]],ex,10)['status'],'numeric_range_exceeded')
        self.assertIsNone(generate(source,KERNEL,{'src/lib.rs':code.replace('->List<B>','->Result<List<B>,Error>')},mapping,c))

    def test_scaffold_implementation_alone_changes_connector_identity(self):
        from i2r_agent import connector_templates as t
        c=self.config()
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'Model.thy').write_text(model('X','X.f input'));(p/'Kernel.thy').write_text(KERNEL)
            before=identity(p,{'src/lib.rs':LIST},MAPPING,{},c);original=t.digest
            with patch.object(t,'digest',side_effect=lambda path:'changed-scaffold' if Path(path).name=='support_framework.py' else original(path)):
                self.assertNotEqual(before,identity(p,{'src/lib.rs':LIST},MAPPING,{},c))

    def test_documented_list_and_shared_callback_compile_and_observe_actual_result(self):
        c=self.config();rc=rust_config({},c)
        code=LIST.replace('{Nil,','{/// Empty list.\nNil,')+' pub fn map<A,B,F>(f:&F,xs:List<A>)->List<B> where F:Fn(A)->B {match xs{List::Nil=>List::Nil,List::Cons(x,t)=>List::Cons(f(x),Box::new(map(f,*t)))}}'
        mapping=MAPPING+[{'source':'constant:H.map','rust_item':'crate::map'}]
        source=model('H',r'H.map (\<lambda>x. x+1) input')
        binding=generate(source,KERNEL,{'src/lib.rs':code},mapping,c)
        self.assertIsNotNone(binding)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);ex=Executor(p/'commands')
            for name,text in [('correct',code),('drop_tail',code.replace('Box::new(map(f,*t))','Box::new(List::Nil)'))]:
                crate=materialize(p/name,{'src/lib.rs':text},rc)
                built=compile_crate(connection(crate,binding['files'],rc,c),rc,c,ex,False)
                self.assertEqual(built['status'],'passed')
                for args in [(),('--i2r-kernel-check',)]:
                    result=execute(built['binary'],[[],[0,7]],ex,10,arguments=args)
                    self.assertEqual(result['outputs'],[[],[1,8]] if name=='correct' else [[],[1]])
                self.assertEqual(execute(built['binary'],[[2**128-1]],ex,10)['status'],'numeric_range_exceeded')
        for bad in [code.replace('f:&F','f:&mut F'),code.replace('Fn(A)','Fn(&A)'),code.replace('Fn(A)','FnMut(A)'),code.replace('Fn(A)','FnOnce(A)'),code.replace('Fn(A)->B','Fn(A)->Result<B,E>'),code.replace('Fn(A)->B','Fn(A)->B+Clone')]:
            self.assertIsNone(generate(source,KERNEL,{'src/lib.rs':bad},mapping,c),bad)
