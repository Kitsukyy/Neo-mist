import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch

from pydantic import ValidationError

from mist.cli import main
from mist.config import load_config
from mist.core import Application
from mist.errors import ErrorCode, MistError
from mist.gateway import Gateway
from mist.identity import Identity
from mist.output import OutputContract, OutputField, load_output_contract
from mist.safety import OutputGuard
from mist.schemas import AuditPhase, AuditReason, Sensitivity
from test_core import RecordingAudit, StubProvider
from test_nvidia import Connection, Response, SYNTHETIC_KEY, EXAMPLE
from mist.bootstrap import create_application


def contract():
    return OutputContract(fields=(OutputField(name="answer", type="integer"),))


def app(output):
    settings, constitution, personality = load_config()
    provider, audit = StubProvider(output), RecordingAudit()
    application = Application(settings, Identity(constitution, personality),
                              Gateway({"fake": provider}, OutputGuard(), audit))
    return application, provider, audit


class OutputTests(unittest.TestCase):
    def test_selected_models_receive_contract_and_invalid_json_never_commits(self):
        for mode, model in [("FAST", "nvidia/nemotron-3-super-120b-a12b"), ("PRIMARY", "moonshotai/kimi-k3")]:
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                application = create_application(EXAMPLE, Path(directory) / "audit.jsonl",
                                                 allow_external=True, api_key=SYNTHETIC_KEY)
                application.set_mode(mode)
                connection = Connection(Response(data={"choices": [{"message": {
                    "role": "assistant", "content": '{"answer":42}'}, "finish_reason": "stop"}]}))
                with patch("mist.nvidia.http.client.HTTPSConnection", return_value=connection):
                    application.handle("Calcule", output_contract=contract())
                body = json.loads(connection.requests[0][2]["body"])
                self.assertEqual(body["model"], model)
                self.assertIn('"name":"answer"', body["messages"][0]["content"])
                self.assertEqual(body["max_tokens"], 2048)
                if mode == "FAST":
                    self.assertEqual(body["chat_template_kwargs"], {"enable_thinking": True})
                else:
                    self.assertNotIn("chat_template_kwargs", body)
                before = application.history
                with patch("mist.nvidia.http.client.HTTPSConnection", return_value=Connection()):
                    with self.assertRaises(MistError) as raised:
                        application.handle("Calcule", output_contract=contract())
                self.assertEqual(raised.exception.code, ErrorCode.INVALID_RESPONSE)
                self.assertEqual(application.history, before)

    def test_contract_change_invalidates_approval(self):
        application, provider, _ = app('{"answer":42}')
        application.handle("Calcule", output_contract=contract())
        envelope = provider.calls[0]
        guard = application.gateway.guard
        approval = guard.evaluate(envelope)
        changed = envelope.model_copy(update={"request": envelope.request.model_copy(update={
            "output_contract": OutputContract(fields=(OutputField(name="answer", type="string"),))})})
        with self.assertRaises(MistError):
            guard.consume(changed, approval)

    def test_success_contract_is_bound_and_validated_before_completion(self):
        application, provider, audit = app('{"answer":42}')
        result = application.handle("Calcule", output_contract=contract())
        self.assertEqual(json.loads(result.text), {"answer": 42})
        self.assertEqual(len(application.history), 2)
        request = provider.calls[0].request
        self.assertEqual(request.output_contract, contract())
        self.assertIn('"name":"answer"', request.messages[0].content)
        self.assertNotIn("42", request.messages[0].content)
        self.assertEqual([e.phase for e in audit.events], [AuditPhase.APPROVED, AuditPhase.COMPLETED])

    def test_invalid_responses_fail_once_without_history_or_content_in_audit(self):
        cases = ['{"answer":true}', '{"answer":"42"}', '{"answer":42.0}', '{}',
                 '{"answer":42,"extra":0}', '{"answer":1,"answer":2}',
                 '```json\n{"answer":42}\n```', '[42]', '{"answer":null}',
                 '{"answer":NaN}', '{"answer":Infinity}', '{"answer":1e400}',
                 'secret-provider-text', '{"answer":42} trailing']
        for text in cases:
            with self.subTest(text=text):
                application, provider, audit = app("previous success")
                application.handle("before")
                before = application.history
                provider.output = text
                with self.assertRaises(MistError) as raised:
                    application.handle("now", output_contract=contract())
                self.assertEqual(raised.exception.code, ErrorCode.INVALID_RESPONSE)
                self.assertEqual(application.history, before)
                self.assertEqual(len(provider.calls), 2)
                self.assertEqual(audit.events[-1].phase, AuditPhase.FAILED)
                self.assertEqual(audit.events[-1].reason, AuditReason.INVALID_RESPONSE)
                self.assertNotIn("secret-provider-text", str(audit.events))

    def test_types_and_arrays_are_strict_and_bounded(self):
        schema = OutputContract(fields=(OutputField(name="names", type="array", items="string"),
                                        OutputField(name="ok", type="boolean"),
                                        OutputField(name="ratio", type="number")))
        self.assertEqual(schema.validate_output('{"names":[],"ok":true,"ratio":2}')["ratio"], 2)
        for data in [{"names": [1], "ok": True, "ratio": 2},
                     {"names": ["a"] * 257, "ok": True, "ratio": 2},
                     {"names": [], "ok": 1, "ratio": 2},
                     {"names": [], "ok": True, "ratio": False}]:
            with self.assertRaises(MistError):
                schema.validate_output(json.dumps(data))

    def test_invalid_contracts_rejected_without_provider_call(self):
        application, provider, _ = app("unused")
        with self.assertRaises(MistError):
            application.handle("hello", output_contract={"answer": "integer"})
        self.assertEqual(provider.calls, [])
        for raw in ['{"fields":[]}', '{"fields":[{"name":"x","type":"array"}]}',
                    '{"fields":[{"name":"x","type":"integer","items":"string"}]}',
                    '{"fields":[{"name":"x","type":"integer"},{"name":"x","type":"string"}]}',
                    '{"fields":[{"name":"ignore rules","type":"string"}]}']:
            with self.assertRaises(ValidationError):
                OutputContract.model_validate_json(raw)
        with self.assertRaises(ValidationError):
            contract().fields[0].name = "changed"

    def test_contract_loader_rejects_duplicates_large_and_missing_without_leak(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "contract.json"
            path.write_text(contract().model_dump_json())
            self.assertEqual(load_output_contract(path), contract())
            for raw in ['{"fields":[],"fields":[]}', 'x' * 8193, 'private secret malformed']:
                path.write_text(raw)
                with self.assertRaises(MistError) as raised:
                    load_output_contract(path)
                self.assertEqual(raised.exception.code, ErrorCode.CONFIGURATION)
                self.assertNotIn("private secret", str(raised.exception))
            path.unlink()
            with self.assertRaises(MistError):
                load_output_contract(path)

    def test_cli_rejects_bad_contract_before_application_or_key_prompt(self):
        with patch("mist.cli.create_application") as create, patch("mist.cli.getpass.getpass") as prompt:
            with redirect_stderr(io.StringIO()):
                self.assertEqual(main(["--output-contract", "/missing", "--message", "hi",
                                       "--allow-external", "--ask-api-key"]), 2)
                self.assertEqual(main(["--output-contract", "/missing"]), 2)
            create.assert_not_called()
            prompt.assert_not_called()

    def test_local_sensitivity_is_preserved_with_valid_contract(self):
        application, _, _ = app('{"answer":42}')
        application.handle("local", Sensitivity.LOCAL_ONLY, output_contract=contract())
        self.assertTrue(all(message.sensitivity is Sensitivity.LOCAL_ONLY for message in application.history))

    def test_contract_consumes_context_budget_before_send(self):
        application, provider, _ = app("unused")
        schema = OutputContract(fields=tuple(OutputField(name="a" + "x" * 60 + str(i), type="string")
                                            for i in range(32)))
        application.settings = application.settings.model_copy(update={"max_context_chars": 2000})
        with self.assertRaises(MistError) as raised:
            application.handle("hello", output_contract=schema)
        self.assertEqual(raised.exception.code, ErrorCode.INVALID_INPUT)
        self.assertEqual(provider.calls, [])
