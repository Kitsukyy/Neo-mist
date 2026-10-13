"""User-managed projects and tasks; completion is a declaration, not execution."""
from datetime import date, datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID, uuid4

from pydantic import Field, model_validator

from mist.memory_types import MemorySource
from mist.schemas import Identifier, StrictModel


class ProjectState(StrEnum):
    ACTIVE = 'active'
    ARCHIVED = 'archived'


class TaskState(StrEnum):
    TODO = 'todo'
    DOING = 'doing'
    BLOCKED = 'blocked'
    DONE = 'done'
    CANCELLED = 'cancelled'


class Priority(StrEnum):
    LOW = 'low'
    NORMAL = 'normal'
    HIGH = 'high'


class ProjectRecord(StrictModel):
    key: Identifier
    name: str = Field(min_length=1, max_length=200)
    objective: str = Field(default='', max_length=2000)
    state: ProjectState = ProjectState.ACTIVE
    sensitivity: Literal['local_only'] = 'local_only'
    revision: int = Field(default=1, ge=1)
    created_by: MemorySource
    updated_by: MemorySource

    @model_validator(mode='after')
    def validate_source(self):
        if self.created_by.origin != 'user' or self.updated_by.origin != 'user':
            raise ValueError('Only user commands manage projects')
        if datetime.fromisoformat(self.updated_by.timestamp) < datetime.fromisoformat(self.created_by.timestamp):
            raise ValueError('Update precedes creation')
        return self


class TaskRecord(StrictModel):
    id: UUID = Field(default_factory=uuid4)
    project: Identifier
    title: str = Field(min_length=1, max_length=500)
    state: TaskState = TaskState.TODO
    priority: Priority = Priority.NORMAL
    due_date: str | None = Field(default=None, pattern=r'^\d{4}-\d{2}-\d{2}$')
    position: int = Field(ge=1)
    revision: int = Field(default=1, ge=1)
    sensitivity: Literal['local_only'] = 'local_only'
    created_by: MemorySource
    updated_by: MemorySource

    @model_validator(mode='after')
    def validate_source(self):
        if self.created_by.origin != 'user' or self.updated_by.origin != 'user':
            raise ValueError('Only user commands manage tasks')
        if datetime.fromisoformat(self.updated_by.timestamp) < datetime.fromisoformat(self.created_by.timestamp):
            raise ValueError('Update precedes creation')
        if self.due_date is not None:
            date.fromisoformat(self.due_date)
        return self
