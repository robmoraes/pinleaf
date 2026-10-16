"""Private staging and durable publication; preserve prior files on failure."""
from __future__ import annotations

import os
import tempfile
from collections.abc import Callable
from pathlib import Path
from threading import Event
from uuid import uuid4

from pinleaf.backup_format import BackupError, read_bytes


class OperationCancelled(BackupError):
    pass


def check_cancel(cancel: Event | None) -> None:
    if cancel is not None and cancel.is_set():
        raise OperationCancelled("Operation cancelled. Your notes were kept.")


def private_directory(path: Path) -> Path:
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.is_symlink():
        raise BackupError("The backup directory must not be a symbolic link.")
    path.chmod(0o700)
    sync_directory(path)
    sync_directory(path.parent)
    return path


def sync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def sync_file(path: Path) -> None:
    with path.open("rb") as source:
        os.fsync(source.fileno())


def publish(path: Path, raw: bytes, *, verify: Callable[[bytes], object],
            overwrite: bool = False, cancel: Event | None = None) -> None:
    check_cancel(cancel)
    descriptor, name = tempfile.mkstemp(prefix=".pinleaf-backup-", dir=path.parent)
    stage = Path(name)
    previous: Path | None = None
    published = False
    retain = False
    try:
        with os.fdopen(descriptor, "wb") as target:
            target.write(raw)
            target.flush()
            os.fsync(target.fileno())
        verify(read_bytes(stage))
        check_cancel(cancel)
        if overwrite and path.exists():
            if path.is_symlink() or not path.is_file():
                raise BackupError("Choose a regular file as the backup destination.")
            previous = path.parent / f".pinleaf-previous-{uuid4()}"
            os.link(path, previous)
            sync_directory(path.parent)
        if overwrite:
            os.replace(stage, path)
        else:
            os.link(stage, path)  # Atomic no-clobber, including competing writers.
            published = True
            stage.unlink()
        published = True
        sync_directory(path.parent)
    except BaseException as exc:
        if published:
            try:
                if previous is not None:
                    os.replace(previous, path)
                    previous = None
                else:
                    path.unlink()
                sync_directory(path.parent)
            except OSError:
                retain = True
                raise BackupError(f"Could not finish or undo publication. Keep {path} and {previous or stage} for recovery.") from exc
        raise
    finally:
        if not retain:
            stage.unlink(missing_ok=True)
            if previous is not None:
                previous.unlink(missing_ok=True)


def write_private(path: Path, raw: bytes) -> None:
    def verify(data: bytes) -> None:
        if data != raw:
            raise BackupError("The recovery file could not be verified.")
    publish(path, raw, verify=verify, overwrite=True)
