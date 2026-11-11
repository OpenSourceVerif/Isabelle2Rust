from __future__ import annotations

import json
from pathlib import Path

from .common import ROOT, Failure, save
from .references import rust_driver
from .planning import validate_files, manifest, normalize_files, validate_plan, PLAN_SCHEMA, require_generation_capabilities

SYSTEM = (ROOT/'prompts/generation-legacy-system.txt').read_text()


AUTO_SYSTEM = (ROOT/'prompts/generation-auto-system.txt').read_text()


def intern_program(programs):
    """Lossless structural sharing, especially for repeated Thingol case primitives."""
    table=[];index={}
    def intern(value):
        if isinstance(value,dict):node={k:intern(v) for k,v in value.items()}
        elif isinstance(value,list):node=[intern(v) for v in value]
        else:return value
        key=json.dumps(node,sort_keys=True,separators=(',',':'))
        if key not in index:index[key]=len(table);table.append(node)
        return {'$ref':index[key]}
    root=intern(programs)
    return {'encoding':'lossless DAG: {$ref:N} means table[N]; recursively expand references', 'root':root,'table':table}


def generation_context(bundle,strategy):
    if strategy=='source_only':
        from .context import stage_context
        result=stage_context(bundle,'generation');result.pop('programs',None)
        result['ablation']='source_only';return result
    from .context import stage_context
    return stage_context(bundle,'G1_generation')


def ownership_plans(bundle,cfg,provider,directory):
    from .context import skill,audit_request
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    payload={'task':'Propose one to three meaningful ownership alternatives for this complete program. Return JSON {"plans":[{"id":"short id","strategy":"concrete ownership decisions","rationale":"why useful","structural_changes":"none or necessary changes"}]}. Do not force multiple plans for a trivial program. Share semantic adaptation; preserve algorithm.',
        'max_plans':cfg['generation'].get('max_ownership_candidates',1),'program':generation_context(bundle,cfg['generation']['strategy'])}
    system=skill('ownership-optimization');prompt=audit_request(directory/'context-audit.json',system,payload)
    reply=provider.call(system,prompt)
    plans=reply.get('plans') if isinstance(reply,dict) else None
    if not isinstance(plans,list) or not plans or len(plans)>min(3,cfg['generation'].get('max_ownership_candidates',3)) or any(not isinstance(x,dict) or not x.get('strategy') for x in plans):
        raise Failure('invalid_ownership_plans','Expected 1..3 concrete ownership plans',reply)
    for i,p in enumerate(plans):p['id']='ownership-'+str(i+1)
    save(directory/'plans.json',plans)
    return plans


