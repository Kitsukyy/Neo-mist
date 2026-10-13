import io
import getpass
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from mist.bootstrap import create_application
from mist.cli import main
from mist.config import load_config
from mist.errors import ErrorCode, MistError
from mist.nvidia import DESTINATION, HOST, MAX_RESPONSE_BYTES, PATH, NvidiaProvider, NvidiaRequestGate
from mist.schemas import AuditReason, ModelConfig, Sensitivity
from test_core import RecordingAudit, envelope

SYNTHETIC_KEY = "nvapi-" + "synthetic-not-a-real-key-0123456789"
EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "nvidia"


class Clock:
    def __init__(self):
        self.now = 0.0
        self.waits = []

    def __call__(self):
        return self.now

    def wait(self, seconds):
        self.waits.append(seconds)
        self.now += seconds


def synthetic_gate():
    clock = Clock()
    return NvidiaRequestGate(clock=clock, wait=clock.wait)


def remote_envelope(text="teste"):
    return envelope(text).model_copy(update={"model": ModelConfig(
        id="nvidia-test", provider="nvidia", model_id="nvidia/nemotron-3.5-lightning-30b-a3b",
        external=True, destination=DESTINATION, enable_thinking=False,
    )})


class Response:
    def __init__(self, status=200, data=None, raw=None, content_type="application/json"):
        self.status = status
        self.content_type = content_type
        self.body = io.BytesIO(raw if raw is not None else json.dumps(data or {
            "choices": [{"message": {"role": "assistant", "content": "Olá, sou a Mist."}, "finish_reason": "stop"}],
        }).encode())
        self.reads = 0

    def getheader(self, name, default):
        return self.content_type

    def read1(self, limit):
        self.reads += 1
        return self.body.read(limit)


class Connection:
    def __init__(self, response=None, error=None):
        self.response = response or Response()
        self.error = error
        self.requests = []
        self.closed = False
        self.sock = None

    def request(self, method, path, **kwargs):
        self.requests.append((method, path, kwargs))
        if self.error is not None:
            raise self.error

    def getresponse(self):
        return self.response

    def close(self):
        self.closed = True


