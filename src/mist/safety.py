import hashlib
import re
import secrets
from dataclasses import dataclass

from mist.errors import ErrorCode, MistError
from mist.schemas import Envelope, Sensitivity


@dataclass(frozen=True)
class Approval:
    handle: str


class OutputGuard:
    """In-process, single-use approvals bound to an immutable final envelope."""

    def __init__(self, allowed_destinations: tuple[str, ...] = ()):
        self.allowed_destinations = frozenset(allowed_destinations)
        self._issued: dict[str, str] = {}
        self._secret_patterns = (
            re.compile(r"(?i)(?:nvapi-|sb_secret_|sk-)[a-z0-9_-]{12,}"),
            re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
            re.compile(r"(?i)\b(?:api[_ -]?key|password|senha|token)\s*[:=]\s*\S{8,}"),
        )

    @staticmethod
    def binding(envelope: Envelope) -> str:
        return hashlib.sha256(envelope.model_dump_json().encode("utf-8")).hexdigest()

    def evaluate(self, envelope: Envelope) -> Approval:
        if envelope.model.external:
            if envelope.model.destination not in self.allowed_destinations:
                raise MistError(ErrorCode.GUARD_BLOCKED)
            if any(pattern.search(envelope.model.model_dump_json()) for pattern in self._secret_patterns):
                raise MistError(ErrorCode.GUARD_BLOCKED)
            for message in envelope.request.messages:
                if message.sensitivity is Sensitivity.LOCAL_ONLY:
                    raise MistError(ErrorCode.GUARD_BLOCKED)
                if any(pattern.search(message.content) for pattern in self._secret_patterns):
                    raise MistError(ErrorCode.GUARD_BLOCKED)
        handle = secrets.token_urlsafe(24)
        self._issued[handle] = self.binding(envelope)
        return Approval(handle)

    def consume(self, envelope: Envelope, approval: Approval) -> None:
        issued = self._issued.pop(approval.handle, None)
        if issued is None or not secrets.compare_digest(issued, self.binding(envelope)):
            raise MistError(ErrorCode.GUARD_BLOCKED)

    def revoke(self, approval: Approval) -> None:
        self._issued.pop(approval.handle, None)
