"""Local catalog attached to the locked memory session; no model/executor access."""
from collections import Counter
from contextlib import contextmanager
from datetime import datetime
import json
import os
from pathlib import Path
import re
import sqlite3
from uuid import UUID, uuid4

from mist.errors import ErrorCode, MistError
from mist.memory import MemoryStore, private_file
from mist.memory_types import MemorySource, normalized, now
from mist.project_types import Priority, ProjectRecord, ProjectState, TaskRecord, TaskState
from mist.safety import OutputGuard

SCHEMA = (
    'CREATE TABLE projects.meta(namespace TEXT NOT NULL)',
    'CREATE TABLE projects.catalog(key TEXT PRIMARY KEY, data TEXT NOT NULL)',
    '''CREATE TABLE projects.tasks(id TEXT PRIMARY KEY, project TEXT NOT NULL,
       position INTEGER NOT NULL, data TEXT NOT NULL, UNIQUE(project,position),
       FOREIGN KEY(project) REFERENCES catalog(key))''',
    '''CREATE TABLE projects.events(id TEXT PRIMARY KEY,time TEXT NOT NULL,
       operation TEXT NOT NULL,project TEXT,task TEXT,revision INTEGER)''',
)
MAX_PROJECTS = 1000
MAX_TASKS_PER_PROJECT = 1000
MAX_TOTAL_TASKS = 10000


