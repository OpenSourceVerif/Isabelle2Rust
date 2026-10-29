#!/usr/bin/env python3
"""AFP from a fresh checkout: initialize, scan, export, compile, audit, report."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import afp_common as common
from state import State


def runtime_arguments(config):
    values = ["--isabelle", config.get("isabelle", "isabelle")]
    if config.get("afp"):
        values += ["--afp", config["afp"]]
    for key, default in (("max_heap_mb", 4500), ("java_heap_mb", 1536), ("stack_space_mb", 512),
                         ("java_active_processors", 2), ("min_available_mb", 512)):
        values += ["--" + key.replace("_", "-"), str(config.get("resources", {}).get(key, default))]
    return values + ["--timeout", "0"]


def call(script, arguments, config_path=None):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    if config_path:
        env["AFP_CONFIG"] = str(Path(config_path).resolve())
    return subprocess.call([sys.executable, str(script), *arguments], cwd=common.PROJECT, env=env)


def smoke(args):
    """Real six-target export and Rust stages in an automatically cleaned directory."""
    import full
    from run import compile_crates
    options = common.arguments('Native smoke').parse_args(runtime_arguments(common.CONFIG))
    options.cargo = 'cargo +1.94.0'
    env, _ = common.environment(options)
    # The temporary location is deliberately outside the persistent work root;
    # failures are reported before it is removed.
    with tempfile.TemporaryDirectory(prefix='afp-smoke-') as temporary, common.experiment_lock():
        base = Path(temporary)
        State(base)
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
        if not result['passed']:
            errors = '\n'.join(p.read_text(errors='replace')[-4000:] for p in (base / 'logs').glob('*.log'))
            raise ValueError('Rust smoke failed:\n' + errors)
        return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--work", type=Path)
    sub = parser.add_subparsers(dest="phase", required=True)
    for name in ("check", "init", "scan-checkpoint", "export-checkpoint", "compile-checkpoint", "status", "report"):
        sub.add_parser(name)
    for name in ("scan", "run"):
        p = sub.add_parser(name)
        p.add_argument("--retry-failed", action="store_true")
    for name in ("export", "compile"):
        p = sub.add_parser(name)
        p.add_argument("--entries", nargs="+")
    p = sub.add_parser("audit")
    p.add_argument("--with-report", action="store_true")
    p = sub.add_parser("clean")
    p.add_argument("--apply", action="store_true")
    p.add_argument("--reset", choices=("compile", "export"))
    p = sub.add_parser("smoke")
    args = parser.parse_args(argv)
    config = common.configure(args.config)
    config_path = args.config or common.EXPERIMENT / "setup/server.local.json"
    config_path = config_path if config_path.is_file() else None
    selected = args.work or Path(config.get("work", common.WORK))
    from clean import validate_root
    base = validate_root(selected)
    runtime = runtime_arguments(config)
    if args.phase == "run":
        # Each boundary is durable and checked before the next stage. Repeating
        # this command resumes the same work root and stops at the first failure.
        phases = ["check"] + ([] if (base / "state.sqlite3").is_file() else ["init"])
        phases += ["scan", "scan-checkpoint", "export", "export-checkpoint", "compile",
                   "compile-checkpoint", "audit", "report", "audit"]
        options = ["--work", str(base)] + (["--config", str(config_path)] if config_path else [])
        for index, phase in enumerate(phases):
            extra = (["--retry-failed"] if phase == "scan" and args.retry_failed else
                     ["--with-report"] if phase == "audit" and index == len(phases) - 1 else [])
            print("[AFP " + phase + "]", flush=True)
            code = call(common.HERE / "afp.py", options + [phase] + extra, config_path)
            if code:
                return code
        return 0
    if args.phase == "check":
        return call(common.EXPERIMENT / "setup/check.py", ["--work", str(base)] +
                    (["--config", str(config_path)] if config_path else []), config_path)
    if args.phase == "clean":
        from clean import clean
        print(json.dumps(clean(base, args.reset, args.apply), indent=2))
        return 0
    if args.phase == "smoke":
        print(json.dumps(smoke(args), indent=2))
        return 0
    if args.phase in ("init", "scan"):
        arguments = ["--output-dir", str(base), *runtime]
        if args.phase == "init":
            arguments += ["--initialize", "--prepare-only"]
        elif args.retry_failed:
            arguments += ["--retry-failed"]
        return call(common.HERE / "scan_frozen.py", arguments, config_path)
    if not (base / "state.sqlite3").is_file():
        raise ValueError("Initialize the run first")
    if args.phase in ("audit", "report"):
        script = common.HERE / ("full_audit.py" if args.phase == "audit" else "full_report.py")
        return call(script, ["--output-dir", str(base)] +
                    (["--data-only"] if args.phase == "audit" and not args.with_report else []), config_path)
    arguments = [args.phase, "--output-dir", str(base), *runtime]
    if getattr(args, "entries", None):
        arguments += ["--entries", *args.entries]
    return call(common.HERE / "full.py", arguments, config_path)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError) as error:
        sys.exit(str(error))
