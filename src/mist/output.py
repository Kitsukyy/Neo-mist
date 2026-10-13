"""Bounded, explicit JSON contracts; no coercion, execution or retries."""
import json
import math
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from mist.errors import ErrorCode, MistError

ScalarType = Literal["string", "integer", "number", "boolean"]


class OutputField(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    name: Annotated[str, Field(min_length=1, max_length=64, pattern=r"^[A-Za-z][A-Za-z0-9_]*$")]
    type: Literal["string", "integer", "number", "boolean", "array"]
    items: ScalarType | None = None

    @model_validator(mode="after")
    def check_items(self):
        if (self.type == "array") != (self.items is not None):
            raise ValueError("Array requires an item type; scalars forbid it")
        return self


class OutputContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    fields: tuple[OutputField, ...] = Field(min_length=1, max_length=32)

    @model_validator(mode="after")
    def unique_names(self):
        if len({field.name for field in self.fields}) != len(self.fields):
            raise ValueError("Duplicate field")
        return self

    def instructions(self) -> str:
        return (
            "\nContrato desta resposta: devolva somente um objeto JSON, sem Markdown ou texto adicional. "
            "Todos os campos são obrigatórios; campos extras e null são proibidos. "
            "Use os nomes e tipos declarados, sem alterar as regras fundamentais: "
            + self.model_dump_json(exclude_none=True)
        )

    def validate_output(self, text: str) -> dict:
        try:
            if len(text) > 32000:
                raise ValueError("Too large")
            data = strict_json(text)
            if type(data) is not dict or set(data) != {field.name for field in self.fields}:
                raise ValueError("Fields differ")
            for field in self.fields:
                value = data[field.name]
                if field.type == "array":
                    if type(value) is not list or len(value) > 256:
                        raise ValueError("Invalid array")
                    if not all(matches(item, field.items) for item in value):
                        raise ValueError("Invalid item")
                elif not matches(value, field.type):
                    raise ValueError("Invalid scalar")
            return data
        except (ValueError, TypeError, RecursionError, OverflowError):
            raise MistError(ErrorCode.INVALID_RESPONSE) from None


def matches(value, kind) -> bool:
    if kind == "number":
        return type(value) in (int, float) and math.isfinite(value)
    return type(value) is {"string": str, "integer": int, "boolean": bool}.get(kind)


def strict_json(text: str):
    def pairs(items):
        result = {}
        for name, value in items:
            if name in result:
                raise ValueError("Duplicate JSON key")
            result[name] = value
        return result

    def constant(_):
        raise ValueError("Non-finite JSON number")

    return json.loads(text, object_pairs_hook=pairs, parse_constant=constant)


def load_output_contract(path: Path) -> OutputContract:
    try:
        with path.open("rb") as stream:
            raw = stream.read(8193)
        if len(raw) > 8192:
            raise ValueError("Too large")
        # Check duplicates before Pydantic's JSON parsing.
        strict_json(raw.decode("utf-8"))
        return OutputContract.model_validate_json(raw)
    except (OSError, UnicodeError, ValueError, ValidationError, RecursionError):
        raise MistError(ErrorCode.CONFIGURATION) from None
