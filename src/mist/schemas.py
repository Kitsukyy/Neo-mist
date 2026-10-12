from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field
from mist.output import OutputContract

Identifier = Annotated[str, Field(min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9._-]+$")]
ModelName = Annotated[str, Field(min_length=1, max_length=200, pattern=r"^[a-zA-Z0-9._/-]+$")]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class Role(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class Sensitivity(StrEnum):
    EXTERNAL_ALLOWED = "external_allowed"
    LOCAL_ONLY = "local_only"


class RouterMode(StrEnum):
    AUTO = "AUTO"
    FAST = "FAST"
    PRIMARY = "PRIMARY"


class Style(StrEnum):
    AUTO = "auto"
    CONCISE = "concise"
    DETAILED = "detailed"


class ConversationMessage(StrictModel):
    role: Role
    content: str = Field(min_length=1, max_length=32000)
    sensitivity: Sensitivity = Sensitivity.EXTERNAL_ALLOWED


class ModelConfig(StrictModel):
    id: Identifier
    provider: Identifier
    model_id: ModelName
    external: bool = False
    destination: Identifier
    enable_thinking: bool | None = None


class Settings(StrictModel):
    version: Literal[1] = 1
    autonomy_level: Literal[0] = 0
    tools_enabled: Literal[False] = False
    default_mode: RouterMode = RouterMode.AUTO
    fast_model: Identifier
    primary_model: Identifier
    max_input_chars: int = Field(default=8000, ge=1, le=16000)
    max_context_chars: int = Field(default=16000, ge=2000, le=32000)
    models: tuple[ModelConfig, ...] = Field(min_length=1, max_length=10)
    allowed_external_destinations: tuple[Identifier, ...] = ()
    provider_timeout_seconds: float = Field(default=45.0, ge=1, le=120, allow_inf_nan=False)
    max_output_tokens: int = Field(default=512, ge=1, le=4096)


class Constitution(StrictModel):
    version: Literal[1] = 1
    preserve_rules: Literal[True] = True
    enforce_privacy: Literal[True] = True
    tools_disabled: Literal[True] = True
    honest_operations: Literal[True] = True
    separate_data_and_instructions: Literal[True] = True
    preserve_memory_provenance: Literal[True] = True
    require_audit: Literal[True] = True


class Personality(StrictModel):
    version: Literal[1] = 1
    name: Literal["Mist"] = "Mist"
    temperament: Literal["contextual"] = "contextual"
    communication: Literal["contextual"] = "contextual"
    relationship: Literal["collaborative"] = "collaborative"
    initiative: Literal["conversational"] = "conversational"


class GenerationRequest(StrictModel):
    request_id: UUID = Field(default_factory=uuid4)
    messages: tuple[ConversationMessage, ...] = Field(min_length=2)
    mode: RouterMode = RouterMode.AUTO
    output_contract: OutputContract | None = None


class Envelope(StrictModel):
    request: GenerationRequest
    model: ModelConfig


class GenerationResponse(StrictModel):
    request_id: UUID
    text: str = Field(min_length=1, max_length=32000)
    provider: Identifier
    model: ModelName
    duration_ms: float = Field(ge=0, allow_inf_nan=False)
    simulated: bool


class AuditPhase(StrEnum):
    APPROVED = "approved"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"


class AuditReason(StrEnum):
    ALLOWED = "allowed"
    GUARD_BLOCKED = "guard_blocked"
    INVALID_RESPONSE = "invalid_response"
    PROVIDER_FAILURE = "provider_failure"
    PROVIDER_AUTH = "provider_auth"
    PROVIDER_TIMEOUT = "provider_timeout"
    RATE_LIMIT = "rate_limit"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    CANCELLED = "cancelled"


class AuditEvent(StrictModel):
    request_id: UUID
    provider: Identifier
    model: ModelName
    phase: AuditPhase
    reason: AuditReason
    duration_ms: float | None = Field(default=None, ge=0, allow_inf_nan=False)
