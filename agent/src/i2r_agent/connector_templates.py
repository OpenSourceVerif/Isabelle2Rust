"""Narrow, source-matched behavioral adapters; unknown shapes stay explicit."""
import re
from pathlib import Path
from .common import digest
from .task_context import fingerprint
from .segmented_contract import interfaces,items

SCHEMA='checked-scalar-observer-v2'
SPECS={
 'fpp-multip':('FirstExample_Test.multip',2,'nat'),
 'fpp-add':('Recursion_Test.add',2,'nat'),
 'fpp-sub':('Recursion_Test.sub',2,'nat'),
 'fpp-fib':('Recursion_Test.fib',1,'nat'),
 'fpp-bool-and':('BasicDef_Test.AND',2,'bool'),
}
KERNEL=r'''theory Kernel imports Model begin
 definition kernel_prepare :: "nat list \<Rightarrow> nat list" where "kernel_prepare x = x"
 definition kernel_run :: "nat list \<Rightarrow> nat list" where "kernel_run x = Model.observe x"
 definition kernel_encode :: "nat list \<Rightarrow> nat list" where "kernel_encode x = x"
 lemma kernel_observation: "kernel_encode (kernel_run (kernel_prepare x)) = Model.observe x"
 by (simp add: kernel_prepare_def kernel_run_def kernel_encode_def) end'''
SCAFFOLD='''pub type WireInt = u128;
pub type Prepared = Vec<WireInt>;
pub type KernelResult = Vec<WireInt>;
pub fn benchmark_prepare(input: &[WireInt]) -> Prepared { input.to_vec() }
pub fn benchmark_run(input: Prepared) -> KernelResult { observe(&input) }
pub fn benchmark_encode(result: KernelResult) -> Vec<WireInt> { result }
'''


def normalized(text):return ' '.join(text.split())


def identity(project,files,mapping,rc,cfg):
    project=Path(project)
    from .observation_helpers import scenario_identity
    return fingerprint({'schema':SCHEMA,'implementation':digest(Path(__file__)),
        'observation_helpers_implementation':digest(Path(__file__).with_name('observation_helpers.py')),
        'list_observer_implementation':digest(Path(__file__).with_name('list_connector_templates.py')),
        'representation_scaffold_implementation':digest(Path(__file__).with_name('support_framework.py')),
        'scenarios':scenario_identity(project),
        'case_metadata':digest(project/'case.json') if (project/'case.json').exists() else None,
        'interfaces':interfaces(files),'overflow_markers':overflow_markers(files),'mapping':mapping,'rust_config':rc,
        'numeric':cfg['preprocessing']['numeric_mode'],'transport':cfg['testing']['transport'],
        'correctness_only':cfg.get('v8',{}).get('correctness_only')})


def overflow_markers(files):
    # Constant initializers are not algorithm bodies, but do bind this exact
    # error contract. interfaces() intentionally omits their values.
    return {path:[r['text'] for r in rows] for path,rows in items(files).items()
            if path.rsplit('::',1)[-1]=='I2R_NUMERIC_OVERFLOW' and any(r['kind']=='const_item' for r in rows)}


def _marked_unit_error(error,files):
    path,row=error;name=path.rsplit('::',1)[-1]
    if normalized(row.get('declaration',''))!='pub struct '+name+';':return False
    marker=path.rsplit('::',1)[0]+'::I2R_NUMERIC_OVERFLOW'
    rows=items(files).get(marker,[])
    if len(rows)!=1 or rows[0]['kind']!='const_item':return False
    declaration=normalized(rows[0]['text'])
    match=re.fullmatch(r'pub const I2R_NUMERIC_OVERFLOW\s*:\s*([\w:]+)\s*=\s*([\w:]+)\s*;',declaration)
    # Same-module short name or its exact crate-qualified spelling only. A
    # payload-bearing error, foreign alias or another initializer stays fallback.
    return bool(match and match[1] in {name,path} and match[2] in {name,path})


def _unique_type(api,name):
    candidates=[(path,rows[0]) for path,rows in api.items() if len(rows)==1 and
        (path==name or path.rsplit('::',1)[-1]==name) and rows[0]['kind'] in {'type_item','enum_item','struct_item'}]
    return candidates[0] if len(candidates)==1 else None


def _native_type(api,name,expected):
    if name==expected:return True
    found=_unique_type(api,name)
    return bool(found and re.fullmatch(r'pub type \w+\s*=\s*'+expected+r'\s*;',normalized(found[1].get('declaration',''))))


