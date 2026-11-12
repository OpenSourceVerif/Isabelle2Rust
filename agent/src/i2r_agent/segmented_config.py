"""Explicit new-workflow configuration and real Cargo materialization."""
from copy import deepcopy
from pathlib import Path
import json
import os
import tomllib
from .common import ROOT, Failure, read, save, merge
from .planning import manifest
from .task_context import fingerprint

WORKFLOW = 'source-translation'


def configure(cfg):
    cfg = deepcopy(cfg)
    policy = cfg.get('segmented')
    if not isinstance(policy, dict) or policy.get('schema_version') != 1:
        raise Failure('missing_segmented_config', 'Use the explicit source-translation configuration')
    required = ['development_performance', 'no_progress_limit', 'max_request_characters', 'review_categories']
    if any(k not in policy for k in required):
        raise Failure('missing_segmented_config', 'Missing required segmented policy', required)
    if cfg['generation']['workflow'] != WORKFLOW: raise Failure('unknown_workflow', cfg['generation']['workflow'])
    if policy.get('algorithm_policy') != 'preserve-source-route':
        raise Failure('invalid_segmented_config','This experiment requires explicit algorithm_policy=preserve-source-route, as selected by the user')
    for section, key in [('budgets','max_model_calls'),('repair','max_attempts'),('preprocessing','max_plan_attempts')]:
        if type(cfg[section].get(key)) is not int or cfg[section][key]<0:
            raise Failure('invalid_segmented_config','Budget must be a nonnegative integer',[section,key])
        if cfg[section].get(key) != 0 and not cfg.get('translation',{}).get('correctness_only'):
            raise Failure('legacy_budget_inheritance', 'New unlimited call allocation must explicitly use 0', [section,key])
    for k in ['source_page_characters','initial_source_characters','initial_code_characters','max_request_characters','no_progress_limit']:
        if not isinstance(policy.get(k),int) or policy[k]<=0:raise Failure('invalid_segmented_config','Expected positive integer',k)
    mandatory={'completeness','semantics','interfaces','ownership','support'}
    if not cfg.get('translation',{}).get('correctness_only'):mandatory.add('cost')
    if not isinstance(policy['review_categories'],list) or not mandatory<=set(policy['review_categories']):raise Failure('invalid_segmented_config','Missing mandatory quality review categories')
    if not cfg['repair'].get('enabled') or cfg['preprocessing'].get('mode')!='auto' or cfg['generation'].get('strategy')!='structured':raise Failure('invalid_segmented_config','Segmented workflow requires semantic analysis and correctness repair')
    for k in ['fixed','regression','differential']:
        if not cfg['testing'].get(k):raise Failure('invalid_segmented_config','Cannot disable a required validation stage',k)
    if cfg['generation']['workflow']=='source-translation':
        from .repair_controller import validate_config
        if 'early_support_tests' in cfg.get('translation',{}):
            if '_configuration_sources' not in cfg:
                cfg['_configuration_sources']=origins(cfg,[('caller-supplied effective configuration',cfg)])
            removed=cfg['translation'].pop('early_support_tests')
            if type(removed) is not bool:raise Failure('invalid_translation_config','Legacy early_support_tests must be boolean before removal')
            cfg['_configuration_sources'].setdefault('removed_legacy_settings',{})['translation.early_support_tests']={
                'value':removed,'reason':'Early semantic testing was removed from the workflow; full-program support tests remain.'}
            cfg['_configuration_sources']['origins'].pop('translation.early_support_tests',None)
        from .semantic_components import SMALL_PROGRAM_DEFAULTS
        missing_limits={k:v for k,v in SMALL_PROGRAM_DEFAULTS.items() if k not in cfg['translation']}
        if missing_limits and '_configuration_sources' not in cfg:
            cfg['_configuration_sources']=origins(cfg,[('caller-supplied effective configuration',cfg)])
        for key,value in missing_limits.items():
            cfg['translation'][key]=value
            cfg['_configuration_sources']['origins']['translation.'+key]='conservative joint-analysis grouping default (2026-11-09); not an empirical optimum'
        validate_config(cfg)
        if cfg['translation'].get('correctness_only'):
            if '_configuration_sources' not in cfg:
                cfg['_configuration_sources']=origins(cfg,[('caller-supplied effective configuration',cfg)])
            policy['support_tests']=True
            policy['development_performance']=False
            policy['review_categories']=[x for x in policy['review_categories'] if x!='cost']
            cfg['translation']['performance_refinement']=False
            cfg['performance']['enabled']=False
            cfg['testing']['final_cases']=0
            if '_configuration_sources' in cfg:
                for key in ['segmented.support_tests','segmented.development_performance','segmented.review_categories','translation.performance_refinement','performance.enabled','testing.final_cases']:
                    cfg['_configuration_sources']['origins'][key]='derived from translation.correctness_only'
    cfg['preprocessing']['max_context_chars'] = policy['max_request_characters']
    if cfg.get('translation',{}).get('correctness_only'):
        cfg.setdefault('context_management',{})['limit_authority']='provider'
        cfg['context_management']['local_character_limits']='inactive as rejection limits; retained only as optional compaction/page-cost hints'
        if '_configuration_sources' in cfg:
            for key in ['context_management.limit_authority','context_management.local_character_limits']:
                cfg['_configuration_sources']['origins'][key]='explicit user instruction: let the DeepSeek interface enforce its context limit'

    names=['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','CARGO_BUILD_TARGET','CARGO_TARGET_DIR','RUSTUP_TOOLCHAIN',
           'RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','CARGO_PROFILE_RELEASE_OPT_LEVEL','CARGO_PROFILE_RELEASE_LTO',
           'CARGO_PROFILE_RELEASE_CODEGEN_UNITS','CARGO_PROFILE_RELEASE_OVERFLOW_CHECKS','CARGO_PROFILE_RELEASE_PANIC']
    cfg['_runtime_environment']={n:os.environ.get(n) for n in names}
    if '_configuration_sources' in cfg:
        cfg['_configuration_sources']['origins']['_runtime_environment']='process environment at workflow start; credential variables excluded'
        cfg['_configuration_sources']['origins']['preprocessing.max_context_chars']='derived from segmented.max_request_characters'
        cfg['_configuration_sources']['effective_fingerprint']=fingerprint({k:v for k,v in cfg.items() if k!='_configuration_sources'})
    return cfg


