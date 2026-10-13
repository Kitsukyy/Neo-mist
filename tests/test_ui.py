import http.client
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace

import mist
from mist.bootstrap import create_application
from mist.errors import ErrorCode, MistError
from mist.core import Application
from mist.gateway import Gateway
from mist.safety import OutputGuard
from mist.schemas import ModelConfig
from mist.ui import LocalHandler, LocalServer, UIConflict, UISession
from test_core import RecordingAudit, StubProvider


class UISessionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.app = create_application(audit_path=self.root/'audit', memory_dir=self.root/'state')
        self.addCleanup(self.app.close)
        self.ui = UISession(self.app)

    def command(self, op, **args):
        return self.ui.command({'op': op, 'revision': self.ui.revision, **args})

    def project(self, key='aurora'):
        self.command('project-create', key=key, name='Aurora', objective='Exemplo fictício')

    def test_project_task_lifecycle_and_declared_progress(self):
        self.project()
        self.command('task-create', title='Revisar roteiro')
        task = self.ui.state()['tasks'][0]
        self.command('task-update', id=task['id'], title='Revisar roteiro final', state='done', priority='high', due_date='2026-11-30')
        state = self.ui.state()
        self.assertEqual(state['progress']['percent'], 100.0)
        self.assertEqual(state['tasks'][0]['due_date'], '2026-11-30')
        self.command('project-update', key='aurora', name='Aurora 2', objective='Novo objetivo')
        self.assertEqual(self.ui.state()['current']['name'], 'Aurora 2')
        self.command('project-state', key='aurora', state='archived')
        self.assertIsNone(self.app.project)
        self.command('project-state', key='aurora', state='active')
        self.command('select', key='aurora')
        self.command('task-delete', id=task['id'], confirm=True)
        self.assertEqual(self.ui.state()['tasks'], [])

    def test_project_switch_clears_history_and_excludes_other_scopes(self):
        self.project()
        self.command('memory-create', text='Memória Aurora')
        self.command('chat', text='Teste local', local=True)
        self.assertTrue(self.ui.state()['history'])
        self.project('lunar')
        self.assertEqual(self.ui.state()['history'], [])
        self.assertEqual(self.ui.state()['memories'], [])
        self.command('select', key=None)
        self.assertIsNone(self.ui.state()['current'])

    def test_stale_tab_cannot_mutate_current_scope(self):
        self.project()
        old_revision = self.ui.revision
        self.project('lunar')
        with self.assertRaises(UIConflict):
            self.ui.command({'op':'task-create','revision':old_revision,'title':'Wrong scope'})
        self.assertEqual(self.app.projects.tasks('lunar'), ())

    def test_memory_correction_privacy_and_deletion(self):
        self.command('memory-create', text='Declaração fictícia')
        item = self.ui.state()['memories'][0]
        self.app.memory.allow_external(item['id'])
        self.command('memory-replace', id=item['id'], text='Declaração corrigida')
        self.assertEqual(self.ui.state()['memories'][0]['candidate']['sensitivity'], 'local_only')
        self.command('chat', text='Teste', local=True)
        self.command('memory-delete', id=item['id'], confirm=True)
        self.assertEqual(self.ui.state()['memories'], [])
        self.assertEqual(self.ui.state()['history'], [])

    def test_destructive_commands_require_explicit_confirmation(self):
        self.command('memory-create', text='Persistir')
        item = self.ui.state()['memories'][0]
        for value in (False, 1, 'true', None):
            with self.assertRaises(MistError): self.command('memory-delete', id=item['id'], confirm=value)
        self.assertEqual(len(self.ui.state()['memories']), 1)

    def test_preferences_invalid_pair_does_not_partially_change(self):
        with self.assertRaises(MistError): self.command('preferences', mode='FAST', style='invalid')
        self.assertEqual(self.ui.state()['mode'], 'AUTO')
        self.command('preferences', mode='PRIMARY', style='concise')
        self.assertEqual(self.ui.state()['style'], 'concise')
        self.command('reset')
        self.assertEqual(self.ui.state()['style'], 'auto')

    def test_unknown_extra_fields_or_command_text_do_not_execute(self):
        for data in ({'op':'shell','revision':0,'command':'pwd'},
                     {'op':'reset','revision':True},
                     {'op':'reset','revision':0,'path':'/tmp'},
                     {'op':'chat','revision':1,'text':'test','local':'false'}):
            if type(data['revision']) is int: data['revision'] = self.ui.revision
            with self.assertRaises(MistError): self.ui.command(data)
        self.command('chat', text='/projects create fake Generated', local=True)
        self.assertEqual(self.app.projects.list(), ())

    def test_failed_generation_still_reports_automatic_capture_and_advances_revision(self):
        with patch.object(self.app.gateway, 'generate', side_effect=MistError(ErrorCode.PROVIDER_TIMEOUT)):
            with self.assertRaises(MistError): self.command('chat', text='Eu prefiro respostas curtas', local=False)
        state = self.ui.state()
        self.assertEqual(state['revision'], 1)
        self.assertEqual(len(state['notices']), 1)
        self.assertEqual(len(state['memories']), 1)
        self.assertEqual(state['history'], [])

    def test_state_does_not_contain_gateway_secrets_or_system_prompt(self):
        state = json.dumps(self.ui.state())
        self.assertNotIn('api_key', state)
        self.assertNotIn('constitution', state)
        self.assertEqual(self.ui.state()['version'], mist.__version__)

    def test_edit_failure_keeps_task_unchanged(self):
        self.project(); self.command('task-create', title='Original')
        task = self.ui.state()['tasks'][0]
        with self.assertRaises(MistError):
            self.command('task-update', id=task['id'], title='Alterado', state='done', priority='high', due_date='2026-02-30')
        self.assertEqual(self.ui.state()['tasks'][0], task)

    def test_local_chat_blocks_external_provider_before_any_call(self):
        model=ModelConfig(id='remote',provider='stub',model_id='test',external=True,destination='approved-api')
        settings=self.app.settings.model_copy(update={'models':(model,),'fast_model':'remote','primary_model':'remote'})
        provider=StubProvider('Resposta fictícia')
        app=Application(settings,self.app.identity,Gateway({'stub':provider},OutputGuard(('approved-api',)),RecordingAudit()),self.app.memory,projects=self.app.projects)
        ui=UISession(app)
        with self.assertRaises(MistError) as raised:
            ui.command({'op':'chat','revision':0,'text':'Somente local','local':True})
        self.assertEqual(raised.exception.code,ErrorCode.GUARD_BLOCKED)
        self.assertEqual(provider.calls,[])
        self.assertTrue(ui.state()['external'])
        ui.command({'op':'chat','revision':1,'text':'Teste fictício autorizado','local':False})
        self.assertEqual(len(provider.calls),1)

    def test_state_memory_limit_reports_more_without_claiming_total(self):
        items=[self.app.remember('Declaração fictícia')]*201
        with patch.object(self.app.memory,'list_items',return_value=items) as listing:
            state=self.ui.state()
        listing.assert_called_once_with(None,limit=201)
        self.assertEqual(len(state['memories']),200)
        self.assertTrue(state['memory_more'])

    def test_failed_operation_does_not_disclose_exception_details(self):
        handler=object.__new__(LocalHandler)
        handler.path='/api/command'
        handler.headers=http.client.HTTPMessage()
        body=b'{"op":"reset","revision":0}'
        handler.headers['Content-Length']=str(len(body))
        handler.headers['Content-Type']='application/json'
        handler.rfile=io.BytesIO(body)
        handler._authorized=Mock(return_value=True)
        handler._json=Mock()
        handler.server=SimpleNamespace(session=SimpleNamespace(command=Mock(side_effect=RuntimeError('PRIVATE-EXCEPTION-CONTENT'))))
        handler.do_POST()
        status,data=handler._json.call_args.args
        self.assertEqual(status,500)
        self.assertNotIn('PRIVATE-EXCEPTION-CONTENT',json.dumps(data))

    def test_storage_survives_another_session(self):
        self.project(); self.command('task-create', title='Persistente')
        self.app.close()
        app = create_application(audit_path=self.root/'audit', memory_dir=self.root/'state')
        try:
            app.use_project('aurora')
            self.assertEqual(UISession(app).state()['tasks'][0]['title'], 'Persistente')
            self.assertEqual(UISession(app).state()['history'], [])
        finally: app.close()

    def test_server_always_binds_loopback(self):
        with LocalServer(self.ui) as server:
            self.assertEqual(server.server_address[0], '127.0.0.1')


class HTTPUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        env = os.environ.copy()
        env['PYTHONPATH'] = str(Path(mist.__file__).resolve().parent.parent)
        cls.process = subprocess.Popen([sys.executable,'-m','mist.ui','--memory-dir',str(cls.root/'state'),
                                      '--audit-path',str(cls.root/'audit')],cwd=cls.root,env=env,
                                      stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        line = cls.process.stdout.readline()
        match = re.search(r'http://127\.0\.0\.1:(\d+)', line)
        if not match:
            cls.process.terminate();cls.process.wait(timeout=5)
            raise AssertionError('Local UI failed to start')
        cls.port = int(match[1]); cls.origin=f'http://127.0.0.1:{cls.port}'
        status,headers,body=cls.request('GET','/')
        cls.token=re.search(rb'name="mist-token" content="([^"]+)"',body).group(1).decode()

    @classmethod
    def tearDownClass(cls):
        cls.process.terminate();cls.process.communicate(timeout=5);cls.temp.cleanup()

    @classmethod
    def request(cls, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection('127.0.0.1',cls.port,timeout=5)
        try:
            connection.request(method,path,body=body,headers=headers or {})
            response=connection.getresponse()
            return response.status,dict(response.getheaders()),response.read()
        finally: connection.close()

    def headers(self):
        return {'X-Mist-Token':self.token,'Origin':self.origin,'Content-Type':'application/json'}

    def test_assets_and_security_headers(self):
        for path, content in (('/','text/html'),('/app.js','text/javascript'),('/style.css','text/css')):
            status,headers,body=self.request('GET',path)
            self.assertEqual(status,200);self.assertTrue(body)
            self.assertIn(content,headers['Content-Type'])
            self.assertEqual(headers['Cache-Control'],'no-store')
            self.assertEqual(headers['X-Frame-Options'],'DENY')
            self.assertIn("default-src 'none'",headers['Content-Security-Policy'])

    def test_api_requires_token(self):
        for headers in ({},{'X-Mist-Token':'invalid'}):
            self.assertEqual(self.request('GET','/api/state',headers=headers)[0],403)
        self.assertEqual(self.request('GET','/api/state',headers=self.headers())[0],200)

    def test_rebinding_host_and_foreign_origins_are_denied(self):
        for header in ({'Host':f'evil.test:{self.port}'},{'Origin':'https://evil.test'},
                       {'Sec-Fetch-Site':'cross-site'},{'Sec-Fetch-Site':'same-site'}):
            self.assertEqual(self.request('GET','/',headers=header)[0],403)

    def test_mutation_requires_origin_even_with_token(self):
        headers=self.headers();del headers['Origin']
        self.assertEqual(self.request('POST','/api/command','{}',headers)[0],403)

    def test_paths_cannot_read_host_files(self):
        for path in ('/../pyproject.toml','/web/../../etc/passwd','/api/export?path=/etc/passwd','/?token=anything'):
            self.assertEqual(self.request('GET',path,headers=self.headers())[0],404)

    def test_invalid_json_types_sizes_and_transfer_encoding(self):
        for body in ('{','[]','null','{"op":"reset","revision":true}', 'x'*32769):
            self.assertEqual(self.request('POST','/api/command',body,self.headers())[0],400)
        headers=self.headers();headers['Transfer-Encoding']='chunked'
        self.assertEqual(self.request('POST','/api/command','{}',headers)[0],400)
        headers=self.headers();headers['Content-Type']='text/plain'
        self.assertEqual(self.request('POST','/api/command','{}',headers)[0],400)

    def test_http_command_and_stale_revision(self):
        status,_,body=self.request('GET','/api/state',headers=self.headers())
        revision=json.loads(body)['revision']
        command=json.dumps({'op':'chat','revision':revision,'text':'Teste fictício','local':True})
        status,_,body=self.request('POST','/api/command',command,self.headers())
        self.assertEqual(status,200)
        reply=json.loads(body)
        self.assertTrue(reply['result']['response']['simulated'])
        self.assertEqual(reply['state']['revision'],revision+1)
        self.assertEqual(self.request('POST','/api/command',command,self.headers())[0],409)

    def test_unsupported_methods_cannot_mutate(self):
        self.assertEqual(self.request('DELETE','/api/command',headers=self.headers())[0],501)

    def test_duplicate_host_headers_are_denied(self):
        connection=http.client.HTTPConnection('127.0.0.1',self.port,timeout=5)
        try:
            connection.putrequest('GET','/')
            connection.putheader('Host',f'127.0.0.1:{self.port}')
            connection.endheaders()
            response=connection.getresponse();self.assertEqual(response.status,403);response.read()
        finally:connection.close()


if __name__ == '__main__':
    unittest.main()
