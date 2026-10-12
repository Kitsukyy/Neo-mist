from mist.errors import ErrorCode, MistError
from mist.gateway import Gateway
from mist.identity import Identity
from mist.output import OutputContract
from mist.router import Router
from mist.schemas import (
    ConversationMessage, Envelope, GenerationRequest, GenerationResponse,
    Role, RouterMode, Sensitivity, Settings, Style,
)


class Application:
    def __init__(self, settings: Settings, identity: Identity, gateway: Gateway):
        self.settings = settings
        self.identity = identity
        self.gateway = gateway
        self.router = Router(settings)
        self.mode = settings.default_mode
        self.style = Style.AUTO
        self._history: list[ConversationMessage] = []

    @property
    def history(self) -> tuple[ConversationMessage, ...]:
        return tuple(self._history)

    def reset(self) -> None:
        self._history.clear()
        self.mode = self.settings.default_mode
        self.style = Style.AUTO

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
        model = self.router.select(text, self.mode)
        user = ConversationMessage(role=Role.USER, content=text, sensitivity=sensitivity)
        instructions = self.identity.instructions(text, self.style)
        instructions += f" Modelo configurado para esta geração: {model.model_id}; provedor: {model.provider}."
        if output_contract is not None:
            instructions += output_contract.instructions()
        system = ConversationMessage(role=Role.SYSTEM, content=instructions)
        history = list(self._history)
        while history and sum(len(m.content) for m in (system, *history, user)) > self.settings.max_context_chars:
            # Keep only complete successful turns; do not orphan assistant messages.
            history = history[2:]
        if sum(len(m.content) for m in (system, *history, user)) > self.settings.max_context_chars:
            raise MistError(ErrorCode.INVALID_INPUT)
        envelope = Envelope(
            request=GenerationRequest(messages=(system, *history, user), mode=self.mode,
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
