"""Per-run adapters: model declarations, actual Isabelle loading, support checks."""
from __future__ import annotations
import json
import re
from pathlib import Path
from .common import ROOT, Failure, digest, read, save

from .context import skill, stage_context, audit_request
SYSTEM = (ROOT/'prompts/preprocessing-system.txt').read_text() + '\n' + skill('semantic-adaptation')
PLAN_SCHEMA = read(ROOT/'config/preprocessing-plan.schema.json')

def normalize_files(files):
    result=dict(files);changes=[]
    for name,code in files.items():
        # Some providers JSON-encode the code twice. Decode only a fully valid
        # additional JSON string layer; retain raw response and record the change.
        if isinstance(code,str) and '\n' not in code and r'\n' in code:
            try:decoded=json.loads('"'+code+'"')
            except ValueError:continue
            if isinstance(decoded,str) and '\n' in decoded:
                result[name]=decoded;changes.append({'file':name,'normalization':'one extra JSON string layer'})
    return result,changes


def validate_files(files):
    if not isinstance(files,dict):raise Failure('invalid_candidate','files must be an object')
    for name,code in files.items():
        p=Path(name)
        if not isinstance(code,str) or p.is_absolute() or '..' in p.parts or len(p.parts)<2 or p.parts[0]!='src' or p.suffix!='.rs' or name=='src/main.rs':
            raise Failure('invalid_candidate_path',str(name))
        # Project-relative Rust files are accepted. FFI may legitimately need
        # unsafe; correctness is checked by compilation and behavior tests.


def check_schema(value, schema, path='$'):
    """Validate the local schema's subset using only the standard library."""
    def bad(message):raise Failure('invalid_plan',path+': '+message)
    if 'oneOf' in schema:
        matches=0
        for alternative in schema['oneOf']:
            try:check_schema(value,alternative,path);matches+=1
            except Failure:pass
        if matches!=1:bad('must match exactly one allowed shape')
        return
    if 'const' in schema and value!=schema['const']:bad('unexpected version/value')
    if 'enum' in schema and value not in schema['enum']:bad('unsupported value')
    kind=schema.get('type')
    types={'object':dict,'array':list,'string':str,'boolean':bool}
    if kind and not isinstance(value,types[kind]):bad('expected '+kind)
    if kind=='object':
        for key in schema.get('required',[]):
            if key not in value:bad('missing '+key)
        properties=schema.get('properties',{})
        for key,item in value.items():
            if key in properties:check_schema(item,properties[key],path+'.'+key)
            elif schema.get('additionalProperties') is False:bad('unexpected '+key)
            elif isinstance(schema.get('additionalProperties'),dict):
                check_schema(item,schema['additionalProperties'],path+'.'+key)
    elif kind=='array':
        if len(value)<schema.get('minItems',0):bad('too few items')
        for index,item in enumerate(value):check_schema(item,schema['items'],f'{path}[{index}]')
    elif kind=='string':
        if len(value.strip())<schema.get('minLength',0):bad('empty text')
        if 'pattern' in schema and not re.fullmatch(schema['pattern'],value):bad('invalid format')


def numeric_policy(cfg):
    from .suites import input_bits
    mode=cfg.get('preprocessing',{}).get('numeric_mode','checked')
    if mode not in {'checked','arbitrary'}:raise Failure('invalid_config','numeric_mode must be checked or arbitrary')
    bits=input_bits(cfg)
    return {'mode':mode,'bounded_indices_allowed':True,'source_words':'preserve source modular semantics',
            'experiment_input_domain':{'max_input_bits':bits or None,
                'meaning':'Explicit bound on observation input values only; intermediate/output ranges still require analysis. It is not a Rust representation selection.'},
            'overflow':'explicit checked error, never silent mathematical wrap',
            'arbitrary_required_for_mathematical_values':mode=='arbitrary',
            'representation_selection':('Checked mode: default nat u128 and int/integer i128; report exceeded input/intermediate ranges. Use native operations when suitable to source behavior.'
                if mode=='checked' else 'Arbitrary mode: preserve unbounded mathematical nat/int values with a model-selected representation/library. Container-derived indices may use bounded native types when their origin establishes that bound.')}


