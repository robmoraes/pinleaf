"""One cancellable worker operation; GTK/live SQLite stay with the caller."""
from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from threading import Event, Thread

from pinleaf.backup_format import BackupError, canonical, decode, encode
from pinleaf.storage.atomic_files import OperationCancelled, check_cancel, publish, write_private
from pinleaf.storage.restore_recovery import PreparedRestore, RestorePreview, RestoreRecovery


@dataclass(frozen=True)
class ExportResult:
    path: Path
    captured_at: str
    warning: str | None = None


class BackupService:
    def __init__(self, database: Path, dispatch: Callable[[Callable], object]) -> None:
        self.recovery = RestoreRecovery(database)
        self.state_path = database.parent / "backup-state.json"
        self.dispatch = dispatch
        self.busy = False
        self.cancel_event = Event()
        self.token = 0
        self.closed = False
        self.thread: Thread | None = None

    def state(self) -> dict:
        try:
            with self.state_path.open("rb") as source:
                raw = source.read(65537)
            if len(raw) > 65536:
                return {}
            state = json.loads(raw)
            return state if isinstance(state, dict) else {}
        except (OSError, ValueError):
            return {}

    def export(self, payload: dict, path: Path, password: str | None,
               overwrite: bool, cancel: Event) -> ExportResult:
        check_cancel(cancel)
        raw = encode(payload, password)
        publish(path, raw, verify=lambda data: decode(data, password), overwrite=overwrite, cancel=cancel)
        warning = None
        try:
            state = self.state()
            state["local"] = {"captured_at": payload["created_at"], "location": str(path)}
            write_private(self.state_path, canonical(state))
        except (OSError, BackupError):
            warning = "The backup was saved, but its local status could not be recorded."
        return ExportResult(path, payload["created_at"], warning)

    def start(self, job: Callable[[Event], object], done: Callable[[object], None],
              failed: Callable[[Exception], None]) -> None:
        if self.busy or self.closed:
            raise BackupError("Another backup operation is in progress.")
        self.busy = True
        self.token += 1
        token = self.token
        self.cancel_event = Event()
        cancel = self.cancel_event

        def worker() -> None:
            result, error = None, None
            try:
                result = job(cancel)
            except Exception as exc:
                error = exc

            def complete() -> bool:
                if self.closed or token != self.token:
                    if isinstance(result, RestorePreview):
                        self.recovery.discard(result)
                    return False
                self.busy = False
                if cancel.is_set() and isinstance(result, (RestorePreview, PreparedRestore)):
                    if isinstance(result, RestorePreview):
                        self.recovery.discard(result)
                    failed(OperationCancelled("Operation cancelled. Your current library was kept."))
                elif error is not None:
                    failed(error)
                else:
                    done(result)
                return False
            self.dispatch(complete)

        self.thread = Thread(target=worker, name="pinleaf-backup", daemon=True)
        self.thread.start()

    def cancel(self) -> None:
        self.cancel_event.set()

    def close(self) -> None:
        self.closed = True
        self.cancel()
        self.token += 1
