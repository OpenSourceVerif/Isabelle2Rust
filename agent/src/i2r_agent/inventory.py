"""Deterministic views over the exported graph; no reconstructed call graph.

Code-printing declarations are implementation evidence, not FFI classifications.
Only explicit case-supplied external bindings with a real source artifact are
confirmed; missing equations and unresolved origins remain separate.
"""
from collections import defaultdict
from pathlib import Path
import re
from .common import Failure, digest


def inventory(programs,catalog,sources,metadata):
    nodes={n['id']:n for p in programs for n in p['nodes']};uses=defaultdict(lambda:{'count':0,'users':set()})
    def walk(x,user):
        if isinstance(x,dict):
            if 'const' in x and isinstance(x['const'],dict) and 'symbol' in x['const']:
                item=uses[x['const']['symbol']];item['count']+=1;item['users'].add(user)
            for value in x.values():walk(value,user)
        elif isinstance(x,list):
            for value in x:walk(value,user)
    for n in nodes.values():walk(n['statement'],n['id'])
    associations=[];relevant=set()
    for symbol in nodes:
        qualified=symbol.split(':',1)[-1]
        candidates=[item for item in catalog if qualified.startswith(item['base_name']+'.') or qualified.startswith(item['theory']+'.')]
        for item in candidates:
            associations.append({'source':symbol,'theory':item['theory'],'path':item['path'],
                'basis':'theory namespace match; code-equation theorem retained separately'})
            relevant.add(item['path'])
    declarations=[]
    for filename in sorted(relevant|set(sources)):
        path=Path(filename)
        content=sources.get(filename)
        if content is None and path.is_file():content=path.read_text()
        if content is None:continue
        # Preserve the actual declaration text and location. Do not infer a
        # concrete external package or source symbol by matching module names.
        lines=content.splitlines()
        for index,line in enumerate(lines):
            if re.match(r'^(code_printing|code_reflect|external_file|compile_generated_files)\b',line):
                end=index+1
                while end<len(lines) and not re.match(r'^(?:code_printing|code_reserved|code_identifier|definition|lemma|theorem|text|setup|ML|end|export_code)\b',lines[end]):end+=1
                declarations.append({'path':filename,'line':index+1,'end_line':end,
                    'kind':'backend_declaration','classification':'not_an_external_dependency_by_itself',
                    'content':'\n'.join(lines[index:end])})
    external=[]
    for item in metadata.get('external_implementations',[]):
        symbol=item['source'];path=Path(item['implementation_path'])
        if symbol not in nodes:raise Failure('invalid_external_evidence','External declaration is not reachable: '+symbol)
        if not path.is_file():raise Failure('invalid_external_evidence','External implementation file missing: '+str(path))
        external.append({**item,'id':item.get('id',symbol),'kind':'explicit_external_implementation',
                         'sha256':digest(path),'content':path.read_text()})
    return {'entries':list(dict.fromkeys(e for p in programs for e in p['entries'])),
        'functions':[{'source':n['id'],'signature':n['statement'].get('signature'),
                      'dependencies':n['dependencies']} for n in nodes.values() if n['statement']['kind']=='function'],
        'types':[n for n in nodes.values() if n['id'].startswith('type:')],
        'operations':[{'source':name,'occurrences':item['count'],'users':sorted(item['users'])} for name,item in sorted(uses.items())],
        'source_associations':associations,'implementation_declarations':declarations,
        'external_implementations':external,
        'unresolved_code_equations':[n['id'] for n in nodes.values() if n['statement']['kind']=='unimplemented'],
        'external_detection_status':'Conservative source evidence. No automatic FFI inference; declarations needing semantic investigation remain visible.'}