def manifest(dependencies,package='i2r_candidate',transport='dashu-ubig',build_dependencies=None):
    if not isinstance(dependencies,dict):raise Failure('invalid_plan','dependencies must be an object')
    dependency_schema=PLAN_SCHEMA['properties']['dependencies']
    check_schema(dependencies,dependency_schema,'dependencies')
    default={'dashu-int':{'version':'=0.6.2','features':['std'],'default-features':False}} if transport in {'dashu-ubig','dashu-ibig'} else ({'num-bigint':'=0.4.6','num-traits':'=0.2.19'} if transport=='bigint' else {})
    deps={**default,**dependencies}
    lines=['[package]',f'name = "{package}"','version = "0.1.0"','edition = "2024"','[dependencies]']
    for name,spec in sorted(deps.items()):
        if not re.fullmatch(r'[A-Za-z0-9_-]+',name):raise Failure('invalid_plan','Invalid crate name '+name)
        if isinstance(spec,str):value=json.dumps(spec)
        else:
            parts=['version = '+json.dumps(spec['version'])]
            if 'features' in spec:parts.append('features = '+json.dumps(spec['features']))
            if 'default-features' in spec:parts.append('default-features = '+str(spec['default-features']).lower())
            value='{ '+', '.join(parts)+' }'
        lines.append(json.dumps(name)+' = '+value)
    if build_dependencies:
        extra=manifest(build_dependencies,transport='none').split('[dependencies]\n',1)[1]
        lines+=['[build-dependencies]',extra.rstrip()]
    return '\n'.join(lines)+'\n'


def validate_plan(plan,bundle):
    check_schema(plan,PLAN_SCHEMA)
    nodes={n['id'] for p in bundle['programs'] for n in p['nodes']}
    nodes|={b['source'] for k in ['types','operations'] for b in bundle.get('base_adapter',{}).get('bindings',{}).get(k,[])}
    entries={e for p in bundle['programs'] for e in p['entries']}
    if plan['numeric_mode']!=bundle['numeric_policy']['mode']:
        raise Failure('invalid_plan','Plan must respect the requested numeric mode')
    exports=[e['source'] for e in plan['architecture']['exports']]
    if set(exports)!=entries or len(exports)!=len(entries):
        raise Failure('invalid_plan','Map each export exactly once',{'expected':sorted(entries),'received':exports})
    units=plan['architecture']['units'];decisions=plan['adaptation']['decisions']
    for group in [units,decisions]:
        if len({x['id'] for x in group})!=len(group):raise Failure('invalid_plan','Duplicate plan item ID')
    referenced=set()
    for unit in units:
        scope=set(unit['source_symbols']);referenced|=scope
        if scope-nodes:raise Failure('invalid_plan','Unit references unknown source IDs',sorted(scope-nodes))
    for decision in decisions:
        scope=set(decision['scope']);referenced|=scope
        if scope-nodes:raise Failure('invalid_plan','Adaptation references unknown source IDs',sorted(scope-nodes))
        # Imported code-target theories can introduce executable constants.
        # Isabelle resolves operation declarations in the actual adapter context.
    ids={b['id'] for b in bundle.get('external_inventory',[])}
    provided=[b['id'] for b in plan['boundaries']]
    if not ids.issubset(provided) or len(provided)!=len(set(provided)):
        raise Failure('invalid_plan','Retain a disposition for each external inventory item',{'expected':sorted(ids),'received':provided})
    # Newly discovered boundaries need a checkable source quotation. This
    # verifies the cited material, not the model's interpretation of its ABI.
    catalog={x['path'] for x in bundle.get('source_catalog',[]) if x.get('available')}
    for boundary in plan['boundaries']:
        if boundary['id'] in ids:continue
        evidence=boundary.get('evidence',{});path=evidence.get('path');quote=evidence.get('quote','')
        if boundary.get('source') not in nodes or path not in catalog|set(bundle.get('sources',{})) or not quote:
            raise Failure('invalid_plan','A newly discovered boundary needs a reachable source ID and evidence {path, quote}',boundary)
        content=bundle.get('sources',{}).get(path)
        if content is None:content=Path(path).read_text()
        if quote not in content:raise Failure('invalid_plan','Boundary evidence quotation not found in the supplied source',boundary)

    manifest(plan['dependencies'],build_dependencies=plan.get('build_dependencies'))
    # This audit records coverage; it is not a claim of semantic validation.
    return {'status':'passed','scope':'schema, source references and explicit boundary coverage only',
            'nodes_not_explicitly_assigned':sorted(nodes-referenced),
            'capability_gaps':[b for b in plan['boundaries'] if b['route']=='unresolved'],
            'semantic_validation':'deferred to generated implementation and behavior testing; no proof claim'}


