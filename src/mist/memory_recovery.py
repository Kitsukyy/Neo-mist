"""Explicit offline recovery keeps the surviving deletion/version registry."""
from contextlib import closing
import os
from pathlib import Path
import sqlite3
import tempfile

from mist.errors import ErrorCode, MistError
from mist.memory import MemoryStore, fcntl, private_file


def recover_memory(directory, snapshot):
    root = Path(directory).absolute()
    fd = None
    try:
        if fcntl is None or not root.is_dir() or root.stat().st_mode & 0o077:
            raise OSError('Private store required')
        if any(path.is_symlink() for path in (root, *root.parents)):
            raise OSError('Symlink directory')
        registry = root / 'registry.sqlite3'
        if not registry.is_file():
            raise OSError('Deletion registry must survive')
        os.close(private_file(registry))
        fd = private_file(root / 'memory.lock')
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        data = root / 'memory.sqlite3'
        if data.exists() or data.is_symlink():
            os.close(private_file(data))
        with tempfile.TemporaryDirectory(prefix='.recovery-', dir=root) as temporary:
            staging = Path(temporary)
            copied_registry = staging / 'registry.sqlite3'
            os.close(private_file(copied_registry, new=True))
            with closing(sqlite3.connect(registry.as_uri() + '?mode=ro', uri=True)) as original, \
                    closing(sqlite3.connect(copied_registry)) as copy:
                if original.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
                    raise OSError('Registry corruption')
                original.backup(copy)
            store = MemoryStore(staging)
            try:
                restored = store.restore(snapshot)
            finally:
                store.close()
            # Persist restrictive revision watermarks before swapping data. A crash
            # can omit data, but must not lower the previous exclusion/version rules.
            with closing(sqlite3.connect(registry)) as original, closing(sqlite3.connect(copied_registry)) as copy:
                original.execute('PRAGMA synchronous=FULL')
                with original:
                    for row in copy.execute('SELECT id,revision,status FROM heads'):
                        original.execute('INSERT INTO heads VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET revision=excluded.revision,status=excluded.status WHERE excluded.revision>=heads.revision', row)
            os.replace(staging / 'memory.sqlite3', data)
            directory_fd = os.open(root, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        return restored
    except (OSError, sqlite3.Error, ValueError):
        raise MistError(ErrorCode.MEMORY_UNAVAILABLE) from None
    finally:
        if fd is not None:
            os.close(fd)
