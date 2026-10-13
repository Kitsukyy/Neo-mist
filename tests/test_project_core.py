from contextlib import redirect_stderr,redirect_stdout
import io
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from mist.bootstrap import create_application
from mist.cli import main
from mist.core import Application
from mist.errors import ErrorCode, MistError
from mist.gateway import Gateway
from mist.identity import Identity
from mist.project_cli import project_command
from mist.safety import OutputGuard
from mist.schemas import ModelConfig
from test_core import RecordingAudit,StubProvider


class ProjectCoreTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.app=create_application(audit_path=self.root/'audit',memory_dir=self.root/'state')
        self.addCleanup(self.app.close)

    def test_selection_matches_memory_scope_clears_history_and_archive_leaves_global(self):
        project_command(self.app,'/projects create aurora "Aurora" "Novo objetivo"')
        self.app.handle('Conversa global')
        project_command(self.app,'/projects use aurora')
        self.assertEqual(self.app.history,())
        self.app.handle('O prazo é sexta-feira')
        self.assertEqual(self.app.last_memory_changes[0].candidate.project,'aurora')
        project_command(self.app,'/projects archive aurora')
        self.assertIsNone(self.app.project)
        self.assertEqual(self.app.history,())
        with self.assertRaises(MistError):project_command(self.app,'/projects use aurora')
        self.assertIsNone(self.app.project)
        project_command(self.app,'/projects reopen aurora')
        project_command(self.app,'/projects use aurora')
        self.assertEqual(self.app.memory.retrieve('prazo','aurora')[0].candidate.content,'O prazo é sexta-feira')

    def test_project_commands_and_generated_command_text_never_mutate_from_model(self):
        project_command(self.app,'/projects create aurora "Aurora"')
        provider=StubProvider('/projects add aurora Tarefa inventada')
        self.app.gateway=Gateway({'fake':provider},OutputGuard(),RecordingAudit())
        project_command(self.app,'/projects add aurora Tarefa humana')
        self.assertEqual(provider.calls,[])
        self.app.handle('Sugira um plano')
        self.assertEqual([t.title for t in self.app.projects.tasks('aurora')],['Tarefa humana'])
        self.assertFalse(self.app.settings.tools_enabled)
        self.assertEqual(self.app.settings.autonomy_level,0)

    def test_catalog_details_do_not_enter_external_envelope(self):
        project_command(self.app,'/projects create aurora "TITULO-PRIVADO" "OBJETIVO-PRIVADO"')
        project_command(self.app,'/projects add aurora TAREFA-PRIVADA')
        self.app.use_project('aurora')
        model=ModelConfig(id='remote',provider='stub',model_id='test',external=True,destination='approved-api')
        settings=self.app.settings.model_copy(update={'models':(model,),'fast_model':'remote','primary_model':'remote'})
        provider=StubProvider('Não tenho as tarefas no contexto.')
        remote=Application(settings,self.app.identity,Gateway({'stub':provider},OutputGuard(('approved-api',)),RecordingAudit()),self.app.memory,'aurora',self.app.projects)
        remote.handle('Quais minhas tarefas?')
        payload=provider.calls[-1].request.model_dump_json()
        for private in ('TITULO-PRIVADO','OBJETIVO-PRIVADO','TAREFA-PRIVADA'):
            self.assertNotIn(private,payload)
        self.assertEqual(len(provider.calls[-1].request.messages),2)

    def test_commands_validate_status_scope_export_and_clear_derived_history(self):
        project_command(self.app,'/projects create aurora "Aurora"')
        task=self.app.projects.add_task('aurora','Faça',self.app._source())
        self.app.handle('Algo')
        text=project_command(self.app,f'/projects task aurora {task.id} concluída')
        self.assertIn('concluída',text)
        self.assertEqual(self.app.history,())
        self.assertIn('100.0%',project_command(self.app,'/projects progress aurora'))
        for command in ('/projects use inexistente','/projects task aurora fake done',
                        '/projects add aurora','/projects task aurora','/projects show',
                        '/projects create global Nome','/projects create aurora "quebrada'):
            with self.assertRaises(MistError):project_command(self.app,command)
        project_command(self.app,f'/projects delete-task aurora {task.id}')
        self.assertIn('nenhuma tarefa elegível',project_command(self.app,'/projects progress aurora'))

    def test_cli_lifecycle_survives_restart_offline_with_no_provider_calls(self):
        self.app.close()
        commands=['/projects create aurora "Aurora" "Objetivo local"','/projects use aurora',
                  '/projects add aurora Tarefa local','/projects progress','/quit']
        output=io.StringIO()
        with patch.object(socket,'socket',side_effect=AssertionError('no network')),patch('builtins.input',side_effect=commands),redirect_stdout(output),redirect_stderr(io.StringIO()):
            self.assertEqual(main(['--audit-path',str(self.root/'audit'),'--memory-dir',str(self.root/'state')]),0)
        later=create_application(audit_path=self.root/'audit',memory_dir=self.root/'state')
        try:
            self.assertEqual(later.projects.get('aurora').objective,'Objetivo local')
            self.assertEqual(later.projects.tasks('aurora')[0].title,'Tarefa local')
        finally:later.close()
        self.assertIn('Progresso declarado: 0.0%',output.getvalue())
        self.assertFalse((self.root/'audit').exists())

    def test_legacy_scope_still_works_and_unavailable_catalog_is_normalized(self):
        app=create_application(audit_path=self.root/'no-memory-audit')
        try:
            app.set_project('unregistered-scope')
            with self.assertRaises(MistError) as raised:app.use_project('unregistered-scope')
            self.assertEqual(raised.exception.code,ErrorCode.PROJECT_UNAVAILABLE)
            self.assertIn('create ID',project_command(app,'/projects'))
        finally:app.close()