def require_generation_capabilities(plan):
    gaps=[b for b in plan['boundaries'] if b['route']=='unresolved']
    if gaps:raise Failure('generation_capability_gap','Plan still has unresolved implementation requirements',gaps)


def prepare_plan(bundle,cfg,provider,directory,executor=None,previous_plan=None,initial_feedback=None):
    from .generation import generation_context
    from .adapters import load_adapter
    directory=Path(directory);history=list(initial_feedback or []);attempts=[];previous=previous_plan
    settings=cfg.get('preprocessing',{})
    bundle={**bundle,'numeric_policy':numeric_policy(cfg)}
    for number in range(1,settings.get('max_plan_attempts',20)+1):
        current=directory/f'plan-{number:02d}';current.mkdir(parents=True,exist_ok=True)
        prompt={'task':'Write this run\'s executable Isabelle code adapter and generation units.',
                'plan_schema':PLAN_SCHEMA,'numeric_policy':bundle['numeric_policy'],
                'latest_failure':history[-1] if history else None,
                'program':stage_context(bundle,'G0_semantic_adaptation'),
                'previous_plan':previous,'feedback':history[-1:],
                'repair_focus':{'latest_failure':history[-1],
                    'instruction':'Apply the specific diagnostic to the complete previous plan. If printing_syntax_hints are supplied, inspect each actual_template and suggested_template; do not return unchanged failing declarations.'} if history else None}
        content=audit_request(current/'context-audit.json',SYSTEM,prompt)
        if not cfg.get('v8',{}).get('correctness_only') and len(content)>settings.get('max_context_chars',1500000):
            raise Failure('context_budget_exceeded','Planning context exceeds preprocessing.max_context_chars; no source was silently truncated')
        save(current/'input.json',prompt)
        plan=None
        try:
            plan=provider.call(SYSTEM,content,options=settings.get('model',{}),phase='preprocessing')
            if isinstance(plan,dict) and 'request_sources' in plan:
                allowed={x['path']:x for x in bundle.get('source_catalog',[]) if x.get('available')}
                supplied={}
                for request in plan['request_sources']:
                    name=request['path']
                    if name not in allowed:raise Failure('invalid_source_request','Request a path from source_catalog: '+name)
                    lines=Path(name).read_text().splitlines()
                    begin=max(1,int(request.get('start_line',1)));end=min(len(lines),int(request.get('end_line',len(lines))))
                    supplied[name+f':{begin}-{end}']='\n'.join(lines[begin-1:end])
                bundle={**bundle,'requested_source_text':{**bundle.get('requested_source_text',{}),**supplied}}
                save(current/'source-response.json',supplied)
                attempts.append({'attempt':number,'status':'source_requested'});continue
            save(current/'plan.json',plan)
            if isinstance(plan,dict):previous=plan
            checks=validate_plan(plan,bundle)
            loaded=load_adapter(plan,bundle,cfg,current/'adapter',executor)
            checks['adapter_loaded']=loaded['status'];checks['adapter_audit']=loaded['audit']
            save(current/'checks.json',checks)
            save(directory/'selected-plan.json',plan)
            record={'status':'passed','plan_attempts':number,'plan_path':str(directory/'selected-plan.json'),
                    'plan_sha256':digest(directory/'selected-plan.json'),'schema_version':3,
                    'adaptation':plan['adaptation'],'architecture':plan['architecture'],'boundaries':plan['boundaries'],
                    'numeric_mode':plan['numeric_mode'],'checks':checks,'earlier_attempts':attempts,
                    'adapter_record':str(current/'adapter/loaded-adapter.json')}
            save(directory/'result.json',record)
            return {**bundle,'g0_programs':bundle['programs'],'programs':[loaded['after_target']],
                    'translation_plan':plan,'loaded_adapter':loaded},record
        except Failure as error:
            if error.code in {'provider_error','budget_exhausted'}:raise
            feedback={'attempt':number,'status':error.code,'message':str(error),'evidence':error.evidence}
            history.append(feedback)
            attempts.append({'attempt':number,'status':error.code,'path':str(current/'plan.json') if plan is not None else None})
            save(current/'failure.json',{**feedback,'previous_plan_retained':previous is not None})
    save(directory/'result.json',{'status':'planning_failed','attempts':attempts,'previous_plan':previous})
    raise Failure('planning_failed','Translation planning exhausted its attempts; last usable plan and all feedback retained',attempts)