class NvidiaTests(unittest.TestCase):
    def setUp(self):
        self.gate = patch('mist.nvidia.NVIDIA_REQUEST_GATE', synthetic_gate())
        self.gate.start()
        self.addCleanup(self.gate.stop)

    def assert_code(self, code, action):
        with self.assertRaises(MistError) as raised:
            action()
        self.assertEqual(raised.exception.code, code)
        self.assertNotIn(SYNTHETIC_KEY, str(raised.exception))

    def call(self, connection, request=None):
        with patch("mist.nvidia.http.client.HTTPSConnection", return_value=connection) as factory:
            text = NvidiaProvider(SYNTHETIC_KEY).generate(request or remote_envelope())
        return text, factory

    def test_fixed_https_request_without_tools_and_with_auth_header_only(self):
        connection = Connection()
        text, factory = self.call(connection)
        self.assertEqual(text, "Olá, sou a Mist.")
        self.assertEqual(factory.call_args.args, (HOST,))
        context = factory.call_args.kwargs["context"]
        self.assertTrue(context.check_hostname)
        self.assertEqual(len(connection.requests), 1)
        method, path, kwargs = connection.requests[0]
        self.assertEqual((method, path), ("POST", PATH))
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer " + SYNTHETIC_KEY)
        self.assertNotIn(SYNTHETIC_KEY.encode(), kwargs["body"])
        body = json.loads(kwargs["body"])
        self.assertEqual(set(body), {"model", "messages", "max_tokens", "temperature", "stream", "chat_template_kwargs"})
        self.assertEqual(body["chat_template_kwargs"], {"enable_thinking": False})
        self.assertEqual(body["max_tokens"], 512)
        self.assertFalse(body["stream"])
        self.assertTrue(connection.closed)

    def test_usage_records_only_numeric_metadata_and_resets_after_failure(self):
        provider = NvidiaProvider(SYNTHETIC_KEY)
        data = {"choices": [{"message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 3, "total_tokens": 13,
                          "private": SYNTHETIC_KEY, "completion_tokens_details": {"reasoning_tokens": 1}}}
        connection = Connection(Response(data=data))
        with patch("mist.nvidia.http.client.HTTPSConnection", return_value=connection):
            provider.generate(remote_envelope())
        self.assertEqual(provider.last_usage, {"prompt_tokens": 10, "completion_tokens": 3,
                                              "total_tokens": 13, "reasoning_tokens": 1})
        self.assertEqual(provider.last_finish_reason, "stop")
        with patch("mist.nvidia.http.client.HTTPSConnection", return_value=Connection(Response(status=429))):
            self.assert_code(ErrorCode.RATE_LIMIT, lambda: provider.generate(remote_envelope()))
        self.assertIsNone(provider.last_usage)
        self.assertIsNone(provider.last_finish_reason)

    def test_http_errors_are_safe_and_never_read_body_or_retry(self):
        for status, code in ((401, ErrorCode.PROVIDER_AUTH), (403, ErrorCode.PROVIDER_AUTH),
                             (429, ErrorCode.RATE_LIMIT), (404, ErrorCode.PROVIDER_UNAVAILABLE),
                             (410, ErrorCode.PROVIDER_UNAVAILABLE), (503, ErrorCode.PROVIDER_UNAVAILABLE),
                             (202, ErrorCode.PROVIDER_FAILURE), (500, ErrorCode.PROVIDER_FAILURE),
                             (302, ErrorCode.PROVIDER_FAILURE)):
            with self.subTest(status=status):
                # HTTP mappings are independent; a 429 now pauses its process gate.
                self.gate.stop()
                self.gate = patch('mist.nvidia.NVIDIA_REQUEST_GATE', synthetic_gate())
                self.gate.start()
                self.addCleanup(self.gate.stop)
                response = Response(status=status, raw=SYNTHETIC_KEY.encode())
                connection = Connection(response)
                self.assert_code(code, lambda: self.call(connection))
                self.assertEqual(response.reads, 0)
                self.assertEqual(len(connection.requests), 1)
                self.assertTrue(connection.closed)

    def test_timeout_and_connection_error_are_safe(self):
        for error, code in ((TimeoutError(SYNTHETIC_KEY), ErrorCode.PROVIDER_TIMEOUT),
                            (OSError(SYNTHETIC_KEY), ErrorCode.PROVIDER_FAILURE)):
            connection = Connection(error=error)
            self.assert_code(code, lambda: self.call(connection))
            self.assertTrue(connection.closed)
            self.assertEqual(len(connection.requests), 1)

    def test_read_timeout_closes_connection(self):
        response = Response()
        with patch.object(response, "read1", side_effect=TimeoutError(SYNTHETIC_KEY)):
            connection = Connection(response)
            self.assert_code(ErrorCode.PROVIDER_TIMEOUT, lambda: self.call(connection))
        self.assertTrue(connection.closed)

    def test_invalid_body_and_content_type_are_rejected(self):
        for response in (Response(raw=b"not json"), Response(raw=b"[]"), Response(raw=b"{}"),
                         Response(raw=b"x" * (MAX_RESPONSE_BYTES + 1)),
                         Response(content_type="text/html")):
            connection = Connection(response)
            self.assert_code(ErrorCode.INVALID_RESPONSE, lambda: self.call(connection))
            self.assertTrue(connection.closed)

    def test_tool_calls_truncation_empty_and_secret_echo_are_rejected(self):
        for change in ({"content": None}, {"content": " "}, {"content": 9},
                       {"content": SYNTHETIC_KEY}, {"role": "system"},
                       {"tool_calls": [{"name": "shell"}]}, {"function_call": {"name": "shell"}}):
            message = {"role": "assistant", "content": "ok", **change}
            connection = Connection(Response(data={"choices": [{"message": message, "finish_reason": "stop"}]}))
            self.assert_code(ErrorCode.INVALID_RESPONSE, lambda: self.call(connection))
        connection = Connection(Response(data={"choices": [{"message": {"role": "assistant", "content": "incompleta"}, "finish_reason": "length"}]}))
        self.assert_code(ErrorCode.INVALID_RESPONSE, lambda: self.call(connection))

    def test_transport_rejects_mismatched_destination_without_network(self):
        for change in ({"external": False}, {"destination": "other"}, {"provider": "fake"}):
            request = remote_envelope()
            request = request.model_copy(update={"model": request.model.model_copy(update=change)})
            with patch("mist.nvidia.http.client.HTTPSConnection") as factory:
                self.assert_code(ErrorCode.GUARD_BLOCKED, lambda: NvidiaProvider(SYNTHETIC_KEY).generate(request))
                factory.assert_not_called()

    def test_config_requires_exact_provider_destination_and_external_flag(self):
        settings, constitution, personality = load_config(EXAMPLE)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "constitution.json").write_text(constitution.model_dump_json())
            (root / "personality.json").write_text(personality.model_dump_json())
            for change in ({"external": False}, {"destination": "other"}, {"provider": "unknown"}):
                data = settings.model_dump(mode="json")
                data["models"][0].update(change)
                (root / "settings.json").write_text(json.dumps(data))
                self.assert_code(ErrorCode.CONFIGURATION, lambda: load_config(root))

    def test_explicit_opt_in_and_key_are_required_before_network(self):
        with patch("mist.nvidia.http.client.HTTPSConnection") as factory:
            self.assert_code(ErrorCode.EXTERNAL_DISABLED, lambda: create_application(EXAMPLE, api_key=SYNTHETIC_KEY))
            self.assert_code(ErrorCode.PROVIDER_AUTH, lambda: create_application(EXAMPLE, allow_external=True, api_key=""))
            factory.assert_not_called()

    def test_gateway_blocks_local_content_secrets_and_missing_allowlist(self):
        with tempfile.TemporaryDirectory() as directory:
            app = create_application(EXAMPLE, Path(directory) / "audit.jsonl", allow_external=True, api_key=SYNTHETIC_KEY)
            with patch("mist.nvidia.http.client.HTTPSConnection") as factory:
                self.assert_code(ErrorCode.GUARD_BLOCKED, lambda: app.handle("privado", Sensitivity.LOCAL_ONLY))
                self.assert_code(ErrorCode.GUARD_BLOCKED, lambda: app.handle(SYNTHETIC_KEY))
                app.gateway.guard.allowed_destinations = frozenset()
                self.assert_code(ErrorCode.GUARD_BLOCKED, lambda: app.handle("teste"))
                factory.assert_not_called()
            self.assertEqual(app.history, ())
            log = (Path(directory) / "audit.jsonl").read_text()
            self.assertNotIn(SYNTHETIC_KEY, log)
            self.assertNotIn("privado", log)

    def test_integrated_response_audit_and_followup(self):
        with tempfile.TemporaryDirectory() as directory:
            app = create_application(EXAMPLE, Path(directory) / "audit.jsonl", allow_external=True, api_key=SYNTHETIC_KEY)
            connection = Connection()
            with patch("mist.nvidia.http.client.HTTPSConnection", return_value=connection):
                result = app.handle("olá")
                connection.response = Response()
                app.handle("continue")
            self.assertFalse(result.simulated)
            self.assertEqual(result.provider, "nvidia")
            self.assertEqual(len(app.history), 4)
            followup = json.loads(connection.requests[-1][2]["body"])
            self.assertEqual([m["role"] for m in followup["messages"]], ["system", "user", "assistant", "user"])
            records = [json.loads(line) for line in (Path(directory) / "audit.jsonl").read_text().splitlines()]
            self.assertEqual([r["phase"] for r in records], ["approved", "completed", "approved", "completed"])

    def test_gateway_preserves_provider_errors_and_cancellation_without_history(self):
        with tempfile.TemporaryDirectory() as directory:
            app = create_application(EXAMPLE, Path(directory) / "audit.jsonl", allow_external=True, api_key=SYNTHETIC_KEY)
            audit = RecordingAudit()
            app.gateway.audit = audit
            with patch("mist.nvidia.http.client.HTTPSConnection", return_value=Connection(Response(status=429))):
                self.assert_code(ErrorCode.RATE_LIMIT, lambda: app.handle("teste"))
            self.assertEqual(audit.events[-1].reason, AuditReason.RATE_LIMIT)
            self.gate.stop()
            self.gate = patch('mist.nvidia.NVIDIA_REQUEST_GATE', synthetic_gate())
            self.gate.start()
            self.addCleanup(self.gate.stop)
            with patch("mist.nvidia.http.client.HTTPSConnection", return_value=Connection(error=KeyboardInterrupt())):
                with self.assertRaises(KeyboardInterrupt):
                    app.handle("teste")
            self.assertEqual(audit.events[-1].reason, AuditReason.CANCELLED)
            self.assertEqual(app.history, ())

    def test_cli_hidden_key_entry(self):
        with tempfile.TemporaryDirectory() as directory:
            stdout, stderr = io.StringIO(), io.StringIO()
            with patch("mist.cli.getpass.getpass", return_value=SYNTHETIC_KEY), \
                    patch("mist.nvidia.http.client.HTTPSConnection", return_value=Connection()), \
                    redirect_stdout(stdout), redirect_stderr(stderr):
                result = main(["--config-dir", str(EXAMPLE), "--allow-external", "--ask-api-key",
                               "--audit-path", str(Path(directory) / "audit.jsonl"), "--message", "teste"])
            self.assertEqual(result, 0)
            self.assertIn("Olá, sou a Mist", stdout.getvalue())
            self.assertNotIn(SYNTHETIC_KEY, stdout.getvalue() + stderr.getvalue())

    def test_cli_refuses_echoing_key_fallback(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch("mist.cli.getpass.getpass", side_effect=getpass.GetPassWarning()), \
                redirect_stdout(stdout), redirect_stderr(stderr):
            result = main(["--config-dir", str(EXAMPLE), "--allow-external", "--ask-api-key"])
        self.assertEqual(result, 2)
        self.assertIn("Entrada oculta indisponível", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
