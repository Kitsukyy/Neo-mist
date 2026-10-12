from collections.abc import Mapping
from time import perf_counter

from pydantic import ValidationError

from mist.audit import Audit
from mist.errors import ErrorCode, MistError
from mist.providers import Provider
from mist.safety import Approval, OutputGuard
from mist.schemas import (
    AuditEvent, AuditPhase, AuditReason, Envelope, GenerationResponse,
)


class Gateway:
    def __init__(self, providers: Mapping[str, Provider], guard: OutputGuard, audit: Audit):
        self.providers = dict(providers)
        self.guard = guard
        self.audit = audit
        self.suspended = False

    def _record(self, envelope: Envelope, phase: AuditPhase, reason: AuditReason,
                duration_ms: float | None = None) -> None:
        try:
            self.audit.record(AuditEvent(
                request_id=envelope.request.request_id,
                provider=envelope.model.provider,
                model=envelope.model.model_id,
                phase=phase, reason=reason, duration_ms=duration_ms,
            ))
        except Exception:
            self.suspended = True
            raise MistError(ErrorCode.AUDIT_FAILURE) from None

    def generate(self, envelope: Envelope) -> GenerationResponse:
        if self.suspended:
            raise MistError(ErrorCode.AUDIT_FAILURE)
        if envelope.model.provider not in self.providers:
            raise MistError(ErrorCode.UNKNOWN_MODEL)
        try:
            approval = self.guard.evaluate(envelope)
        except MistError as exc:
            if exc.code is not ErrorCode.GUARD_BLOCKED:
                raise MistError(ErrorCode.GUARD_FAILURE) from None
            self._record(envelope, AuditPhase.BLOCKED, AuditReason.GUARD_BLOCKED)
            raise MistError(ErrorCode.GUARD_BLOCKED) from None
        except Exception:
            raise MistError(ErrorCode.GUARD_FAILURE) from None
        return self.dispatch(envelope, approval)

    def dispatch(self, envelope: Envelope, approval: Approval) -> GenerationResponse:
        """Internal send boundary. Approval cannot come from model text."""
        if self.suspended:
            self.guard.revoke(approval)
            raise MistError(ErrorCode.AUDIT_FAILURE)
        try:
            self.guard.consume(envelope, approval)
        except Exception:
            raise MistError(ErrorCode.GUARD_BLOCKED) from None
        if envelope.model.provider not in self.providers:
            raise MistError(ErrorCode.UNKNOWN_MODEL)
        self._record(envelope, AuditPhase.APPROVED, AuditReason.ALLOWED)
        start = perf_counter()
        try:
            text = self.providers[envelope.model.provider].generate(envelope)
            response = GenerationResponse(
                request_id=envelope.request.request_id, text=text,
                provider=envelope.model.provider, model=envelope.model.model_id,
                duration_ms=(perf_counter() - start) * 1000,
                simulated=envelope.model.provider == "fake",
            )
            if not response.text.strip():
                raise MistError(ErrorCode.INVALID_RESPONSE)
            if envelope.request.output_contract is not None:
                envelope.request.output_contract.validate_output(response.text)
        except MistError as exc:
            reasons = {
                ErrorCode.INVALID_RESPONSE: AuditReason.INVALID_RESPONSE,
                ErrorCode.PROVIDER_AUTH: AuditReason.PROVIDER_AUTH,
                ErrorCode.PROVIDER_TIMEOUT: AuditReason.PROVIDER_TIMEOUT,
                ErrorCode.RATE_LIMIT: AuditReason.RATE_LIMIT,
                ErrorCode.PROVIDER_UNAVAILABLE: AuditReason.PROVIDER_UNAVAILABLE,
                ErrorCode.PROVIDER_FAILURE: AuditReason.PROVIDER_FAILURE,
                ErrorCode.GUARD_BLOCKED: AuditReason.GUARD_BLOCKED,
            }
            code = exc.code if exc.code in reasons else ErrorCode.PROVIDER_FAILURE
            self._record(envelope, AuditPhase.FAILED, reasons[code])
            raise MistError(code) from None
        except ValidationError:
            self._record(envelope, AuditPhase.FAILED, AuditReason.INVALID_RESPONSE)
            raise MistError(ErrorCode.INVALID_RESPONSE) from None
        except KeyboardInterrupt:
            self._record(envelope, AuditPhase.FAILED, AuditReason.CANCELLED)
            raise
        except Exception:
            self._record(envelope, AuditPhase.FAILED, AuditReason.PROVIDER_FAILURE)
            raise MistError(ErrorCode.PROVIDER_FAILURE) from None
        self._record(envelope, AuditPhase.COMPLETED, AuditReason.ALLOWED, response.duration_ms)
        return response