class ProjectStore:
    def __init__(self, memory: MemoryStore):
        self.memory = memory
        try:
            with memory._lock:
                if memory._db is None:
                    raise OSError('Memory session closed')
                if any(row[1] == 'projects' for row in memory._db.execute('PRAGMA database_list')):
                    raise OSError('Catalog already attached')
                path = memory.directory/'projects.sqlite3'
                os.close(private_file(path))
                memory._db.execute('ATTACH DATABASE ? AS projects', (str(path),))
                memory._db.execute('PRAGMA projects.journal_mode=DELETE')
                memory._db.execute('PRAGMA projects.synchronous=FULL')
                memory._db.execute('PRAGMA projects.secure_delete=ON')
                memory._db.execute('PRAGMA foreign_keys=ON')
            with self.transaction():
                version = self.db.execute('PRAGMA projects.user_version').fetchone()[0]
                if version not in (0,1):
                    raise OSError('Unknown catalog schema')
                if version == 0:
                    for statement in SCHEMA:
                        self.db.execute(statement)
                    self.db.execute('INSERT INTO projects.meta VALUES(?)', (memory.namespace,))
                    self.db.execute('PRAGMA projects.user_version=1')
                if self.db.execute('SELECT namespace FROM projects.meta').fetchone()[0] != memory.namespace:
                    raise OSError('Namespace mismatch')
                if self.db.execute('PRAGMA projects.quick_check').fetchone()[0] != 'ok':
                    raise OSError('Catalog integrity failure')
                if self.db.execute('PRAGMA projects.foreign_key_check').fetchone() is not None:
                    raise OSError('Catalog relation failure')
        except (OSError, sqlite3.Error, ValueError, MistError):
            # Bootstrap closes the owning memory session on initialization failure.
            raise MistError(ErrorCode.PROJECT_UNAVAILABLE) from None

    @property
    def db(self):
        if self.memory._db is None:
            raise MistError(ErrorCode.PROJECT_UNAVAILABLE)
        return self.memory._db

    @contextmanager
    def transaction(self):
        try:
            with self.memory.transaction():
                yield
        except MistError as exc:
            if exc.code is ErrorCode.MEMORY_UNAVAILABLE:
                raise MistError(ErrorCode.PROJECT_UNAVAILABLE) from None
            raise

    @staticmethod
    def key(value):
        if not isinstance(value,str) or not re.fullmatch(r'[a-zA-Z0-9._-]{1,80}',value) or value in ('global','.','..'):
            raise MistError(ErrorCode.PROJECT_INVALID)
        if any(pattern.search(value) for pattern in OutputGuard()._secret_patterns):
            raise MistError(ErrorCode.PROJECT_INVALID)
        return value

    @staticmethod
    def text(value, maximum, *, empty=False):
        if not isinstance(value,str) or len(value)>maximum or any(ord(char)<32 or ord(char)==127 for char in value):
            raise MistError(ErrorCode.PROJECT_INVALID)
        value=normalized(value)
        if (not value and not empty) or any(pattern.search(value) for pattern in OutputGuard()._secret_patterns):
            raise MistError(ErrorCode.PROJECT_INVALID)
        return value

    @staticmethod
    def source(value):
        try:
            source=MemorySource.model_validate_json(value.model_dump_json())
            if source.origin!='user':
                raise ValueError('Not a user command')
            return source
        except (ValueError,AttributeError):
            raise MistError(ErrorCode.PROJECT_INVALID) from None

    def event(self, operation, project, task=None, revision=None):
        self.db.execute('INSERT INTO projects.events VALUES(?,?,?,?,?,?)',
                        (str(uuid4()),now(),operation,project,str(task) if task else None,revision))

    def _get(self,key,*,active=False):
        key=self.key(key)
        row=self.db.execute('SELECT data FROM projects.catalog WHERE key=?',(key,)).fetchone()
        if row is None:
            raise MistError(ErrorCode.PROJECT_NOT_FOUND)
        item=ProjectRecord.model_validate_json(row[0])
        if item.key!=key:
            raise ValueError('Inconsistent catalog')
        if active and item.state is ProjectState.ARCHIVED:
            raise MistError(ErrorCode.PROJECT_ARCHIVED)
        return item

    def create(self,key,name,objective,source):
        key,name,objective,source=self.key(key),self.text(name,200),self.text(objective,2000,empty=True),self.source(source)
        item=ProjectRecord(key=key,name=name,objective=objective,created_by=source,updated_by=source)
        with self.transaction():
            if self.db.execute('SELECT 1 FROM projects.catalog WHERE key=?',(key,)).fetchone() is not None:
                raise MistError(ErrorCode.PROJECT_INVALID)
            if self.db.execute('SELECT count(*) FROM projects.catalog').fetchone()[0]>=MAX_PROJECTS:
                raise MistError(ErrorCode.PROJECT_INVALID)
            self.db.execute('INSERT INTO projects.catalog VALUES(?,?)',(key,item.model_dump_json()))
            self.event('create_project',key,revision=item.revision)
        return item

    def get(self,key,*,active=False):
        with self.transaction():
            item=self._get(key,active=active)
            self.event('read_project',key)
            return item

    def list(self):
        with self.transaction():
            items=tuple(ProjectRecord.model_validate_json(row[0]) for row in self.db.execute('SELECT data FROM projects.catalog ORDER BY key'))
            self.event('list_projects',None)
            return items

    def update(self,key,source,*,name=None,objective=None,state=None):
        source=self.source(source)
        changes={}
        if name is not None:changes['name']=self.text(name,200)
        if objective is not None:changes['objective']=self.text(objective,2000,empty=True)
        if state is not None:
            try:changes['state']=ProjectState(state)
            except (ValueError,TypeError):raise MistError(ErrorCode.PROJECT_INVALID) from None
        if not changes:raise MistError(ErrorCode.PROJECT_INVALID)
        with self.transaction():
            item=self._get(key,active=state is None)
            if datetime.fromisoformat(source.timestamp)<datetime.fromisoformat(item.updated_by.timestamp):
                raise MistError(ErrorCode.PROJECT_INVALID)
            updated=ProjectRecord.model_validate_json(item.model_copy(update={**changes,'updated_by':source,'revision':item.revision+1}).model_dump_json())
            self.db.execute('UPDATE projects.catalog SET data=? WHERE key=?',(updated.model_dump_json(),key))
            self.event('update_project',key,revision=updated.revision)
            return updated

    def _task(self,key,task_id):
        try:task_id=str(UUID(str(task_id)))
        except (ValueError,TypeError):raise MistError(ErrorCode.PROJECT_INVALID) from None
        row=self.db.execute('SELECT data FROM projects.tasks WHERE id=? AND project=?',(task_id,key)).fetchone()
        if row is None:raise MistError(ErrorCode.PROJECT_NOT_FOUND)
        task=TaskRecord.model_validate_json(row[0])
        if str(task.id)!=task_id or task.project!=key:raise ValueError('Inconsistent task')
        return task

    def add_task(self,key,title,source):
        title,source=self.text(title,500),self.source(source)
        with self.transaction():
            self._get(key,active=True)
            if (self.db.execute('SELECT count(*) FROM projects.tasks WHERE project=?',(key,)).fetchone()[0]>=MAX_TASKS_PER_PROJECT
                    or self.db.execute('SELECT count(*) FROM projects.tasks').fetchone()[0]>=MAX_TOTAL_TASKS):
                raise MistError(ErrorCode.PROJECT_INVALID)
            position=self.db.execute('SELECT coalesce(max(position),0)+1 FROM projects.tasks WHERE project=?',(key,)).fetchone()[0]
            item=TaskRecord(project=key,title=title,position=position,created_by=source,updated_by=source)
            self.db.execute('INSERT INTO projects.tasks VALUES(?,?,?,?)',(str(item.id),key,position,item.model_dump_json()))
            self.event('add_task',key,item.id,item.revision)
            return item

    def tasks(self,key):
        with self.transaction():
            self._get(key)
            items=tuple(TaskRecord.model_validate_json(row[0]) for row in self.db.execute('SELECT data FROM projects.tasks WHERE project=? ORDER BY position,id',(key,)))
            if any(item.project!=key for item in items):raise ValueError('Inconsistent task scope')
            self.event('list_tasks',key)
            return items

    def update_task(self,key,task_id,source,*,title=None,state=None,priority=None,due_date=...):
        source=self.source(source)
        changes={}
        if title is not None:changes['title']=self.text(title,500)
        try:
            if state is not None:changes['state']=TaskState(state)
            if priority is not None:changes['priority']=Priority(priority)
        except (ValueError,TypeError):raise MistError(ErrorCode.PROJECT_INVALID) from None
        if due_date is not ...:changes['due_date']=due_date
        if not changes:raise MistError(ErrorCode.PROJECT_INVALID)
        with self.transaction():
            self._get(key,active=True)
            item=self._task(key,task_id)
            if datetime.fromisoformat(source.timestamp)<datetime.fromisoformat(item.updated_by.timestamp):
                raise MistError(ErrorCode.PROJECT_INVALID)
            try:
                updated=TaskRecord.model_validate_json(item.model_copy(update={**changes,'updated_by':source,'revision':item.revision+1}).model_dump_json())
            except (ValueError,TypeError):raise MistError(ErrorCode.PROJECT_INVALID) from None
            self.db.execute('UPDATE projects.tasks SET data=? WHERE id=? AND project=?',(updated.model_dump_json(),str(item.id),key))
            self.event('update_task',key,item.id,updated.revision)
            return updated

    def delete_task(self,key,task_id,source):
        source=self.source(source)
        with self.transaction():
            self._get(key,active=True)
            item=self._task(key,task_id)
            if datetime.fromisoformat(source.timestamp)<datetime.fromisoformat(item.updated_by.timestamp):
                raise MistError(ErrorCode.PROJECT_INVALID)
            self.db.execute('DELETE FROM projects.tasks WHERE id=? AND project=?',(str(item.id),key))
            self.event('delete_task',key,item.id,item.revision)

    def progress(self,key):
        tasks=self.tasks(key)
        counts=Counter(item.state.value for item in tasks)
        eligible=len(tasks)-counts['cancelled']
        return {'total':len(tasks),'eligible':eligible,'counts':dict(counts),
                'percent':round(100*counts['done']/eligible,1) if eligible else None}

    def export(self,path):
        # No restore/import route; only a fresh private JSON file.
        path=Path(path)
        created_identity=None
        try:
            with self.transaction():
                projects=[ProjectRecord.model_validate_json(row[0]).model_dump(mode='json') for row in self.db.execute('SELECT data FROM projects.catalog ORDER BY key')]
                tasks=[TaskRecord.model_validate_json(row[0]).model_dump(mode='json') for row in self.db.execute('SELECT data FROM projects.tasks ORDER BY project,position,id')]
                payload=(json.dumps({'schema_version':1,'namespace':self.memory.namespace,'projects':projects,'tasks':tasks},ensure_ascii=False,indent=2)+'\n').encode()
                if len(payload)>20_000_000:raise MistError(ErrorCode.PROJECT_INVALID)
                if any(part.is_symlink() for part in (path.parent,*path.parent.parents)):
                    raise MistError(ErrorCode.PROJECT_INVALID)
                self.event('export_projects',None)
                try:
                    fd=private_file(path,new=True)
                except OSError:raise MistError(ErrorCode.PROJECT_UNAVAILABLE) from None
                info=os.fstat(fd)
                created_identity=(info.st_dev,info.st_ino)
                with os.fdopen(fd,'wb') as stream:
                    stream.write(payload)
                    stream.flush()
                    os.fsync(stream.fileno())
        except BaseException:
            if created_identity is not None:
                try:
                    info=path.stat(follow_symlinks=False)
                    if (info.st_dev,info.st_ino)==created_identity:
                        path.unlink()
                except OSError:
                    pass  # An unrelated/replaced file must not be deleted.
            raise
