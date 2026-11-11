"""Small exact-source primitive proposals; never silently committed boundaries."""
from copy import deepcopy
from .task_context import fingerprint
from .segmentation import graph,project_functions
from .common import Failure

SCHEMA='explicit-source-primitive-defaults-v1'
FIELDS=['id', 'name', 'kind', 'source_type', 'execution_type', 'type_variables', 'execution_equations', 'constructors', 'fields', 'datatype', 'variables', 'abstract', 'supers', 'dependencies', 'instance_identity', 'instance_resolutions', 'specifications', 'function_input_equations', 'execution_sorts', 'type_dependencies', 'class_dependencies']
# Operational source identities recorded from the admitted Isabelle2025 source
# models (add, bool-and, isort). Caller lists and document locations are not
# semantics; type/constructor/equation/dependency changes reject the default.
HASHES={
 'type:Nat.nat':'2550a2f250346e4c637bf787134f1e121b68df4e60961d9fa989620657fb1626',
 'constant:Nat.zero_nat_inst.zero_nat':'f2a4d517b49fba99c2418f27abe3717470a4a07ae03ccee3c867653e8c02494c',
 'constant:Nat.Suc':'54d2c6ff2d448b4b2e947a4f9b94c0c824bfbab432b767c16aca156523b9d089',
 'type:HOL.bool':'bea1a8feae4d5e9d384af8fce0151c1195c80e7ee897e84c1cab28823595e4e0',
 'constant:HOL.True':'ec8134565ee170e6df05f58cbfa4fbe684a702961e4af15106a8d930d388a056',
 'constant:HOL.False':'b1ed811d3aeeb17f0b056d29e13390b3e0b4f0180aa8d2c15cac0e7622f0a62f',
 'constant:HOL.If':'4ba966c4cf5b9d5bc73dca58d43df3709281ff6506dc599045edecf48729b8fa'}


def operational_identity(entity):return fingerprint({k:entity[k] for k in FIELDS if k in entity})


def proposals(model,numeric):
    mode=numeric.get('mode') if isinstance(numeric,dict) else numeric
    if mode not in {'checked','arbitrary'}:return []
    reachable=set(graph(model)['edges']);mandatory=project_functions(model);rows=[]
    for source,expected in HASHES.items():
        entity=model['entities'].get(source)
        if source not in reachable or source in mandatory or not entity or operational_identity(entity)!=expected:continue
        if source.startswith('type:Nat') or source.startswith('constant:Nat'):
            representation='u128' if mode=='checked' else 'dashu_int::UBig (dashu-int =0.6.2)'
            conditions=[f'Natural-number representation is {representation}; preserve every source recurrence and generic caller.',
                'Zero is exactly 0; Suc is n+1. Checked Suc must reject u128::MAX with explicit I2R_NUMERIC_OVERFLOW, never wrap or saturate.' if mode=='checked' else 'Zero is exactly 0 and successor is unbounded n+1; no narrowing to machine integers.',
                'This is a primitive representation default, not permission to simplify business equations or narrow polymorphic types.']
            basis='Exact admitted Nat datatype/constructor operational source identity; natural zero and successor.'
        else:
            conditions=['Use bool/true/false for this exact HOL boolean datatype.',
                'HOL.If selects only the chosen branch. Preserve lazy evaluation and branch ownership; do not eagerly evaluate both branches or add Clone/Copy bounds to arbitrary result types.',
                'No default equality/order adapter is inferred for other types or class instances.']
            basis='Exact admitted HOL boolean constructors and If equations; branch-selective source semantics.'
        rows.append({'source':source,'kind':'native' if source.startswith('type:') else 'inlined','basis':basis,'conditions':conditions,
                     'default_identity':expected,'default_schema':SCHEMA})
    return rows


def apply(reply,available):
    flag=reply.get('use_default_adaptations',False)
    if type(flag) is not bool:raise Failure('invalid_default_adaptations','use_default_adaptations must be explicit boolean')
    explicit=reply.get('boundaries',[])
    if not isinstance(explicit,list):raise Failure('invalid_default_adaptations','boundaries must be an array')
    revoked=reply.get('revoke_default_adaptations',[])
    allowed={r['source'] for r in available}
    if not isinstance(revoked,list) or any(not isinstance(n,str) or n not in allowed for n in revoked) or len(set(revoked))!=len(revoked):
        raise Failure('invalid_default_adaptations','Revoke only unique supplied default source IDs')
    overridden={r.get('source') for r in explicit if isinstance(r,dict)}
    selected=[deepcopy(r) for r in available if flag and r['source'] not in set(revoked)|overridden]
    return selected+explicit,{'schema':SCHEMA,'explicitly_accepted':flag,'available':[r['source'] for r in available],
        'selected':[r['source'] for r in selected],'revoked':revoked,'overridden':sorted(overridden&allowed),
        'identity':fingerprint(available),'policy':'No defaults without explicit acceptance; source coverage/partition validators still run.'}
