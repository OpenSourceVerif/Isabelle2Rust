"""Lossless source display, complete evidence inventory and exact checker citations."""
from copy import deepcopy
import json
from unittest.mock import patch
import pytest
from i2r_agent import source_evidence as ev,source_suite_review as review
from i2r_agent.common import Failure
from i2r_agent.program_model import readable
from i2r_agent.segmented_context import pages
from i2r_agent.task_context import fingerprint

def ty(name,*args):return {'kind':'type','name':name,'args':list(args)}
def fn(*types):
    result=types[-1]
    for arg in reversed(types[:-1]):result=ty('fun',arg,result)
    return result
BOOL=ty('HOL.bool');CHAR=ty('String.char');LIST=ty('List.list',CHAR)
SIGNATURES={'HOL.False':BOOL,'HOL.True':BOOL,'String.char.Char':fn(*([BOOL]*8),CHAR),'List.list.Nil':LIST,'List.list.Cons':fn(CHAR,LIST,LIST)}
ARITIES={'HOL.False':0,'HOL.True':0,'String.char.Char':8,'List.list.Nil':0,'List.list.Cons':2}
def ctor(name,*args):
    term={'kind':'const','name':name,'type':deepcopy(SIGNATURES[name])}
    for arg in args:term={'kind':'apply','function':term,'argument':arg}
    return term

def model_for(*terms):
    name='constant:Example.literal'
    entity={'id':name,'name':'Example.literal','kind':'constant','dependencies':[],
        'source_type':LIST,'execution_type':LIST,'type_variables':[],
        'execution_equations':[{'arguments':[],'rhs':{'text':'source literal','term':term}} for term in terms]}
    declarations={'id':'type:Example.data','kind':'type','constructors':[{'id':'constant:'+name,'fields':[{} for _ in range(arity)]} for name,arity in ARITIES.items()]}
    return entity,{'entries':[name],'entities':{name:entity,'type:Example.data':declarations}}

def literal():
    # Argument order is a source fact, not a guessed ASCII/big-endian decoder.
    bits=[False,False,False,True,False,True,True,False]
    char=ctor('String.char.Char',*(ctor('HOL.True' if x else 'HOL.False') for x in bits))
    return ctor('List.list.Cons',char,ctor('List.list.Nil'))

def test_eight_field_character_and_list_roundtrip_without_decoding():
    term=literal();entity,model=model_for(term);before=deepcopy(model)
    evidence=ev.constructor_literals(entity,model);row=evidence['subtrees'][0]
    assert ev.restore_constructor(row,evidence['types'],ev.constructor_arities(model))==term
    assert row['term_sha256']==ev.identity(term) and evidence['entity_sha256']==ev.identity(entity)
    char=row['tree'][2][0]
    assert char[0]=='String.char.Char'
    assert [x[0] for x in char[2]]==['HOL.False','HOL.False','HOL.False','HOL.True','HOL.False','HOL.True','HOL.True','HOL.False']
    assert row['tree'][2][1][0]=='List.list.Nil' and len(evidence['types'])==4
    assert model==before
    assert len(json.dumps(evidence))<len(json.dumps(term))


def test_nested_polymorphic_tree_and_shared_types_roundtrip():
    a={'kind':'free','name':"'a",'sort':['HOL.equal']};tree=ty('Tree.tree',a)
    signatures={'Leaf':fn(a,tree),'Branch':fn(tree,tree,tree),'Atom':a}
    def node(name,*args):
        out={'kind':'const','name':name,'type':deepcopy(signatures[name])}
        for arg in args:out={'kind':'apply','function':out,'argument':arg}
        return out
    leaf=node('Leaf',node('Atom'));term=node('Branch',leaf,node('Branch',leaf,leaf))
    entity,model=model_for(term)
    entity['source_type']=deepcopy(tree);entity['execution_type']=deepcopy(tree)
    model['entities']['type:Tree']={'constructors':[{'id':'constant:'+n,'fields':[{}]*k} for n,k in [('Leaf',1),('Branch',2),('Atom',0)]]}
    evidence=ev.constructor_literals(entity,model)
    assert len(evidence['types'])==3
    assert any("'a" in json.dumps(t) for t in evidence['types'].values())
    assert ev.restore_constructor(evidence['subtrees'][0],evidence['types'],ev.constructor_arities(model))==term

@pytest.mark.parametrize('change',['extra_apply_field','extra_const_field'])
def test_unknown_ast_fields_fall_back_unchanged(change):
    term=literal()
    if change=='extra_apply_field':term['source_annotation']={'exact':'keep me'}
    else:
        head,_=ev.applications(term);head['source_annotation']='keep me'
    entity,model=model_for(term);evidence=ev.constructor_literals(entity,model)
    assert evidence['types']=={} and evidence['subtrees'][0]['term']==term
    ev.verify_constructor_evidence(evidence,entity,model)

@pytest.mark.parametrize('term',[
    {'kind':'bound','index':0,'type':BOOL},
    {'kind':'const','name':'Undeclared.looks_like_constructor','type':BOOL},
    {'kind':'apply','function':{'kind':'const','name':'List.list.Cons','type':SIGNATURES['List.list.Cons']},'argument':ctor('HOL.True')},
])
def test_open_unknown_and_partial_terms_are_not_compacted(term):
    entity,model=model_for(term)
    with pytest.raises(ValueError):ev.compact_constructor(term,ev.constructor_arities(model),{})
    assert ev.constructor_literals(entity,model) is None
    # Existing readable equations remain available; this is not a guessed literal.
    assert readable(entity,model)['execution_equations'][0]['rhs']['text']=='source literal'

