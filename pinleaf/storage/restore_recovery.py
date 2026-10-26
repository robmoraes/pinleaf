"""Durable restore boundaries, reconciled before opening or repairing NoteStore."""
from __future__ import annotations

import hashlib
import os
import shutil
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from threading import Event
from uuid import UUID, uuid4

from pinleaf.backup_format import BackupError, ValidatedBackup, canonical, decode, encode, library_digest, parse
from pinleaf.storage.atomic_files import check_cancel, private_directory, publish, sync_directory, sync_file, write_private
from pinleaf.storage.library_backup import build_stage, read_library, replace_rows


SUFFIXES = ("", "-journal", "-wal", "-shm")


@dataclass(frozen=True)
class RestorePreview:
    backup: ValidatedBackup
    attempt: str
    stage: Path
    recovery: Path


@dataclass(frozen=True)
class PreparedRestore:
    preview: RestorePreview
    old_digest: str | None
    originals: dict | None = None


def _hash_file(path: Path) -> dict:
    digest, size = hashlib.sha256(), 0
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
    return {"sha256": digest.hexdigest(), "size": size}


class RestoreRecovery:
    def __init__(self, database: Path, *, checkpoint: Callable[[str], None] = lambda _: None) -> None:
        self.database = database
        self.root = database.parent
        self.staging = self.root / "restore-staging"
        self.backups = self.root / "backups"
        self.journal = self.root / "restore-journal.json"
        self.checkpoint = checkpoint

    def stage(self, backup: ValidatedBackup, cancel: Event | None = None) -> RestorePreview:
        check_cancel(cancel)
        attempt = str(uuid4())
        directory = private_directory(private_directory(self.staging) / attempt)
        private_directory(self.backups)
        preview = RestorePreview(backup, attempt, directory / "selected.sqlite3",
                                 self.backups / f"pinleaf-recovery-{attempt}.pinleaf-backup")
        try:
            build_stage(backup.payload, preview.stage)
            sync_file(preview.stage)
            sync_directory(directory)
            self.checkpoint("stage_validated")
            check_cancel(cancel)
            return preview
        except BaseException:
            self.discard(preview)
            raise

    def discard(self, preview: RestorePreview) -> None:
        # Retain everything referenced by a recovery-critical journal.
        if not self.journal.exists() and preview.stage.parent == self.staging / preview.attempt:
            shutil.rmtree(preview.stage.parent, ignore_errors=True)

    def prepare(self, preview: RestorePreview, current: dict | None,
                cancel: Event | None = None) -> PreparedRestore:
        if self.journal.exists():
            raise BackupError("A previous restore needs recovery before another can start.")
        check_cancel(cancel)
        if current is not None:
            raw = encode(current)
            publish(preview.recovery, raw, verify=decode, cancel=cancel, overwrite=True)
            self.checkpoint("recovery_saved")
            check_cancel(cancel)
            return PreparedRestore(preview, library_digest(current["library"]))
        originals = {}
        directory = private_directory(preview.stage.parent / "original")
        for suffix in SUFFIXES:
            source = Path(str(self.database) + suffix)
            if not source.exists():
                continue
            if source.is_symlink() or not source.is_file():
                raise BackupError("The original database files could not be safely preserved.")
            check_cancel(cancel)
            target = directory / ("database" + suffix)
            if target.is_symlink():
                raise BackupError("The original recovery destination must be a regular file.")
            with source.open("rb") as incoming, target.open("wb") as outgoing:
                target.chmod(0o600)
                shutil.copyfileobj(incoming, outgoing, length=1024 * 1024)
                outgoing.flush()
                os.fsync(outgoing.fileno())
            metadata = _hash_file(source)
            if _hash_file(target) != metadata:
                raise BackupError("The original database recovery copy could not be verified.")
            originals[suffix] = metadata
        sync_directory(directory)
        sync_directory(preview.stage.parent)
        check_cancel(cancel)
        self.checkpoint("original_preserved")
        return PreparedRestore(preview, None, originals)

    def _record(self, prepared: PreparedRestore) -> dict:
        record = {"version": 1, "kind": "logical" if prepared.old_digest is not None else "files",
                  "attempt": prepared.preview.attempt,
                  "new_digest": library_digest(prepared.preview.backup.payload["library"]),
                  "old_digest": prepared.old_digest, "originals": prepared.originals}
        write_private(self.journal, canonical(record))
        self.checkpoint("journal_saved")
        return record

    def apply(self, store, prepared: PreparedRestore, *, before_replace: Callable[[], None] = lambda: None) -> Path:
        """Main thread only; no cancellation after the durable journal boundary."""
        if prepared.old_digest != library_digest(read_library(store.connection)):
            raise BackupError("The current notes changed during preparation. Retry Restore.")
        self._record(prepared)
        before_replace()
        store.connection.execute("PRAGMA synchronous=FULL")
        with store.transaction():
            replace_rows(store.connection, prepared.preview.backup.payload["library"])
            self.checkpoint("rows_replaced")
        self.checkpoint("committed")
        outcome = self.reconcile()
        if outcome != "restored":
            raise BackupError("The restore did not commit. The current library was retained.")
        return prepared.preview.recovery

    def apply_unreadable(self, prepared: PreparedRestore) -> Path:
        originals = prepared.originals or {}
        current = {suffix: _hash_file(Path(str(self.database) + suffix)) for suffix in SUFFIXES
                   if Path(str(self.database) + suffix).exists()}
        if current != originals:
            raise BackupError("The original database changed during preservation. Retry Restore.")
        record = self._record(prepared)
        self._install_files(record)
        self.checkpoint("installed")
        if self.reconcile() != "restored":
            raise BackupError("The selected backup could not be installed. Original files were preserved.")
        return prepared.preview.stage.parent / "original"

    def _load_record(self) -> dict:
        try:
            if self.journal.is_symlink():
                raise ValueError()
            with self.journal.open("rb") as source:
                raw = source.read(8193)
            if len(raw) > 8192:
                raise ValueError()
            record = parse(raw, limit=8192)
            required = {"version", "kind", "attempt", "new_digest", "old_digest", "originals"}
            if set(record) != required or record["version"] != 1 or record["kind"] not in {"logical", "files"}:
                raise ValueError()
            if str(UUID(record["attempt"])) != record["attempt"]:
                raise ValueError()
            for value in (record["new_digest"], record["old_digest"]):
                if value is not None and (len(value) != 64 or any(c not in "0123456789abcdef" for c in value)):
                    raise ValueError()
            if record["new_digest"] is None or (record["kind"] == "logical") != (record["old_digest"] is not None):
                raise ValueError()
            if record["kind"] == "files":
                if not isinstance(record["originals"], dict) or not set(record["originals"]) <= set(SUFFIXES):
                    raise ValueError()
            return record
        except (ValueError, TypeError, KeyError, AttributeError, OSError) as exc:
            raise BackupError("The restore journal is unreadable. Keep the database and recovery artifacts; do not start an empty library.") from exc

    def _digest(self, path: Path, *, recover_transaction: bool = False) -> str | None:
        if not path.is_file():
            return None
        connection = None
        try:
            mode = "rw" if recover_transaction else "ro"
            connection = sqlite3.connect(path.resolve().as_uri() + f"?mode={mode}", uri=True)
            connection.execute("BEGIN")
            if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                return None
            return library_digest(read_library(connection))
        except (sqlite3.Error, BackupError):
            return None
        finally:
            if connection is not None:
                connection.close()

    def _install_files(self, record: dict) -> None:
        directory = self.staging / record["attempt"]
        stage = directory / "selected.sqlite3"
        if self._digest(stage) != record["new_digest"]:
            raise BackupError("The staged restore database could not be verified. Original files were retained.")
        for suffix, metadata in record["originals"].items():
            if _hash_file(directory / "original" / ("database" + suffix)) != metadata:
                raise BackupError("The preserved original database files could not be verified.")
        # Keep the verified source until journal cleanup. Every crash can repeat installation.
        installation = directory / "install.sqlite3"
        shutil.copyfile(stage, installation)
        installation.chmod(0o600)
        sync_file(installation)
        for suffix in SUFFIXES:
            Path(str(self.database) + suffix).unlink(missing_ok=True)
            self.checkpoint("removed_" + (suffix or "database"))
        sync_directory(self.root)
        os.replace(installation, self.database)
        sync_directory(self.root)

    def reconcile(self) -> str | None:
        if not self.journal.exists():
            return None
        record = self._load_record()
        actual = self._digest(self.database, recover_transaction=record["kind"] == "logical")
        if record["kind"] == "files" and actual != record["new_digest"]:
            stage = self.staging / record["attempt"] / "selected.sqlite3"
            if self._digest(stage) != record["new_digest"]:
                self._restore_originals(record)
                self.journal.unlink()
                sync_directory(self.root)
                return "retained"
            self._install_files(record)
            actual = self._digest(self.database)
        if actual == record["new_digest"]:
            outcome = "restored"
        elif record["kind"] == "logical" and actual == record["old_digest"]:
            outcome = "retained"
        else:
            raise BackupError("Interrupted restore could not be reconciled. Keep the database, restore-staging and backups folders for recovery.")
        self.checkpoint("reconciled")
        self.journal.unlink()
        sync_directory(self.root)
        # Corrupt-source originals are deliberate retained recovery artifacts.
        if record["kind"] == "logical":
            shutil.rmtree(self.staging / record["attempt"], ignore_errors=True)
        return outcome

    def _restore_originals(self, record: dict) -> None:
        directory = self.staging / record["attempt"] / "original"
        for suffix, metadata in record["originals"].items():
            if _hash_file(directory / ("database" + suffix)) != metadata:
                raise BackupError("Original recovery artifacts are incomplete. Keep all files for recovery.")
        for suffix in SUFFIXES:
            destination = Path(str(self.database) + suffix)
            if suffix in record["originals"]:
                stage = directory.parent / ("reinstall" + suffix)
                shutil.copyfile(directory / ("database" + suffix), stage)
                stage.chmod(0o600)
                sync_file(stage)
                os.replace(stage, destination)
            else:
                destination.unlink(missing_ok=True)
            self.checkpoint("original_file_" + (suffix or "database"))
        sync_directory(self.root)
        self.checkpoint("originals_restored")
