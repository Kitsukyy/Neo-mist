"""Local memory contracts. Model text cannot call these operations."""
from datetime import datetime, timezone
from enum import StrEnum
import json
import unicodedata
from uuid import UUID, uuid4

from pydantic import Field, model_validator

from mist.schemas import Identifier, MemorySettings, Sensitivity, StrictModel, Style


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class MemoryKind(StrEnum):
    SEMANTIC = 'semantic'
    EPISODIC = 'episodic'
    PREFERENCE = 'preference'


class EpistemicState(StrEnum):
    DECLARED = 'declared'
    INFERRED = 'inferred'
    HYPOTHESIS = 'hypothesis'


class MemoryStatus(StrEnum):
    CANDIDATE = 'candidate'
    ACTIVE = 'active'
    ARCHIVED = 'archived'
    SUPERSEDED = 'superseded'


class MemorySource(StrictModel):
    origin: str = Field(pattern=r'^(user|application|model)$')
    session_id: UUID
    message_id: UUID
    timestamp: str = Field(max_length=40)

    @model_validator(mode='after')
    def valid_time(self):
        value = datetime.fromisoformat(self.timestamp)
        if value.tzinfo is None:
            raise ValueError('Source time must have a timezone')
        return self


class MemoryCandidate(StrictModel):
    content: str = Field(min_length=1, max_length=2000)
    kind: MemoryKind = MemoryKind.SEMANTIC
    state: EpistemicState = EpistemicState.DECLARED
    project: Identifier | None = None
    sensitivity: Sensitivity = Sensitivity.LOCAL_ONLY
    source: MemorySource
    slot: Identifier | None = None
    style: Style | None = None
    correction: bool = False
    expires_at: str | None = Field(default=None, max_length=40)
    parents: tuple[UUID, ...] = Field(default=(), max_length=16)

    @model_validator(mode='after')
    def validate_candidate(self):
        if not self.content.strip() or '\x00' in self.content:
            raise ValueError('Invalid content')
        if self.source.origin != 'user' and self.state is EpistemicState.DECLARED:
            raise ValueError('Only attributed user statements are declared')
        if self.style is not None and (self.kind is not MemoryKind.PREFERENCE or self.slot != 'communication.style'):
            raise ValueError('Style requires a preference slot')
        if self.correction and self.source.origin != 'user':
            raise ValueError('Only explicit user corrections replace declarations')
        if self.expires_at is not None and datetime.fromisoformat(self.expires_at).tzinfo is None:
            raise ValueError('Expiry time must have a timezone')
        if len(set(self.parents)) != len(self.parents):
            raise ValueError('Duplicate parents')
        return self


class MemoryItem(StrictModel):
    id: UUID = Field(default_factory=uuid4)
    revision: int = Field(default=1, ge=1)
    candidate: MemoryCandidate
    sources: tuple[MemorySource, ...] = Field(min_length=1, max_length=100)
    status: MemoryStatus
    created_at: str
    updated_at: str

    @model_validator(mode='after')
    def validate_item(self):
        for value in (self.created_at, self.updated_at):
            if datetime.fromisoformat(value).tzinfo is None:
                raise ValueError('Item timestamps need timezones')
        if self.candidate.source not in self.sources:
            raise ValueError('Current source missing')
        if self.id in self.candidate.parents:
            raise ValueError('An item cannot derive from itself')
        return self

    def context_data(self):
        return {'id': str(self.id), 'revision': self.revision, 'content': self.candidate.content,
                'kind': self.candidate.kind.value, 'state': self.candidate.state.value,
                'project': self.candidate.project, 'selection': ('persistent_style_preference' if self.candidate.style is not None else 'lexical_match'),
                'sources': [source.model_dump(mode='json') for source in self.sources]}


def normalized(text: str) -> str:
    # Preserve case and internal whitespace: this is exact, not semantic, equality.
    return unicodedata.normalize('NFC', text.replace('\r\n', '\n').replace('\r', '\n')).strip()


def render_items(items: tuple[MemoryItem, ...]) -> str:
    return json.dumps({'retrieved_local_memory': [item.context_data() for item in items]}, ensure_ascii=False)
