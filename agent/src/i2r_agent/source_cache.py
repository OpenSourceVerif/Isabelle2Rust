"""Strict mechanical source extraction cache; model analysis is always fresh."""
from copy import deepcopy
from pathlib import Path
from .common import read,digest,Failure
from . import tool_sources
from .source_input import numeric_contract

def load(project,cfg):
    spec=cfg.get('preprocessing',{}).get('source_cache')
    if not spec:return None
    path=Path(spec['path'])
    if digest(path)!=spec['sha256']:raise Failure('stale_source_cache','Mechanical cache hash changed')
    bundle=read(path)
    forbidden={'semantic_analysis','segmentation','prepared_identity','implementation_strategy','files','mapping','_context_archive'}
    if forbidden.intersection(bundle):raise Failure('stale_source_cache','Mechanical source cache must not contain model analysis/candidate/history',sorted(forbidden.intersection(bundle)))
    if Path(bundle['source_project']).resolve()!=Path(project).resolve():raise Failure('stale_source_cache','Source project changed')
    for name,h in bundle['source_hashes'].items():
        if digest(Path(project)/name)!=h:raise Failure('stale_source_cache','Source file changed',name)
    for row in bundle.get('source_catalog',[]):
        if row.get('sha256') and digest(row['path'])!=row['sha256']:raise Failure('stale_source_cache','Imported source changed',row['path'])
    wanted=numeric_contract(cfg)
    if any(bundle['numeric_policy'].get(k)!=v for k,v in wanted.items()):raise Failure('stale_source_cache','Numeric contract changed')
    tool_sources.verify(bundle['tool_sources'])
    return deepcopy(bundle)
