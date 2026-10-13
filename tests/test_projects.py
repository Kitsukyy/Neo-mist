from contextlib import closing, contextmanager
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

from mist.bootstrap import create_application
from mist.errors import ErrorCode, MistError
from mist.memory import MemoryStore
from mist.memory_types import MemorySource, now
from mist.project_types import ProjectState, TaskState
from mist.projects import ProjectStore


def source():
    return MemorySource(origin='user',session_id=uuid4(),message_id=uuid4(),timestamp=now())


class ProjectTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.memory=MemoryStore(self.root/'state')
        self.addCleanup(lambda:self.memory.close())
        self.store=ProjectStore(self.memory)

    def project(self,key='aurora'):
        return self.store.create(key,'Projeto Aurora','Objetivo privado',source())

    def assert_error(self,code,action):
        with self.assertRaises(MistError) as raised:action()
        self.assertEqual(raised.exception.code,code)
        return str(raised.exception)

    def test_project_and_task_sources_revisions_and_dates_survive_reopen(self):
        first=self.project()
        task=self.store.add_task('aurora','Tarefa privada',source())
        changed=self.store.update_task('aurora',task.id,source(),state='blocked',priority='high',due_date='2026-10-20')
        project=self.store.update('aurora',source(),name='Aurora revisada',objective='Novo objetivo')
        self.memory.close()
        self.memory=MemoryStore(self.root/'state');self.store=ProjectStore(self.memory)
        self.assertEqual(self.store.get('aurora'),project)
        self.assertEqual(self.store.tasks('aurora'),(changed,))
        self.assertEqual(changed.created_by,task.created_by)
        self.assertEqual(project.created_by,first.created_by)
        self.assertNotEqual(changed.updated_by.message_id,task.updated_by.message_id)
        self.assertEqual(changed.revision,2)
        self.assertEqual(changed.sensitivity,'local_only')

    def test_task_id_cannot_read_change_or_delete_another_project(self):
        self.project();self.project('luna')
        task=self.store.add_task('aurora','Só Aurora',source())
        for action in (lambda:self.store.update_task('luna',task.id,source(),state='done'),
                       lambda:self.store.delete_task('luna',task.id,source())):
            self.assert_error(ErrorCode.PROJECT_NOT_FOUND,action)
        self.assertEqual(self.store.tasks('luna'),())
        self.assertEqual(self.store.tasks('aurora'),(task,))

    def test_archive_freezes_updates_and_reopen_preserves_tasks(self):
        self.project();task=self.store.add_task('aurora','Conservar',source())
        self.store.update('aurora',source(),state='archived')
        for action in (lambda:self.store.get('aurora',active=True),
                       lambda:self.store.add_task('aurora','Nova',source()),
                       lambda:self.store.update_task('aurora',task.id,source(),state='done'),
                       lambda:self.store.update('aurora',source(),objective='Outro')):
            self.assert_error(ErrorCode.PROJECT_ARCHIVED,action)
        self.assertEqual(self.store.tasks('aurora'),(task,))
        self.store.update('aurora',source(),state='active')
        self.assertEqual(self.store.update_task('aurora',task.id,source(),state='done').state,TaskState.DONE)

    def test_progress_excludes_cancelled_and_has_no_empty_percentage(self):
        self.project()
        self.assertIsNone(self.store.progress('aurora')['percent'])
        tasks=[self.store.add_task('aurora',name,source()) for name in ('Um','Dois','Três')]
        self.store.update_task('aurora',tasks[0].id,source(),state='done')
        self.store.update_task('aurora',tasks[1].id,source(),state='cancelled')
        self.store.update_task('aurora',tasks[2].id,source(),state='blocked')
        result=self.store.progress('aurora')
        self.assertEqual((result['eligible'],result['total'],result['percent']),(2,3,50.0))
        self.assertEqual(result['counts'],{'done':1,'cancelled':1,'blocked':1})

    def test_invalid_secret_control_content_keys_and_nonuser_source_not_saved(self):
        secret='nvapi-'+'synthetic-not-a-real-key-0123456789'
        for key,name,objective,origin in (
                ('global','Nome','','user'),('../escape','Nome','','user'),('bad','Nome',secret,'user'),
                ('bad',secret,'','user'),('bad','N\x1bome','','user'),('bad','Nome','','model'),
                ('bad',' ','','user'),('bad','Nome','x'*2001,'user')):
            with self.subTest(key=key,name=name[:10]):
                src=source().model_copy(update={'origin':origin})
                message=self.assert_error(ErrorCode.PROJECT_INVALID,lambda:self.store.create(key,name,objective,src))
                self.assertNotIn(secret,message)
        self.assertEqual(self.store.list(),())

    def test_duplicate_key_and_invalid_task_update_preserve_original(self):
        self.project()
        self.assert_error(ErrorCode.PROJECT_INVALID,lambda:self.project())
        task=self.store.add_task('aurora','Original',source())
        for changes in ({'state':'inventado'},{'priority':'urgente'},{'due_date':'2026-02-30'},
                        {'due_date':'amanhã'},{'title':'\x00'},{'title':'x'*501}):
            self.assert_error(ErrorCode.PROJECT_INVALID,lambda:self.store.update_task('aurora',task.id,source(),**changes))
        self.assertEqual(self.store.tasks('aurora'),(task,))

    def test_failed_metadata_audit_rolls_back_task_update_and_creation(self):
        self.project();task=self.store.add_task('aurora','Sem mudança',source())
        self.memory._db.execute("CREATE TRIGGER projects.fail_event BEFORE INSERT ON events WHEN NEW.operation IN ('update_task','create_project') BEGIN SELECT RAISE(ABORT,'synthetic failure'); END")
        self.assert_error(ErrorCode.PROJECT_UNAVAILABLE,lambda:self.store.update_task('aurora',task.id,source(),state='done'))
        self.assert_error(ErrorCode.PROJECT_UNAVAILABLE,lambda:self.project('luna'))
        self.assertEqual(self.store.tasks('aurora'),(task,))
        self.assertEqual([item.key for item in self.store.list()],['aurora'])

    def test_delete_purges_text_and_audit_has_metadata_only(self):
        self.project();task=self.store.add_task('aurora','UNIQUE-DELETED-TEXT',source())
        self.store.delete_task('aurora',task.id,source())
        self.assertEqual(self.store.tasks('aurora'),())
        events=list(self.memory._db.execute('SELECT * FROM projects.events'))
        event_text=str([tuple(row) for row in events])
        self.assertNotIn('Objetivo privado',event_text)
        self.assertNotIn('UNIQUE-DELETED-TEXT',event_text)
        self.assertIn('delete_task',event_text)
        self.assertNotIn(b'UNIQUE-DELETED-TEXT',(self.root/'state/projects.sqlite3').read_bytes())

    def test_export_is_private_nonoverwriting_and_not_a_memory_snapshot(self):
        self.project();task=self.store.add_task('aurora','Exporte',source())
        path=self.root/'projects.json';self.store.export(path)
        result=json.loads(path.read_text())
        self.assertEqual(result['projects'][0]['key'],'aurora')
        self.assertEqual(result['tasks'][0]['id'],str(task.id))
        self.assertNotIn('items',result)
        self.assertEqual(path.stat().st_mode & 0o777,0o600)
        before=path.read_bytes()
        self.assert_error(ErrorCode.PROJECT_UNAVAILABLE,lambda:self.store.export(path))
        self.assertEqual(path.read_bytes(),before)
        link=self.root/'link';link.symlink_to(self.root,target_is_directory=True)
        self.assert_error(ErrorCode.PROJECT_INVALID,lambda:self.store.export(link/'no.json'))
        self.assertFalse((self.root/'no.json').exists())

    def test_memory_restore_does_not_roll_back_project_or_deleted_task(self):
        self.project();task=self.store.add_task('aurora','Antiga tarefa',source())
        snapshot=self.root/'memory.json';self.memory.snapshot(snapshot)
        changed=self.store.update('aurora',source(),objective='Vigente')
        self.store.delete_task('aurora',task.id,source())
        self.memory.restore(snapshot)
        self.assertEqual(self.store.get('aurora'),changed)
        self.assertEqual(self.store.tasks('aurora'),())

    def test_closed_owner_and_second_instance_cannot_use_catalog(self):
        self.assert_error(ErrorCode.MEMORY_UNAVAILABLE,lambda:MemoryStore(self.root/'state'))
        self.memory.close()
        self.assert_error(ErrorCode.PROJECT_UNAVAILABLE,lambda:self.store.list())

    def test_unsafe_catalog_files_and_unknown_schema_fail_bootstrap(self):
        self.memory.close()
        path=self.root/'state/projects.sqlite3'
        path.chmod(0o644)
        self.assert_error(ErrorCode.PROJECT_UNAVAILABLE,lambda:create_application(audit_path=self.root/'audit',memory_dir=self.root/'state'))
        path.chmod(0o600)
        with closing(sqlite3.connect(path)) as db, db:db.execute('PRAGMA user_version=9')
        self.assert_error(ErrorCode.PROJECT_UNAVAILABLE,lambda:create_application(audit_path=self.root/'audit',memory_dir=self.root/'state'))
        with closing(sqlite3.connect(path)) as db, db:db.execute('PRAGMA user_version=1')
        app=create_application(audit_path=self.root/'audit',memory_dir=self.root/'state');app.close()

    def test_interrupted_initial_migration_is_atomic_and_reopenable(self):
        folder=self.root/'interrupted'
        owner=MemoryStore(folder)
        try:
            with patch('mist.projects.SCHEMA',('CREATE TABLE projects.meta(namespace TEXT)','invalid sql')):
                self.assert_error(ErrorCode.PROJECT_UNAVAILABLE,lambda:ProjectStore(owner))
        finally:owner.close()
        with closing(sqlite3.connect(folder/'projects.sqlite3')) as db, db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],0)
            self.assertEqual(db.execute('SELECT name FROM sqlite_master WHERE type="table"').fetchall(),[])
        later=MemoryStore(folder)
        try:self.assertEqual(ProjectStore(later).list(),())
        finally:later.close()

    def test_catalog_from_different_namespace_is_rejected(self):
        self.memory.close()
        with closing(sqlite3.connect(self.root/'state/projects.sqlite3')) as db, db:
            db.execute('UPDATE meta SET namespace=?',(str(uuid4()),))
        self.assert_error(ErrorCode.PROJECT_UNAVAILABLE,lambda:create_application(audit_path=self.root/'audit',memory_dir=self.root/'state'))

    def test_bootstrap_cancellation_releases_memory_owner_lock(self):
        folder=self.root/'cancelled'
        with patch('mist.bootstrap.ProjectStore',side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                create_application(audit_path=self.root/'audit',memory_dir=folder)
        owner=MemoryStore(folder)
        try:self.assertEqual(ProjectStore(owner).list(),())
        finally:owner.close()

    def test_capacity_rejection_does_not_add_partial_project_or_task(self):
        with patch('mist.projects.MAX_PROJECTS',2),patch('mist.projects.MAX_TASKS_PER_PROJECT',2),patch('mist.projects.MAX_TOTAL_TASKS',3):
            self.project();self.project('luna')
            self.assert_error(ErrorCode.PROJECT_INVALID,lambda:self.project('outro'))
            self.store.add_task('aurora','Um',source());self.store.add_task('aurora','Dois',source())
            self.assert_error(ErrorCode.PROJECT_INVALID,lambda:self.store.add_task('aurora','Extra',source()))
            self.store.add_task('luna','Três',source())
            self.assert_error(ErrorCode.PROJECT_INVALID,lambda:self.store.add_task('luna','Extra',source()))
            self.assertEqual(len(self.store.tasks('aurora')),2)
            self.assertEqual(len(self.store.tasks('luna')),1)

    def test_stale_source_cannot_rollback_or_delete_current_task(self):
        self.project();task=self.store.add_task('aurora','Atual',source())
        stale=source().model_copy(update={'timestamp':'2020-01-01T00:00:00+00:00'})
        self.assert_error(ErrorCode.PROJECT_INVALID,lambda:self.store.update_task('aurora',task.id,stale,state='done'))
        self.assert_error(ErrorCode.PROJECT_INVALID,lambda:self.store.delete_task('aurora',task.id,stale))
        self.assertEqual(self.store.tasks('aurora'),(task,))

    def test_failed_export_audit_never_creates_private_content_file(self):
        self.project()
        self.memory._db.execute("CREATE TRIGGER projects.fail_export BEFORE INSERT ON events WHEN NEW.operation='export_projects' BEGIN SELECT RAISE(ABORT,'synthetic failure'); END")
        path=self.root/'not-created.json'
        self.assert_error(ErrorCode.PROJECT_UNAVAILABLE,lambda:self.store.export(path))
        self.assertFalse(path.exists())

    def test_failed_export_commit_cleans_only_the_new_file(self):
        self.project()
        original=self.memory.transaction
        @contextmanager
        def fail_commit():
            with original():
                yield
                raise sqlite3.OperationalError('synthetic commit failure')
        path=self.root/'not-committed.json'
        with patch.object(self.memory,'transaction',fail_commit):
            self.assert_error(ErrorCode.PROJECT_UNAVAILABLE,lambda:self.store.export(path))
        self.assertFalse(path.exists())
        self.assertEqual(self.memory._db.execute("SELECT count(*) FROM projects.events WHERE operation='export_projects'").fetchone()[0],0)
