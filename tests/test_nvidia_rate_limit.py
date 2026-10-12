import json
import tempfile
from pathlib import Path
from threading import Event, Thread
import unittest
from unittest.mock import patch

from mist.bootstrap import create_application
from mist.errors import ErrorCode, MistError
from mist.nvidia import MIN_REQUEST_INTERVAL, NvidiaProvider, NvidiaRequestGate
from test_nvidia import Clock, Connection, Response, SYNTHETIC_KEY, EXAMPLE, remote_envelope


class NvidiaRateLimitTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.gate = NvidiaRequestGate(clock=self.clock, wait=self.clock.wait)
        gate_patch = patch('mist.nvidia.NVIDIA_REQUEST_GATE', self.gate)
        gate_patch.start()
        self.addCleanup(gate_patch.stop)

    def test_distinct_adapters_and_models_share_spaced_starts(self):
        starts = []
        def connect(*args, **kwargs):
            starts.append(self.clock.now)
            return Connection()
        with patch('mist.nvidia.http.client.HTTPSConnection', side_effect=connect):
            for index in range(3):
                request = remote_envelope()
                request = request.model_copy(update={'model': request.model.model_copy(update={
                    'model_id': 'moonshotai/kimi-k3' if index % 2 else 'nvidia/nemotron-3-super-120b-a12b'})})
                NvidiaProvider(SYNTHETIC_KEY).generate(request)
        self.assertEqual(starts, [0.0, MIN_REQUEST_INTERVAL, 2 * MIN_REQUEST_INTERVAL])

    def test_long_response_needs_no_additional_delay(self):
        connection = Connection()
        def respond():
            self.clock.now += 10
            return Response()
        with patch.object(connection, 'getresponse', side_effect=respond), \
                patch('mist.nvidia.http.client.HTTPSConnection', return_value=connection):
            provider = NvidiaProvider(SYNTHETIC_KEY)
            provider.generate(remote_envelope())
            provider.generate(remote_envelope())
        self.assertEqual(self.clock.waits, [])

    def test_slow_transport_preparation_does_not_shorten_start_interval(self):
        starts = []
        def connect(*args, **kwargs):
            if not starts:
                self.clock.now += 5
            connection = Connection()
            request = connection.request
            def send(*args, **kwargs):
                starts.append(self.clock.now)
                request(*args, **kwargs)
            connection.request = send
            return connection
        with patch('mist.nvidia.http.client.HTTPSConnection', side_effect=connect):
            provider = NvidiaProvider(SYNTHETIC_KEY)
            provider.generate(remote_envelope())
            provider.generate(remote_envelope())
        self.assertEqual(starts, [5.0, 5.0 + MIN_REQUEST_INTERVAL])

    def test_early_wakeup_rechecks_remaining_delay(self):
        waits = []
        def wait(seconds):
            waits.append(seconds)
            self.clock.now += seconds / 2 if len(waits) == 1 else seconds
        self.gate._wait = wait
        with patch('mist.nvidia.http.client.HTTPSConnection', side_effect=lambda *a, **k: Connection()):
            provider = NvidiaProvider(SYNTHETIC_KEY)
            provider.generate(remote_envelope())
            provider.generate(remote_envelope())
        self.assertEqual(waits, [MIN_REQUEST_INTERVAL, MIN_REQUEST_INTERVAL / 2])

    def test_failure_still_counts_for_spacing(self):
        with patch('mist.nvidia.http.client.HTTPSConnection', return_value=Connection(error=OSError())):
            with self.assertRaises(MistError):
                NvidiaProvider(SYNTHETIC_KEY).generate(remote_envelope())
        with patch('mist.nvidia.http.client.HTTPSConnection', return_value=Connection()):
            NvidiaProvider(SYNTHETIC_KEY).generate(remote_envelope())
        self.assertEqual(self.clock.waits, [MIN_REQUEST_INTERVAL])

    def test_429_blocks_new_application_and_session_reset_without_network(self):
        with tempfile.TemporaryDirectory() as directory:
            audit = Path(directory) / 'audit.jsonl'
            app = create_application(EXAMPLE, audit, allow_external=True, api_key=SYNTHETIC_KEY)
            with patch('mist.nvidia.http.client.HTTPSConnection', return_value=Connection(Response(status=429))) as factory:
                with self.assertRaises(MistError) as first:
                    app.handle('sintético')
                self.assertEqual(first.exception.code, ErrorCode.RATE_LIMIT)
                app.reset()
                for application in (app, create_application(EXAMPLE, audit, allow_external=True, api_key=SYNTHETIC_KEY)):
                    with self.assertRaises(MistError) as blocked:
                        application.handle('sintético')
                    self.assertEqual(blocked.exception.code, ErrorCode.RATE_LIMIT)
                    self.assertEqual(application.history, ())
                self.assertEqual(factory.call_count, 1)
            log = audit.read_text()
            self.assertNotIn(SYNTHETIC_KEY, log)
            records = [json.loads(line) for line in log.splitlines()]
            self.assertEqual(sum(row['reason'] == 'rate_limit' for row in records), 3)

    def test_queued_call_cannot_escape_429_pause(self):
        entered, release, second_started = Event(), Event(), Event()
        errors = []
        connection = Connection(Response(status=429))
        def respond():
            entered.set()
            if not release.wait(2):
                raise AssertionError('test synchronization timeout')
            return connection.response
        def call(started=None):
            if started:
                started.set()
            try:
                NvidiaProvider(SYNTHETIC_KEY).generate(remote_envelope())
            except MistError as exc:
                errors.append(exc.code)
        with patch.object(connection, 'getresponse', side_effect=respond), \
                patch('mist.nvidia.http.client.HTTPSConnection', return_value=connection) as factory:
            first = Thread(target=call)
            second = Thread(target=call, args=(second_started,))
            first.start()
            try:
                self.assertTrue(entered.wait(1))
                second.start()
                self.assertTrue(second_started.wait(1))
            finally:
                release.set()
                first.join(2)
                if second.ident is not None:
                    second.join(2)
            self.assertFalse(first.is_alive())
            self.assertFalse(second.is_alive())
            self.assertEqual(factory.call_count, 1)
        self.assertEqual(errors, [ErrorCode.RATE_LIMIT, ErrorCode.RATE_LIMIT])

    def test_interrupt_during_wait_sends_nothing_and_releases_lock(self):
        with patch('mist.nvidia.http.client.HTTPSConnection', side_effect=lambda *a, **k: Connection()) as factory:
            provider = NvidiaProvider(SYNTHETIC_KEY)
            provider.generate(remote_envelope())
            with patch.object(self.gate, '_wait', side_effect=KeyboardInterrupt()):
                with self.assertRaises(KeyboardInterrupt):
                    provider.generate(remote_envelope())
            self.assertEqual(factory.call_count, 1)
            provider.generate(remote_envelope())
            self.assertEqual(factory.call_count, 2)


if __name__ == '__main__':
    unittest.main()
