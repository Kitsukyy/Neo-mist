"""Private SQLite/FTS5 memory with a separate, non-content restore registry."""
from contextlib import contextmanager
from collections import deque
from datetime import datetime
try:
    import fcntl
except ImportError:
    fcntl = None
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
from threading import RLock
from uuid import UUID, uuid4

from pydantic import Field, ValidationError, model_validator

from mist.errors import ErrorCode, MistError
from mist.memory_types import (MemoryCandidate, MemoryItem, MemoryKind, MemorySettings,
                               MemoryStatus, normalized, now, render_items)
from mist.safety import OutputGuard
from mist.schemas import Identifier, Sensitivity, StrictModel

SCHEMA = (
    'CREATE TABLE meta(namespace TEXT NOT NULL)',
    '''CREATE TABLE items(id TEXT PRIMARY KEY, revision INTEGER NOT NULL, status TEXT NOT NULL,
       project TEXT, kind TEXT NOT NULL, sensitivity TEXT NOT NULL, slot TEXT, digest TEXT NOT NULL,
       expires REAL, data TEXT NOT NULL)''',
    'CREATE TABLE versions(id TEXT, revision INTEGER, data TEXT NOT NULL, PRIMARY KEY(id,revision))',
    'CREATE INDEX lookup ON items(project,kind,status,slot)',
    'CREATE TABLE relations(parent TEXT,child TEXT,PRIMARY KEY(parent,child))',
    'CREATE TABLE events(id TEXT PRIMARY KEY,time TEXT NOT NULL,operation TEXT NOT NULL,item TEXT,revision INTEGER)',
    "CREATE VIRTUAL TABLE search USING fts5(id UNINDEXED,content,tokenize='unicode61 remove_diacritics 2')",
)


class MemorySnapshot(StrictModel):
    schema_version: int = Field(ge=1, le=1)
    namespace: UUID
    items: tuple[MemoryItem, ...] = Field(max_length=10000)
    versions: tuple[MemoryItem, ...] = Field(max_length=100000)

    @model_validator(mode='after')
    def validate_graph(self):
        items = {item.id: item for item in self.items}
        if len(items) != len(self.items):
            raise ValueError('Duplicate item')
        degrees = {key: 0 for key in items}
        children = {key: [] for key in items}
        for item in self.items:
            for parent_id in item.candidate.parents:
                if parent_id in items:
                    parent = items[parent_id]
                    if parent.candidate.project not in (None, item.candidate.project):
                        raise ValueError('Cross-project provenance')
                    degrees[item.id] += 1
                    children[parent_id].append(item.id)
        queue = deque(key for key in items if degrees[key] == 0)
        visited = 0
        while queue:
            key = queue.popleft()
            visited += 1
            for child in children[key]:
                degrees[child] -= 1
                if degrees[child] == 0:
                    queue.append(child)
        if visited != len(items):
            raise ValueError('Cyclic provenance')
        return self


def private_file(path: Path, *, new=False):
    flags = os.O_RDWR | os.O_CREAT | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0)
    if new:
        flags |= os.O_EXCL
    fd = os.open(path, flags, 0o600)
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_nlink != 1 or info.st_uid != os.getuid():
        os.close(fd)
        raise OSError('Unsafe local file')
    return fd


