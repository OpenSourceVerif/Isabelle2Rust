import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
from i2r_agent.common import config, Failure
from i2r_agent.generation import generate
from i2r_agent.planning import candidate_contract
from test_planning import fixture


class OwnershipFlowTests(unittest.TestCase):
    def test_local_repair_preserves_other_files_and_does_not_reinsert_root(self):
        bundle,plan=fixture();bundle['translation_plan']=plan
        previous={'src/lib.rs':'pub mod tree;\npub use tree::Tree;\nuse tree::Tree;\n',
                  'src/tree.rs':'pub enum Tree { Leaf }'}
        bundle['loaded_adapter']={'support':{'root':'pub mod tree;\npub use tree::Tree;',
            'files':{'src/tree.rs':previous['src/tree.rs']}},'bindings':{}}
        provider=Mock();provider.call.return_value={'edits':[{'file':'src/lib.rs','old':'\nuse tree::Tree;','new':''}]}
        with tempfile.TemporaryDirectory() as d:
            out=generate(bundle,config(),provider,d,{'status':'compile_failed'},previous)
            self.assertEqual(out['files']['src/tree.rs'],previous['src/tree.rs'])
            self.assertEqual(out['files']['src/lib.rs'].count('use tree::Tree;'),1)
            self.assertNotIn('programs',__import__('json').loads(provider.call.call_args.args[1])['program'])

    def test_compiler_repair_retains_concrete_source_export_type(self):
        bundle,plan=fixture();bundle['translation_plan']=plan
        signature={'variables':[],'type':{'constructor':'Nat.nat','args':[]}}
        for node in bundle['programs'][0]['nodes']:
            if node['id']=='constant:M.observe':node['statement']['signature']=signature
        provider=Mock();provider.call.return_value={'files':{'src/lib.rs':'pub fn observe() {}'}}
        with tempfile.TemporaryDirectory() as d:
            generate(bundle,config(),provider,d,{'status':'compile_failed'},{'src/lib.rs':'pub fn observe() {}'})
        context=__import__('json').loads(provider.call.call_args.args[1])['program']
        self.assertEqual(context['source_export_signatures'],[{'source':'constant:M.observe','signature':signature}])
        self.assertEqual(context['adaptation_decisions'],plan['adaptation']['decisions'])
        self.assertNotIn('programs',context)

    def test_ownership_support_can_change_but_embedded_declarations_require_sync(self):
        bundle,plan=fixture();bundle['translation_plan']=plan
        bundle['loaded_adapter']={'support':{'root':'pub mod tree;',
            'files':{'src/tree.rs':'pub type Tree = Box<u128>;'}},'bindings':{}}
        provider=Mock();provider.call.return_value={'files':{'src/lib.rs':'pub mod tree;',
            'src/tree.rs':'pub type Tree = std::rc::Rc<u128>;'},'ownership_changes':'Share immutable nodes'}
        with tempfile.TemporaryDirectory() as d:
            out=generate(bundle,config(),provider,d)
            self.assertIn('Rc',out['loaded_adapter']['support']['files']['src/tree.rs'])
        bundle['loaded_adapter']['bindings']['support_modules']=[{'module':'tree','code':'pub type Tree = Box<u128>;'}]
        with tempfile.TemporaryDirectory() as d,self.assertRaises(Failure) as e:
            generate(bundle,config(),provider,d)
        self.assertEqual(e.exception.code,'binding_sync_required')

    def test_contract_repair_keeps_the_polymorphic_requirements_named_by_prompt(self):
        bundle,plan=fixture();bundle['translation_plan']=plan
        bundle['programs'][0]['nodes'][0]['statement']={
            'kind':'function','signature':{'variables':[['a',['HOL.equal']]],'type':{'var':'a'}}}
        provider=Mock();provider.call.return_value={'files':{'src/lib.rs':'pub fn observe<T>(x:T)->T{x}'}}
        with tempfile.TemporaryDirectory() as d:
            generate(bundle,config(),provider,d,{'status':'plan_contract_failed'})
        context=__import__('json').loads(provider.call.call_args.args[1])['program']
        self.assertEqual(context['polymorphic_exports'],[{'source':'constant:M.observe',
            'type_variables':['a'],'class_constraints':{'a':['HOL.equal']}}])
        self.assertNotIn('programs',context)

    def test_final_graph_coverage_includes_nonentry_symbols(self):
        bundle,plan=fixture()
        usage=[{'decision':'nat','locations':['src/lib.rs'],'implementation':'native'}]
        with self.assertRaises(Failure) as e:
            candidate_contract(plan,{'src/lib.rs':''},[{'source':'constant:M.observe','rust':'observe'}],usage,bundle)
        self.assertEqual(e.exception.evidence['missing'],['type:Nat.nat'])

    def test_missing_adaptation_usage_reports_actionable_ids(self):
        bundle,plan=fixture()
        mapping=[{'source':n['id'],'rust':'observe'} for n in bundle['programs'][0]['nodes']]
        with self.assertRaises(Failure) as e:
            candidate_contract(plan,{'src/lib.rs':'pub fn observe(){}'},mapping,[],bundle)
        self.assertEqual(e.exception.evidence,{'required':['nat'],'missing':['nat'],'unknown':[]})


if __name__=='__main__':unittest.main()
