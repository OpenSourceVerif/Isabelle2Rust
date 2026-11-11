"""Fail closed when resuming preprocessing against different input identities."""
from pathlib import Path
from .common import ROOT, digest, read, Failure
from .task_context import fingerprint
from . import tool_sources, repair_knowledge


def identity(project, cfg):
    project=Path(project).resolve()
    files={str(p.relative_to(project)):digest(p) for p in project.rglob('*')
           if p.is_file() and (p.suffix in {'.thy','.ML'} or p.name in {'agent.toml','case.json','ROOT','ROOTS'})}
    metadata=read(project/'case.json') if (project/'case.json').exists() else {}
    for name in metadata.get('source_files',[]):files[str(Path(name).resolve())]=digest(Path(name))
    return fingerprint({'schema':1,'project':str(project),'files':files,
                        'config':{k:v for k,v in cfg.items() if k!='_configuration_sources'},
                        'prompts':{str(p.relative_to(ROOT)):digest(p) for p in (ROOT/'prompts').glob('*') if p.is_file()},
                        'implementation':{p.name:digest(p) for p in Path(__file__).parent.glob('*.py')},
                        'knowledge':repair_knowledge.manifest(),'tools':tool_sources.manifest()})


def validate(bundle, expected):
    if bundle.get('prepared_identity')!=expected:
        raise Failure('stale_preprocessing_cache','Prepared source/config/tool identity is missing or changed; preserve this run and use a new diagnostics directory')
    tool_sources.verify(bundle['tool_sources'])
    for row in bundle.get('source_catalog',[]):
        if row.get('available') and (not Path(row['path']).is_file() or digest(Path(row['path']))!=row.get('sha256')):
            raise Failure('stale_preprocessing_cache','Imported source changed',row['path'])
