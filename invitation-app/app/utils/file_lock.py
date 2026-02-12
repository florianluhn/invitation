import json
import os
import sys
from pathlib import Path
from contextlib import contextmanager

# Cross-platform file locking
if sys.platform == "win32":
    import msvcrt

    def _lock_shared(f):
        msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)

    def _lock_exclusive(f):
        msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)

    def _unlock(f):
        try:
            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
        except OSError:
            pass
else:
    import fcntl

    def _lock_shared(f):
        fcntl.flock(f.fileno(), fcntl.LOCK_SH)

    def _lock_exclusive(f):
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)

    def _unlock(f):
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)


@contextmanager
def locked_json_read(filepath):
    """Read a JSON file with a shared lock."""
    filepath = Path(filepath)
    if not filepath.exists():
        yield [] if filepath.name != "config.json" else {}
        return
    with open(filepath, "r") as f:
        _lock_shared(f)
        try:
            content = f.read().strip()
            yield json.loads(content) if content else ([] if filepath.name != "config.json" else {})
        finally:
            _unlock(f)


@contextmanager
def locked_json_write(filepath):
    """Read-modify-write a JSON file with an exclusive lock.

    Usage:
        with locked_json_write('data.json') as data:
            data.append(new_item)
        # File is written on context exit
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    if not filepath.exists():
        filepath.write_text("[]")

    with open(filepath, "r+") as f:
        _lock_exclusive(f)
        try:
            content = f.read().strip()
            data = json.loads(content) if content else []
            yield data
            f.seek(0)
            f.truncate()
            json.dump(data, f, indent=2, default=str)
        finally:
            _unlock(f)


def write_json(filepath, data):
    """Write data to a JSON file with an exclusive lock."""
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w") as f:
        _lock_exclusive(f)
        try:
            json.dump(data, f, indent=2, default=str)
        finally:
            _unlock(f)


def read_json(filepath):
    """Read a JSON file with a shared lock."""
    filepath = Path(filepath)
    if not filepath.exists():
        return [] if filepath.name != "config.json" else {}
    with open(filepath, "r") as f:
        _lock_shared(f)
        try:
            content = f.read().strip()
            return json.loads(content) if content else []
        finally:
            _unlock(f)
