import getpass
import importlib.util
import io
import json
from pathlib import Path
import socket
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from test_nvidia import Connection, Response, SYNTHETIC_KEY, synthetic_gate

ROOT = Path(__file__).resolve().parents[1]


def runner():
    spec = importlib.util.spec_from_file_location('memory_evaluation', ROOT/'evaluations/run_memory.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class MemoryEvaluationTests(unittest.TestCase):
    def setUp(self):
        gate = patch('mist.nvidia.NVIDIA_REQUEST_GATE', synthetic_gate())
        gate.start()
        self.addCleanup(gate.stop)

    def test_offline_reopens_storage_without_network_and_never_scores_quality(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(socket, 'socket', side_effect=AssertionError('network forbidden')):
            output = Path(directory)/'run'
            manifest = runner().run(output)
            records = json.loads((output/'results.json').read_text())
            self.assertEqual(manifest['completed_cases'], 10)
            self.assertEqual(manifest['quality_status'], 'not_measured_simulation')
            self.assertTrue(all(record['response']['simulated'] and record['review'] is None for record in records))
            self.assertTrue(all(all(record['code_checks'].values()) for record in records))
            for name in ('manifest.json', 'results.json'):
                self.assertEqual((output/name).stat().st_mode & 0o777, 0o600)
            self.assertEqual(output.stat().st_mode & 0o777, 0o700)
            with self.assertRaises(FileExistsError):
                runner().run(output)

    def test_real_flow_filters_local_deleted_and_old_revision_before_transport(self):
        connections = []
        def connect(*args, **kwargs):
            connection = Connection()
            connections.append(connection)
            return connection
        with tempfile.TemporaryDirectory() as directory, patch('mist.nvidia.http.client.HTTPSConnection', side_effect=connect):
            output = Path(directory)/'run'
            manifest = runner().run(output, real=True, api_key=SYNTHETIC_KEY)
            records = json.loads((output/'results.json').read_text())
            self.assertEqual(manifest['completed_cases'], 10)
            self.assertEqual(manifest['quality_status'], 'pending_manual_review')
            bodies = [json.loads(connection.requests[0][2]['body']) for connection in connections]
            self.assertEqual(len(bodies), 10)
            self.assertEqual({body['model'] for body in bodies}, {'nvidia/nemotron-3-super-120b-a12b', 'moonshotai/kimi-k3'})
            self.assertTrue(all(all(record['code_checks'].values()) for record in records))
            for record, body in zip(records, bodies):
                text = json.dumps(body, ensure_ascii=False)
                if record['case'] == 'local_memory_not_sent':
                    self.assertNotIn('Pessoa Sintética Aster', text)
                if record['case'] == 'deleted_name_absent':
                    self.assertNotIn('Pessoa Sintética Apagada', text)
                if record['case'] == 'corrected_name_current_revision':
                    self.assertIn('Pessoa Sintética Nova', text)
                    self.assertNotIn('Pessoa Sintética Antiga', text)
                self.assertIsNone(record['review'])
            persisted = ''.join((output/name).read_text() for name in ('manifest.json','results.json','audit.jsonl'))
            self.assertNotIn(SYNTHETIC_KEY, persisted)

    def test_rate_limit_and_auth_stop_without_followup_or_retry(self):
        for status, expected in ((429,'RATE_LIMIT'), (401,'PROVIDER_AUTH')):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as directory, \
                    patch('mist.nvidia.NVIDIA_REQUEST_GATE', synthetic_gate()), \
                    patch('mist.nvidia.http.client.HTTPSConnection', return_value=Connection(Response(status=status))) as network:
                output = Path(directory)/'run'
                manifest = runner().run(output, real=True, api_key=SYNTHETIC_KEY)
                records = json.loads((output/'results.json').read_text())
                self.assertTrue(manifest['stopped'])
                self.assertEqual(manifest['attempted_cases'], 1)
                self.assertEqual(manifest['completed_cases'], 0)
                self.assertEqual(records[0]['error'], expected)
                self.assertIsNone(records[0]['review'])
                self.assertEqual(network.call_count, 1)

    def test_hidden_input_forwarded_without_echo_or_unsafe_fallback(self):
        module = runner()
        result = {'kind':'real_synthetic_memory_regression', 'attempted_cases':10, 'completed_cases':10,
                  'planned_cases':10, 'stopped':False, 'quality_status':'pending_manual_review'}
        stdout = io.StringIO()
        with patch.object(module.getpass, 'getpass', return_value=SYNTHETIC_KEY), \
                patch.object(module, 'run', return_value=result) as run, redirect_stdout(stdout):
            self.assertEqual(module.main(['--real','--ask-api-key','--output','/tmp/example']), 0)
            self.assertEqual(run.call_args.kwargs['api_key'], SYNTHETIC_KEY)
        self.assertNotIn(SYNTHETIC_KEY, stdout.getvalue())
        with patch.object(module.getpass, 'getpass', side_effect=getpass.GetPassWarning()), \
                patch.object(module, 'run') as run, redirect_stdout(io.StringIO()):
            self.assertEqual(module.main(['--real','--ask-api-key','--output','/tmp/example']), 2)
            self.assertEqual(module.main(['--ask-api-key','--output','/tmp/example']), 2)
            run.assert_not_called()

    def test_deadline_leaves_unattempted_cases_and_does_not_claim_completion(self):
        module = runner()
        with tempfile.TemporaryDirectory() as directory, patch.object(module, 'monotonic', side_effect=[0,2]):
            manifest = module.run(Path(directory)/'run', deadline_seconds=1)
        self.assertTrue(manifest['stopped'])
        self.assertEqual(manifest['attempted_cases'], 0)
        self.assertEqual(manifest['completed_cases'], 0)
        self.assertEqual(manifest['planned_cases'], 10)

    def test_fixed_continuation_only_queries_three_pending_primary_cases(self):
        module = runner()
        with tempfile.TemporaryDirectory() as directory, patch.object(socket, 'socket', side_effect=AssertionError('network forbidden')):
            output = Path(directory)/'run'
            manifest = module.run(output, case_set='primary-continuation')
            records = json.loads((output/'results.json').read_text())
            self.assertEqual(manifest['completed_cases'], 3)
            self.assertEqual({record['mode'] for record in records}, {'PRIMARY'})
            self.assertEqual([record['case'] for record in records],
                             ['hypothesis_not_fact','corrected_name_current_revision','deleted_name_absent'])
            with self.assertRaises(ValueError):
                module.run(Path(directory)/'unsafe', case_set='../private')
            self.assertFalse((Path(directory)/'unsafe').exists())
