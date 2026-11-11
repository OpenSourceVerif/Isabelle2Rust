"""Compiler-located binding repair context; the complete frozen oracle stays immutable."""
import json,re
from pathlib import Path
from .common import save,digest,Failure
from .task_context import fingerprint
from .segmented_context import pages

POLICY='compiler-group-binding-context-v1'

def prepare(frozen,result,state,cfg,directory):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    archive=directory/'original-binding-evidence.json'
    save(archive,{'frozen':frozen,'failure':result})
    diagnostic=result.get('diagnostic','')
    locations=re.findall(r'-->\s+([^\s:]+\.rs):(\d+):(\d+)',diagnostic)
    known=bool(locations) and all(re.fullmatch(r'tests/source_contract_\d+\.rs',p) for p,_,_ in locations)
    indices={int(re.search(r'_(\d+)\.rs',p)[1]) for p,_,_ in locations} if known else set(range(len(frozen['tests'])))
    if any(i>=len(frozen['tests']) for i in indices):known=False;indices=set(range(len(frozen['tests'])))
    # Unit diagnostics do not identify the injected test index reliably. Retain
    # all units/source ownership unless the compiler located integration-only errors.
    units=set() if known else set(range(len(frozen.get('unit_tests',[]))))
    prefixes=tuple(f'__i2r_source_contract_{i}::' for i in sorted(indices))
    obligations=[o for o in frozen['obligations'] if not known or not o.get('test_name') or o['test_name'].startswith(prefixes)]
    ids={o['source'] for o in obligations if o.get('source') in state['bundle']['source_model']['entities']}
    source_pages=pages(state['bundle']['source_model'],state['bundle']['source_model']['entities'],cfg['segmented']['source_page_characters'])
    for page in source_pages:page['required_for_group']=page['source'] in ids
    # All other artifacts remain exact, requestable pages, not opaque hashes.
    artifact_index=[]
    for kind,seq in [('integration',frozen['tests']),('unit',frozen.get('unit_tests',[]))]:
        for index,item in enumerate(seq):
            code=item if kind=='integration' else item['source'];name=f'{kind}:{index}';size=cfg['segmented']['source_page_characters']
            chunks=[code[n:n+size] for n in range(0,len(code),size)] or ['']
            page_ids=[]
            for part,text in enumerate(chunks):
                pid=f'frozen-test:{name}#{fingerprint(code)[:10]}:{part+1}';page_ids.append(pid)
                source_pages.append({'id':pid,'artifact':name,'part':part+1,'parts':len(chunks),'text':text,'required_for_group':False,'notice':'Exact immutable frozen test text. Join ordered parts. This adds evidence, not permission to edit another group.'})
            artifact_index.append({'kind':kind,'index':index,'sha256':fingerprint(code),'characters':len(code),'pages':page_ids})
    # Obligation text is also requestable exactly, including unrelated groups.
    text=json.dumps(frozen['obligations'],ensure_ascii=False);size=cfg['segmented']['source_page_characters'];chunks=[text[n:n+size] for n in range(0,len(text),size)] or ['[]']
    for part,chunk in enumerate(chunks):source_pages.append({'id':f'frozen-obligations#{fingerprint(text)[:10]}:{part+1}','artifact':'all_obligations','part':part+1,'parts':len(chunks),'text':chunk,'required_for_group':False,'notice':'Exact JSON fragment; join ordered parts to recover all original obligations.'})
    scope={'policy':POLICY,'compiler_localized':known,'integration_indices':sorted(indices),'unit_indices':sorted(units),
           'compiler_locations':[{'file':p,'line':int(line),'column':int(col)} for p,line,col in locations],
           'required_source_ids':sorted(ids),'archive':str(archive),'archive_sha256':digest(archive),
           'full_frozen_identity':frozen['identity'],'full_obligations_sha256':fingerprint(frozen['obligations']),
           'artifacts':artifact_index,'unchanged_artifact_rule':'Only compiler-selected bindings may change; all original groups/obligations/assertions remain required and are executed together after repair.'}
    selected={'identity':frozen['identity'],'integration_tests':[{'index':i,'source':frozen['tests'][i]} for i in sorted(indices)],
              'unit_tests':[{'index':i,**frozen['unit_tests'][i]} for i in sorted(units)],'obligations':obligations}
    # Keep the diagnostic in the primary request. Full original records are in
    # the archive; omit repeated tests/obligations and duplicated compile record.
    failure={k:v for k,v in result.items() if k not in {'immutable_test_sources','immutable_unit_tests','obligations','compilation','missing_required_tests'}}
    failure['unexecuted_required_test_count']=len(result.get('missing_required_tests',[]))
    failure['execution_note']='Compilation failed; no missing test is counted as executed or covered.'
    mapping=[row for row in state['mapping'] if not known or row.get('source') in ids]
    save(directory/'context-scope.json',scope)
    return {'frozen':selected,'failure':failure,'mapping':mapping,'focused_binding_scope':scope},source_pages


def restrict(proposal,scope):
    for edit in proposal.get('edits',[]):
        allowed=scope['integration_indices'] if edit.get('kind')=='integration' else scope['unit_indices'] if edit.get('kind')=='unit' else []
        if edit.get('index') not in allowed:raise Failure('invalid_support_binding_patch','Edit lies outside compiler-selected test artifacts',edit)
    for row in proposal.get('relocations',[]):
        if row.get('integration_index') not in scope['integration_indices']:raise Failure('invalid_support_binding_patch','Relocation outside compiler-selected test artifacts',row)
    for row in proposal.get('unit_locations',[]):
        if row.get('index') not in scope['unit_indices']:raise Failure('invalid_support_binding_patch','Unit relocation outside compiler-selected test artifacts',row)
