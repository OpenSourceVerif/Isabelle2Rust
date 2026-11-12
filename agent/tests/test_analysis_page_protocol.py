"""Paging feedback preserves exact source evidence and existing budget controls."""
from copy import deepcopy
from unittest.mock import Mock,patch
import pytest
from i2r_agent import segmented_context as ctx
from i2r_agent.common import Failure,read
from test_segmented_workflow import source
from test_translation_workflow import cfg

A='constant:A.f#0123456789:1'
B='constant:A.f#0123456789:2'
CAT={A:{'id':A,'text':'original first fragment'},B:{'id':B,'text':'original second fragment'}}

def rejection(reply,progress=None):
    progress={} if progress is None else progress
    with pytest.raises(Failure) as caught:ctx.reject_page_reply_alias(reply,CAT,{A},{A},progress)
    return caught.value,progress

def test_reply_page_objects_never_supply_source_or_alias_ids():
    original=deepcopy(CAT);seen={A};reply={'requested_material':{'pages':[{'id':B+'-typo','text':'forged source'}]}}
    failure,progress=rejection(reply)
    assert failure.code=='invalid_page_request'
    assert failure.evidence['missing_page_ids']==[B]
    assert 'forged source' not in str(failure.evidence) and CAT==original and seen=={A}
    assert 'top-level request_pages' in failure.evidence['instruction']
    # Even a correct top-level request does not authorize a second page-content channel.
    reply['request_pages']=[B]
    assert rejection(reply)[0].code=='invalid_page_request'

def test_same_missing_set_escalates_and_new_set_starts_at_one():
    reply={'requested_material':{'pages':[{'id':B}]}}
    first,state=rejection(reply);second,state=rejection(reply,state)
    assert first.evidence['same_missing_pages_repetitions']==1
    assert second.evidence['same_missing_pages_repetitions']==2
    assert second.evidence['next_action']=='correct_page_request_only'
    changed=ctx.page_reading_failure('incomplete_analysis','unread',CAT,set(),set(),state)
    assert changed.evidence['same_missing_pages_repetitions']==1

def test_valid_transition_retains_notes_and_clears_only_reading_feedback(tmp_path):
    failure,_=rejection({'requested_material':{'pages':[{'id':B}]}})
    feedback={'status':failure.code,'evidence':failure.evidence}
    old={A:'Retained precise first-fragment fact'}
    notes,material,resolved=ctx.advance_source_reading(old,{'request_pages':[B]}, {A},CAT,100,feedback,tmp_path)
    assert notes==old and material['pages']==[CAT[B]] and resolved is None
    assert (tmp_path/'resolved-reading-feedback.json').exists()
    unrelated={'status':'invalid_component_plan','evidence':{}}
    assert ctx.advance_source_reading(old,{'request_pages':[B]},{A},CAT,100,unrelated,tmp_path)[2]==unrelated

@pytest.mark.parametrize('reply,code',[
    ({'request_pages':[B]},'missing_reading_notes'),
    ({'request_pages':[B],'reading_notes':{A+'-typo':'fact'}},'invalid_reading_notes'),
    ({'request_pages':[B+'-typo'],'reading_notes':{A:'fact'}},'unknown_page'),
])
def test_correction_never_bypasses_exact_notes_or_catalog(reply,code,tmp_path):
    existing={};feedback={'status':'invalid_page_request'}
    with pytest.raises(Failure) as caught:ctx.advance_source_reading(existing,reply,{A},CAT,100,feedback,tmp_path)
    assert caught.value.code==code and existing=={} and feedback=={'status':'invalid_page_request'}
    assert not (tmp_path/'resolved-reading-feedback.json').exists()

def small_config():
    c=cfg();c['segmented'].update(source_page_characters=80,initial_source_characters=80,no_progress_limit=16)
    return c

def test_analysis_escalation_checkpoint_resume_and_changed_scope(tmp_path):
    c=small_config();b=source();calls=[]
    def wrong(provider,conf,path,payload,analysis=False):
        calls.append(deepcopy(payload))
        if len(calls)==3:raise Failure('provider_error','offline interruption')
        return {'requested_material':{'pages':[{'id':payload['page_catalog'][-1]['id'],'text':'forged'}]}}
    with patch.object(ctx,'ask',side_effect=wrong),pytest.raises(Failure) as caught:ctx.analyze(b,c,Mock(),tmp_path)
    assert caught.value.code=='provider_error' and len(calls)==3
    assert calls[2]['task'].startswith('Correct only') and calls[2]['unvalidated_current_proposal'] is None
    checkpoint=read(tmp_path/'analysis-state.json')
    assert checkpoint['stalled']==2 and checkpoint['page_stall']['repetitions']==2
    assert checkpoint['notes']=={} and len(checkpoint['seen'])==1
    resumed=[]
    def stop(provider,conf,path,payload,analysis=False):
        resumed.append(payload);raise Failure('provider_error','offline interruption')
    with patch.object(ctx,'ask',side_effect=stop),pytest.raises(Failure):ctx.analyze(b,c,Mock(),tmp_path)
    assert resumed[0]['task']==calls[2]['task'] and resumed[0]['read_pages']==calls[2]['read_pages']
    assert read(tmp_path/'analysis-state.json')['stalled']==2
    changed=deepcopy(c);changed['segmented']['initial_source_characters']+=1
    with patch.object(ctx,'ask') as ask,pytest.raises(Failure) as caught:ctx.analyze(b,changed,Mock(),tmp_path)
    assert caught.value.code=='analysis_resume_mismatch';ask.assert_not_called()
    # The context implementation bytes are already bound into the existing resume scope.
    original_read=ctx.Path.read_text
    def changed_code(path,*args,**kwargs):
        text=original_read(path,*args,**kwargs)
        return text+'\n# changed context implementation' if path==ctx.Path(ctx.__file__) else text
    with patch.object(ctx.Path,'read_text',changed_code),patch.object(ctx,'ask') as ask,pytest.raises(Failure) as caught:ctx.analyze(b,c,Mock(),tmp_path)
    assert caught.value.code=='analysis_resume_mismatch';ask.assert_not_called()

def test_existing_no_progress_limit_still_applies(tmp_path):
    c=small_config();c['segmented']['no_progress_limit']=2
    def wrong(*args,**kwargs):return {'requested_material':{'pages':[]}}
    with patch.object(ctx,'ask',side_effect=wrong) as ask,pytest.raises(Failure) as caught:ctx.analyze(source(),c,Mock(),tmp_path)
    assert caught.value.code=='analysis_no_progress' and ask.call_count==2

def test_changed_source_page_representation_rejects_saved_analysis(tmp_path):
    c=small_config();b=source()
    with patch.object(ctx,'ask',side_effect=Failure('provider_error','offline')),pytest.raises(Failure):ctx.analyze(b,c,Mock(),tmp_path)
    original=ctx.pages
    def changed(*args,**kwargs):
        result=original(*args,**kwargs);result[0]={**result[0],'text':result[0]['text']+' changed display'};return result
    with patch.object(ctx,'pages',side_effect=changed),patch.object(ctx,'ask') as ask,pytest.raises(Failure) as caught:ctx.analyze(b,c,Mock(),tmp_path)
    assert caught.value.code=='analysis_resume_mismatch';ask.assert_not_called()
