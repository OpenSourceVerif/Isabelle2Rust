"""Stage-specific complete graph inputs, with source excerpts and size audits."""
import json
import re
from pathlib import Path
from .common import ROOT, save


def skill(name):
    return (ROOT/'skills'/name/'SKILL.md').read_text()


def bindings_for(programs, loaded):
    bindings=loaded.get('bindings',{})
    # Binding export is already restricted to the reachable graph. Concrete
    # invocations are retained on disk, not repeated in every model request.
    return {k:v for k,v in bindings.items() if k not in {'concrete_applications','support_modules'}}


def source_context(bundle):
    symbols={n['id'].split(':',1)[-1] for p in bundle['programs'] for n in p['nodes']}
    short={x.rsplit('.',1)[-1] for x in symbols}
    result={}
    command=re.compile(r'^(?:definition|abbreviation|fun|function|partial_function|datatype|record|primrec|lemma|theorem|text|section|subsection|code_printing|code_identifier|end|context|locale|interpretation)\b',re.M)
    definition=re.compile(r'^(?:definition|abbreviation|fun|function|partial_function|datatype|record|primrec)\s+(?:\([^)]*\)\s*)?(?:\([^)]*\)\s*)?([^\s:\[]+)')
    for name,content in bundle['sources'].items():
        if not Path(name).is_absolute():
            result[name]={'selection':'project source','text':content};continue
        marks=list(command.finditer(content));pieces=[]
        for i,m in enumerate(marks):
            end=marks[i+1].start() if i+1<len(marks) else len(content)
            block=content[m.start():end];match=definition.match(block)
            if match and (match[1].strip('"') in short or any(re.search(r'\b'+re.escape(s)+r'\b',block[:250]) for s in short)):
                pieces.append({'line':content[:m.start()].count('\n')+1,'text':block})
        result[name]={'selection':'reachable definition excerpts; full source saved and requestable','excerpts':pieces}
    return result


def stage_context(bundle, stage):
    from .generation import intern_program
    from .export_contract import polymorphic_exports
    loaded=bundle.get('loaded_adapter') or bundle.get('base_adapter') or {}
    catalog=[{k:x[k] for k in ['theory','base_name','path','available'] if k in x}
             for x in bundle.get('source_catalog',[])]
    return {'stage':stage,'programs':intern_program(bundle['programs']),
        'polymorphic_exports':polymorphic_exports(bundle),
        'graph_contract':'Complete graph, all nodes and equations retained; recursively expand $ref. Dependencies and SCCs come from Isabelle.',
        'sources':source_context(bundle),'source_catalog':catalog,
        'requested_source_text':bundle.get('requested_source_text',{}),
        'effective_bindings':bindings_for(bundle['programs'],loaded),
        'support':loaded.get('support',{}),'numeric_policy':bundle.get('numeric_policy'),
        'external_inventory':bundle.get('external_inventory',[]),
        'observation_binding':bundle.get('observation_binding'),
        'kernel':bundle.get('kernel'),'workload':bundle.get('workload'),
        'translation_plan':{k:v for k,v in bundle.get('translation_plan',{}).items() if k!='adapter'},
        'source_collection':'No sibling theory glob. Full source archived; selected definitions and all exported code equations available.'}


def audit_request(path, system, payload):
    sizes={k:len(json.dumps(v,ensure_ascii=False)) for k,v in payload.items()}
    text=json.dumps(payload,ensure_ascii=False)
    save(path,{'system_characters':len(system),'user_characters':len(text),'sections':sizes,
        'token_estimate_range':[int((len(system)+len(text))/4),int((len(system)+len(text))/2)],
        'token_estimate_notice':'Character heuristic only; exact provider usage is saved after response. No silent source-graph truncation.'})
    return text
