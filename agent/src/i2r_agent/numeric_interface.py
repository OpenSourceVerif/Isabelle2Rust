"""Opt-in, versioned numeric contract; legacy configuration is a strict no-op.

This is generation policy and trusted Cargo material, not a generated-source
rewriter. A paired experiment selects its backend only after code is frozen.
"""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import re
from .common import ROOT, Failure
from .task_context import fingerprint

SCHEMA = 'paired-numerics-v1'
RUNTIME = Path(__file__).with_name('numeric_runtime')
BACKENDS = {'arbitrary': 'i2r-arbitrary', 'checked': 'i2r-checked'}

GUIDANCE = '''PAIRED NUMERICS: This explicit experiment generates ONE implementation for TWO numeric backends. Use i2r_numeric::Nat for mathematical nat and i2r_numeric::Int for mathematical int/integer; local public type aliases are allowed. Keep all original generic parameters generic. Both opaque types have Clone, Default, Debug, Display, Eq, Ord, Hash, FromStr, and NEVER Copy. Do not access backend types/fields, import Dashu/num-bigint, branch on backend cfg/features, or use u128/i128 to implement mathematical operations. Source words retain their separate modular semantics. Native resident-container indices require a source-derived bound.
The controller supplies the immutable i2r-numeric path dependency and feature wiring. Do not add it or a bigint crate to rust_config.dependencies, and do not change reserved i2r-arbitrary/i2r-checked features or numeric_interface. Compilation initially uses arbitrary. No numeric optimization objective or machine-range bound applies to generation.
API (identical under both backends): Nat::zero(), Nat::one(), Nat::from(u8/u16/u32/u64/u128/usize), Int::zero(), Int::one(), Int::from(i8/i16/i32/i64/i128/isize/u8/u16/u32/u64); decimal literals use "...".parse::<Nat/Int>().expect("valid source literal"). Operators +,-,*,/,% accept owned or borrowed operands; += and *= accept owned/borrowed operands for both types; Int also supports -= and unary -. Nat subtraction truncates at zero. Nat division by zero returns zero and modulo zero returns the dividend. Int / is FLOOR division (round toward negative infinity), % has the divisor's sign; div by zero is zero, mod by zero is the dividend. Use these only when the exact source operation has this contract; never infer permission to replace a business recurrence.
Explicit methods: Nat::{is_zero, succ, sub_trunc(&Nat), try_add(&Nat), try_mul(&Nat), try_to_u128, try_to_usize, clamped_len(usize), try_shl(usize), shr(usize), try_pow(u32)}; Int::{is_zero,is_negative,try_add(&Int),try_sub(&Int),try_mul(&Int),try_neg,try_from_nat(&Nat),to_nat,try_to_i128,try_div_floor(&Int),mod_floor(&Int)}. try_* returns NumResult<T>=Result<T,NumericError>. Int::to_nat truncates negatives to zero. Nat::clamped_len is for source-clamped take/drop counts only. Do not assume other methods or conversions exist.
The arbitrary backend uses pinned Dashu UBig/IBig with no 128-bit limit. The checked backend uses u128/i128 and reports NumericError::Overflow (I2R_NUMERIC_OVERFLOW) on every unrepresentable intermediate/result, without wrap, saturation or bigint fallback. Operators panic with this exact explicit marker; callers may use the fallible methods instead. The same error API and code exist in both backends. Keep all tests/source obligations; arbitrary large-value tests remain mandatory where feasible. Wire conversion/decimal serialization belong outside benchmark_run. Generic numeric workload instantiations use Nat/Int, not an unchanged raw bigint type, so both builds actually exercise the selected backend.'''


def enabled(cfg):
    name = cfg.get('preprocessing', {}).get('numeric_interface')
    if name not in {None, SCHEMA}:
        raise Failure('invalid_numeric_interface', str(name))
    return name == SCHEMA


def runtime_files():
    return {name: (RUNTIME / name).read_text() for name in ['Cargo.toml', 'src/lib.rs']}


def contract():
    files = {name: hashlib.sha256(text.encode()).hexdigest() for name, text in runtime_files().items()}
    return {'schema': SCHEMA, 'package': 'i2r-numeric', 'version': '0.1.0',
            'runtime_sha256': fingerprint(files), 'files': files,
            'nat': 'i2r_numeric::Nat', 'int': 'i2r_numeric::Int',
            'backends': {'arbitrary': 'dashu-int =0.6.2 UBig/IBig', 'checked': 'u128/i128 with explicit overflow'},
            'copy': False, 'dispatch': 'compile-time Cargo feature', 'guidance': GUIDANCE}


