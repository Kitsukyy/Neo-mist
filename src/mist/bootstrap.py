import os
from pathlib import Path

from mist.audit import JsonAudit
from mist.config import load_config
from mist.core import Application
from mist.errors import ErrorCode, MistError
from mist.gateway import Gateway
from mist.identity import Identity
from mist.nvidia import NvidiaProvider
from mist.providers import FakeModel
from mist.safety import OutputGuard


def default_audit_path() -> Path:
    state_home = os.environ.get("XDG_STATE_HOME")
    root = Path(state_home) if state_home else Path.home() / ".local" / "state"
    return root / "neo-mist" / "audit.jsonl"


def create_application(config_dir: Path | None = None, audit_path: Path | None = None,
                       *, allow_external: bool = False, api_key: str | None = None) -> Application:
    settings, constitution, personality = load_config(config_dir)
    providers = {"fake": FakeModel()}
    if any(model.external for model in settings.models):
        if not allow_external:
            raise MistError(ErrorCode.EXTERNAL_DISABLED)
        providers["nvidia"] = NvidiaProvider(
            api_key if api_key is not None else os.environ.get("NVIDIA_API_KEY", ""),
            timeout=settings.provider_timeout_seconds, max_tokens=settings.max_output_tokens,
        )
    gateway = Gateway(
        providers, OutputGuard(settings.allowed_external_destinations),
        JsonAudit(audit_path if audit_path is not None else default_audit_path()),
    )
    return Application(settings, Identity(constitution, personality), gateway)
