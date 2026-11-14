"""Executable reuse must never turn a changed program into a fallback cell."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from i2r_agent.optimization_matrix import executable_identity, expand_aliases


class MatrixReuseTests(unittest.TestCase):
    def test_identity_includes_code_connector_and_numeric_backend(self):
        state={'files':{'src/lib.rs':'code'},'connector':{'src/lib.rs':'observer'},'rust_config':{'x':1}}
        with patch('i2r_agent.optimization_matrix.interface.backend_config',side_effect=lambda rc,b:{**rc,'backend':b}):
            original=executable_identity(state,'arbitrary')
            self.assertNotEqual(original,executable_identity(state,'checked'))
            for key in ['files','connector','rust_config']:
                changed=deepcopy(state);changed[key]['new']='different'
                self.assertNotEqual(original,executable_identity(changed,'arbitrary'))
            context=deepcopy(state);context['guidance']='different non-executable label'
            self.assertEqual(original,executable_identity(context,'arbitrary'))

    def test_aliases_share_observations_without_inventing_raw_samples(self):
        raw={'summary':{'off-arbitrary':{'median_ns':10}},'processes':{'off-arbitrary':[{'samples':[10]}]},
             'raw_samples':[{'implementation':'off-arbitrary','batch_ns':100}]}
        aliases={'off-arbitrary':'off-arbitrary','full-arbitrary':'off-arbitrary','off-checked':'off-checked'}
        with tempfile.TemporaryDirectory() as tmp:
            result=expand_aliases(raw,aliases,Path(tmp))
            self.assertEqual(result['summary']['full-arbitrary'],raw['summary']['off-arbitrary'])
            self.assertNotIn('off-checked',result['summary'])
            self.assertEqual(result['raw_samples'],raw['raw_samples'])
            self.assertEqual(len(raw['summary']),1)
            self.assertTrue((Path(tmp)/'matrix-measurement.json').exists())