def apply_policy(policy, cfg):
    if not enabled(cfg):
        return policy
    if cfg['preprocessing']['numeric_mode'] != 'arbitrary':
        raise Failure('invalid_numeric_interface', 'Paired generation is performed once under arbitrary semantics')
    result = deepcopy(policy)
    result['numeric_interface'] = contract()
    result['numeric_library'] = {'name': 'i2r-numeric', 'version': '=0.1.0',
                                 'nat': 'i2r_numeric::Nat', 'int': 'i2r_numeric::Int', 'integer': 'i2r_numeric::Int'}
    result['representation_selection'] = GUIDANCE
    return result


def bind_rust_config(rc, cfg):
    if not enabled(cfg):
        if 'numeric_interface' in rc:
            raise Failure('invalid_rust_config', 'numeric_interface requires explicit paired-numerics configuration')
        return rc
    expected = {k: v for k, v in contract().items() if k != 'guidance'}
    if rc.get('numeric_interface', expected) != expected:
        raise Failure('numeric_runtime_changed', 'The numeric runtime is controller-owned and immutable')
    if any(name in rc['dependencies'] for name in ['i2r-numeric', 'dashu-int', 'num-bigint', 'ibig']):
        raise Failure('invalid_rust_config', 'Use the supplied i2r_numeric::Nat/Int runtime; do not declare backend dependencies')
    if rc['build_script'] is not None or rc['cfg']:
        raise Failure('invalid_rust_config', 'Paired experiments do not permit business-code build scripts or custom cfg')
    rc = deepcopy(rc)
    rc['numeric_interface'] = expected
    for backend, feature in BACKENDS.items():
        value = ['i2r-numeric/' + backend]
        if feature in rc['features'] and rc['features'][feature] != value:
            raise Failure('invalid_rust_config', 'Reserved numeric feature: ' + feature)
        rc['features'][feature] = value
    if any(x in BACKENDS.values() for x in rc['features'].get('default', [])):
        raise Failure('invalid_rust_config', 'Numeric backend selection is explicit, never a default feature')
    active = [x for x in rc['enabled_features'] if x in BACKENDS.values()]
    if active and active != [BACKENDS['arbitrary']]:
        raise Failure('invalid_rust_config', 'Generate and validate the frozen program under arbitrary first')
    if not active:
        rc['enabled_features'].append(BACKENDS['arbitrary'])
    return rc


def backend_config(rc, backend):
    """Pure compile configuration; never edits business source or strategy."""
    if backend not in BACKENDS or rc.get('numeric_interface', {}).get('schema') != SCHEMA:
        raise Failure('invalid_numeric_backend', backend)
    out = deepcopy(rc)
    out['enabled_features'] = [x for x in out['enabled_features'] if x not in BACKENDS.values()] + [BACKENDS[backend]]
    return out


def cargo_dependency(rc, path='numeric-runtime'):
    if 'numeric_interface' not in rc:
        return ''
    verify_runtime(rc)
    return '\n[dependencies.i2r-numeric]\npath = ' + json.dumps(path) + '\ndefault-features = false\n'


def verify_runtime(rc):
    expected = {k: v for k, v in contract().items() if k != 'guidance'}
    if rc.get('numeric_interface') != expected:
        raise Failure('numeric_runtime_changed', 'Frozen numeric contract no longer matches runtime files')


def managed_runtime(rc):
    if 'numeric_interface' not in rc:
        return {}
    verify_runtime(rc)
    return {'numeric-runtime/' + k: v for k, v in runtime_files().items()}


