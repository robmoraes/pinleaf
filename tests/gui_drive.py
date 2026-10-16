"""Real-app Drive restore QA with disposable data.

Run directly in a graphical session. Default uses a stateful provider double.
--live downloads only the two synthetic copies recorded by the D02 smoke drill;
it reuses explicitly saved development access and never opens new consent.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import traceback
from pathlib import Path
from threading import Event
from unittest.mock import patch
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib

from pinleaf.app import run
from pinleaf.backup_format import decode, encode
from pinleaf.config import AppConfig
from pinleaf.services.drive_auth import DriveAuth, DriveAuthError, DriveConnection
from pinleaf.services.drive_backup import DriveDestination, DriveTransport, UploadAttempt
from pinleaf.storage.library_backup import read_library
from test_drive_backup import FakeDrive

PASSWORD = "Synthetic-drive-smoke-only-789"


def main() -> None:
    live = "--live" in sys.argv
    large = "--large" in sys.argv
    if live and large:
        raise SystemExit("The existing live fixtures are small; use --large with the provider double.")
    visual = "--visual" in sys.argv
    keyboard = None
    if visual:
        from gui_desktop_qualification import XInput, screenshot
        keyboard = XInput()
    payload = json.loads((ROOT / "specs/015-local-backup-and-google-drive/contracts/examples/valid-unprotected.pinleaf-backup").read_bytes())["payload"]
    if large:
        from drive_two_installations import synthetic_library
        payload = synthetic_library()
    if live:
        clients = list((ROOT / "tmp").glob("client_secret_*.json"))
        if len(clients) != 1:
            raise RuntimeError("Expected one development OAuth client.")
        os.environ["PINLEAF_GOOGLE_CLIENT_FILE"] = str(clients[0])
        def no_consent(*_args):
            raise DriveAuthError("Connect the development app before running this live drill.")
        auth = DriveAuth(Path("/tmp/pinleaf-dev/pinleaf"), authorizer=no_consent)
        auth.connect(Event())
        destination = DriveDestination(DriveTransport(auth))
        manifest = json.loads((ROOT / "tmp/drive-smoke-results.json").read_bytes())
        by_id = {copy.file_id: copy for copy in destination.list_copies(Event())}
        copies = [by_id[item["file_id"]] for item in manifest]
        assert len(copies) == 2 and {copy.protected for copy in copies} == {False, True}
        copies.sort(key=lambda copy: copy.protected)
    else:
        provider = FakeDrive()
        destination = DriveDestination(provider)
        auth = DriveAuth(Path("/tmp/synthetic-drive-auth"))
        auth.connection = DriveConnection("test@example.org", True)
        auth.client_id = "client"
        copies = []
        for password in (None, PASSWORD):
            source = UploadAttempt(("client", "test@example.org"), payload["created_at"], password is not None, encode(payload, password))
            copies.append(destination.upload(source, Event()))

    errors, helpers, messages = [], [], []
    state = {"phase": "setup", "case": 0, "heartbeats": 0}
    connection = auth.connection
    with tempfile.TemporaryDirectory(prefix="pinleaf-drive-restore-qa-") as directory:
        root = Path(directory)
        database = root / "notes.sqlite3"

        def check() -> bool:
            app = Gio.Application.get_default()
            if app is None or app.backup_service is None:
                return True
            state["app"] = app
            try:
                if app.backup_service.busy:
                    state["heartbeats"] += 1
                    return True
                window = app.backup_window
                selected = copies[state["case"]]
                phase = state["phase"]
                if phase == "setup":
                    assert app.startup_error is None
                    if not helpers:
                        helpers.append(app.tray)
                        app.backup_service.drive_auth = auth
                        app.backup_service.drive = destination
                    before = set(app.note_windows)
                    app.create_note()
                    note_id = next(iter(set(app.note_windows) - before))
                    state["target_note"] = note_id
                    state["editor"] = app.note_windows[note_id]
                    state["editor"].text_view.get_buffer().set_text("Target before remote restore")
                    app.show_backup()
                    if visual and state["case"] == 1:
                        Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.FORCE_DARK)
                        keyboard.resize(app.backup_window, 360, 680)
                    state["phase"] = "list"
                elif phase == "list":
                    window.refresh_drive.emit("clicked")
                    state["phase"] = "choose"
                elif phase in ("choose", "capture-choose"):
                    if visual and phase == "choose":
                        state["phase"] = "capture-choose"
                        return True
                    if visual:
                        if state["case"] == 1:
                            assert window.get_width() <= 380, window.get_width()
                        screenshot("drive-copies-narrow-dark" if state["case"] else "drive-copies-light", window)
                    row = window.drive_copies.get_first_child()
                    while row is not None and selected.name not in row.get_first_child().get_text():
                        row = row.get_next_sibling()
                    assert row is not None
                    row.get_last_child().emit("clicked")
                    state["phase"] = "password" if selected.protected else "preview"
                elif phase == "password":
                    assert window.preview is None
                    assert window.password_window.unlock
                    if visual:
                        screenshot("drive-password-dark", window.password_window)
                    window.password_window.password.set_text("wrong-synthetic-password")
                    window.password_window.confirm.emit("clicked")
                    state["phase"] = "retry-password"
                elif phase == "retry-password":
                    assert window.preview is None and window.unlock_button.get_visible()
                    window.unlock_button.emit("clicked")
                    window.password_window.password.set_text(PASSWORD)
                    window.password_window.confirm.emit("clicked")
                    state["phase"] = "preview"
                elif phase in ("preview", "capture-preview"):
                    assert window.preview is not None
                    assert window.preview.backup.payload == payload
                    if visual and phase == "preview":
                        state["phase"] = "capture-preview"
                        return True
                    if visual:
                        screenshot("drive-preview-narrow-dark" if state["case"] else "drive-preview-light", window)
                    assert app.store.get(state["target_note"]) is not None
                    state["recovery"] = window.preview.recovery
                    window._confirm_restore()
                    assert window.confirmation.get_default_response() == "cancel"
                    if visual:
                        state["phase"] = "default-cancel"
                        return True
                    window.confirmation.response("cancel")
                    assert app.store.get(state["target_note"]) is not None
                    state["editor"].text_view.get_buffer().set_text("Latest target edit before final remote restore")
                    window._confirm_restore()
                    window.confirmation.response("restore")
                    state["phase"] = "verify"
                elif phase == "default-cancel":
                    screenshot("drive-confirmation-narrow-dark" if state["case"] else "drive-confirmation-light", window.confirmation)
                    keyboard.focus(window.confirmation)
                    keyboard.key("Return")
                    state["phase"] = "after-default-cancel"
                elif phase == "after-default-cancel":
                    assert not window.confirmation.get_visible()
                    assert app.store.get(state["target_note"]) is not None
                    state["editor"].text_view.get_buffer().set_text("Latest target edit before final remote restore")
                    window._confirm_restore()
                    window.confirmation.response("restore")
                    state["phase"] = "verify"
                elif phase == "verify":
                    assert window.preview is None
                    actual = read_library(app.store.connection)
                    assert actual == payload["library"]
                    recovered = decode(state["recovery"].read_bytes()).payload["library"]
                    target = next(note for note in recovered["notes"] if note["id"] == state["target_note"])
                    assert target["content"] == "Latest target edit before final remote restore"
                    assert auth.connection is connection
                    assert not list(root.glob("drive-download-*"))
                    for note in payload["library"]["notes"]:
                        if not note["is_open"] or note["deleted_at"] is not None:
                            assert note["id"] not in app.note_windows
                    assert len(app.note_windows) == 2
                    if state["case"] == 0:
                        state["case"] = 1
                        state["phase"] = "setup"
                    else:
                        state["phase"] = "done"
                        app.quit()
                        return False
                return True
            except BaseException:
                errors.append(traceback.format_exc())
                app.quit()
                return False

        def timeout() -> bool:
            errors.append(f"Drive restore QA timed out at {state['phase']}")
            Gio.Application.get_default().quit()
            return False

        try:
            with patch("pinleaf.app.load_config", return_value=AppConfig(root, database)), \
                 patch("pinleaf.app.APP_ID", "dev.pinleaf.DriveQA" + uuid4().hex), \
                 patch("pinleaf.ui.backup_window.show_error", side_effect=lambda *args: messages.append(args[1])):
                GLib.timeout_add(200, check)
                watchdog = GLib.timeout_add_seconds(90, timeout)
                code = run(["pinleaf-drive-restore-qa"])
                if not errors:
                    GLib.source_remove(watchdog)
                assert code == 0 or errors
            if errors:
                raise AssertionError("\n".join(errors))
            assert len(messages) == 1, messages  # Only the deliberate wrong password.
        finally:
            app = state.get("app")
            if app and app.backup_service and app.backup_service.thread:
                app.backup_service.thread.join(35)
                assert not app.backup_service.thread.is_alive(), "QA worker did not stop"
            for tray in helpers:
                tray.stop()
                if tray._process is not None:
                    tray._process.wait(timeout=5)
            if keyboard:
                keyboard.close()
    print(json.dumps({"status": "PASS", "provider": "live" if live else "double",
                      "notes": len(payload["library"]["notes"]),
                      "restored_modes": ["unprotected", "protected"],
                      "responsive_worker_heartbeats": state["heartbeats"]}))


if __name__ == "__main__":
    main()