def generate(bundle,cfg,provider,directory,feedback=None,previous=None):
    from .context import skill,audit_request
    from .export_contract import polymorphic_exports
    from copy import deepcopy
    if cfg['testing'].get('transport')=='auto':
        cfg=deepcopy(cfg);cfg['testing']['transport']='dashu-ubig' # legacy caller compatibility; v5 uses a separate connector
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    compiler_only=feedback and feedback.get('status') in {'compile_failed','plan_contract_failed','invalid_candidate','invalid_model_response','incomplete_response','stalled_candidate'}
    context=({'effective_bindings':bundle.get('loaded_adapter',{}).get('bindings',{}),
              'support_root':bundle.get('loaded_adapter',{}).get('support',{}).get('root',''),
              'source_export_signatures':[{'source':n['id'],'signature':n['statement']['signature']}
                  for graph in bundle['programs'] for n in graph['nodes']
                  if n['id'] in graph['entries'] and 'signature' in n['statement']],
              'polymorphic_exports':polymorphic_exports(bundle),
              'adaptation_decisions':bundle.get('translation_plan',{}).get('adaptation',{}).get('decisions',[]),
              'observation_binding':bundle.get('observation_binding'),'kernel':bundle.get('kernel')}
             if compiler_only else generation_context(bundle,cfg['generation']['strategy']))
    if compiler_only:context['effective_bindings']={k:v for k,v in context['effective_bindings'].items() if k not in {'concrete_applications','support_modules'}}
    payload={'task':'Repair the actual candidate' if feedback else 'Translate the complete final Thingol graph',
        'program':context,'ownership_plan':bundle.get('ownership_plan'),
        'previous_candidate':previous,'previous_contract':bundle.get('previous_contract'),
        'feedback':feedback,'generation_constraints':{'numeric_policy':bundle.get('numeric_policy'),
        'clippy':'off','support_root_assembly':'model owns complete lib.rs; controller never prepends Rust declarations'}}
    system=AUTO_SYSTEM+'\n'+skill('ownership-optimization')
    prompt=audit_request(directory/'context-audit.json',system,payload)
    if not cfg.get('v8',{}).get('correctness_only') and len(prompt)>cfg['preprocessing']['max_context_chars']:raise Failure('context_budget_exceeded','Context exceeds published limit; graph not truncated')
    reply=provider.call(system,prompt)
    if not isinstance(reply,dict):raise Failure('invalid_candidate','Expected JSON object')
    if reply.get('revised_plan') is not None:raise Failure('adapter_revision_requested',reply.get('plan_revision_reason','Adapter correctness repair'),reply['revised_plan'])
    if reply.get('ownership_adapter') is not None:raise Failure('ownership_adapter_requested',reply.get('reason','Ownership binding synchronization'),reply['ownership_adapter'])
    files=dict(previous or {})
    incoming=reply.get('files',{})
    if not isinstance(incoming,dict):raise Failure('invalid_candidate','files must be object')
    files.update(incoming)
    for edit in reply.get('edits',[]):
        name,old,new=edit.get('file'),edit.get('old'),edit.get('new')
        if name not in files or not isinstance(old,str) or not old or files[name].count(old)!=1 or not isinstance(new,str):
            raise Failure('invalid_candidate','Edit requires one exact match in existing file',edit)
        files[name]=files[name].replace(old,new,1)
    if 'src/lib.rs' not in files:raise Failure('invalid_candidate','Return src/lib.rs')
    files,normalizations=normalize_files(files);save(directory/'format-normalizations.json',normalizations)
    support=deepcopy(bundle.get('loaded_adapter',{}).get('support',{'files':{},'root':''}))
    validate_files({n:c for n,c in files.items() if n not in support['files']})
    embedded={'src/'+x['module']+'.rs' for x in bundle.get('loaded_adapter',{}).get('bindings',{}).get('support_modules',[])}
    changed=[]
    for name,content in support['files'].items():
        if name in files and files[name]!=content:
            if name in embedded or not name.endswith('.rs') or not name.startswith('src/'):
                raise Failure('binding_sync_required','Changed Isabelle-embedded or build support; return ownership_adapter to synchronize declarations',bundle.get('translation_plan'))
            changed.append(name)
        files.setdefault(name,content)
        support['files'][name]=files[name]
    if changed and not (reply.get('ownership_changes') or bundle.get('previous_contract',{}).get('ownership_changes')):
        raise Failure('plan_contract_failed','Describe ownership changes to support files: '+', '.join(changed))
    save(directory/'ownership-support-changes.json',{'files':changed,'reason':reply.get('ownership_changes'),
        'validation':'compiled and behavior-tested; no automatic proof of ownership-only changes'})
    for name,content in files.items():
        p=directory/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(content)
    plan=deepcopy(bundle.get('translation_plan',{}))
    if plan:
        for name in plan['adapter']['rust_files']:
            if name in files:plan['adapter']['rust_files'][name]=files[name]
    (directory/'Cargo.toml').write_text(manifest(plan.get('dependencies',{}),transport=cfg['testing'].get('transport','dashu-ubig'),build_dependencies=plan.get('build_dependencies')))
    if bundle.get('observation_binding'):(directory/'src/main.rs').write_text(rust_driver('',False,transport=cfg['testing'].get('transport','dashu-ubig'),kernel=bool(bundle.get('kernel'))))
    actual_loaded={**bundle.get('loaded_adapter',{}),'support':support}
    if actual_loaded.get('theory'):
        from .storage import attach_adapter
        attach_adapter(directory,actual_loaded,bundle['programs'])
    previous_contract=bundle.get('previous_contract',{})
    metadata={k:reply.get(k,previous_contract.get(k,[] if k in {'mapping','adaptation_usage'} else '')) for k in ['mapping','adaptation_usage','ownership_changes','notes']}
    save(directory/'translation.json',metadata);save(directory/'migration-plan.json',plan)
    save(directory/'plan-revision.json',{'reason':'ownership support changes' if changed else 'none','revised':bool(changed)})
    return {'prompt':prompt,'files':files,'crate':str(directory),'translation_plan':plan,
            **metadata,'loaded_adapter':actual_loaded,'plan_revision_reason':'ownership-only support changes' if changed else 'none'}
