from __future__ import annotations

import copy
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from threading import Event
from unittest.mock import patch

from pinleaf import backup_format as fmt
from pinleaf.services.backup_service import BackupService
from pinleaf.services.note_service import NoteService
from pinleaf.services.context_controller import ContextController, TransitionError
from pinleaf.storage import atomic_files
from pinleaf.storage.library_backup import build_stage, capture, read_library
from pinleaf.storage.restore_recovery import RestoreRecovery
from pinleaf.storage.sqlite_store import NoteStore


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "specs/015-local-backup-and-google-drive/contracts"
PASSWORD = "Synthetic-example-only-789"


def fixture() -> dict:
    return json.loads((CONTRACTS / "examples/valid-unprotected.pinleaf-backup").read_bytes())["payload"]


class PortableFormatTests(unittest.TestCase):
    def test_contracts_are_bundled_verbatim(self):
        for name in ("backup-payload.schema.json", "backup-envelope.schema.json"):
            self.assertEqual((CONTRACTS / name).read_bytes(), (ROOT / "pinleaf/resources/backup" / name).read_bytes())

    def test_all_contract_fixtures(self):
        for path in (CONTRACTS / "examples").glob("*.pinleaf-backup"):
            with self.subTest(path=path.name):
                if path.name.startswith("valid-"):
                    fmt.decode(path.read_bytes(), PASSWORD)
                else:
                    with self.assertRaises(fmt.BackupError):
                        fmt.decode(path.read_bytes(), PASSWORD)

    def test_both_modes_and_fresh_randomness(self):
        payload = fixture()
        plain = fmt.encode(payload)
        first, second = fmt.encode(payload, PASSWORD), fmt.encode(payload, PASSWORD)
        self.assertNotEqual(first, second)
        self.assertEqual(fmt.decode(plain).payload, payload)
        self.assertEqual(fmt.decode(first, PASSWORD).payload, payload)
        self.assertNotIn(b"library", first)
        with self.assertRaises(fmt.PasswordRequired):
            fmt.decode(first)
        for password in ("wrong", PASSWORD + " "):
            with self.assertRaises(fmt.AuthenticationError):
                fmt.decode(first, password)
        mutated = json.loads(first)
        mutated["nonce"] = "AAAAAAAAAAAAAAAA"
        with self.assertRaises(fmt.AuthenticationError):
            fmt.decode(fmt.canonical(mutated), PASSWORD)

    def test_invalid_kdf_rejected_before_derivation(self):
        envelope = json.loads(fmt.encode(fixture(), PASSWORD))
        envelope["kdf"]["n"] = 2**40
        with patch.object(fmt, "_key") as derive:
            with self.assertRaises(fmt.BackupError):
                fmt.decode(fmt.canonical(envelope), PASSWORD)
            derive.assert_not_called()

    def test_password_bounds_and_unicode_preservation(self):
        payload = fixture()
        password = " e\u0301🔐 "
        self.assertEqual(fmt.decode(fmt.encode(payload, password), password).payload, payload)
        for password in ("", "x" * 1025, "\ud800"):
            with self.subTest(password_length=len(password)), self.assertRaises(fmt.BackupError):
                fmt.encode(payload, password)

    def test_strict_json_depth_types_and_bounds(self):
        for raw in (b'{"x":1,"x":2}', b'{"x":1.0}', b'{"x":NaN}', b'{"x":true}',
                    b'[]', b'\xef\xbb\xbf{}', b'{"x":9223372036854775808}', b'\xff',
                    b'{"x":' + b'[' * 17 + b']' * 17 + b'}'):
            with self.subTest(raw=raw[:30]), self.assertRaises(fmt.BackupError):
                fmt.parse(raw)
        self.assertEqual(fmt.parse(b'{"x":"[\\\"[["}'), {"x": '["[['})
        with self.assertRaises(fmt.BackupError):
            fmt.parse(b"{}", limit=1)
        with patch.object(fmt, "MAX_PAYLOAD_BYTES", 1), self.assertRaises(fmt.BackupError):
            fmt.validate_payload(fixture())
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "oversized.pinleaf-backup"
            with path.open("wb") as output:
                output.truncate(fmt.MAX_FILE_BYTES + 1)
            with self.assertRaises(fmt.BackupError):
                fmt.read_bytes(path)

    def test_semantic_invariants_and_unknown_fields(self):
        def duplicate_id(p): p["library"]["notes"].append(copy.deepcopy(p["library"]["notes"][0]))
        def missing_group(p): p["library"]["notes"][0]["group_id"] = "absent"
        def bad_key(p): p["library"]["profiles"][0]["name_key"] = "wrong"
        def missing_context(p): p["library"]["profile_context"].clear()
        def shared_context(p):
            group = next(row for row in p["library"]["groups"] if row["is_shared"])
            p["library"]["active_context"] = {"profile_id": group["profile_id"], "group_id": group["id"]}
        def secret(p): p["library"]["app_settings"].append({"key": "google_token", "value": "test-only"})
        for change in (duplicate_id, missing_group, bad_key, missing_context, shared_context, secret):
            payload = fixture()
            change(payload)
            with self.subTest(change=change.__name__), self.assertRaises(fmt.BackupError):
                fmt.encode(payload)

    def test_preview_is_immutable_and_raw_nulls_geometry_survive(self):
        payload = fixture()
        note = payload["library"]["notes"][0]
        note.update(font_size=None, text_color=None, font_family="Unavailable font", width=-(2**63), position_x=2**63-1)
        backup = fmt.decode(fmt.encode(payload))
        mutable = backup.payload
        mutable["library"]["notes"].clear()
        self.assertEqual(backup.payload, payload)


class LocalBackupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / "notes.sqlite3"
        self.store = NoteStore(self.path)
        self.addCleanup(lambda: self.store.close())
        self.service = NoteService(self.store)
        self.service.create_note()
        self.recovery = RestoreRecovery(self.path)

    def test_capture_all_raw_records_without_changing_values(self):
        before = read_library(self.store.connection)
        payload = capture(self.store.connection)
        self.assertEqual(payload["library"], before)
        self.assertEqual(read_library(self.store.connection), before)
        with self.store.transaction():
            self.store.connection.execute("INSERT INTO app_settings VALUES ('device-only','excluded')")
            self.store.connection.execute("UPDATE notes SET font_size=NULL,text_color=NULL")
        payload = capture(self.store.connection)
        self.assertEqual(payload["library"]["app_settings"], [])
        self.assertIsNone(payload["library"]["notes"][0]["font_size"])
        fmt.decode(fmt.encode(payload))

    def test_trusted_staging_and_full_replacement_repeated(self):
        selected = fixture()
        stage = self.root / "stage.sqlite3"
        build_stage(selected, stage)
        with sqlite3.connect(stage) as staged:
            self.assertEqual(fmt.library_digest(read_library(staged)), fmt.library_digest(selected["library"]))
            self.assertEqual(staged.execute("PRAGMA integrity_check").fetchone()[0], "ok")
        for _ in range(2):
            preview = self.recovery.stage(fmt.decode(fmt.encode(selected)))
            current = capture(self.store.connection)
            prepared = self.recovery.prepare(preview, current)
            recovery_path = self.recovery.apply(self.store, prepared)
            self.assertEqual(fmt.decode(recovery_path.read_bytes()).payload["library"], current["library"])
            self.assertEqual(fmt.library_digest(read_library(self.store.connection)), fmt.library_digest(selected["library"]))
            self.assertEqual(recovery_path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(recovery_path.parent.stat().st_mode & 0o777, 0o700)
            self.assertFalse(self.recovery.journal.exists())

    def test_stale_current_or_failed_recovery_blocks_replacement(self):
        before = capture(self.store.connection)
        preview = self.recovery.stage(fmt.decode(fmt.encode(fixture())))
        prepared = self.recovery.prepare(preview, before)
        self.service.create_note()
        with self.assertRaises(fmt.BackupError):
            self.recovery.apply(self.store, prepared)
        self.assertFalse(self.recovery.journal.exists())
        with patch("pinleaf.storage.restore_recovery.publish", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                self.recovery.prepare(preview, capture(self.store.connection))
        self.assertEqual(len(self.store.list_notes()), 2)

    def test_transaction_error_rolls_back_and_reconciles(self):
        before = capture(self.store.connection)
        def fail(point):
            if point == "rows_replaced":
                raise OSError("injected")
        recovery = RestoreRecovery(self.path, checkpoint=fail)
        prepared = recovery.prepare(recovery.stage(fmt.decode(fmt.encode(fixture()))), before)
        with self.assertRaises(OSError):
            recovery.apply(self.store, prepared)
        self.assertEqual(recovery.reconcile(), "retained")
        self.assertEqual(read_library(self.store.connection), before["library"])

    def test_cancel_and_atomic_destination_overwrite_faults(self):
        destination = self.root / "export.pinleaf-backup"
        old = fmt.encode(capture(self.store.connection))
        destination.write_bytes(old)
        raw = fmt.encode(fixture())
        with self.assertRaises(FileExistsError):
            atomic_files.publish(destination, raw, verify=fmt.decode)
        self.assertEqual(destination.read_bytes(), old)
        event = Event()
        event.set()
        with self.assertRaises(atomic_files.OperationCancelled):
            atomic_files.publish(destination, raw, verify=fmt.decode, overwrite=True, cancel=event)
        original_sync = atomic_files.sync_directory
        calls = []
        def fail_after_publication(path):
            calls.append(path)
            if len(calls) == 2:
                raise OSError("fsync failed")
            original_sync(path)
        with patch.object(atomic_files, "sync_directory", side_effect=fail_after_publication):
            with self.assertRaises(OSError):
                atomic_files.publish(destination, raw, verify=fmt.decode, overwrite=True)
        self.assertEqual(destination.read_bytes(), old)
        self.assertFalse(list(self.root.glob(".pinleaf-*")))
        atomic_files.publish(destination, raw, verify=fmt.decode, overwrite=True)
        self.assertEqual(fmt.decode(destination.read_bytes()).payload, fixture())

    def test_worker_completion_is_dispatched_and_stale_result_ignored(self):
        callbacks, results = [], []
        service = BackupService(self.path, callbacks.append)
        service.start(lambda _: "done", results.append, results.append)
        service.thread.join(timeout=3)
        self.assertTrue(service.busy)
        self.assertEqual(results, [])
        callbacks.pop()()
        self.assertEqual(results, ["done"])
        self.assertFalse(service.busy)
        service.start(lambda _: "late", results.append, results.append)
        service.thread.join(timeout=3)
        service.close()
        callbacks.pop()()
        self.assertEqual(results, ["done"])

    def test_status_damage_does_not_block_notes_or_export(self):
        service = BackupService(self.path, lambda _: None)
        service.state_path.write_bytes(b"broken")
        self.assertEqual(service.state(), {})
        payload = capture(self.store.connection)
        result = service.export(payload, self.root / "export.pinleaf-backup", None, False, Event())
        self.assertEqual(service.state()["local"]["captured_at"], result.captured_at)
        self.assertEqual(fmt.decode(result.path.read_bytes()).payload, payload)

    def test_flush_failure_preserves_unsaved_editor_and_context(self):
        from test_context_controller import FakeEditor
        from unittest.mock import Mock
        note = self.store.list_notes()[0]
        editor = FakeEditor(note, self.service)
        editor.pending, editor.fail_save = "Unsaved draft", True
        refreshed = Mock()
        controller = ContextController(self.service, {note.id: editor}, lambda _: None, on_refresh=refreshed)
        before = read_library(self.store.connection)
        with self.assertRaises(TransitionError):
            controller.capture_library()
        self.assertEqual(editor.pending, "Unsaved draft")
        self.assertEqual(read_library(self.store.connection), before)
        self.assertFalse(editor.disposed)
        editor.fail_save = False
        captured = controller.capture_library()
        self.assertEqual(captured["library"]["notes"][0]["content"], "Unsaved draft")
        self.assertFalse(controller.busy)
        self.assertEqual(refreshed.call_count, 2)

    def test_export_snapshot_excludes_later_edit_and_needs_no_network(self):
        import socket
        note = self.store.list_notes()[0]
        self.service.update_content(note.id, "Captured")
        payload = capture(self.store.connection)
        self.service.update_content(note.id, "Later edit")
        service = BackupService(self.path, lambda _: None)
        with patch.object(socket, "socket", side_effect=AssertionError("Network is forbidden")):
            result = service.export(payload, self.root / "offline.pinleaf-backup", None, False, Event())
            self.assertEqual(fmt.decode(result.path.read_bytes()).payload["library"]["notes"][0]["content"], "Captured")
        self.assertEqual(self.store.get(note.id).content, "Later edit")

    def test_preservation_failure_keeps_closed_original_files(self):
        damaged = self.root / "damaged.sqlite3"
        damaged.write_bytes(b"synthetic damage")
        wal = Path(str(damaged) + "-wal")
        wal.write_bytes(b"synthetic WAL")
        with self.assertRaises(sqlite3.DatabaseError):
            NoteStore(damaged)
        self.assertEqual(wal.read_bytes(), b"synthetic WAL")
        recovery = RestoreRecovery(damaged)
        preview = recovery.stage(fmt.decode(fmt.encode(fixture())))
        with patch("pinleaf.storage.restore_recovery.shutil.copyfileobj", side_effect=OSError("full")):
            with self.assertRaises(OSError):
                recovery.prepare(preview, None)
        self.assertEqual(damaged.read_bytes(), b"synthetic damage")
        self.assertEqual(wal.read_bytes(), b"synthetic WAL")
        self.assertFalse(recovery.journal.exists())

        prepared = recovery.prepare(preview, None)
        self.assertTrue({"", "-wal"}.issubset(prepared.originals))
        for suffix in prepared.originals:
            self.assertEqual((preview.stage.parent / "original" / ("database" + suffix)).read_bytes(),
                             Path(str(damaged) + suffix).read_bytes())

    def test_missing_stage_recovers_exact_corrupt_original_set(self):
        damaged = self.root / "damaged.sqlite3"
        damaged.write_bytes(b"synthetic damage")
        wal = Path(str(damaged) + "-wal")
        wal.write_bytes(b"synthetic WAL")
        recovery = RestoreRecovery(damaged)
        preview = recovery.stage(fmt.decode(fmt.encode(fixture())))
        prepared = recovery.prepare(preview, None)
        recovery._record(prepared)
        damaged.unlink()
        wal.unlink()
        preview.stage.unlink()
        self.assertEqual(recovery.reconcile(), "retained")
        self.assertEqual(damaged.read_bytes(), b"synthetic damage")
        self.assertEqual(wal.read_bytes(), b"synthetic WAL")
        self.assertFalse(recovery.journal.exists())

    def test_cancel_preparation_can_retry_same_preview(self):
        event = Event()
        recovery = RestoreRecovery(self.path, checkpoint=lambda point: event.set() if point == "recovery_saved" else None)
        preview = recovery.stage(fmt.decode(fmt.encode(fixture())))
        current = capture(self.store.connection)
        with self.assertRaises(atomic_files.OperationCancelled):
            recovery.prepare(preview, current, event)
        self.assertFalse(recovery.journal.exists())
        event.clear()
        recovery.checkpoint = lambda _: None
        prepared = recovery.prepare(preview, current, event)
        self.assertEqual(prepared.old_digest, fmt.library_digest(current["library"]))

    def test_publication_and_rollback_failure_retains_both_copies(self):
        destination = self.root / "export.pinleaf-backup"
        old, new = fmt.encode(capture(self.store.connection)), fmt.encode(fixture())
        destination.write_bytes(old)
        calls = []
        replace = os.replace
        def fail_rollback(source, target):
            if Path(source).name.startswith(".pinleaf-previous-"):
                raise PermissionError("rollback denied")
            replace(source, target)
        def fail_sync(path):
            calls.append(path)
            if len(calls) == 2:
                raise OSError("fsync failed")
        with patch.object(atomic_files.os, "replace", side_effect=fail_rollback), patch.object(atomic_files, "sync_directory", side_effect=fail_sync):
            with self.assertRaisesRegex(fmt.BackupError, "Keep"):
                atomic_files.publish(destination, new, verify=fmt.decode, overwrite=True)
        self.assertEqual(destination.read_bytes(), new)
        self.assertEqual(next(self.root.glob(".pinleaf-previous-*")).read_bytes(), old)

    def test_large_two_installation_roundtrip_retained_owners_and_all_fields(self):
        payload = fixture()
        library = payload["library"]
        base = copy.deepcopy(library["notes"][0])
        for index in range(1000 - len(library["notes"])):
            row = dict(base, id=f"bulk-{index:04}", content=f"Café 📝\nSynthetic note {index}",
                       is_open=int(index % 3 == 0), deleted_at=base["created_at"] if index % 7 == 0 else None,
                       font_family="Unavailable synthetic font", font_size=None, text_color=None)
            library["notes"].append(row)
        removed_at = base["created_at"]
        library["profiles"].append({"id": "deleted-profile", "name": "Archived", "name_key": "archived", "deleted_at": removed_at})
        library["groups"].append({"id": "deleted-group", "profile_id": "deleted-profile", "name": "Old", "name_key": "old", "is_shared": 0, "deleted_at": removed_at})
        library["notes"].append(dict(base, id="deleted-owner-note", group_id="deleted-group", deleted_at=removed_at))
        self.assertEqual(len(library["notes"]), 1001)
        with tempfile.TemporaryDirectory() as target_directory:
            target = NoteStore(Path(target_directory) / "independent.sqlite3")
            try:
                recovery = RestoreRecovery(target.database_path)
                for password in (None, PASSWORD):
                    raw = fmt.encode(payload, password)
                    preview = recovery.stage(fmt.decode(raw, password))
                    prepared = recovery.prepare(preview, capture(target.connection))
                    recovery.apply(target, prepared)
                    self.assertEqual(fmt.library_digest(read_library(target.connection)), fmt.library_digest(library))
            finally:
                target.close()


class RestoreProcessTests(unittest.TestCase):
    def test_interrupted_original_fallback_is_repeatable(self):
        for boundary in ("original_file_database", "original_file_-journal", "original_file_-wal", "original_file_-shm", "originals_restored"):
            with self.subTest(boundary=boundary), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "damaged.sqlite3"
                originals = {suffix: f"synthetic original {suffix}".encode() for suffix in ("", "-wal", "-shm", "-journal")}
                for suffix, raw in originals.items():
                    Path(str(path) + suffix).write_bytes(raw)
                recovery = RestoreRecovery(path)
                preview = recovery.stage(fmt.decode(fmt.encode(fixture())))
                prepared = recovery.prepare(preview, None)
                recovery._record(prepared)
                preview.stage.unlink()
                for suffix in originals:
                    Path(str(path) + suffix).unlink()
                code = """
import os,sys
from pathlib import Path
from pinleaf.storage.restore_recovery import RestoreRecovery
recovery=RestoreRecovery(Path(sys.argv[1]),checkpoint=lambda point: os._exit(75) if point==sys.argv[2] else None)
recovery.reconcile()
"""
                result = subprocess.run([sys.executable, "-c", code, str(path), boundary], timeout=10)
                self.assertEqual(result.returncode, 75)
                self.assertEqual(recovery.reconcile(), "retained")
                for suffix, raw in originals.items():
                    self.assertEqual(Path(str(path) + suffix).read_bytes(), raw)

    def test_process_death_at_every_logical_boundary(self):
        for boundary, expected in (("stage_validated", "old"), ("recovery_saved", "old"), ("journal_saved", "old"),
                                   ("rows_replaced", "old"), ("committed", "new"), ("reconciled", "new")):
            with self.subTest(boundary=boundary), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "notes.sqlite3"
                store = NoteStore(path)
                NoteService(store).create_note()
                old = fmt.library_digest(read_library(store.connection))
                store.close()
                code = """
import os, sys
from pathlib import Path
from pinleaf.backup_format import decode
from pinleaf.storage.restore_recovery import RestoreRecovery
from pinleaf.storage.library_backup import capture
from pinleaf.storage.sqlite_store import NoteStore
path, selected, boundary = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
store = NoteStore(path)
recovery = RestoreRecovery(path, checkpoint=lambda point: os._exit(73) if point == boundary else None)
preview = recovery.stage(decode(selected.read_bytes()))
prepared = recovery.prepare(preview, capture(store.connection))
recovery.apply(store, prepared)
"""
                result = subprocess.run([sys.executable, "-c", code, str(path),
                    str(CONTRACTS / "examples/valid-unprotected.pinleaf-backup"), boundary], timeout=15)
                self.assertEqual(result.returncode, 73)
                recovery = RestoreRecovery(path)
                outcome = recovery.reconcile()
                self.assertIn(outcome, (None, "restored", "retained"))
                store = NoteStore(path)
                try:
                    actual = fmt.library_digest(read_library(store.connection))
                    self.assertEqual(actual, old if expected == "old" else fmt.library_digest(fixture()["library"]))
                finally:
                    store.close()

    def test_corrupt_startup_files_preserved_and_crash_install_finishes(self):
        boundaries = ("original_preserved", "journal_saved", "removed_database", "removed_-journal", "removed_-wal", "removed_-shm", "installed")
        for boundary in boundaries:
            with self.subTest(boundary=boundary), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "notes.sqlite3"
                originals = {"": b"not a database", "-wal": b"synthetic WAL", "-shm": b"synthetic SHM", "-journal": b"synthetic journal"}
                for suffix, raw in originals.items():
                    Path(str(path) + suffix).write_bytes(raw)
                code = """
import os,sys
from pathlib import Path
from pinleaf.backup_format import decode
from pinleaf.storage.restore_recovery import RestoreRecovery
path, selected, boundary = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
recovery = RestoreRecovery(path, checkpoint=lambda point: os._exit(74) if point == boundary else None)
preview = recovery.stage(decode(selected.read_bytes()))
prepared = recovery.prepare(preview, None)
recovery.apply_unreadable(prepared)
"""
                result = subprocess.run([sys.executable, "-c", code, str(path),
                    str(CONTRACTS / "examples/valid-unprotected.pinleaf-backup"), boundary], timeout=15)
                self.assertEqual(result.returncode, 74)
                recovery = RestoreRecovery(path)
                if boundary == "original_preserved":
                    self.assertIsNone(recovery.reconcile())
                    self.assertEqual(path.read_bytes(), originals[""])
                else:
                    self.assertEqual(recovery.reconcile(), "restored")
                    store = NoteStore(path)
                    self.assertEqual(fmt.library_digest(read_library(store.connection)), fmt.library_digest(fixture()["library"]))
                    store.close()
                preserved = next((Path(directory) / "restore-staging").glob("*/original"))
                for suffix, raw in originals.items():
                    self.assertEqual((preserved / ("database" + suffix)).read_bytes(), raw)

    def test_corrupt_journal_prevents_empty_seeding(self):
        with tempfile.TemporaryDirectory() as directory:
            recovery = RestoreRecovery(Path(directory) / "absent.sqlite3")
            recovery.journal.write_bytes(b"broken")
            with self.assertRaises(fmt.BackupError):
                recovery.reconcile()
            self.assertFalse(recovery.database.exists())


if __name__ == "__main__":
    unittest.main()
