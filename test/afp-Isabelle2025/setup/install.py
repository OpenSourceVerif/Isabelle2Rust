#!/usr/bin/env python3
"""Idempotent, checksum-verified Ubuntu x86_64 setup; --dry-run changes nothing."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile

SETUP = Path(__file__).resolve().parent
EXPERIMENT = SETUP.parent
REPOSITORY = EXPERIMENT.parents[1]
LOCK = json.loads((SETUP / 'dependencies.json').read_text())
sys.path.insert(0, str(EXPERIMENT / 'tools'))
from scan_store import file_digest
import afp_common as common


def run(argv, env=None, cwd=None):
    """Keep all paths as argument-vector elements, including spaces in roots."""
    print('+', ' '.join(map(str, argv)), flush=True)
    subprocess.run([str(x) for x in argv], check=True, env=env, cwd=cwd)


def fetch(name, cache):
    """A partial download is never accepted or extracted without its pinned SHA."""
    item = LOCK[name]
    path = cache / item['url'].rsplit('/', 1)[1]
    cache.mkdir(parents=True, exist_ok=True)
    if not path.is_file():
        partial = path.with_name(path.name + '.part')
        run(['curl', '-fL', '--retry', '3', '--continue-at', '-', '-o', partial, item['url']])
        if file_digest(partial) != item['sha256']:
            raise ValueError('Downloaded digest mismatch: ' + name)
        partial.rename(path)
    if file_digest(path) != item['sha256']:
        raise ValueError('Cached digest mismatch: ' + name)
    return path


def extract(archive, destination):
    """Reject archive paths and link targets that could escape the staging root."""
    destination = Path(destination).resolve()
    with tarfile.open(archive) as source:
        for item in source:
            path = destination / item.name
            if not path.resolve().is_relative_to(destination) or item.isdev():
                raise ValueError('Unsafe archive member: ' + item.name)
            if item.issym() or item.islnk():
                target = path.parent / item.linkname if item.issym() else destination / item.linkname
                if not target.resolve().is_relative_to(destination):
                    raise ValueError('Unsafe archive link: ' + item.name)
            # Check each member after earlier links have been materialized,
            # including on Python versions without tarfile's data filter.
            options = {'filter': 'data'} if hasattr(tarfile, 'data_filter') else {}
            source.extract(item, destination, **options)


def unpack(name, prefix, top, destination):
    if destination.exists():
        return  # Final version/source checks validate reused installations.
    archive = fetch(name, prefix / 'downloads')
    with tempfile.TemporaryDirectory(prefix='.afp-install-', dir=prefix) as temporary:
        stage = Path(temporary)
        extract(archive, stage)
        tree = stage / top
        if name == 'afp':
            patch = SETUP / LOCK['afp']['patch']
            if file_digest(patch) != LOCK['afp']['patch_sha256']:
                raise ValueError('Frozen AFP patch digest mismatch')
            run(['patch', '--batch', '--forward', '-p1', '-i', patch], cwd=tree)
        tree.rename(destination)


def make_config(args):
    """Generate local absolute paths; historical machine locations are never defaults."""
    prefix = args.prefix.resolve()
    config = {'repository': str(REPOSITORY), 'isabelle': str(args.isabelle or prefix / 'Isabelle2025/bin/isabelle'),
              'afp': str(args.afp or prefix / 'afp-2025-frozen'),
              'work': str((args.work or EXPERIMENT / 'work').resolve()),
              'compiler_settings': str(args.config.with_name('compiler-settings.local.json').resolve()),
              'user_home': str((args.user_home or prefix / 'user').resolve()),
              'cargo_bin': str(Path(os.environ.get('CARGO_HOME', Path.home() / '.cargo')) / 'bin'),
              'resources': {'max_heap_mb': args.max_heap_mb, 'java_heap_mb': args.java_heap_mb,
                            'stack_space_mb': 512, 'java_active_processors': 2, 'min_available_mb': 512},
              'path_map': {}}
    go = args.go_root or prefix / 'go-1.26.8'
    compilers = {'ISABELLE_CC': shutil.which('cc') or '/usr/bin/cc',
                 'ISABELLE_OCAMLFIND': str(args.ocamlfind) if args.ocamlfind else shutil.which('ocamlfind') or '/usr/bin/ocamlfind',
                 'ISABELLE_SMLNJ': shutil.which('sml') or '/usr/bin/sml',
                 'ISABELLE_GOEXE': str(go / 'bin'), 'ISABELLE_GOROOT': str(go),
                 'ISABELLE_CAKEML_HOME': str(args.cakeml or prefix / 'cakeml-2.0')}
    return config, compilers


def plan(args):
    """Expose every installation action before downloads or privileged apt calls."""
    config, compilers = make_config(args)
    return {'platform': LOCK['platform'], 'prefix': str(args.prefix.resolve()),
            'system_packages': [] if args.skip_system_packages or args.configure_only else LOCK['system_packages'],
            'downloads': {} if args.configure_only else {k: LOCK[k] for k in ('isabelle', 'afp', 'go', 'cakeml', 'rustup')},
            'rustlightast': LOCK['rustlightast'], 'rust': LOCK['rust'],
            'steps': ['apt update/install', 'verify and unpack archives', 'apply frozen AFP additions patch',
                      'install Rust 1.94.0, rustfmt, clippy', 'clone/check pinned sibling RustLightAST',
                      'register fixed AFP in isolated Isabelle USER_HOME', 'Isabelle ghc_setup',
                      'cargo fetch --locked (optimizer and generated-crate seed)',
                      'write server-local config and installed package versions',
                      'build fresh Rust/Go prerequisite heaps serially with proofs and timeout_build=false',
                      'check versions, conditions, source identity, writability and frozen evidence']
                     if not args.configure_only else ['write server-local configuration for existing installations'],
            'config_path': str(args.config.resolve()), 'config': config, 'compilers': compilers,
            'generated_programs_executed': False}


def install(args):
    config, compilers = make_config(args)
    env = dict(os.environ, USER_HOME=config['user_home'])
    env.pop('ISABELLE_IDENTIFIER', None)
    env['PATH'] = str(Path.home() / '.cargo/bin') + os.pathsep + env['PATH']
    if not args.configure_only:
        if platform.system() != 'Linux' or platform.machine() != 'x86_64':
            raise ValueError('Ubuntu x86_64 required')
        if not args.skip_system_packages:
            sudo = [] if os.geteuid() == 0 else ['sudo']
            run([*sudo, 'apt-get', 'update'])
            run([*sudo, 'apt-get', 'install', '-y', *LOCK['system_packages']])
        args.prefix.mkdir(parents=True, exist_ok=True)
        prefix = args.prefix.resolve()
        unpack('isabelle', prefix, 'Isabelle2025', Path(config['isabelle']).parent.parent)
        unpack('afp', prefix, 'afp-2025-03-17', Path(config['afp']))
        unpack('go', prefix, 'go', prefix / 'go-1.26.8')
        unpack('cakeml', prefix, 'cakeml-2.0', Path(compilers['ISABELLE_CAKEML_HOME']))
        if not shutil.which('rustup', path=env['PATH']):
            installer = fetch('rustup', prefix / 'downloads')
            installer.chmod(0o755)
            run([installer, '-y', '--no-modify-path', '--profile', 'minimal', '--default-toolchain', 'none'], env)
        run(['rustup', 'toolchain', 'install', '1.94.0', '--profile', 'minimal', '--component', 'rustfmt', '--component', 'clippy'], env)
        ast = REPOSITORY.parent / 'RustLightAST'
        if not ast.exists():
            run(['git', 'clone', '--no-checkout', LOCK['rustlightast']['url'], ast])
            run(['git', '-C', ast, 'checkout', '--detach', LOCK['rustlightast']['commit']])
        revision = subprocess.check_output(['git', '-C', str(ast), 'rev-parse', 'HEAD'], text=True).strip()
        dirty = subprocess.check_output(['git', '-C', str(ast), 'status', '--porcelain'], text=True)
        if revision != LOCK['rustlightast']['commit'] or dirty:
            raise ValueError('Existing sibling RustLightAST must be clean at the pinned commit; it was not changed')
        run([config['isabelle'], 'components', '-u', str(Path(config['afp']) / 'thys')], env)
        run([config['isabelle'], 'ghc_setup'], env)
        run(['cargo', '+1.94.0', 'fetch', '--locked', '--manifest-path', REPOSITORY / 'optimize/Cargo.toml'], env)
        with tempfile.TemporaryDirectory(prefix='.afp-cargo-seed-', dir=prefix) as temporary:
            seed = Path(temporary);(seed / 'src').mkdir();(seed / 'src/main.rs').write_text('fn main() {}\n')
            (seed / 'Cargo.toml').write_text('[package]\nname="isabelle_exported"\nversion="0.1.0"\nedition="2021"\n[dependencies]\nnum-bigint="=0.4.6"\nnum-traits="=0.2.19"\n')
            shutil.copyfile(REPOSITORY / 'scripts/isabelle-exported.Cargo.lock', seed / 'Cargo.lock')
            run(['cargo', '+1.94.0', 'fetch', '--locked', '--manifest-path', seed / 'Cargo.toml'], env)
    # apt may have installed tools absent when the process first started.
    for key, executable in [('ISABELLE_CC', 'cc'), ('ISABELLE_OCAMLFIND', 'ocamlfind'), ('ISABELLE_SMLNJ', 'sml')]:
        # An explicit switch wrapper must survive rediscovery of system tools;
        # findlib and its compiler/libraries must belong to the same toolchain.
        if key == 'ISABELLE_OCAMLFIND' and args.ocamlfind:
            continue
        compilers[key] = shutil.which(executable) or compilers[key]
    args.config.parent.mkdir(parents=True, exist_ok=True)
    common.write_json(Path(config['compiler_settings']), compilers)
    common.write_json(args.config.resolve(), config)
    if not args.configure_only:
        installed = subprocess.check_output(['dpkg-query', '-W', '-f=${Package}\t${Version}\n', *LOCK['system_packages']], text=True)
        common.write_json(args.config.with_name('installed.local.json'), {'packages': installed.splitlines(), 'dependencies': LOCK})
        env['AFP_CONFIG'] = str(args.config.resolve())
        # Environment initialization applies heap limits after getsettings.
        from afp import runtime_arguments
        common.configure(args.config)
        options = common.arguments('heap setup').parse_args(runtime_arguments(config))
        build_env, _ = common.environment(options)
        run([config['isabelle'], 'build', '-b', *common.build_options(options),
             '-d', REPOSITORY, '-d', str(Path(config['afp']) / 'thys'), 'Rust', 'Go'], build_env)
        run([sys.executable, SETUP / 'check.py', '--config', args.config,
             '--receipt', args.config.with_name('environment.local.json')], env)
    print(json.dumps({'config': str(args.config.resolve()), 'configured_only': args.configure_only}, indent=2))


def arguments(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prefix', type=Path, required=True, help='user-writable installation/cache root')
    p.add_argument('--config', type=Path, default=SETUP / 'server.local.json')
    p.add_argument('--work', type=Path)
    p.add_argument('--user-home', type=Path, help='Isabelle USER_HOME (default: PREFIX/user; HOME itself is unchanged)')
    p.add_argument('--max-heap-mb', type=int, default=4500)
    p.add_argument('--java-heap-mb', type=int, default=1536)
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--skip-system-packages', action='store_true')
    p.add_argument('--ocamlfind', type=Path, help='OCaml 4.14.x findlib wrapper (pins compiler and library paths)')
    p.add_argument('--configure-only', action='store_true', help='write local config for existing installations')
    for name in ('isabelle', 'afp', 'cakeml', 'go-root'):
        p.add_argument('--' + name, type=Path, help='existing location (configure-only)')
    args = p.parse_args(argv)
    if not args.configure_only and any((args.isabelle, args.afp, args.cakeml, args.go_root)):
        p.error('existing-location overrides require --configure-only')
    if args.max_heap_mb <= 0 or args.java_heap_mb <= 0:
        p.error('heap limits must be positive')
    for name in ('prefix', 'config', 'work', 'user_home', 'isabelle', 'afp', 'cakeml', 'go_root', 'ocamlfind'):
        value = getattr(args, name)
        if value is not None:
            setattr(args, name, value.resolve())
    return args


if __name__ == '__main__':
    try:
        args = arguments()
        if args.dry_run:
            print(json.dumps(plan(args), ensure_ascii=False, indent=2))
        else:
            install(args)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        sys.exit(str(error))
