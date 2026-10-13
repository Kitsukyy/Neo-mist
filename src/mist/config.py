from importlib.resources import files
from pathlib import Path
from typing import TypeVar

from pydantic import ValidationError

from mist.errors import ErrorCode, MistError
from mist.schemas import Constitution, Personality, Settings, StrictModel

T = TypeVar("T", bound=StrictModel)


def load_document(name: str, schema: type[T], directory: Path | None) -> T:
    try:
        source = directory / name if directory is not None else files("mist").joinpath("defaults", name)
        return schema.model_validate_json(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValidationError, ValueError):
        # ValidationError text can contain the original input, including secrets.
        raise MistError(ErrorCode.CONFIGURATION) from None


def load_config(directory: Path | None = None) -> tuple[Settings, Constitution, Personality]:
    settings = load_document("settings.json", Settings, directory)
    constitution = load_document("constitution.json", Constitution, directory)
    personality = load_document("personality.json", Personality, directory)
    ids = [model.id for model in settings.models]
    if len(set(ids)) != len(ids) or settings.fast_model not in ids or settings.primary_model not in ids:
        raise MistError(ErrorCode.CONFIGURATION)
    if settings.max_input_chars >= settings.max_context_chars:
        raise MistError(ErrorCode.CONFIGURATION)
    for model in settings.models:
        if model.provider == "fake":
            if model.external or model.destination != "offline" or model.enable_thinking is not None:
                raise MistError(ErrorCode.CONFIGURATION)
        elif model.provider == "nvidia":
            if not model.external or model.destination != "nvidia-integrate":
                raise MistError(ErrorCode.CONFIGURATION)
        else:
            raise MistError(ErrorCode.CONFIGURATION)
    if len(set(settings.allowed_external_destinations)) != len(settings.allowed_external_destinations):
        raise MistError(ErrorCode.CONFIGURATION)
    if any(destination != "nvidia-integrate" for destination in settings.allowed_external_destinations):
        raise MistError(ErrorCode.CONFIGURATION)
    return settings, constitution, personality
