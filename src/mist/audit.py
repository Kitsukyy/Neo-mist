import json
import os
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from mist.errors import ErrorCode, MistError
from mist.schemas import AuditEvent


class Audit(Protocol):
    def record(self, event: AuditEvent) -> None: ...


class JsonAudit:
    """Append metadata only, fsync before proceeding, owner-only regular files."""

    def __init__(self, path: Path):
        self.path = path

    def record(self, event: AuditEvent) -> None:
        fd = None
        try:
            self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            flags = (os.O_WRONLY | os.O_APPEND | os.O_CREAT
                     | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
            fd = os.open(self.path, flags, 0o600)
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077:
                raise OSError("unsafe audit file")
            payload = event.model_dump(mode="json")
            payload["timestamp"] = datetime.now(timezone.utc).isoformat()
            data = (json.dumps(payload, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
            view = memoryview(data)
            while view:
                written = os.write(fd, view)
                if written == 0:
                    raise OSError("incomplete audit write")
                view = view[written:]
            os.fsync(fd)
        except (OSError, ValueError, TypeError):
            raise MistError(ErrorCode.AUDIT_FAILURE) from None
        finally:
            if fd is not None:
                os.close(fd)
