"""Typed wrapper-only source facts, extracted separately from translation closure."""
from pathlib import Path
from .common import Failure,read,save,digest
from .task_context import fingerprint
from . import tool_sources
from .program_model import readable

def ownership_for(candidate_model,partition=None):
    """Bind actual validated scheduling ownership, never infer from mapping prose."""
    source=fingerprint(candidate_model)
    if not isinstance(partition,dict) or partition.get('source_version')!=source or partition.get('policy')!='semantic-components':
        return None  # Unknown/legacy/stale scheduling cannot relax protection.
    from .semantic_components import compose
    try:expected=compose(candidate_model,partition['boundaries'],partition['components'])
    except (Failure,KeyError,TypeError) as error:
        raise Failure('observation_ownership_changed','Cannot reproduce effective candidate ownership',str(error))
    actual_version=fingerprint({'composition':expected['version'],'grouping_decision':partition['grouping_decision']}) if partition.get('grouping_decision') else expected['version']
    if partition.get('version')!=actual_version:raise Failure('observation_ownership_changed','Partition identity mismatch')
    for key in ['owner','units','source_edges','boundaries','order']:
        if expected.get(key)!=partition.get(key):
            raise Failure('observation_ownership_changed','Actual ownership differs from recomputed source/boundary closure',key)
    proof={'schema':'effective-candidate-ownership-v1','source_identity':source,
           'boundaries':expected['boundaries'],'components':expected['components'],
           'partition_identity':expected['version'],'protected_sources':sorted(expected['owner'])}
    proof['identity']=fingerprint(proof)
    return proof


def resolve_ownership(candidate_model,proof):
    source=fingerprint(candidate_model)
    if proof is None:
        return set(candidate_model['entities']),{'mode':'conservative_all_source','source_identity':source,'reason':'Missing, legacy or stale effective ownership'}
    if not isinstance(proof,dict) or proof.get('schema')!='effective-candidate-ownership-v1' or proof.get('identity')!=fingerprint({k:v for k,v in proof.items() if k!='identity'}):
        raise Failure('observation_ownership_changed','Ownership proof schema/hash mismatch')
    if proof['source_identity']!=source:
        return set(candidate_model['entities']),{'mode':'conservative_all_source','source_identity':source,'stale_proof_identity':proof['identity']}
    from .semantic_components import compose
    try:expected=compose(candidate_model,proof['boundaries'],proof['components'])
    except (Failure,KeyError,TypeError) as error:
        raise Failure('observation_ownership_changed','Invalid ownership proof closure',str(error))
    if sorted(expected['owner'])!=proof.get('protected_sources') or expected['version']!=proof.get('partition_identity'):
        raise Failure('observation_ownership_changed','Ownership proof cannot omit or alter actual required definitions')
    return set(expected['owner']),{'mode':'effective_source_boundary_closure','proof':proof,
        'pruned_source_ids':sorted(set(candidate_model['entities'])-set(expected['owner']))}


def verify(bundle,project,candidate_model,ownership=None):
    project=Path(project).resolve()
    if Path(bundle['source_project']).resolve()!=project:raise Failure('observation_source_changed','Wrapper project mismatch')
    for name,h in bundle['source_hashes'].items():
        if digest(project/name)!=h:raise Failure('observation_source_changed','Wrapper source changed',name)
    for row in bundle.get('source_catalog',[]):
        if row.get('sha256') and digest(row['path'])!=row['sha256']:raise Failure('observation_source_changed','Imported source changed',row['path'])
    tool_sources.verify(bundle['tool_sources'])
    entries=bundle['source_model']['entries']
    if not entries or not all(n.startswith(('constant:Model.','constant:Kernel.')) for n in entries):raise Failure('observation_source_changed','Expected actual wrapper export roots',entries)
    # Candidate graph is never rewritten or extended by observation extraction.
    protected,ownership_evidence=resolve_ownership(candidate_model,ownership);model=bundle['source_model']
    extra={n:readable(e) for n,e in model['entities'].items() if n not in protected}
    return {'schema':'typed-wrapper-observation-v2','wrapper_source_hashes':bundle['source_hashes'],
        'wrapper_entries':entries,'candidate_required_calls':candidate_model['entries'],
        'protected_candidate_sources':sorted(protected),'candidate_source_identity':fingerprint(candidate_model),
        'candidate_ownership':ownership_evidence,
        'external_source_scope':'Complete extracted wrapper closure minus mechanically proven protected candidate definitions; no required external source fields are removed',
        'external_observation_helpers':list(extra.values()),
        'source_model_identity':fingerprint(model),
        'scope':'These are mechanically extracted Isabelle wrapper equations and dependencies. Implement Model/Kernel input construction, imported helper computations and result encoding in the connector only. Preserve their positions in kernel_prepare/kernel_run/kernel_encode. Call mapped candidate targets; do not copy or reimplement any protected candidate definition. A generic candidate typeclass parameter can receive a connector-local newtype instance grounded in the supplied external source equations and admitted boundary conditions. Rust orphan rules forbid implementing a foreign candidate trait directly on a foreign primitive; local newtypes and reversible wire conversions can supply observation instantiation without replacing candidate algorithms. Do not specialize away or reimplement protected generic algorithm/method bodies. An imported helper absent from candidate API is observation adaptation, never a reason to modify the candidate. This material contains source facts, not expected outputs or a Rust implementation.'}

def acquire(project,candidate_model,cfg,work,executor,ownership=None):
    spec=cfg.get('testing',{}).get('observation_source',{'enabled':True})
    if not spec:return None
    if not isinstance(spec,dict):raise Failure('observation_source_changed','Expected explicit wrapper extraction configuration')
    if spec.get('artifact'):
        path=Path(spec['artifact'])
        if digest(path)!=spec.get('sha256'):raise Failure('observation_source_changed','Pinned wrapper artifact changed')
        bundle=read(path)
    else:
        from .source_input import preprocess
        work=Path(work);path=work/'wrapper-bundle.json'
        bundle=read(path) if path.exists() else preprocess(project,cfg,work/'extraction',executor)
        if not path.exists():save(path,bundle)
    return verify(bundle,project,candidate_model,ownership)

def classify_issue(reply,mapping):
    if reply.get('binding_issue'):raise Failure('connector_binding_issue',str(reply['binding_issue']))
    if not reply.get('algorithm_issue'):return
    source=reply.get('candidate_source');evidence=reply.get('candidate_evidence')
    if source not in {r['source'] for r in mapping} or not isinstance(evidence,str) or not evidence.strip():
        raise Failure('connector_binding_issue','Unclassified observation obstacle: candidate defects require candidate_source in the supplied mapping and concrete candidate_evidence; missing wrapper helper material is binding-only',reply)
    raise Failure('connector_algorithm_defect',str(reply['algorithm_issue']),{'source':source,'evidence':evidence})
