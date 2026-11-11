import tempfile
import unittest
from pathlib import Path
from copy import deepcopy
from i2r_agent import segmented_run as runner
from i2r_agent.common import ROOT, config, merge, read
from i2r_agent.segmentation import partition
from i2r_agent.segmented_config import configure, rust_config


class SharedInvalidationTest(unittest.TestCase):
    def make_state(self):
        cfg=configure(merge(config(),read(Path(__file__).parent/'fixtures/segmented-source.json')['base']))
        entities={}
        for name in ['A.f','A.g']:
            ident='constant:'+name
            entities[ident]={'id':ident,'name':name,'kind':'constant','source_type':{},
                             'dependencies':[],'execution_equations':[],'callers':[]}
        model={'kind':'isabelle2rust-program','schema_version':1,'entries':list(entities),
               'entities':entities,'uses':[],'recursive_groups':[],'provenance':{}}
        plan=partition(model)
        mapping=[{'source':'constant:A.'+n,'kind':'direct','rust_item':'crate::'+n} for n in ['f','g']]
        source='fn shared()->u128 {1}\npub fn f()->u128 {shared()}\npub fn g()->u128 {shared()}\n'
        state={'bundle':{'source_model':model},'partition':plan,'files':{'src/lib.rs':source},
               'mapping':mapping,'rust_config':rust_config({},cfg),'completed':list(plan['order']),
               'reviews':{u:{'version':'old'} for u in plan['order']},'transactions':[],
               'behavior_version':'old','whole_review_version':'old'}
        return state,cfg

    def change(self,state,cfg,source):
        with tempfile.TemporaryDirectory() as d:
            return runner.apply_transaction(state,{'files':{'src/lib.rs':source}},cfg,Path(d))

    def test_simultaneous_business_and_shared_edit_invalidates_both_branches(self):
        state,cfg=self.make_state();original=deepcopy(state)
        source=state['files']['src/lib.rs'].replace('{1}','{2}').replace('f()->u128 {shared()}','f()->u128 {shared()+1}')
        after=self.change(state,cfg,source)
        self.assertEqual(after['completed'],[])
        self.assertEqual(after['reviews'],{})
        self.assertNotIn('behavior_version',after)
        self.assertNotIn('whole_review_version',after)
        self.assertEqual(state,original)

    def test_business_only_edit_keeps_independent_unit_and_addition_keeps_both(self):
        state,cfg=self.make_state();text=state['files']['src/lib.rs']
        after=self.change(state,cfg,text.replace('f()->u128 {shared()}','f()->u128 {shared()+1}'))
        kept=[u for u,row in state['partition']['units'].items() if 'constant:A.g' in row['members']]
        self.assertEqual(after['completed'],kept)
        added=self.change(state,cfg,text+'fn new_helper()->u128 {0}\n')
        self.assertEqual(added['completed'],state['completed'])
        inline_added=self.change(state,cfg,text+'#[inline(always)]\nfn new_helper()->u128 {0}\n')
        self.assertEqual(inline_added['completed'],state['completed'])
        inline_existing=self.change(state,cfg,text.replace('pub fn f','#[inline]\npub fn f'))
        self.assertEqual(inline_existing['completed'],kept)
        cfg_added=self.change(state,cfg,text+'#[cfg(any())]\nfn new_helper()->u128 {0}\n')
        self.assertEqual(cfg_added['completed'],[])

    def test_import_and_business_edit_rechecks_other_branch(self):
        state,cfg=self.make_state()
        text='mod left {pub fn shared()->u128 {1}}\nmod right {pub fn shared()->u128 {2}}\nuse left::shared;\npub fn f()->u128 {shared()}\npub fn g()->u128 {shared()}\n'
        state['files']['src/lib.rs']=text
        edited=text.replace('use left::shared','use right::shared').replace('f()->u128 {shared()}','f()->u128 {shared()+1}')
        self.assertEqual(self.change(state,cfg,edited)['completed'],[])

    def test_added_local_function_shadowing_glob_rechecks_both_branches(self):
        state,cfg=self.make_state()
        text='mod helpers {pub fn shared()->u128 {1}}\nuse helpers::*;\npub fn f()->u128 {shared()}\npub fn g()->u128 {shared()}\n'
        state['files']['src/lib.rs']=text
        self.assertEqual(self.change(state,cfg,text+'fn shared()->u128 {2}\n')['completed'],[])

    def test_new_inherent_method_can_override_blanket_trait_dispatch(self):
        state,cfg=self.make_state()
        text='struct Value; trait Get {fn get(&self)->u128;} impl<T> Get for T {fn get(&self)->u128 {1}}\nimpl Value {fn unused(&self)->u128 {0}}\npub fn f()->u128 {Value.get()}\npub fn g()->u128 {Value.get()}\n'
        state['files']['src/lib.rs']=text
        edited=text.replace('impl Value {','impl Value {fn get(&self)->u128 {2}')
        self.assertEqual(self.change(state,cfg,edited)['completed'],[])
