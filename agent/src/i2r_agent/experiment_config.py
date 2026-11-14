"""Explicit experiment switches, frozen with the run and inherited by workers.

An absent experiment file (including --off alone) changes no legacy config key.
"""
from copy import deepcopy
from pathlib import Path
from .common import Failure, read, save
from .numeric_interface import SCHEMA

SOURCE_LIMITS = {'directions': 2, 'calls': 10, 'seconds': 1200,
                 'reserve_rust_calls': 12, 'reserve_rust_seconds': 1800}
SOURCE_ARGUMENTS = {'calls': 'source_calls', 'seconds': 'source_seconds',
                    'reserve_rust_calls': 'rust_reserve_calls', 'reserve_rust_seconds': 'rust_reserve_seconds'}


def arguments(parser):
    numeric = parser.add_mutually_exclusive_group()
    numeric.add_argument('--arbitrary', dest='numeric_variant', action='store_const', const='arbitrary', default=None,
                         help='Use the original arbitrary-precision generation policy')
    numeric.add_argument('--checked', dest='numeric_variant', action='store_const', const='checked',
                         help='Use the original checked integer generation policy')
    numeric.add_argument('--paired-numerics', dest='numeric_variant', action='store_const', const='paired',
                         help='Generate one common-numeric implementation, then compare both backends')
    optimization = parser.add_mutually_exclusive_group()
    optimization.add_argument('--off', dest='optimization_mode', action='store_const', const='off', default=None,
                              help='Disable optimization (default)')
    optimization.add_argument('--rust-only', dest='optimization_mode', action='store_const', const='rust-only')
    optimization.add_argument('--full', dest='optimization_mode', action='store_const', const='full')
    parser.add_argument('--optimization-calls', type=int, default=None,
                        help='Per-case optimization call limit (default 25, including repairs)')
    parser.add_argument('--optimization-seconds', type=int, default=None,
                        help='Per-case optimization elapsed-time limit (default 3600)')
    parser.add_argument('--source-calls', type=int, default=None, help='Full source-phase call cap, including proof repair and source realization')
    parser.add_argument('--source-seconds', type=int, default=None, help='Full source-phase elapsed-time cap')
    parser.add_argument('--rust-reserve-calls', type=int, default=None, help='Calls reserved for Rust refinement after Full source work')
    parser.add_argument('--rust-reserve-seconds', type=int, default=None, help='Seconds reserved for Rust refinement after Full source work')


def initialize(run, args):
    path = Path(run) / 'experiment.json'
    numeric = getattr(args, 'numeric_variant', None)
    optimization = getattr(args, 'optimization_mode', None)
    requested_limits = {k: getattr(args, a, None) for k, a in [
        ('max_model_calls', 'optimization_calls'), ('max_seconds', 'optimization_seconds')]}
    requested_source = {k: getattr(args, a, None) for k, a in SOURCE_ARGUMENTS.items()}
    if any(v is not None and v < 1 for v in [*requested_limits.values(), *requested_source.values()]):
        raise Failure('invalid_optimization_budget', 'Optimization budgets must be positive')
    if path.exists():
        old = read(path)
        if old.get('schema') != 1 or (numeric is not None and numeric != old['numeric']) or (optimization is not None and optimization != old['optimization']):
            raise Failure('experiment_changed', 'Run switches are frozen; use a new run for a different experiment')
        if any(v is not None and old.get('optimization_limits', {}).get(k) != v for k, v in requested_limits.items()):
            raise Failure('experiment_changed', 'Optimization budgets are frozen')
        if any(v is not None and old.get('optimization_limits', {}).get('source_limits', SOURCE_LIMITS).get(k) != v for k, v in requested_source.items()):
            raise Failure('experiment_changed', 'Source-phase budgets are frozen')
        if any(v is not None for v in requested_source.values()) and old['optimization'] != 'full':
            raise Failure('invalid_optimization_budget', 'Source-phase budgets require --full')
        return old
    if any(v is not None for v in requested_source.values()) and optimization != 'full':
        raise Failure('invalid_optimization_budget', 'Source-phase budgets require --full')
    if any(v is not None for v in requested_limits.values()) and optimization in {None, 'off'}:
        raise Failure('invalid_optimization_budget', 'Select --rust-only or --full to set a search budget')
    if numeric is None and optimization in {None, 'off'}:
        return None
    if (Path(run) / 'release.json').exists():
        raise Failure('experiment_changed', 'Cannot add experiment switches to an existing legacy run')
    value = {'schema': 1, 'numeric': numeric, 'optimization': optimization or 'off'}
    if optimization in {'rust-only', 'full'}:
        value['optimization_limits'] = {k: requested_limits[k] or v for k, v in
                                       [('max_model_calls', 25), ('max_seconds', 3600)]}
        if any(v is not None for v in requested_source.values()):
            source = {**SOURCE_LIMITS, **{k: v for k, v in requested_source.items() if v is not None}}
            total = value['optimization_limits']
            if source['calls'] + source['reserve_rust_calls'] > total['max_model_calls'] or source['seconds'] + source['reserve_rust_seconds'] > total['max_seconds']:
                raise Failure('invalid_optimization_budget', 'Source cap plus reserved Rust allowance must fit the total budget')
            total['source_limits'] = source
    save(path, value)
    return value


def apply(cfg, run):
    path = Path(run) / 'experiment.json'
    if not path.exists():
        return cfg
    return apply_selection(cfg, read(path))


def apply_selection(cfg, selection):
    mode = selection['numeric']
    if mode is None:
        return cfg
    out = deepcopy(cfg)
    if mode == 'paired':
        out['preprocessing'].update(numeric_mode='arbitrary', numeric_library='dashu-int', numeric_interface=SCHEMA)
    elif mode in {'arbitrary', 'checked'}:
        out['preprocessing']['numeric_mode'] = mode
        out['preprocessing'].pop('numeric_interface', None)
        if mode == 'checked':
            out['preprocessing'].pop('numeric_library', None)
    else:
        raise Failure('invalid_numeric_mode', str(mode))
    return out