def validate_candidate(files, rc):
    if 'numeric_interface' not in rc:
        return
    # Parse tokens so comments/documentation mentioning a backend are harmless.
    from tree_sitter import Language, Parser
    import tree_sitter_rust
    parser = Parser(Language(tree_sitter_rust.language()))
    failures = []
    for name, source in files.items():
        root = parser.parse(source.encode()).root_node
        todo = [root]
        while todo:
            node = todo.pop()
            if node.type in {'line_comment', 'block_comment'}:
                continue
            text = node.text.decode()
            if node.type in {'identifier', 'type_identifier'} and text in {'dashu_int', 'num_bigint', 'ibig'}:
                failures.append([name, node.start_point.row + 1, 'backend-specific path: ' + text])
            if node.type == 'attribute_item' and re.search(r'\bcfg(?:_attr)?\s*\([^)]*(?:feature|target_|test)', text) and not re.fullmatch(r'#\[cfg\(test\)\]', text.replace(' ', '')):
                failures.append([name, node.start_point.row + 1, 'conditional business implementation'])
            if node.type == 'macro_invocation' and text.startswith(('cfg!', 'include!', 'include_str!', 'include_bytes!', 'env!', 'option_env!')):
                failures.append([name, node.start_point.row + 1, 'external or conditional business implementation'])
            todo.extend(node.named_children)
    if failures:
        raise Failure('paired_numeric_contract_failed', 'Use one backend-independent business implementation', failures)


def validate_connector(files, rc):
    """Reject wire work in the reachable measured connector, without editing it.

    This checks explicit local calls and type aliases; source correspondence and
    a timing-boundary audit remain required for indirect callbacks/trait calls.
    """
    if 'numeric_interface' not in rc:
        return
    from tree_sitter import Language, Parser
    import tree_sitter_rust
    parser=Parser(Language(tree_sitter_rust.language()));functions={};aliases={}
    for source in files.values():
        todo=[parser.parse(source.encode()).root_node]
        while todo:
            node=todo.pop();todo.extend(node.named_children)
            name=node.child_by_field_name('name')
            if name is None:continue
            if node.type=='function_item':functions[name.text.decode()]=node
            if node.type in {'type_item','struct_item'}:aliases[name.text.decode()]=node.text.decode()
    problems=[];pending=['benchmark_run'];seen=set()
    while pending:
        name=pending.pop()
        if name in seen or name not in functions:continue
        seen.add(name);todo=[functions[name].child_by_field_name('body')]
        while todo:
            node=todo.pop()
            if node is None or node.type in {'line_comment','block_comment'}:continue
            todo.extend(node.named_children)
            if node.type=='call_expression':
                target=node.child_by_field_name('function')
                if target is None:continue
                text=target.text.decode();simple=text.rsplit('::',1)[-1]
                if text in {'observe','benchmark_prepare','benchmark_encode'} or re.search(r'\.(?:to_string|parse)\b',text):
                    problems.append(name+': '+text)
                if target.type=='identifier' and text in functions:pending.append(text)
            if node.type=='macro_invocation' and node.text.decode().startswith(('format!','write!','println!')):
                problems.append(name+': formatting in measured work')
    for name in ['Prepared','KernelResult']:
        seen_aliases=set();pending=[name]
        while pending:
            item=pending.pop()
            if item in seen_aliases:continue
            seen_aliases.add(item);text=aliases.get(item,'')
            if re.search(r'\b(?:WireInt|UBig|IBig|dashu_int)\b',text):problems.append(name+': raw wire/backend type')
            pending.extend(word for word in re.findall(r'\b[A-Za-z_]\w*\b',text) if word in aliases and word not in seen_aliases)
    if problems:
        raise Failure('paired_connector_boundary_failed',
                      'Prepared and KernelResult must use algorithm types (Nat/Int for generic numeric instantiations); convert wires only in prepare/encode, and call candidate operations directly from benchmark_run', sorted(set(problems)))


def prompt(text, cfg):
    """Numeric policy slot for existing role templates; legacy bytes unchanged."""
    if not enabled(cfg):
        return text
    text = re.sub(r'Checked uses u128/i128[^\n]*', GUIDANCE, text)
    text = re.sub(r'Checked nat/int are u128/i128.*?Keep original polymorphism and required operation semantics\.', GUIDANCE, text)
    if GUIDANCE not in text:
        text += '\n' + GUIDANCE
    if 'benchmark_prepare' in text:
        text += '\nPAIRED BINDING: Prepared/KernelResult must store algorithm types, not WireInt/UBig/IBig. benchmark_run cannot delegate to observe, benchmark_prepare or benchmark_encode; it must invoke candidate operations on already prepared values and return raw results. Reachable measured helpers cannot parse/format numeric strings. Use Nat/Int for generic mathematical numeric elements and callbacks. This is a source kernel boundary requirement, not permission to optimize the algorithm.\n'
    return text
