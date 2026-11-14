from pathlib import Path
from copy import deepcopy
import pytest
from i2r_agent import optimization_materials as m
from i2r_agent.task_context import Archive
from i2r_agent.common import Failure,digest


def bundle(path, text, archive, line=1):
    path.write_text(text)
    return {'source_model':{'entries':['constant:Example.f'],'entities':{'constant:Example.f':{'name':'Example.f','specifications':[{'file':str(path),'line':line}]}}},
            'source_catalog':[{'path':str(path),'theory':'Example','available':True,'sha256':digest(path)}],
            'source_versions':{str(path):archive.put('source',text)},'_context_archive':str(archive.directory),'sources':{}}


def test_initial_context_contains_frozen_theorem_text_not_modified_disk(tmp_path):
    p=tmp_path/'Example.thy';a=Archive(tmp_path/'archive');b=bundle(p,'definition f where "f x = x"\nlemma existing_fact: "f x = x" by simp\n',a)
    p.write_text('Changed after baseline freeze')
    material,audit=m.initial_sources(b)
    assert 'existing_fact' in material['sources'][0]['text']
    assert 'Changed after' not in material['sources'][0]['text']
    assert audit['selections'][0]['coverage']=='complete_theory'


def test_large_theory_keeps_definition_in_bounded_explicit_window(tmp_path):
    p=tmp_path/'Example.thy';a=Archive(tmp_path/'archive');lines=['(* '+'x'*800+' *)']*200
    lines[100]='definition f where "f x = x"';b=bundle(p,'\n'.join(lines),a,line=101)
    material,audit=m.initial_sources(b)
    assert 'definition f' in material['sources'][0]['text']
    assert audit['characters']<=m.INITIAL_CHARACTERS
    assert audit['selections'][0]['coverage']=='definition_window'
    assert audit['selections'][0]['start_line']<=101<=audit['selections'][0]['end_line']


def test_no_unique_catalog_match_is_reported_without_reading_unrelated_file(tmp_path):
    a=Archive(tmp_path/'archive');b=bundle(tmp_path/'Example.thy','private material',a)
    e=b['source_model']['entities']['constant:Example.f'];e['name']='Unknown.f';e['specifications']=[{'file':'missing.thy','line':1}]
    material,audit=m.initial_sources(b)
    assert not material and audit['unavailable']


def test_changed_unarchived_source_is_not_used_as_initial_evidence(tmp_path):
    a=Archive(tmp_path/'archive');p=tmp_path/'Example.thy';b=bundle(p,'original',a);b['source_versions']={};p.write_text('mutated')
    with pytest.raises(Failure,match='catalog'):m.initial_sources(b)


def test_thin_export_wrapper_includes_direct_callee_theory(tmp_path):
    a=Archive(tmp_path/'archive');b=bundle(tmp_path/'Example.thy','definition f where "f = Library.g"',a)
    p=tmp_path/'Library.thy';text='definition g where "g x = x"\nlemma known_g: "g x = x" by simp';p.write_text(text)
    b['source_model']['entities']['constant:Example.f']['dependencies']=['constant:Library.g']
    b['source_model']['entities']['constant:Library.g']={'name':'Library.g','specifications':[{'file':str(p),'line':1}]}
    b['source_catalog'].append({'path':str(p),'theory':'Library','available':True,'sha256':digest(p)})
    b['source_versions'][str(p)]=a.put('source',text)
    material,audit=m.initial_sources(b)
    assert any('known_g' in row['text'] for row in material['sources'])
    assert len(audit['selections'])==2
