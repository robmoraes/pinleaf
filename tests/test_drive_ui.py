from __future__ import annotations

import tempfile
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
from pinleaf.storage.atomic_files import check_cancel
from pinleaf.ui.backup_window import BackupWindow


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
