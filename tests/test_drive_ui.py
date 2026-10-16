from __future__ import annotations

import tempfile
import json
import copy
import time
import unittest
from pathlib import Path
from threading import Event
from unittest.mock import Mock, patch

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk

from pinleaf.services.backup_service import BackupService
from pinleaf.services.drive_auth import DriveConnection
from pinleaf.services.drive_backup import DriveDestination, DriveError
from pinleaf.backup_format import decode
from pinleaf.storage.atomic_files import check_cancel
from pinleaf.ui.backup_window import BackupWindow
from test_drive_backup import FakeDrive


class DriveUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not Gtk.init_check() or Gdk.Display.get_default() is None:
            raise unittest.SkipTest("GTK display required for Drive UI tests")
        Adw.init()
        cls.app = Adw.Application(application_id="dev.pinleaf.DriveTests", flags=Gio.ApplicationFlags.NON_UNIQUE)
        cls.app.register(None)

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.service = BackupService(Path(self.directory.name) / "notes.sqlite3", GLib.idle_add)
        self.parent = Adw.ApplicationWindow(application=self.app)
        self.window = BackupWindow(parent=self.parent, service=self.service,
                                   capture=Mock(), gate=Mock(), apply=Mock())

    def tearDown(self):
        self.service.close()
        if self.service.thread:
            self.service.thread.join(3)
        self.window.destroy()
        self.parent.destroy()
        self.directory.cleanup()

    def wait_idle(self):
        deadline = time.monotonic() + 3
        while self.service.busy and time.monotonic() < deadline:
            GLib.MainContext.default().iteration(False)
            time.sleep(0.005)
        self.assertFalse(self.service.busy)

    def test_connect_disconnect_updates_account_and_keeps_local_controls(self):
        connection = DriveConnection("test@example.org", True)
        def connect(_cancel, *, session_only):
            self.assertTrue(session_only)
            self.service.drive_auth.connection = connection
            return connection
        self.window.session_only.set_active(True)
        with patch.object(self.service.drive_auth, "connect", side_effect=connect):
            self.window.connect_drive.emit("clicked")
            self.wait_idle()
        self.assertIn("test@example.org", self.window.drive_status.get_text())
        self.assertTrue(self.window.create_button.get_sensitive())
        self.assertTrue(self.window.restore_button.get_sensitive())
        def disconnect(_cancel):
            self.service.drive_auth.connection = None
        with patch.object(self.service.drive_auth, "disconnect", side_effect=disconnect):
            self.window.disconnect_drive.emit("clicked")
            self.wait_idle()
        self.assertIn("Not connected", self.window.drive_status.get_text())

    def test_cancel_browser_wait_preserves_library_and_returns_controls(self):
        started = Event()
        def connect(cancel, **_kwargs):
            started.set()
            cancel.wait(2)
            check_cancel(cancel)
        with patch.object(self.service.drive_auth, "connect", side_effect=connect):
            self.window.connect_drive.emit("clicked")
            self.assertTrue(started.wait(1))
            self.window.cancel_button.emit("clicked")
            self.wait_idle()
        self.assertIsNone(self.service.drive_auth.connection)
        self.assertTrue(self.window.create_button.get_sensitive())
        self.assertFalse((Path(self.directory.name) / "notes.sqlite3").exists())

    def drive_fixture(self):
        self.service.drive_auth.connection = DriveConnection("test@example.org", True)
        self.service.drive_auth.client_id = "client"
        provider = FakeDrive()
        self.service.drive = DriveDestination(provider)
        root = Path(__file__).resolve().parents[1]
        payload = json.loads((root / "specs/015-local-backup-and-google-drive/contracts/examples/valid-unprotected.pinleaf-backup").read_bytes())["payload"]
        self.window.capture = Mock(return_value=payload)
        self.window._drive_status()
        return provider, payload

    def test_drive_save_default_off_then_list_without_downloading(self):
        provider, payload = self.drive_fixture()
        before_local_status = self.window.status.get_text()
        self.window.save_drive.emit("clicked")
        password = self.window.password_window
        self.assertFalse(password.protection.get_active())
        self.assertEqual(password.confirm.get_label(), "Save to Drive")
        password.confirm.emit("clicked")
        self.wait_idle()
        file_id = next(iter(provider.raw))
        self.assertEqual(decode(provider.raw[file_id]).payload, payload)
        self.assertIn("Drive backup saved", self.window.drive_transfer_status.get_text())
        self.assertEqual(self.window.status.get_text(), before_local_status)
        self.window.refresh_drive.emit("clicked")
        self.wait_idle()
        self.assertIn("Found 1 completed copies", self.window.drive_transfer_status.get_text())
        self.assertIn("Unprotected", self.window.drive_copies.get_first_child().get_text())
        self.assertFalse(self.window.retry_drive.get_visible())

    def test_failed_drive_save_retries_original_capture_despite_later_edits(self):
        provider, payload = self.drive_fixture()
        original = copy.deepcopy(payload)
        def lost(stage, _item):
            if stage == "uploaded":
                raise DriveError("Synthetic interruption. Retry.")
        provider.after = lost
        with patch("pinleaf.ui.backup_window.show_error") as error:
            self.window._save_drive("synthetic-password")
            self.wait_idle()
        error.assert_called_once()
        self.assertTrue(self.window.retry_drive.get_visible())
        file_id = self.service.drive_attempt.file_id
        payload["library"]["notes"][0]["content"] = "Later local edit"
        provider.after = lambda *_: None
        self.window.retry_drive.emit("clicked")
        self.wait_idle()
        self.assertEqual(decode(provider.raw[file_id], "synthetic-password").payload, original)
        self.window.capture.assert_called_once()
        self.assertFalse(self.window.retry_drive.get_visible())
        self.assertTrue(self.window.create_button.get_sensitive())
        self.assertTrue(self.window.restore_button.get_sensitive())

    def test_failed_refresh_removes_stale_results(self):
        provider, _ = self.drive_fixture()
        self.window._save_drive(None)
        self.wait_idle()
        self.window.refresh_drive.emit("clicked")
        self.wait_idle()
        self.assertIsNotNone(self.window.drive_copies.get_first_child())
        provider.before = Mock(side_effect=DriveError("Synthetic offline"))
        with patch("pinleaf.ui.backup_window.show_error"):
            self.window.refresh_drive.emit("clicked")
            self.wait_idle()
        self.assertIsNone(self.window.drive_copies.get_first_child())
        self.assertIn("Synthetic offline", self.window.drive_transfer_status.get_text())

    def test_disconnect_cancels_active_transfer_then_forgets_session(self):
        provider, _ = self.drive_fixture()
        started = Event()
        original = self.service.drive.upload
        def slow(attempt, cancel):
            started.set()
            cancel.wait(2)
            check_cancel(cancel)
            return original(attempt, cancel)
        with patch.object(self.service.drive, "upload", side_effect=slow):
            self.window._save_drive(None)
            self.assertTrue(started.wait(1))
            self.assertTrue(self.window.disconnect_drive.get_sensitive())
            self.window.disconnect_drive.emit("clicked")
            self.wait_idle()
        self.assertIsNone(self.service.drive_auth.connection)
        self.assertIsNone(self.service.drive_attempt)
        self.assertEqual(provider.raw, {})
        self.assertTrue(self.window.create_button.get_sensitive())
