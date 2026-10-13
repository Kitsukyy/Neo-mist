import re
from uuid import uuid4

from mist.errors import ErrorCode, MistError
from mist.gateway import Gateway
from mist.identity import Identity
from mist.output import OutputContract
from mist.memory import MemoryStore
from mist.memory_capture import capture_declaration
from mist.memory_types import MemoryCandidate, MemorySource, now, render_items
from mist.projects import ProjectStore
from mist.router import Router
from mist.schemas import (
    ConversationMessage, Envelope, GenerationRequest, GenerationResponse,
    Role, RouterMode, Sensitivity, Settings, Style,
)


class Application:
    def __init__(self, settings: Settings, identity: Identity, gateway: Gateway,
                 memory: MemoryStore | None = None, project: str | None = None,
                 projects: ProjectStore | None = None):
        self.settings = settings
        self.identity = identity
        self.gateway = gateway
        self.router = Router(settings)
        self.mode = settings.default_mode
        self.style = Style.AUTO
        self._history: list[ConversationMessage] = []
        self.memory = memory
        self.projects = projects
        self.session_id = uuid4()
        self.project = None
        self.last_memory_changes = ()
        self.set_project(project)

    def set_project(self, project):
        if project is not None and (not isinstance(project, str) or not re.fullmatch(r'[a-zA-Z0-9._-]{1,80}', project)):
            raise MistError(ErrorCode.MEMORY_INVALID)
        self.project = project
        self._history.clear()

    def _source(self):
        return MemorySource(origin='user', session_id=self.session_id, message_id=uuid4(), timestamp=now())

    def require_memory(self):
        if self.memory is None:
            raise MistError(ErrorCode.MEMORY_UNAVAILABLE)
        return self.memory

    def require_projects(self):
        if self.projects is None:
            raise MistError(ErrorCode.PROJECT_UNAVAILABLE)
        return self.projects

    def use_project(self,key):
        item=self.require_projects().get(key,active=True)
        self.set_project(item.key)
        return item

    def remember(self, text):
        try:
            source = self._source()
            candidate = (capture_declaration(text, source, self.project) if isinstance(text, str) else None)
            candidate = candidate or MemoryCandidate(content=text, project=self.project, source=source)
        except ValueError:
            raise MistError(ErrorCode.MEMORY_INVALID) from None
        return self.require_memory().remember(candidate)

    def forget(self, item_id):
        count = self.require_memory().delete(item_id, self.project)
        # Remove replies derived from deleted memory as well as retrieved context.
        self._history.clear()
        self.last_memory_changes = ()
        return count

    def replace_memory(self, item_id, text):
        store = self.require_memory()
        item = store.get(item_id, self.project)
        candidate = item.candidate.model_copy(update={'content': text, 'source': self._source(), 'correction': True,
                                                      'sensitivity': Sensitivity.LOCAL_ONLY})
        changed = store.replace(item_id, candidate, self.project)
        self._history.clear()
        return changed

    def close(self):
        if self.memory is not None:
            self.memory.close()

    @property
    def history(self) -> tuple[ConversationMessage, ...]:
        return tuple(self._history)

    def reset(self) -> None:
        self._history.clear()
        self.mode = self.settings.default_mode
        self.style = Style.AUTO
        self.last_memory_changes = ()

    def set_mode(self, value: str) -> None:
        try:
            self.mode = RouterMode(value.upper())
        except (ValueError, AttributeError):
            raise MistError(ErrorCode.INVALID_INPUT) from None

    def set_style(self, value: str) -> None:
        try:
            self.style = Style(value.lower())
        except (ValueError, AttributeError):
            raise MistError(ErrorCode.INVALID_INPUT) from None

    def handle(self, text: str, sensitivity: Sensitivity = Sensitivity.EXTERNAL_ALLOWED,
               *, output_contract: OutputContract | None = None) -> GenerationResponse:
        if not isinstance(text, str) or not text.strip() or len(text) > self.settings.max_input_chars:
            raise MistError(ErrorCode.INVALID_INPUT)
        if not isinstance(sensitivity, Sensitivity):
            raise MistError(ErrorCode.INVALID_INPUT)
        if output_contract is not None and not isinstance(output_contract, OutputContract):
            raise MistError(ErrorCode.INVALID_INPUT)
        self.last_memory_changes = ()
        if self.memory is not None and self.settings.memory.automatic:
            candidate = capture_declaration(text, self._source(), self.project)
            if candidate is not None:
                saved = self.memory.remember(candidate, automatic=True)
                self.last_memory_changes = (saved,)
                if candidate.correction:
                    self._history.clear()
        model = self.router.select(text, self.mode)
        user = ConversationMessage(role=Role.USER, content=text, sensitivity=sensitivity)
        items = ()
        effective_style = self.style
        local_style = False
        if self.memory is not None:
            items = self.memory.retrieve(text, self.project, external=model.external, settings=self.settings.memory)
            explicit_detail = any(term in text.casefold() for term in ('explique', 'passo a passo', 'detalhe'))
            if self.style is Style.AUTO and not explicit_detail:
                for item in items:
                    if item.candidate.style is not None:
                        effective_style = item.candidate.style
                        local_style = item.candidate.sensitivity is Sensitivity.LOCAL_ONLY
                        break
        instructions = self.identity.instructions(text, effective_style, memory_enabled=self.memory is not None)
        instructions += f" Modelo configurado para esta geração: {model.model_id}; provedor: {model.provider}."
        if output_contract is not None:
            instructions += output_contract.instructions()
        system = ConversationMessage(role=Role.SYSTEM, content=instructions,
                                     sensitivity=Sensitivity.LOCAL_ONLY if local_style else Sensitivity.EXTERNAL_ALLOWED)
        recovered = ()
        while items and len(render_items(items)) + len(instructions) + len(text) > self.settings.max_context_chars:
            items = items[:-1]
        if items:
            recovered = (ConversationMessage(role=Role.USER, content=render_items(items), sensitivity=(
                Sensitivity.LOCAL_ONLY if any(item.candidate.sensitivity is Sensitivity.LOCAL_ONLY for item in items)
                else Sensitivity.EXTERNAL_ALLOWED)),)
        history = list(self._history)
        while history and sum(len(m.content) for m in (system, *recovered, *history, user)) > self.settings.max_context_chars:
            # Keep only complete successful turns; do not orphan assistant messages.
            history = history[2:]
        if sum(len(m.content) for m in (system, *recovered, *history, user)) > self.settings.max_context_chars:
            raise MistError(ErrorCode.INVALID_INPUT)
        envelope = Envelope(
            request=GenerationRequest(messages=(system, *recovered, *history, user), mode=self.mode,
                                      output_contract=output_contract),
            model=model,
        )
        response = self.gateway.generate(envelope)
        # A reply derived from local-only context remains local-only.
        reply_sensitivity = (
            Sensitivity.LOCAL_ONLY if any(m.sensitivity is Sensitivity.LOCAL_ONLY
                                         for m in envelope.request.messages)
            else Sensitivity.EXTERNAL_ALLOWED
        )
        assistant = ConversationMessage(role=Role.ASSISTANT, content=response.text, sensitivity=reply_sensitivity)
        history.extend((user, assistant))
        while history and sum(len(m.content) for m in (system, *history)) > self.settings.max_context_chars:
            history = history[2:]
        # Failed requests never update successful conversation state.
        self._history = history
        return response
