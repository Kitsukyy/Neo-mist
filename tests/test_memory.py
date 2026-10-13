import json
from contextlib import closing
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4
import mist

from mist.errors import ErrorCode, MistError
from mist.memory import MemoryStore
from mist.memory_types import (EpistemicState, MemoryCandidate, MemoryKind, MemorySettings,
                               MemorySource, MemoryStatus, now, render_items)
from mist.schemas import Sensitivity, Style


def candidate(text='Projeto Aurora aprovado', **changes):
    return MemoryCandidate(content=text, source=MemorySource(origin='user', session_id=uuid4(),
        message_id=uuid4(), timestamp=now()), **changes)


class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / 'memory'
        self.store = MemoryStore(self.path)
        self.addCleanup(self.store.close)

    def assert_code(self, code, action):
        with self.assertRaises(MistError) as raised:
            action()
        self.assertEqual(raised.exception.code, code)
        self.assertNotIn('private-secret', str(raised.exception))

    def test_persistence_and_private_files(self):
        item = self.store.remember(candidate())
        self.store.close()
        self.store = MemoryStore(self.path)
        self.addCleanup(self.store.close)
        self.assertEqual(self.store.get(item.id), item)
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o700)
        for path in self.path.iterdir():
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_occupied_store_rejects_second_connection(self):
        self.assert_code(ErrorCode.MEMORY_UNAVAILABLE, lambda: MemoryStore(self.path))

    def test_interrupted_migration_rolls_back_both_databases(self):
        from mist.memory import SCHEMA
        other = self.root / 'interrupted'
        with patch('mist.memory.SCHEMA', (*SCHEMA, 'INVALID SQL')):
            self.assert_code(ErrorCode.MEMORY_UNAVAILABLE, lambda: MemoryStore(other))
        store = MemoryStore(other)
        self.addCleanup(store.close)
        self.assertEqual(store.list_items(), ())

    def test_process_exit_before_commit_recovers_without_partial_memory(self):
        self.store.close()
        script = '''import os,sys
sys.path.insert(0,sys.argv[1])
from pathlib import Path
from uuid import uuid4
from mist.memory import MemoryStore
from mist.memory_types import MemoryItem,MemoryCandidate,MemorySource,MemoryStatus,now
s=MemoryStore(Path(sys.argv[2]))
source=MemorySource(origin="user",session_id=uuid4(),message_id=uuid4(),timestamp=now())
item=MemoryItem(candidate=MemoryCandidate(content="interrupted synthetic item",source=source),sources=(source,),status=MemoryStatus.ACTIVE,created_at=now(),updated_at=now())
with s.transaction():
    s._save(item)
    s._event("remember",item)
    os._exit(7)
'''
        result = subprocess.run([sys.executable, '-c', script, str(Path(mist.__file__).resolve().parents[1]), str(self.path)], capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 7, result.stderr.decode())
        self.store = MemoryStore(self.path)
        self.addCleanup(self.store.close)
        self.assertEqual(self.store.list_items(), ())
        self.assertEqual(self.store._db.execute('SELECT COUNT(*) FROM registry.heads').fetchone()[0], 0)
        self.assertEqual(self.store._db.execute("SELECT COUNT(*) FROM events WHERE operation!='list'").fetchone()[0], 0)

    def test_expiry_is_inherited_by_derivatives(self):
        parent = self.store.remember(candidate('Fonte Aurora', expires_at='2099-01-01T00:00:00+00:00'))
        child = self.store.remember(candidate('Derivado Aurora', parents=(parent.id,)))
        self.assertEqual(child.candidate.expires_at, parent.candidate.expires_at)
        expired = self.store.remember(candidate('Fonte vencida', expires_at='2000-01-01T00:00:00+00:00'))
        self.assert_code(ErrorCode.MEMORY_INVALID, lambda: self.store.remember(candidate('Inválido', parents=(expired.id,))))

    def test_old_raw_data_file_is_reconciled_with_deletion_registry(self):
        item = self.store.remember(candidate('Texto Aurora removido'))
        raw = self.root / 'old.sqlite3'
        shutil.copyfile(self.path / 'memory.sqlite3', raw)
        self.store.delete(item.id)
        self.store.close()
        shutil.copyfile(raw, self.path / 'memory.sqlite3')
        self.store = MemoryStore(self.path)
        self.addCleanup(self.store.close)
        self.assertEqual(self.store.list_items(), ())
        self.assertEqual(self.store.retrieve('Aurora'), ())

    def test_unknown_schema_and_corruption_fail_closed(self):
        self.store.close()
        data = self.path / 'memory.sqlite3'
        with closing(sqlite3.connect(data)) as connection:
            connection.execute('PRAGMA user_version=99')
        self.assert_code(ErrorCode.MEMORY_UNAVAILABLE, lambda: MemoryStore(self.path))
        data.write_bytes(b'private-secret-corrupt-database')
        self.assert_code(ErrorCode.MEMORY_UNAVAILABLE, lambda: MemoryStore(self.path))

    def test_public_directory_symlink_hardlink_and_missing_registry_rejected(self):
        public = self.root / 'public'
        public.mkdir(mode=0o755)
        self.assert_code(ErrorCode.MEMORY_UNAVAILABLE, lambda: MemoryStore(public))
        linked = self.root / 'linked'
        linked.symlink_to(self.path)
        self.assert_code(ErrorCode.MEMORY_UNAVAILABLE, lambda: MemoryStore(linked))
        self.store.close()
        (self.path / 'registry.sqlite3').unlink()
        self.assert_code(ErrorCode.MEMORY_UNAVAILABLE, lambda: MemoryStore(self.path))
        other = self.root / 'unsafe'
        other.mkdir(mode=0o700)
        target = self.root / 'target'
        target.touch(mode=0o600)
        os.link(target, other / 'memory.lock')
        self.assert_code(ErrorCode.MEMORY_UNAVAILABLE, lambda: MemoryStore(other))

    def test_exact_dedup_preserves_sources_and_state(self):
        first = self.store.remember(candidate('  Preferência: café\r\nsem açúcar  '))
        again = self.store.remember(candidate('Preferência: cafe\u0301\nsem açúcar'))
        self.assertEqual(again.id, first.id)
        self.assertEqual(len(again.sources), 2)
        self.assertEqual(again.revision, 2)
        self.assertEqual(again.candidate.state, EpistemicState.DECLARED)
        different = self.store.remember(candidate('preferência: café\nsem açúcar'))
        self.assertNotEqual(different.id, first.id)
        scoped = self.store.remember(candidate('Preferência: café\nsem açúcar', project='aurora'))
        self.assertNotEqual(scoped.id, first.id)

    def test_retrieval_never_promotes_hypothesis(self):
        source = MemorySource(origin='application', session_id=uuid4(), message_id=uuid4(), timestamp=now())
        item = self.store.remember(MemoryCandidate(content='Talvez prefira cafe', source=source, state=EpistemicState.HYPOTHESIS))
        for _ in range(3):
            self.assertEqual(self.store.retrieve('cafe')[0].candidate.state, EpistemicState.HYPOTHESIS)
        self.assertEqual(self.store.get(item.id).revision, 1)

    def test_model_candidate_not_auto_active_or_confirmed(self):
        source = MemorySource(origin='model', session_id=uuid4(), message_id=uuid4(), timestamp=now())
        value = MemoryCandidate(content='Usuário gosta de café', source=source, state=EpistemicState.INFERRED)
        item = self.store.remember(value)
        self.assertEqual(item.status, MemoryStatus.CANDIDATE)
        self.assertEqual(self.store.retrieve('cafe'), ())
        self.assert_code(ErrorCode.MEMORY_INVALID, lambda: self.store.accept(item.id))
        invalid = value.model_copy(update={'state': EpistemicState.DECLARED})
        self.assert_code(ErrorCode.MEMORY_INVALID, lambda: self.store.remember(invalid))

    def test_conflict_waits_for_acceptance_and_explicit_correction_replaces(self):
        old = self.store.remember(candidate('Meu nome é Aurora', slot='user.name'))
        proposed = self.store.remember(candidate('Meu nome é Luna', slot='user.name'), automatic=True)
        self.assertEqual(proposed.status, MemoryStatus.CANDIDATE)
        self.assertEqual([item.id for item in self.store.retrieve('nome')], [old.id])
        changed = self.store.remember(candidate('Meu nome é Luna', slot='user.name', correction=True), automatic=True)
        self.assertEqual(changed.id, old.id)
        self.assertEqual(changed.revision, 2)
        self.assertEqual(self.store.retrieve('Aurora'), ())
        self.assertEqual(self.store.retrieve('Luna')[0].candidate.content, 'Meu nome é Luna')

    def test_accept_replaces_conflicting_slot(self):
        old = self.store.remember(candidate('Meu nome é Aurora', slot='user.name'))
        pending = self.store.remember(candidate('Meu nome é Luna', slot='user.name'))
        changed = self.store.accept(pending.id)
        self.assertEqual(changed.id, old.id)
        self.assertEqual(self.store.get(pending.id).status, MemoryStatus.ARCHIVED)
        self.assertEqual(self.store.retrieve('nome')[0].candidate.content, 'Meu nome é Luna')

    def test_project_scope_and_external_filter(self):
        global_item = self.store.remember(candidate('Aurora global', sensitivity=Sensitivity.EXTERNAL_ALLOWED))
        local = self.store.remember(candidate('Aurora local', project='a'))
        self.store.remember(candidate('Aurora outro projeto', project='b', sensitivity=Sensitivity.EXTERNAL_ALLOWED))
        self.assertEqual({item.id for item in self.store.retrieve('Aurora', 'a')}, {global_item.id, local.id})
        self.assertEqual({item.id for item in self.store.retrieve('Aurora', 'a', external=True)}, {global_item.id})
        self.assert_code(ErrorCode.MEMORY_NOT_FOUND, lambda: self.store.get(local.id, 'b'))
        self.assert_code(ErrorCode.MEMORY_NOT_FOUND, lambda: self.store.delete(local.id, 'b'))

    def test_query_is_literal_no_fts_or_sql_execution(self):
        item = self.store.remember(candidate('Aurora aprovada'))
        self.assertEqual(self.store.retrieve('"Aurora" OR x')[0].id, item.id)
        self.assertEqual(self.store.retrieve("Aurora'; DROP TABLE items; --")[0].id, item.id)
        self.assertEqual(self.store.retrieve('aurora')[0].id, item.id)

    def test_budget_and_deterministic_ties(self):
        for _ in range(5):
            self.store.remember(candidate('Aurora ' + str(uuid4())))
        limits = MemorySettings(max_items=2, max_chars=1000)
        first = self.store.retrieve('Aurora', settings=limits)
        second = self.store.retrieve('Aurora', settings=limits)
        self.assertEqual(first, second)
        self.assertLessEqual(len(first), 2)
        self.assertLessEqual(len(render_items(first)), 1000)
        self.assertEqual(self.store.retrieve('Aurora', settings=MemorySettings(max_chars=256)), ())

    def test_preference_and_expiry(self):
        preference = self.store.remember(candidate('Prefiro respostas curtas', kind=MemoryKind.PREFERENCE, slot='communication.style', style=Style.CONCISE))
        self.assertEqual(self.store.retrieve('olá')[0].id, preference.id)
        expired = self.store.remember(candidate('Aurora expirou', expires_at='2020-01-01T00:00:00+00:00'))
        self.assertNotIn(expired.id, {item.id for item in self.store.retrieve('Aurora')})

    def test_secret_is_rejected_without_persistence(self):
        for content in ('senha=private-secret', 'nvapi-synthetic-not-a-real-key-0123456789', '-----BEGIN PRIVATE KEY-----'):
            self.assert_code(ErrorCode.MEMORY_INVALID, lambda: self.store.remember(candidate(content)))
        self.assertEqual(self.store.list_items(), ())

    def test_derived_privacy_correction_and_delete_cascade(self):
        parent = self.store.remember(candidate('Aurora fonte'))
        child = self.store.remember(candidate('Aurora resumo', parents=(parent.id,), sensitivity=Sensitivity.EXTERNAL_ALLOWED))
        grandchild = self.store.remember(candidate('Aurora derivado', parents=(child.id,)))
        self.assertEqual(child.candidate.sensitivity, Sensitivity.LOCAL_ONLY)
        self.assert_code(ErrorCode.MEMORY_INVALID, lambda: self.store.allow_external(child.id))
        self.store.replace(parent.id, candidate('Aurora corrigida'))
        self.assertEqual(self.store.get(child.id).status, MemoryStatus.ARCHIVED)
        self.assertEqual(self.store.get(grandchild.id).status, MemoryStatus.ARCHIVED)
        self.assertEqual(self.store.delete(parent.id), 3)
        self.assertEqual(self.store.list_items(), ())
        self.assertEqual(self.store._db.execute('SELECT COUNT(*) FROM search').fetchone()[0], 0)
        self.assertEqual(self.store._db.execute('SELECT COUNT(*) FROM versions').fetchone()[0], 0)
        self.assertNotIn(b'Aurora corrigida', (self.path / 'memory.sqlite3').read_bytes())
        registry = (self.path / 'registry.sqlite3').read_bytes()
        self.assertNotIn(b'Aurora', registry)

    def test_external_permission_can_be_revoked_for_derivatives(self):
        parent = self.store.remember(candidate('Aurora fonte', sensitivity=Sensitivity.EXTERNAL_ALLOWED))
        child = self.store.remember(candidate('Aurora derivado', parents=(parent.id,), sensitivity=Sensitivity.EXTERNAL_ALLOWED))
        self.assertEqual(len(self.store.retrieve('Aurora', external=True)), 2)
        self.store.restrict_local(parent.id)
        self.assertEqual(self.store.retrieve('Aurora', external=True), ())
        self.assertEqual(self.store.get(child.id).candidate.sensitivity, Sensitivity.LOCAL_ONLY)

    def test_transaction_failure_rolls_back_content_fts_registry_and_audit(self):
        self.store._db.execute("CREATE TRIGGER fail_event BEFORE INSERT ON events BEGIN SELECT RAISE(ABORT,'private-secret'); END")
        self.assert_code(ErrorCode.MEMORY_UNAVAILABLE, lambda: self.store.remember(candidate()))
        self.store._db.execute('DROP TRIGGER fail_event')
        self.assertEqual(self.store.list_items(), ())
        self.assertEqual(self.store._db.execute('SELECT COUNT(*) FROM search').fetchone()[0], 0)
        self.assertEqual(self.store._db.execute('SELECT COUNT(*) FROM registry.heads').fetchone()[0], 0)

    def test_delete_rollback_does_not_leave_partial_tombstone(self):
        item = self.store.remember(candidate())
        self.store._db.execute("CREATE TRIGGER fail_delete BEFORE INSERT ON events WHEN NEW.operation='delete' BEGIN SELECT RAISE(ABORT,'private-secret'); END")
        self.assert_code(ErrorCode.MEMORY_UNAVAILABLE, lambda: self.store.delete(item.id))
        self.assertEqual(self.store.get(item.id), item)
        self.assertEqual(self.store._db.execute('SELECT COUNT(*) FROM registry.deleted').fetchone()[0], 0)

    def test_snapshot_preserves_versions_and_does_not_overwrite(self):
        item = self.store.remember(candidate())
        self.store.replace(item.id, candidate('Aurora nova'))
        path = self.root / 'snapshot.json'
        self.store.snapshot(path)
        data = json.loads(path.read_text())
        self.assertEqual(len(data['versions']), 2)
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assert_code(ErrorCode.MEMORY_UNAVAILABLE, lambda: self.store.snapshot(path))

    def test_restore_never_resurrects_deleted_content_or_derivatives(self):
        parent = self.store.remember(candidate())
        child = self.store.remember(candidate('Derivado Aurora', parents=(parent.id,)))
        path = self.root / 'old.json'
        self.store.snapshot(path)
        self.store.delete(parent.id)
        self.assertEqual(self.store.restore(path), 0)
        self.assertEqual(self.store.list_items(), ())
        self.assert_code(ErrorCode.MEMORY_NOT_FOUND, lambda: self.store.get(child.id))

    def test_restore_missing_data_respects_latest_revision_and_archive(self):
        old = self.store.remember(candidate())
        old_path = self.root / 'old.json'
        self.store.snapshot(old_path)
        self.store.replace(old.id, candidate('Aurora nova'))
        self.store.archive(old.id)
        new_path = self.root / 'new.json'
        self.store.snapshot(new_path)
        self.store.close()
        (self.path / 'memory.sqlite3').unlink()
        self.store = MemoryStore(self.path)
        self.addCleanup(self.store.close)
        self.assertEqual(self.store.restore(old_path), 0)
        self.assertEqual(self.store.restore(new_path), 1)
        self.assertEqual(self.store.get(old.id).status, MemoryStatus.ARCHIVED)
        self.assertEqual(self.store.retrieve('Aurora'), ())

    def test_restore_new_store_foreign_namespace_and_malformed_data_rejected(self):
        self.store.remember(candidate())
        path = self.root / 'snapshot.json'
        self.store.snapshot(path)
        other = MemoryStore(self.root / 'other')
        self.addCleanup(other.close)
        self.assert_code(ErrorCode.MEMORY_INVALID, lambda: other.restore(path))
        path.write_text('{"private-secret":true}')
        self.assert_code(ErrorCode.MEMORY_INVALID, lambda: self.store.restore(path))

    def test_cyclic_snapshot_is_rejected_before_changing_live_data(self):
        a = self.store.remember(candidate('Aurora A'))
        b = self.store.remember(candidate('Aurora B'))
        path = self.root / 'snapshot.json'
        self.store.snapshot(path)
        payload = json.loads(path.read_text())
        payload['items'][0]['candidate']['parents'] = [payload['items'][1]['id']]
        payload['items'][1]['candidate']['parents'] = [payload['items'][0]['id']]
        path.write_text(json.dumps(payload))
        self.assert_code(ErrorCode.MEMORY_INVALID, lambda: self.store.restore(path))
        self.assertEqual({item.id for item in self.store.list_items()}, {a.id, b.id})

    def test_snapshot_cannot_create_cross_project_provenance(self):
        self.store.remember(candidate('Aurora A', project='a'))
        self.store.remember(candidate('Aurora B', project='b'))
        path = self.root / 'snapshot.json'
        self.store.snapshot(path)
        payload = json.loads(path.read_text())
        payload['items'][0]['candidate']['parents'] = [payload['items'][1]['id']]
        path.write_text(json.dumps(payload))
        self.assert_code(ErrorCode.MEMORY_INVALID, lambda: self.store.restore(path))

    def test_metadata_audit_has_no_content(self):
        item = self.store.remember(candidate('Aurora private-secret example'))
        self.store.retrieve('Aurora')
        self.store.delete(item.id)
        events = [dict(row) for row in self.store._db.execute('SELECT * FROM events')]
        self.assertNotIn('private-secret', json.dumps(events))


if __name__ == '__main__':
    unittest.main()
