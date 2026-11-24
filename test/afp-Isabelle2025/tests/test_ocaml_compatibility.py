#!/usr/bin/env python3
"""Explicit compiler selection and opt-in real Native_Word OCaml probes."""
import _paths
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import afp_common as common


def checker():
    spec = importlib.util.spec_from_file_location('afp_ocaml_check', common.EXPERIMENT / 'setup/check.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class OCamlConfigurationTests(unittest.TestCase):
    def test_explicit_switch_wrapper_survives_system_tool_discovery(self):
        # A configured OCaml 4 wrapper (including paths with spaces) must not
        # be replaced by a system OCaml 5 ocamlfind when configuration is saved.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            wrapper = root / 'OCaml 4 tools/ocamlfind'
            config = root / 'server.local.json'
            result = subprocess.run([
                sys.executable, '-B', str(common.EXPERIMENT / 'setup/install.py'),
                '--prefix', str(root / 'deps'), '--configure-only',
                '--config', str(config), '--ocamlfind', str(wrapper)],
                capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            settings = json.loads(config.read_text())['compilers']
            self.assertEqual(settings['ISABELLE_OCAMLFIND'], str(wrapper))

    @unittest.skipUnless(os.environ.get('AFP_TEST_OCAML4_FIND'), 'opt-in OCaml 4 native compilation')
    def test_ocaml4_compiles_native_word_adaptation_with_zarith(self):
        # Exercise the same native link command as Isabelle without executing
        # the generated program; both Pervasives and Zarith must be available.
        result = checker().check_ocaml(os.environ['AFP_TEST_OCAML4_FIND'], os.environ.copy())
        self.assertTrue(result['native_version'].startswith('4.'))
        self.assertEqual(result['native_word_check'], 'passed')
        self.assertFalse(result['generated_programs_executed'])

    @unittest.skipUnless(os.environ.get('AFP_TEST_OCAML5_FIND'), 'opt-in incompatible OCaml 5 witness')
    def test_ocaml5_is_rejected_even_when_zarith_is_installed(self):
        # Package discovery alone used to accept this toolchain. The actual
        # equality adaptation must fail with the missing Pervasives diagnostic.
        with self.assertRaisesRegex(ValueError, 'Unbound module Pervasives'):
            checker().check_ocaml(os.environ['AFP_TEST_OCAML5_FIND'], os.environ.copy())


if __name__ == '__main__':
    unittest.main()