def origins(cfg, layers):
    """Actual leaf origins, for study construction before any derived settings."""
    result = {}
    def visit(value, prefix, source):
        for k,v in value.items():
            key = prefix + k
            if isinstance(v,dict):visit(v,key+'.',source)
            else:result[key] = source
    for label, layer in layers: visit(layer,'',label)
    return {'origins':result,'effective_fingerprint':fingerprint(cfg)}


def rust_config(value, cfg):
    defaults={'edition':'2024','toolchain':cfg['tools']['rust_toolchain'],
        'dependencies':{},'build_dependencies':{},'features':{},'enabled_features':[],
        'default_features':True,'cfg':[],'target':None,'build_script':None}
    if not isinstance(value,dict) or set(value)-set(defaults):
        raise Failure('invalid_rust_config','Unknown Rust configuration fields',sorted(set(value)-set(defaults)) if isinstance(value,dict) else value)
    out={**defaults,**deepcopy(value)}
    if out['edition'] not in {'2021','2024'}:raise Failure('invalid_rust_config','Unsupported Rust edition')
    if not isinstance(out['toolchain'],str) or not out['toolchain']:raise Failure('invalid_rust_config','toolchain must be explicit')
    if out['target'] is not None and not isinstance(out['target'],str):raise Failure('invalid_rust_config','target must be a target triple')
    for k in ['enabled_features','cfg']:
        if not isinstance(out[k],list) or any(not isinstance(x,str) for x in out[k]):raise Failure('invalid_rust_config',k)
    if not isinstance(out['features'],dict) or any(not isinstance(v,list) or any(not isinstance(x,str) for x in v) for v in out['features'].values()):raise Failure('invalid_rust_config','features must map names to arrays')
    if not isinstance(out['default_features'],bool):raise Failure('invalid_rust_config','default_features must be boolean')
    if out['build_script'] is not None and not isinstance(out['build_script'],str):raise Failure('invalid_rust_config','build_script must be Rust text')
    try:manifest(out['dependencies'],transport='none',build_dependencies=out['build_dependencies'])
    except Failure as e:
        raise Failure('invalid_rust_config',
            'Cargo dependency versions must be EXACTLY pinned: use "=0.6.2", not "0.6.2" or "^0.6.2". '
            'Allowed forms: {"dashu-int":"=0.6.2"} or {"dashu-int":{"version":"=0.6.2","features":["std"],"default-features":false}}. '
            'This also applies to build_dependencies. '+str(e),
            {'received_dependencies':out['dependencies'],'received_build_dependencies':out['build_dependencies'],
             'cause':e.code,'purpose':'Freeze resolved dependency requests for reproducible code/config comparisons; Cargo.lock is archived too.'}) from e
    return out


def cargo_text(rc, package='i2r_candidate', transport='none'):
    text=manifest(rc['dependencies'],package=package,transport=transport,build_dependencies=rc['build_dependencies'])
    text=text.replace('edition = "2024"', 'edition = '+json.dumps(rc['edition']))
    text+='\n[features]\n'
    for k,v in rc['features'].items():text+=json.dumps(k)+' = '+json.dumps(v)+'\n'
    tomllib.loads(text)
    return text


def materialize(directory, files, rc):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    desired={**files,'rust-config.json':json.dumps(rc,indent=2)+'\n','Cargo.toml':cargo_text(rc), 'rust-toolchain.toml':'[toolchain]\nchannel = '+json.dumps(rc['toolchain'])+'\n'}
    if rc['build_script'] is not None:desired['build.rs']='#![forbid(unsafe_code)]\n'+rc['build_script']
    old=read(directory/'.managed-files.json') if (directory/'.managed-files.json').exists() else []
    for n in set(old)-set(desired):
        path=directory/n
        if path.is_file():path.unlink()
    for n,text in desired.items():
        path=directory/n;path.parent.mkdir(parents=True,exist_ok=True)
        if n=='src/lib.rs':text='#![forbid(unsafe_code)]\n'+text
        if not path.exists() or path.read_text()!=text:path.write_text(text)
    save(directory/'.managed-files.json',sorted(desired))
    return directory


def cargo_command(rc, cfg, verb, crate, *extra):
    args=[cfg['tools']['cargo'],'+'+rc['toolchain'],verb,'--manifest-path',str(Path(crate)/'Cargo.toml'),'--target-dir',str(Path(crate)/'target')]
    if rc['target']:args+=['--target',rc['target']]
    if rc['enabled_features']:args+=['--features',','.join(rc['enabled_features'])]
    if not rc['default_features']:args+=['--no-default-features']
    if rc['cfg']:args+=['--config','build.rustflags='+json.dumps([y for x in rc['cfg'] for y in ['--cfg',x]])]
    return args+list(map(str,extra))
