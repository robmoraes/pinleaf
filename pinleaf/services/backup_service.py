"""One cancellable worker operation; GTK/live SQLite stay with the caller."""
from __future__ import annotations

import json
import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from threading import Event, Thread

from pinleaf.backup_format import BackupError, canonical, decode, encode
from pinleaf.storage.atomic_files import OperationCancelled, check_cancel, publish, write_private
from pinleaf.storage.restore_recovery import PreparedRestore, RestorePreview, RestoreRecovery
from pinleaf.services.drive_auth import DriveAuth
from pinleaf.services.drive_backup import DriveCopy, DriveDestination, DriveError, DriveTransport, UploadAttempt


@dataclass(frozen=True)
class ExportResult:
    path: Path
    captured_at: str
    warning: str | None = None


@dataclass(frozen=True)
class DriveExportResult:
    copy: DriveCopy
    warning: str | None = None


class BackupService:
    def __init__(self, database: Path, dispatch: Callable[[Callable], object]) -> None:
        self.recovery = RestoreRecovery(database)
        self.drive_auth = DriveAuth(database.parent)
        self.drive = DriveDestination(DriveTransport(self.drive_auth))
        self.drive_attempt: UploadAttempt | None = None
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

    def _drive_owner(self) -> tuple[str, str]:
        connection = self.drive_auth.connection
        if connection is None or self.drive_auth.client_id is None:
            raise DriveError("Connect Google Drive before saving or listing backups.")
        return self.drive_auth.client_id, connection.account

    def save_drive(self, payload: dict, password: str | None, cancel: Event) -> DriveExportResult:
        owner = self._drive_owner()
        self.drive_attempt = None
        check_cancel(cancel)
        raw = encode(payload, password)
        decode(raw, password)
        check_cancel(cancel)
        self.drive_attempt = UploadAttempt(owner, payload["created_at"], password is not None, raw)
        return self.retry_drive(cancel)

    def retry_drive(self, cancel: Event) -> DriveExportResult:
        attempt = self.drive_attempt
        if attempt is None or attempt.owner != self._drive_owner():
            raise DriveError("There is no retryable save for this connected account. Start a new save.")
        copy = self.drive.upload(attempt, cancel)
        warning = None
        try:
            state = self.state()
            owner_key = hashlib.sha256(canonical(list(attempt.owner))).hexdigest()
            state["drive"] = {"owner": owner_key, "file_id": copy.file_id, "captured_at": copy.captured_at}
            write_private(self.state_path, canonical(state))
        except (OSError, BackupError):
            warning = "The Drive copy was saved, but its local status could not be recorded."
        self.drive_attempt = None
        return DriveExportResult(copy, warning)

    def list_drive(self, cancel: Event) -> list[DriveCopy]:
        self._drive_owner()
        return self.drive.list_copies(cancel)

    def last_drive_status(self) -> dict | None:
        try:
            owner_key = hashlib.sha256(canonical(list(self._drive_owner()))).hexdigest()
        except DriveError:
            return None
        value = self.state().get("drive")
        if (isinstance(value, dict) and value.get("owner") == owner_key
                and isinstance(value.get("captured_at"), str)):
            return value
        return None

    def disconnect_drive(self, cancel: Event) -> None:
        self.drive_attempt = None
        self.drive_auth.disconnect(cancel)

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
        self.drive_auth.credentials = None
        self.drive_attempt = None