class MemoryStore:
    def __init__(self, directory: Path):
        self.directory = Path(directory).absolute()
        self._lock = RLock()
        self._db = None
        self._lock_fd = None
        try:
            if fcntl is None or sqlite3.sqlite_version_info < (3, 42, 0):
                raise OSError('SQLite FTS5 secure-delete required')
            if any(part.is_symlink() for part in (self.directory, *self.directory.parents)):
                raise OSError('Symlink directory')
            self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
            info = self.directory.stat()
            if not stat.S_ISDIR(info.st_mode) or info.st_mode & 0o077 or info.st_uid != os.getuid():
                raise OSError('Private directory required')
            self._lock_fd = private_file(self.directory / 'memory.lock')
            fcntl.flock(self._lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            data, registry = self.directory / 'memory.sqlite3', self.directory / 'registry.sqlite3'
            if data.exists() and not registry.exists():
                raise OSError('Restore registry missing')
            for path in (data, registry):
                os.close(private_file(path))
            self._db = sqlite3.connect(data.as_uri() + '?mode=rw', uri=True, isolation_level=None, timeout=1)
            self._db.row_factory = sqlite3.Row
            self._db.execute('PRAGMA trusted_schema=OFF')
            self._db.execute('PRAGMA journal_mode=DELETE')
            self._db.execute('PRAGMA synchronous=FULL')
            self._db.execute('PRAGMA secure_delete=ON')
            self._db.execute('PRAGMA temp_store=MEMORY')
            self._db.execute('ATTACH DATABASE ? AS registry', (str(registry),))
            self._db.execute('PRAGMA registry.journal_mode=DELETE')
            self._db.execute('PRAGMA registry.synchronous=FULL')
            self._migrate()
            if self._db.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
                raise OSError('Integrity failure')
            with self.transaction():
                # A manually copied old data file cannot bypass the current registry.
                stale = list(self._db.execute('SELECT i.id FROM items i LEFT JOIN registry.heads h ON h.id=i.id WHERE i.id IN (SELECT id FROM registry.deleted) OR i.revision<h.revision'))
                for row in stale:
                    key = row[0]
                    self._db.execute('DELETE FROM search WHERE id=?', (key,))
                    self._db.execute('DELETE FROM items WHERE id=?', (key,))
                    self._db.execute('DELETE FROM versions WHERE id=?', (key,))
        except (OSError, sqlite3.Error, ValueError, MistError):
            self.close()
            raise MistError(ErrorCode.MEMORY_UNAVAILABLE) from None
        except BaseException:
            self.close()
            raise

    @contextmanager
    def transaction(self):
        with self._lock:
            if self._db is None:
                raise MistError(ErrorCode.MEMORY_UNAVAILABLE)
            try:
                self._db.execute('BEGIN IMMEDIATE')
                yield
                self._db.execute('COMMIT')
            except BaseException as exc:
                if self._db.in_transaction:
                    self._db.execute('ROLLBACK')
                if isinstance(exc, (sqlite3.Error, OSError, ValidationError, ValueError, TypeError)):
                    raise MistError(ErrorCode.MEMORY_UNAVAILABLE) from None
                raise

    def _migrate(self):
        with self.transaction():
            rv = self._db.execute('PRAGMA registry.user_version').fetchone()[0]
            version = self._db.execute('PRAGMA user_version').fetchone()[0]
            if version not in (0, 1) or rv not in (0, 1):
                raise OSError('Unknown schema')
            if rv == 0:
                self._db.execute('CREATE TABLE registry.meta(namespace TEXT NOT NULL)')
                self._db.execute('INSERT INTO registry.meta VALUES(?)', (str(uuid4()),))
                self._db.execute('CREATE TABLE registry.deleted(id TEXT PRIMARY KEY,time TEXT NOT NULL)')
                self._db.execute('CREATE TABLE registry.heads(id TEXT PRIMARY KEY,revision INTEGER NOT NULL,status TEXT NOT NULL)')
                self._db.execute('PRAGMA registry.user_version=1')
            self.namespace = self._db.execute('SELECT namespace FROM registry.meta').fetchone()[0]
            UUID(self.namespace)
            if version == 0:
                for statement in SCHEMA:
                    self._db.execute(statement)
                self._db.execute('INSERT INTO meta VALUES(?)', (self.namespace,))
                self._db.execute("INSERT INTO search(search,rank) VALUES('secure-delete',1)")
                self._db.execute('PRAGMA user_version=1')
            if self._db.execute('SELECT namespace FROM meta').fetchone()[0] != self.namespace:
                raise OSError('Namespace mismatch')

    def close(self):
        if self._db is not None:
            self._db.close()
            self._db = None
        if self._lock_fd is not None:
            os.close(self._lock_fd)
            self._lock_fd = None

    def _event(self, operation, item=None):
        self._db.execute('INSERT INTO events VALUES(?,?,?,?,?)',
                         (str(uuid4()), now(), operation, str(item.id) if item else None, item.revision if item else None))

    @staticmethod
    def _candidate(candidate):
        try:
            candidate = MemoryCandidate.model_validate_json(candidate.model_dump_json())
            # Reuse the same complementary credential patterns as the output guard.
            if any(pattern.search(candidate.content) for pattern in OutputGuard()._secret_patterns):
                raise ValueError('Credential content')
            return candidate.model_copy(update={'content': normalized(candidate.content)})
        except (ValueError, AttributeError, ValidationError):
            raise MistError(ErrorCode.MEMORY_INVALID) from None

    @staticmethod
    def _digest(candidate):
        content = {'text': candidate.content, 'state': candidate.state.value, 'slot': candidate.slot,
                   'style': candidate.style.value if candidate.style else None,
                   'parents': sorted(str(parent) for parent in candidate.parents)}
        return hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()

    def _save(self, item):
        c = item.candidate
        expiry = datetime.fromisoformat(c.expires_at).timestamp() if c.expires_at else None
        self._db.execute('INSERT OR REPLACE INTO items VALUES(?,?,?,?,?,?,?,?,?,?)',
                         (str(item.id), item.revision, item.status.value, c.project, c.kind.value,
                          c.sensitivity.value, c.slot, self._digest(c), expiry, item.model_dump_json()))
        self._db.execute('INSERT OR REPLACE INTO versions VALUES(?,?,?)', (str(item.id), item.revision, item.model_dump_json()))
        self._db.execute('INSERT INTO registry.heads VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET revision=excluded.revision,status=excluded.status',
                         (str(item.id), item.revision, item.status.value))
        self._db.execute('DELETE FROM search WHERE id=?', (str(item.id),))
        if item.status is MemoryStatus.ACTIVE:
            self._db.execute('INSERT INTO search(id,content) VALUES(?,?)', (str(item.id), c.content))
        for parent in c.parents:
            self._db.execute('INSERT OR IGNORE INTO relations VALUES(?,?)', (str(parent), str(item.id)))

    def _get(self, item_id, project=None):
        try:
            item_id = str(UUID(str(item_id)))
        except (ValueError, TypeError):
            raise MistError(ErrorCode.MEMORY_INVALID) from None
        row = self._db.execute('SELECT data FROM items WHERE id=? AND (project IS NULL OR project=?)', (item_id, project)).fetchone()
        if row is None:
            raise MistError(ErrorCode.MEMORY_NOT_FOUND)
        try:
            return MemoryItem.model_validate_json(row['data'])
        except ValidationError:
            raise MistError(ErrorCode.MEMORY_UNAVAILABLE) from None

    def get(self, item_id, project=None):
        with self.transaction():
            item = self._get(item_id, project)
            self._event('get', item)
            return item

    def remember(self, candidate, *, automatic=False):
        c = self._candidate(candidate)
        with self.transaction():
            for parent_id in c.parents:
                parent = self._get(parent_id, c.project)
                if parent.status is not MemoryStatus.ACTIVE or (parent.candidate.expires_at and datetime.fromisoformat(parent.candidate.expires_at).timestamp() <= datetime.fromisoformat(now()).timestamp()):
                    raise MistError(ErrorCode.MEMORY_INVALID)
                if parent.candidate.sensitivity is Sensitivity.LOCAL_ONLY:
                    c = c.model_copy(update={'sensitivity': Sensitivity.LOCAL_ONLY})
                if parent.candidate.expires_at and (c.expires_at is None or datetime.fromisoformat(c.expires_at) > datetime.fromisoformat(parent.candidate.expires_at)):
                    c = c.model_copy(update={'expires_at': parent.candidate.expires_at})
            conflict = self._db.execute('SELECT data FROM items WHERE project IS ? AND kind=? AND slot=? AND status=? ORDER BY id LIMIT 1',
                                        (c.project, c.kind.value, c.slot, 'active')).fetchone() if c.slot else None
            if conflict and c.correction and MemoryItem.model_validate_json(conflict['data']).candidate.content != c.content:
                return self._replace(MemoryItem.model_validate_json(conflict['data']), c)
            duplicate = self._db.execute('SELECT data FROM items WHERE digest=? AND project IS ? AND kind=? AND sensitivity=? AND status IN (?,?) ORDER BY id LIMIT 1',
                (self._digest(c), c.project, c.kind.value, c.sensitivity.value, 'active', 'candidate')).fetchone()
            if duplicate:
                item = MemoryItem.model_validate_json(duplicate['data'])
                if c.source not in item.sources:
                    if len(item.sources) >= 100:
                        raise MistError(ErrorCode.MEMORY_INVALID)
                    item = item.model_copy(update={'candidate': c, 'revision': item.revision + 1, 'sources': (*item.sources, c.source), 'updated_at': now()})
                    self._save(item)
                    self._event('deduplicate', item)
                return item
            conflict = self._db.execute('SELECT data FROM items WHERE project IS ? AND kind=? AND slot=? AND status=? ORDER BY id LIMIT 1',
                                        (c.project, c.kind.value, c.slot, 'active')).fetchone() if c.slot else None
            if conflict and c.correction:
                return self._replace(MemoryItem.model_validate_json(conflict['data']), c)
            status = MemoryStatus.CANDIDATE if conflict or c.source.origin == 'model' else MemoryStatus.ACTIVE
            stamp = now()
            item = MemoryItem(candidate=c, sources=(c.source,), status=status, created_at=stamp, updated_at=stamp)
            self._save(item)
            self._event('automatic_candidate' if automatic else 'remember', item)
            return item

    def _descendants(self, item_id):
        return {row[0] for row in self._db.execute('WITH RECURSIVE children(id) AS (SELECT child FROM relations WHERE parent=? UNION SELECT r.child FROM relations r JOIN children c ON r.parent=c.id) SELECT id FROM children', (str(item_id),))}

    def _archive_children(self, item_id):
        for child_id in self._descendants(item_id):
            row = self._db.execute('SELECT data FROM items WHERE id=?', (child_id,)).fetchone()
            if row:
                item = MemoryItem.model_validate_json(row['data'])
                self._save(item.model_copy(update={'revision': item.revision + 1, 'status': MemoryStatus.ARCHIVED, 'updated_at': now()}))

    def _replace(self, item, candidate):
        # Old content remains versioned until explicit deletion; never current in FTS.
        old = item.model_copy(update={'status': MemoryStatus.SUPERSEDED})
        self._db.execute('UPDATE versions SET data=? WHERE id=? AND revision=?', (old.model_dump_json(), str(item.id), item.revision))
        self._archive_children(item.id)
        sensitivity = (Sensitivity.LOCAL_ONLY if Sensitivity.LOCAL_ONLY in
                       (candidate.sensitivity, item.candidate.sensitivity) else Sensitivity.EXTERNAL_ALLOWED)
        candidate = candidate.model_copy(update={'sensitivity': sensitivity, 'parents': item.candidate.parents})
        changed = item.model_copy(update={'candidate': candidate, 'sources': (candidate.source,), 'revision': item.revision + 1,
                                        'status': MemoryStatus.ACTIVE, 'updated_at': now()})
        self._save(changed)
        self._event('replace', changed)
        return changed

    def replace(self, item_id, candidate, project=None):
        c = self._candidate(candidate)
        with self.transaction():
            item = self._get(item_id, project)
            if (c.kind, c.project, c.slot) != (item.candidate.kind, item.candidate.project, item.candidate.slot):
                raise MistError(ErrorCode.MEMORY_INVALID)
            if c.source.origin != 'user':
                raise MistError(ErrorCode.MEMORY_INVALID)
            return self._replace(item, c)

    def accept(self, item_id, project=None):
        with self.transaction():
            item = self._get(item_id, project)
            if item.status is not MemoryStatus.CANDIDATE or item.candidate.source.origin != 'user':
                raise MistError(ErrorCode.MEMORY_INVALID)
            c = item.candidate
            other = self._db.execute('SELECT id FROM items WHERE project IS ? AND slot=? AND status=?', (c.project, c.slot, 'active')).fetchone() if c.slot else None
            if other:
                replaced = self._replace(self._get(other[0], project), c)
                self._db.execute('DELETE FROM search WHERE id=?', (str(item.id),))
                self._save(item.model_copy(update={'status': MemoryStatus.ARCHIVED, 'revision': item.revision + 1, 'updated_at': now()}))
                return replaced
            changed = item.model_copy(update={'status': MemoryStatus.ACTIVE, 'revision': item.revision + 1, 'updated_at': now()})
            self._save(changed)
            self._event('accept', changed)
            return changed

    def archive(self, item_id, project=None):
        with self.transaction():
            item = self._get(item_id, project)
            self._archive_children(item.id)
            self._save(item.model_copy(update={'revision': item.revision + 1, 'status': MemoryStatus.ARCHIVED, 'updated_at': now()}))
            self._event('archive', item)

    def restrict_local(self, item_id, project=None):
        with self.transaction():
            item = self._get(item_id, project)
            for key in (str(item.id), *self._descendants(item.id)):
                row = self._db.execute('SELECT data FROM items WHERE id=?', (key,)).fetchone()
                if row:
                    value = MemoryItem.model_validate_json(row[0])
                    self._save(value.model_copy(update={'candidate': value.candidate.model_copy(update={'sensitivity': Sensitivity.LOCAL_ONLY}),
                                                       'revision': value.revision + 1, 'updated_at': now()}))
            self._event('restrict_local', item)

    def allow_external(self, item_id, project=None):
        with self.transaction():
            item = self._get(item_id, project)
            if any(self._get(parent, project).candidate.sensitivity is Sensitivity.LOCAL_ONLY for parent in item.candidate.parents):
                raise MistError(ErrorCode.MEMORY_INVALID)
            changed = item.model_copy(update={'candidate': item.candidate.model_copy(update={'sensitivity': Sensitivity.EXTERNAL_ALLOWED}),
                                            'revision': item.revision + 1, 'updated_at': now()})
            self._save(changed)
            self._event('allow_external', changed)

    def delete(self, item_id, project=None):
        with self.transaction():
            item = self._get(item_id, project)
            ids = {str(item.id), *self._descendants(item.id)}
            for key in ids:
                self._db.execute('INSERT OR IGNORE INTO registry.deleted VALUES(?,?)', (key, now()))
                self._db.execute('DELETE FROM search WHERE id=?', (key,))
                self._db.execute('DELETE FROM versions WHERE id=?', (key,))
                self._db.execute('DELETE FROM items WHERE id=?', (key,))
                self._db.execute('DELETE FROM relations WHERE parent=? OR child=?', (key, key))
                self._db.execute('DELETE FROM registry.heads WHERE id=?', (key,))
            self._event('delete', item)
            return len(ids)

    def list_items(self, project=None, *, limit=100):
        if type(limit) is not int or not 1 <= limit <= 1000:
            raise MistError(ErrorCode.MEMORY_INVALID)
        with self.transaction():
            rows = self._db.execute('SELECT data FROM items WHERE project IS NULL OR project=? ORDER BY id LIMIT ?', (project, limit))
            items = tuple(MemoryItem.model_validate_json(row[0]) for row in rows)
            self._event('list')
            return items

    def retrieve(self, query, project=None, *, external=False, settings=None):
        settings = settings or MemorySettings()
        try:
            settings = MemorySettings.model_validate_json(settings.model_dump_json())
            if not isinstance(query, str) or len(query) > 16000 or type(external) is not bool:
                raise ValueError('Invalid retrieval')
        except (ValueError, AttributeError):
            raise MistError(ErrorCode.MEMORY_INVALID) from None
        stopwords = {'a', 'o', 'as', 'os', 'e', 'é', 'de', 'do', 'da', 'dos', 'das', 'em', 'no', 'na',
                     'um', 'uma', 'eu', 'meu', 'minha', 'qual', 'quais', 'que', 'como', 'para', 'por', 'foi'}
        tokens = list(dict.fromkeys(token.casefold() for token in re.findall(r'[^\W_]+', query, re.UNICODE)
                                   if token.casefold() not in stopwords))[:16]
        expression = ' OR '.join('"' + token[:48] + '"' for token in tokens)
        with self.transaction():
            filters = "i.status='active' AND (i.project IS NULL OR i.project=?) AND (i.expires IS NULL OR i.expires>?) AND (?=0 OR i.sensitivity='external_allowed')"
            args = (project, datetime.fromisoformat(now()).timestamp(), int(external))
            preferences = list(self._db.execute('SELECT i.data FROM items i WHERE ' + filters + " AND i.slot='communication.style' ORDER BY (i.project IS NULL),i.id", args))
            rows = list(self._db.execute('SELECT i.data FROM search JOIN items i ON i.id=search.id WHERE search MATCH ? AND ' + filters + ' ORDER BY bm25(search),i.id LIMIT 200', (expression, *args))) if expression else []
            selected, seen = [], set()
            for row in (*preferences, *rows):
                item = MemoryItem.model_validate_json(row[0])
                if any(self._get(parent, project).status is not MemoryStatus.ACTIVE for parent in item.candidate.parents):
                    continue
                if item.id in seen:
                    continue
                seen.add(item.id)
                candidate = (*selected, item)
                if len(render_items(candidate)) <= settings.max_chars:
                    selected.append(item)
                if len(selected) >= settings.max_items:
                    break
            self._event('retrieve')
            return tuple(selected)

    def snapshot(self, path):
        path = Path(path)
        with self.transaction():
            items = tuple(MemoryItem.model_validate_json(row[0]) for row in self._db.execute('SELECT data FROM items ORDER BY id'))
            versions = tuple(MemoryItem.model_validate_json(row[0]) for row in self._db.execute('SELECT data FROM versions ORDER BY id,revision'))
            snapshot = MemorySnapshot(schema_version=1, namespace=UUID(self.namespace), items=items, versions=versions)
            payload = (snapshot.model_dump_json(indent=2) + '\n').encode('utf-8')
            if len(payload) > 20_000_000:
                raise MistError(ErrorCode.MEMORY_INVALID)
            try:
                fd = private_file(path, new=True)
                with os.fdopen(fd, 'wb') as stream:
                    stream.write(payload)
                    stream.flush()
                    os.fsync(stream.fileno())
            except OSError:
                raise MistError(ErrorCode.MEMORY_UNAVAILABLE) from None
            self._event('snapshot')

    def restore(self, path):
        # JSON is validated data; never execute schemas or SQL from a backup file.
        try:
            path = Path(path)
            if path.is_symlink() or path.stat().st_size > 20_000_000:
                raise ValueError('Unsafe snapshot')
            snapshot = MemorySnapshot.model_validate_json(path.read_bytes())
            if str(snapshot.namespace) != self.namespace or len({item.id for item in snapshot.items}) != len(snapshot.items):
                raise ValueError('Wrong namespace or duplicate items')
            for item in (*snapshot.items, *snapshot.versions):
                self._candidate(item.candidate)
        except (OSError, ValueError, MistError):
            raise MistError(ErrorCode.MEMORY_INVALID) from None
        with self.transaction():
            deleted = {row[0] for row in self._db.execute('SELECT id FROM registry.deleted')}
            heads = {row[0]: (row[1], row[2]) for row in self._db.execute('SELECT id,revision,status FROM registry.heads')}
            eligible = {str(item.id): item for item in snapshot.items if str(item.id) not in deleted
                        and item.revision >= heads.get(str(item.id), (0, 'active'))[0]}
            changed = True
            while changed:
                changed = False
                for key, item in tuple(eligible.items()):
                    if any(str(parent) not in eligible and self._db.execute('SELECT 1 FROM items WHERE id=?', (str(parent),)).fetchone() is None for parent in item.candidate.parents):
                        del eligible[key]
                        changed = True
            restored = set()
            for key, item in eligible.items():
                current = self._db.execute('SELECT revision FROM items WHERE id=?', (key,)).fetchone()
                if current and current[0] >= item.revision:
                    continue
                if key in heads and item.revision == heads[key][0]:
                    item = item.model_copy(update={'status': MemoryStatus(heads[key][1])})
                # Restoring data never grants fresh permission to send it externally.
                item = item.model_copy(update={'candidate': item.candidate.model_copy(update={'sensitivity': Sensitivity.LOCAL_ONLY})})
                parent_items = [eligible.get(str(parent)) or self._get(parent, item.candidate.project) for parent in item.candidate.parents]
                if any(parent.candidate.sensitivity is Sensitivity.LOCAL_ONLY for parent in parent_items):
                    item = item.model_copy(update={'candidate': item.candidate.model_copy(update={'sensitivity': Sensitivity.LOCAL_ONLY})})
                self._save(item)
                restored.add(key)
            for item in snapshot.versions:
                if str(item.id) in restored and item.revision <= eligible[str(item.id)].revision:
                    self._db.execute('INSERT OR IGNORE INTO versions VALUES(?,?,?)', (str(item.id), item.revision, item.model_dump_json()))
            self._event('restore')
            return len(restored)