@pytest.mark.parametrize('change',['missing_tree','missing_argument','wrong_constructor','wrong_type','wrong_path','wrong_hash','wrong_entity','reordered_bits'])
def test_changed_or_incomplete_evidence_rejected(change):
    entity,model=model_for(literal(),literal());evidence=ev.constructor_literals(entity,model)
    row=evidence['subtrees'][0]
    if change=='missing_tree':evidence['subtrees'].clear();evidence['types'].clear()
    elif change=='missing_argument':row['tree'][2].pop()
    elif change=='wrong_constructor':row['tree'][0]='Forged.constructor'
    elif change=='wrong_type':evidence['types'][row['tree'][1]]['name']='Wrong.type'
    elif change=='wrong_path':row['path']='/execution_equations/99/rhs/term'
    elif change=='wrong_hash':row['term_sha256']='0'*64
    elif change=='wrong_entity':evidence['source']='constant:Other'
    elif change=='reordered_bits':row['tree'][2][0][2].reverse()
    with pytest.raises((ValueError,KeyError,IndexError)):ev.verify_constructor_evidence(evidence,entity,model)


def checker_fixture():
    entity,model=model_for(literal())
    frozen={'identity':'source-suite','tests':['#[test] fn literal() { assert_eq!(candidate(), vec![true, false]); }'],'unit_tests':[],'obligations':[]}
    state={'bundle':{'source_model':model,'numeric_policy':{}},'files':{},'mapping':[],'rust_config':{}}
    cfg={'segmented':{'source_page_characters':16000},'model':{},'generation':{}}
    material=review.payload(frozen,state,cfg)
    page=next(p for p in material['source'] if p['source']==entity['id'])
    quote='["HOL.False", "t2", []]'
    assert quote in page['text'] and quote not in json.dumps(entity)
    test=material['inventory'][0]['id']
    proposal={'action':'test_wrong','derivation':'Ordered constructor fields supply the source value.',
        'source_evidence':[{'id':'e1','kind':'source','source':entity['id'],'page_id':page['id'],'quote':quote}],
        'tests':[{'id':test,'verdict':'wrong','basis':['e1'],'premise':'fixed input','expectation':'source constructor fields','assertion':'equality','reason':'ordered source fields'}],
        'obligations':[],'edits':[{'kind':'integration','index':0,'test_id':test,'old':'vec![true, false]','new':'vec![false, true]'}]}
    return frozen,state,cfg,material,proposal

def test_actual_checker_revision_accepts_exact_compact_quote_and_preserves_test_guards():
    frozen,state,cfg,material,proposal=checker_fixture()
    revised=review.revise(frozen,proposal,state,material)
    assert revised['tests']==['#[test] fn literal() { assert_eq!(candidate(), vec![false, true]); }']
    assert frozen['tests']==['#[test] fn literal() { assert_eq!(candidate(), vec![true, false]); }']
    proposal['edits'][0]['new']='candidate()'
    with pytest.raises(Failure):review.revise(frozen,proposal,state,material)

@pytest.mark.parametrize('change',['stale_page','forged_quote','wrong_source'])
def test_actual_checker_rejects_unbound_compact_citations(change):
    frozen,state,cfg,material,proposal=checker_fixture();citation=proposal['source_evidence'][0]
    if change=='stale_page':citation['page_id']=citation['page_id'].split('#')[0]+'#old-page:1'
    elif change=='forged_quote':citation['quote']='["FORGED_CONSTRUCTOR", "t2", []]'
    else:citation['source']='constant:Other'
    with pytest.raises(Failure):review.revise(frozen,proposal,state,material)


def test_new_source_view_invalidates_checker_scope_and_old_page_ids():
    frozen,state,cfg,material,proposal=checker_fixture()
    before=review.scope(frozen,state,cfg)
    with patch.object(review,'pages',return_value=[{'id':'old-view','text':'old-view'}]):
        assert review.scope(frozen,state,cfg)!=before
    name=state['bundle']['source_model']['entries'][0];entity=state['bundle']['source_model']['entities'][name]
    old=readable(entity);term=entity['execution_equations'][0]['rhs']['term']
    old['source_constructor_literals']={'subtrees':[{'term':term,'path':'/execution_equations/0/rhs/term','term_sha256':ev.identity(term)}]}
    old_id=name+'#'+fingerprint(json.dumps(old,ensure_ascii=False))[:10]+':1'
    assert old_id not in {p['id'] for p in material['source']}

def test_failure_checker_reconstructs_current_material_and_rejects_tampering():
    from i2r_agent import source_failure_review as failure
    frozen,state,cfg,material,proposal=checker_fixture();test=material['inventory'][0]['id'];name=state['bundle']['source_model']['entries'][0]
    frozen['obligations']=[{'source':name,'test_name':test,'expected_basis':'ordered source literal'}]
    proposal['obligations']=[{'id':'o:0','verdict':'covered','tests':[test],'basis':['e1'],'reason':'ordered source literal'}]
    material=failure.payload(frozen,state,cfg,[test])
    revised=review.revise(frozen,proposal,state,material)
    assert 'vec![false, true]' in revised['tests'][0]
    tampered=deepcopy(material);tampered['source'][0]['text']=tampered['source'][0]['text'].replace('source literal','forged literal')
    with pytest.raises(Failure):review.revise(frozen,proposal,state,tampered)


def test_author_and_translation_share_the_same_verified_literal_view():
    from i2r_agent.support_scope import material as author_material
    entity,model=model_for(literal());name=entity['id']
    translation=pages(model,[name],16000)
    authored=author_material(model,[name],16000)
    byid={p['id']:p for p in authored}
    for page in translation:
        assert byid[page['id']]['text']==page['text']
    evidence=json.loads(''.join(p['text'] for p in translation))['source_constructor_literals']
    ev.verify_constructor_evidence(evidence,entity,model)