def candidate_contract(plan,files,mapping,usage,bundle):
    """Traceability only. rustc and behavior tests check the actual implementation."""
    support=bundle.get('loaded_adapter',{}).get('support',{}).get('files',{})
    for name,content in support.items():
        if name not in files:
            raise Failure('plan_contract_failed','Candidate omitted loaded support: '+name)
    validate_files({name:content for name,content in files.items() if name not in support})
    if 'src/lib.rs' not in files:raise Failure('plan_contract_failed','Missing crate-root source')
    if not isinstance(mapping,list) or not all(isinstance(m,dict) and isinstance(m.get('source'),str) and isinstance(m.get('rust'),str) for m in mapping):
        raise Failure('plan_contract_failed','Return source-to-Rust export mapping')
    nodes={n['id'] for p in bundle['programs'] for n in p['nodes']}
    bound={b['source'] for k in ['types','operations'] for b in bundle.get('loaded_adapter',{}).get('bindings',{}).get(k,[])}
    entries={e['source'] for e in plan['architecture']['exports']}
    mapped={m['source'] for m in mapping}
    if mapped-(nodes|bound|entries) or (nodes|entries)-mapped:
        raise Failure('plan_contract_failed','Map every G1 node and original export, including inlined/trait machinery',
            {'missing':sorted((nodes|entries)-mapped),'unknown':sorted(mapped-(nodes|bound|entries))})
    if not isinstance(usage,list) or not all(isinstance(u,dict) and isinstance(u.get('decision'),str) and isinstance(u.get('locations'),list) and u['locations'] and all(isinstance(x,str) for x in u['locations']) and isinstance(u.get('implementation'),str) and u['implementation'].strip() for u in usage):
        raise Failure('plan_contract_failed','Return adaptation usage locations and implementation descriptions')
    decisions={d['id'] for d in plan['adaptation']['decisions']}
    reported={u['decision'] for u in usage}
    if reported!=decisions:
        raise Failure('plan_contract_failed','Trace every adaptation decision in the candidate',
                      {'required':sorted(decisions),'missing':sorted(decisions-reported),'unknown':sorted(reported-decisions)})
    for u in usage:
        if any(loc.split(':',1)[0] not in files for loc in u['locations']):
            raise Failure('plan_contract_failed','Adaptation location names a missing source file')
    from .export_contract import check_exports
    export_check=check_exports(bundle,files,mapping)
    return {'status':'recorded','exports':mapping,'adaptation_usage':usage,'polymorphic_exports':export_check,
            'scope':'Reported source correspondence; no fixed file layout, signature, helper-call or semantic proof check'}
