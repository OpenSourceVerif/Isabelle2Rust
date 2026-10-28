#!/usr/bin/env python3
"""The supported entry point: verify frozen inputs, start fresh, export, compile, audit."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import afp_common as common


def runtime_arguments(config):
    """One serial, proof-checked, unlimited resource policy for every phase."""
    values = ['--isabelle', config.get('isabelle', 'isabelle')]
    for key, option in [('afp', '--afp'), ('compiler_settings', '--compiler-settings')]:
        if config.get(key):
            values += [option, str(config[key])]
    resources = config.get('resources', {})
    for key, default in [('max_heap_mb', 4500), ('java_heap_mb', 1536),
                         ('stack_space_mb', 512), ('java_active_processors', 2),
                         ('min_available_mb', 512)]:
        values += ['--' + key.replace('_', '-'), str(resources.get(key, default))]
    return values + ['--timeout', '0']


def call(script, arguments, config_path=None):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    if config_path:
        env['AFP_CONFIG'] = str(Path(config_path).resolve())
    return subprocess.call([sys.executable, str(script), *arguments], cwd=common.PROJECT, env=env)


def scan_root():
    return common.EXPERIMENT / 'scan'


def verify_frozen():
    import frozen
    return frozen.verify(scan_root(), common.EXPERIMENT / 'setup/frozen-files.jsonl', frozen.EXPECTED)


def owned(base):
    """A stage must target a fresh continuation, never retained scan/report data."""
    from clean import targets
    targets(base)  # Validates the marker and all protected roots without deleting.
    if not (base / 'candidate-baseline.json').is_file():
        raise ValueError('Initialize the candidate handoff first')


def require_run_sources(base, config):
    """Stop before native work if frozen installations or recorded tools changed."""
    from frozen import verify_sources
    from scan_store import file_digest
    verify_sources(scan_root(), config['afp'], config['isabelle'])
    sources = common.read_json(base / 'source-manifest.json', {})
    if not sources:
        raise ValueError('Missing run source inventory')
    for name, expected in sources.items():
        path = common.resolve_path(name)
        if not path.is_file() or file_digest(path) != expected:
            raise ValueError('Run source changed; phase stopped before execution: ' + name)


def smoke(args):
    """Real six-target export and Rust stages in an automatically cleaned directory."""
    import full
    from run import compile_crates
    options = common.arguments('Native smoke').parse_args(runtime_arguments(common.CONFIG))
    options.cargo = 'cargo +1.94.0'
    env, _ = common.environment(options)
    # The temporary location is deliberately outside the persistent work root;
    # failures are reported before it is removed, with an optional saved receipt.
    with tempfile.TemporaryDirectory(prefix='afp-smoke-') as temporary, common.experiment_lock():
        base = Path(temporary)
        env['CARGO_TARGET_DIR'] = str(base / '_build/cargo-target')
        exported = full.fixture(base, options, env)
        manifests = sorted(base.glob('tooling/export-fixture/attempt-*/artifacts/**/Cargo.toml'))
        if len(manifests) != 1:
            raise ValueError('Smoke expected one successful singleton Rust crate')
        optimizer_target = base / '_build/optimizer-target'
        built = common.command(['cargo', '+1.94.0', 'build', '--locked', '--offline',
                   '--manifest-path', str(common.PROJECT / 'optimize/Cargo.toml'), '--bin', 'cargo-opt',
                   '--target-dir', str(optimizer_target)], base / 'optimizer.log', options, env)
        if built['status'] != 'passed':
            raise ValueError('Smoke optimizer build failed: ' + (base / 'optimizer.log').read_text()[-8000:])
        first = compile_crates(manifests, 'stage1', options, env, base / 'logs')
        out = base / 'rust-stage2'
        optimized = common.command(['sh', str(common.PROJECT / 'scripts/with-stack.sh'), '65536',
                  str(optimizer_target / 'debug/cargo-opt'), str(manifests[0].parent),
                  '--out-dir', str(out)], base / 'optimization.log', options, env)
        second = compile_crates([out / 'Cargo.toml'], 'stage2', options, env, base / 'logs') if optimized['status'] == 'passed' else {'status': 'blocked'}
        result = {'passed': all(x['status'] == 'passed' for x in (first, optimized, second)),
                  'six_language_export': exported['status'], 'stage1': first['status'],
                  'optimization': optimized['status'], 'stage2': second['status'],
                  'generated_programs_executed': False, 'temporary_artifacts_removed': True}
        if args.receipt:
            common.write_json(args.receipt.resolve(), result)
        if not result['passed']:
            errors = '\n'.join(p.read_text(errors='replace')[-4000:] for p in (base / 'logs').glob('*.log'))
            raise ValueError('Rust smoke failed:\n' + errors)
        return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, help='server-local JSON (default: setup/server.local.json)')
    parser.add_argument('--work', type=Path, help='override the dedicated work directory')
    sub = parser.add_subparsers(dest='phase', required=True)
    for name in ('check', 'verify', 'verify-report', 'init', 'export-checkpoint', 'status', 'report'):
        sub.add_parser(name)
    p = sub.add_parser('audit')
    p.add_argument('--with-report', action='store_true', help='also audit the newly generated work/report')
    for name in ('export', 'compile'):
        p = sub.add_parser(name)
        p.add_argument('--entries', nargs='+', help='optional bounded entry selection; the gate still covers all rows')
    p = sub.add_parser('clean')
    p.add_argument('--apply', action='store_true', help='perform the previewed cleanup')
    p.add_argument('--reset', choices=('compile', 'export'), help='explicitly reset retained stage results too')
    p = sub.add_parser('smoke')
    p.add_argument('--receipt', type=Path, help='optional compact result outside the temporary directory')
    p = sub.add_parser('path')
    p.add_argument('historical', help='original repository-relative or absolute evidence path')
    args = parser.parse_args(argv)
    config = common.configure(args.config)
    selected_work = args.work or Path(config.get('work', common.WORK))
    if selected_work.is_symlink():
        raise ValueError('A work root symlink is not accepted')
    base = selected_work.resolve()
    config_path = args.config or (common.EXPERIMENT / 'setup/server.local.json')
    if not config_path.is_file():
        config_path = None
    if args.phase == 'verify':
        answer = verify_frozen()
    elif args.phase == 'verify-report':
        from retained_report import verify
        answer = verify(common.EXPERIMENT)
    elif args.phase == 'check':
        # Check the selected work root, including a command-line override,
        # before initialization creates anything in that directory.
        check_arguments = ['--work', str(base)]
        if config_path:
            check_arguments += ['--config', str(config_path)]
        return call(common.EXPERIMENT / 'setup/check.py', check_arguments, config_path)
    elif args.phase == 'path':
        records = [json.loads(s) for s in (common.EXPERIMENT / 'report/selected-evidence.jsonl').read_text().splitlines()]
        origin = args.historical
        old = '/home/spring/Isabelle2Rust/Isabelle2Rust/'
        if origin.startswith(old):
            origin = origin[len(old):]
        found = next((common.EXPERIMENT / x['path'] for x in records if x['original'] == origin), None)
        found = found or common.resolve_path(args.historical)
        if not found.is_file():
            raise ValueError('Historical reference was not retained: ' + args.historical)
        print(found)
        return 0
    elif args.phase == 'smoke':
        answer = smoke(args)
    elif args.phase == 'clean':
        from clean import clean
        answer = clean(base, args.reset, args.apply)
    elif args.phase == 'init':
        import full
        from frozen import verify_sources
        # Initialization refuses nonempty roots and repeated calls before any
        # writes; it cannot adopt old exports, caches, or compilation results.
        if base.exists() and any(base.iterdir()):
            raise ValueError('Initialization requires an empty work directory')
        from clean import validate_root
        validate_root(selected_work)
        verify_frozen()
        if not config.get('afp') or not config.get('isabelle'):
            raise ValueError('Generate the server-local configuration first')
        verify_sources(scan_root(), config['afp'], config['isabelle'])
        with common.experiment_lock():
            answer = full.initialize_candidates(base, scan_root())
            # Immutable per-entry results bound memory as the native receipt
            # inventory grows, while preserving the exact accepted scan rows.
            full.compact_results(base)
            common.write_json(base / 'afp-work.json', {'kind': 'afp-work-v1', 'created': common.timestamp(),
                                                     'baseline_sha256': answer['snapshot_sha256']})
    else:
        owned(base)
        if args.phase in ('audit', 'report'):
            script = common.HERE / ('full_audit.py' if args.phase == 'audit' else 'full_report.py')
            return call(script, ['--output-dir', str(base)] + (['--data-only'] if args.phase == 'audit' and not args.with_report else []), config_path)
        if args.phase != 'status':
            require_run_sources(base, config)
        arguments = [args.phase, '--output-dir', str(base), *runtime_arguments(config)]
        if getattr(args, 'entries', None):
            arguments += ['--entries', *args.entries]
        return call(common.HERE / 'full.py', arguments, config_path)
    print(json.dumps(answer, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, OSError) as error:
        sys.exit(str(error))
