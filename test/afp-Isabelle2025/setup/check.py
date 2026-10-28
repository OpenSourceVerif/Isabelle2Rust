#!/usr/bin/env python3
"""Check server versions, all compiler conditions, sources and retained evidence."""
import argparse
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import afp_common as common
from afp import runtime_arguments, verify_frozen
from frozen import verify_sources


def check(config, work=None):
    """Fail closed and retain honest individual failures for a new installation."""
    checks = []
    def run(name, action):
        try:
            value = action()
            checks.append({'check': name, 'passed': True, 'value': value})
        except Exception as error:
            checks.append({'check': name, 'passed': False, 'error': str(error)})
    def output(argv, env=None):
        return subprocess.check_output([str(x) for x in argv], env=env, text=True, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL).strip()
    def require(test, message):
        if not test:
            raise ValueError(message)
        return message
    run('platform', lambda: require(platform.system() == 'Linux' and platform.machine() == 'x86_64', 'Linux x86_64 required'))
    options = common.arguments('server environment').parse_args(runtime_arguments(config))
    env = None
    try:
        env, metadata = common.environment(options)
        checks.append({'check': 'Isabelle/AFP versions and checked/unlimited policy', 'passed': True, 'value': metadata})
    except Exception as error:
        checks.append({'check': 'Isabelle/AFP environment', 'passed': False, 'error': str(error)})
    for tool in ('rustc', 'cargo'):
        def rust(tool=tool):
            value = output([tool, '+1.94.0', '--version'])
            require(value.startswith(tool + ' 1.94.0 '), value)
            return value
        run(tool, rust)
    for tool, arguments in [('rustfmt', ['--version']), ('cargo', ['clippy', '--version'])]:
        run(tool + ' optimizer support', lambda tool=tool, arguments=arguments: output([tool, '+1.94.0', *arguments]))
    ast = common.PROJECT.parent / 'RustLightAST'
    lock = common.read_json(common.EXPERIMENT / 'setup/dependencies.json')
    def ast_revision():
        revision = output(['git', '-C', ast, 'rev-parse', 'HEAD'])
        require(revision == lock['rustlightast']['commit'], 'Wrong RustLightAST commit: ' + revision)
        require(not output(['git', '-C', ast, 'status', '--porcelain']), 'RustLightAST has local changes')
        return revision
    run('sibling RustLightAST', ast_revision)
    if env:
        conditions = common.read_json(common.EXPERIMENT / 'scan/source-inputs.json')['conditions']
        for key in conditions:
            def compiler(key=key):
                value = env.get(key)
                require(bool(value), 'Missing condition: ' + key)
                path = Path(value)
                if key == 'ISABELLE_CAKEML_HOME':
                    require((path / 'basis_ffi.c').is_file() and os.access(path / 'bin/x86_64-linux/cake', os.X_OK), 'Incomplete CakeML component')
                    from scan_store import file_digest
                    require(file_digest(path / 'bin/x86_64-linux/cake') == conditions[key]['sha256'], 'CakeML binary differs from fixed component')
                    return str(path)
                if key == 'ISABELLE_GOEXE':
                    goroot = Path(env.get('ISABELLE_GOROOT', '__missing__'))
                    require((goroot / 'VERSION').is_file() and (goroot / 'src/runtime/runtime2.go').is_file(), 'Incomplete Go root')
                    result = output([path / 'go', 'version'], env)
                    require('go1.26.8 ' in result, result)
                    return result
                if key == 'ISABELLE_OCAMLFIND':
                    return {'version': output([path, 'ocamlc', '-version'], env), 'zarith': output([path, 'query', 'zarith'], env)}
                require(path.is_file() and os.access(path, os.X_OK), 'Condition is not executable: ' + str(path))
                if key in {'ISABELLE_CC', 'ISABELLE_GHC'}:
                    result = output([path, '--version'], env)
                    if key == 'ISABELLE_GHC':
                        require('9.6.6' in result, 'Expected matching Isabelle GHC 9.6.6: ' + result)
                    return result
                if key == 'ISABELLE_SMLNJ':
                    return output([path], env)
                from scan_store import file_digest
                require(file_digest(path) == conditions[key]['sha256'], 'Bundled MLton differs from fixed component')
                return str(path)
            run(key, compiler)
        run('Scala bundled tool', lambda: output([options.isabelle, 'scala', '-e', 'println(util.Properties.versionString)'], env))
        run('frozen source identity', lambda: verify_sources(common.EXPERIMENT / 'scan', options.afp, options.isabelle))
    def writable():
        # Check the nearest existing parent without populating empty work/.
        directory = Path(work or common.WORK).resolve()
        while not directory.exists():
            directory = directory.parent
        with tempfile.NamedTemporaryFile(prefix='.afp-write-check-', dir=directory):
            pass
        return str(directory)
    run('work parent writable', writable)
    run('complete frozen evidence', verify_frozen)
    return {'passed': all(c['passed'] for c in checks), 'checked': common.timestamp(), 'checks': checks,
            'generated_programs_executed': False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config', type=Path)
    p.add_argument('--work', type=Path, help='check a dedicated work root instead of the configured one')
    p.add_argument('--receipt', type=Path, help='optional server-local environment record')
    args = p.parse_args()
    result = check(common.configure(args.config), args.work)
    if args.receipt:
        common.write_json(args.receipt.resolve(), result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return int(not result['passed'])


if __name__ == '__main__':
    raise SystemExit(main())