def generate(case,model,kernel,files,mapping,cfg):
    def no(reason):return {'status':'fallback_required','reason':reason,'schema':SCHEMA}
    if cfg['preprocessing']['numeric_mode']!='checked' or cfg['testing']['transport']!='native-u128':return no('Only checked native-u128 transport is supported')
    if case not in SPECS:return no('Source entry is outside the five admitted scalar families')
    source,arity,kind=SPECS[case];theory=source.split('.')[0]
    args=' '.join(f'(input!{i})' for i in range(arity))
    term=f'{source} {args}' if kind=='nat' else f'if {source} (input!0 mod 2 = 1) (input!1 mod 2 = 1) then 1 else 0'
    expected=f'theory Model imports {theory} begin definition observe :: "nat list \\<Rightarrow> nat list" where "observe input = [{term}]" end'
    if normalized(model)!=normalized(expected):return no('Model.thy does not exactly match the supported source observation')
    if normalized(kernel)!=normalized(KERNEL):return no('Kernel.thy is not the proved identity prepare/run/encode shape')
    rows=[r for r in mapping if r.get('source')=='constant:'+source]
    if len(rows)!=1:return no('Entry needs exactly one source-to-Rust mapping')
    path=rows[0].get('rust_item','')
    if not re.fullmatch(r'crate(?:::[A-Za-z_]\w*)+',path):return no('Entry mapping is not a fully qualified Rust item')
    api=interfaces(files);entry=api.get(path,[])
    if len(entry)!=1 or entry[0]['kind']!='function_item':return no('Entry is not a unique concrete function')
    sig=re.fullmatch(r'pub fn ([A-Za-z_]\w*)\(([^()]*)\)\s*->\s*(.+)',entry[0]['signature'].strip())
    if not sig:return no('Unsupported generic, borrowed, unsafe or qualified function signature')
    params=[p.strip() for p in sig[2].split(',') if p.strip()]
    if len(params)!=arity:return no('Rust/source arities differ')
    expected_type='u128' if kind=='nat' else 'bool'
    for param in params:
        parsed=re.fullmatch(r'(?:mut\s+)?[A-Za-z_]\w*\s*:\s*([A-Za-z_][\w:]*)',param)
        if not parsed or not _native_type(api,parsed[1],expected_type):return no('Argument type is not a verified scalar or unambiguous primitive alias')
    result_type=sig[3].strip();error_path=None
    result=re.fullmatch(r'(?:std::result::)?Result\s*<\s*([\w:]+)\s*,\s*([\w:]+)\s*>',result_type)
    if result:
        if kind!='nat' or not _native_type(api,result[1],'u128'):return no('Only checked natural Result output is supported')
        error=_unique_type(api,result[2])
        if not error:return no('Result error type is ambiguous or external')
        declaration=normalized(re.sub(r'(?m)//[^\n]*','',error[1].get('declaration','')));error_name=error[0].rsplit('::',1)[-1]
        is_unit=error_name=='I2R_NUMERIC_OVERFLOW' and declaration=='pub struct I2R_NUMERIC_OVERFLOW;'
        is_enum=bool(re.fullmatch(r'pub enum '+re.escape(error_name)+r'\s*\{\s*I2R_NUMERIC_OVERFLOW\s*,?\s*\}',declaration))
        if not (is_unit or is_enum or _marked_unit_error(error,files)):return no('Error is not exclusively the explicit numeric-overflow outcome')
        error_path=error[0].replace('crate::','i2r_candidate::',1)
    elif not _native_type(api,result_type,expected_type):return no('Output is not the source scalar type')
    rust_path=path.replace('crate::','i2r_candidate::',1)
    result_sig=f'std::result::Result<u128, {error_path}>' if error_path else expected_type
    arguments=', '.join(f'input[{i}]' if kind=='nat' else f'input[{i}] % 2 == 1' for i in range(arity))
    value='value' if kind=='nat' else 'if value { 1 } else { 0 }'
    call=f'entry({arguments})'
    if error_path:call+=' .unwrap_or_else(|_| panic!("I2R_NUMERIC_OVERFLOW"))'
    # The concrete function-pointer type is checked by Cargo too: aliases,
    # import shadowing and Result representations cannot silently alter the ABI.
    binding=f'''pub fn observe(input: &[WireInt]) -> Vec<WireInt> {{
    assert!(input.len() >= {arity}, "I2R_INPUT_DOMAIN");
    let entry: fn({', '.join([expected_type]*arity)}) -> {result_sig} = {rust_path};
    let value = {call};
    vec![{value}]
}}
'''
    return {'status':'generated','schema':SCHEMA,'files':{'src/lib.rs':SCAFFOLD+binding},
        'source':source,'rust_item':path,'arity':arity,'kind':kind,'result_error':error_path,
        'shared_characters':len(SCAFFOLD),'binding_characters':len(binding),
        'basis':'Exact Model/Kernel shape, source mapping and scalar interface; Cargo and dual-reference execution remain required.'}
