"""Real GTK local backup/restore with temporary data and an isolated X11 bus.

Usage: tests/gui_session.py /usr/bin/python3 tests/gui_backup.py [--corrupt]
"""
from __future__ import annotations

import json
import sys
import tempfile
import traceback
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, Gtk

from gui_desktop_qualification import XInput, focused_within, screenshot
from pinleaf.app import run
from pinleaf.backup_format import decode, encode, library_digest
from pinleaf.config import AppConfig
from pinleaf.models import NoteColor
from pinleaf.services.context_controller import TransitionError
from pinleaf.storage.library_backup import read_library


def main() -> None:
    corrupt = "--corrupt" in sys.argv
    large = "--large" in sys.argv
    errors, helpers, state = [], [], {}
    keyboard = XInput()
    with tempfile.TemporaryDirectory(prefix="pinleaf-backup-qa-") as directory:
        root = Path(directory)
        path = root / "notes.sqlite3"
        destination = root / "protected.pinleaf-backup"
        if corrupt:
            path.write_bytes(b"synthetic damaged database")
            Path(str(path) + "-wal").write_bytes(b"synthetic WAL")
        fixture = Path(__file__).resolve().parents[1] / "specs/015-local-backup-and-google-drive/contracts/examples/valid-unprotected.pinleaf-backup"

        def check() -> bool:
            app = Gio.Application.get_default()
            try:
                step = state.get("step", 0)
                window = app.backup_window
                if app.backup_service and app.backup_service.busy:
                    state["heartbeats"] = state.get("heartbeats", 0) + 1
                    return True
                if corrupt:
                    if step == 0:
                        assert app.startup_error is not None
                        app.show_backup(startup_only=True)
                    elif step == 1:
                        assert not window.create_button.get_visible()
                        window._selected(fixture.read_bytes())
                    elif step == 2:
                        assert window.preview is not None
                        screenshot("startup-restore-preview", window)
                        window._confirm_restore()
                    elif step == 3:
                        window.confirmation.response("restore")
                    elif step == 4:
                        assert app.startup_error is None
                        assert app.main_window is not None
                        preserved = next((root / "restore-staging").glob("*/original"))
                        assert (preserved / "database").read_bytes() == b"synthetic damaged database"
                        assert (preserved / "database-wal").read_bytes() == b"synthetic WAL"
                        assert len(app.note_windows) == 2
                        helpers.append(app.tray)
                        screenshot("startup-restore-complete", window)
                        app.quit()
                        return False
                else:
                    if step == 0:
                        assert app.startup_error is None
                        helpers.append(app.tray)
                        app.create_note()
                        state["note"] = next(iter(app.note_windows))
                        state["editor"] = app.note_windows[state["note"]]
                        state["editor"].text_view.get_buffer().set_text("Pending capture 🔐\nA second line")
                        app.create_note()
                        hidden = next(key for key in app.note_windows if key != state["note"])
                        app.hide_note(hidden)
                        state["hidden"] = hidden
                        with app.store.transaction():
                            app.store.connection.execute("UPDATE notes SET font_family='Unavailable synthetic font',font_size=NULL,text_color=NULL WHERE id=?", (state["note"],))
                        if large:
                            base = read_library(app.store.connection)["notes"][0]
                            with app.store.transaction():
                                from pinleaf.storage.library_backup import COLUMNS
                                columns = COLUMNS["notes"]
                                rows = [dict(base, id=f"bulk-{index:04}", is_open=0,
                                    deleted_at=base["created_at"] if index % 7 == 0 else None) for index in range(998)]
                                app.store.connection.executemany(
                                    f"INSERT INTO notes ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})",
                                    [tuple(row[key] for key in columns) for row in rows])
                        # Exercise the actual main-menu entry.
                        def find(widget):
                            if isinstance(widget, Gtk.Button) and widget.get_label() == "Backup & Restore…":
                                return widget
                            child = widget.get_first_child()
                            while child:
                                found = find(child)
                                if found: return found
                                child = child.get_next_sibling()
                        button = find(app.main_window)
                        assert button is not None
                        button.emit("clicked")
                    elif step == 1:
                        assert window is not None
                        screenshot("local-backups-light", window)
                        window.create_button.emit("clicked")
                    elif step == 2:
                        form = window.password_window
                        assert not form.protection.get_active()
                        assert not form.fields.get_visible()
                        screenshot("create-unprotected-light", form)
                        keyboard.focus(form)
                        keyboard.key("Escape")
                    elif step == 3:
                        assert not window.password_window.get_visible()
                        window.create_button.emit("clicked")
                        window.password_window.confirm.emit("clicked")
                    elif step == 4:
                        if state.get("protected_ready"):
                            form = window.password_window
                            screenshot("create-protected-light", form)
                            form.confirm.emit("clicked")
                            state["step"] = step + 1
                            return True
                        assert window.chooser.get_visible()
                        window.chooser.emit("response", Gtk.ResponseType.CANCEL)
                        assert not destination.exists()
                        window.create_button.emit("clicked")
                        form = window.password_window
                        form.protection.set_active(True)
                        form.password.set_text("Synthetic-password-🔐")
                        form.confirmation.set_text("mismatch")
                        form.confirm.emit("clicked")
                        assert "match" in form.error.get_text()
                        assert window.chooser is None
                        form.confirmation.set_text("Synthetic-password-🔐")
                        state["protected_ready"] = True
                        return True
                    elif step == 5:
                        assert window.chooser.get_visible()
                        window.chooser.set_current_folder(Gio.File.new_for_path(str(root)))
                        window.chooser.set_current_name(destination.name)
                    elif step == 6:
                        assert window.chooser.get_file().get_path() == str(destination)
                        window.chooser.emit("response", Gtk.ResponseType.ACCEPT)
                    elif step == 7:
                        assert destination.exists(), window.status.get_text()
                        state["raw"] = destination.read_bytes()
                        state["captured"] = decode(state["raw"], "Synthetic-password-🔐").payload
                        assert next(row for row in state["captured"]["library"]["notes"] if row["id"] == state["note"])["content"] == "Pending capture 🔐\nA second line"
                        assert not app.store.get(state["hidden"]).is_open
                        window._selected(state["raw"])
                    elif step == 8:
                        assert window.preview is None
                        form = window.password_window
                        assert form.unlock and form.fields.get_visible()
                        assert focused_within(form, form.password)
                        form.password.set_text("wrong")
                        form.confirm.emit("clicked")
                    elif step == 9:
                        assert window.preview is None
                        assert "Wrong password" in window.status.get_text()
                        for dialog in Gtk.Window.list_toplevels():
                            if isinstance(dialog, Adw.MessageDialog) and dialog.get_visible():
                                dialog.response("ok")
                                dialog.close()
                        window._read_selection("Synthetic-password-🔐")
                    elif step == 10:
                        assert window.preview is not None
                        hidden_count = sum(row["deleted_at"] is None and not row["is_open"] for row in state["captured"]["library"]["notes"])
                        assert f"{hidden_count} hidden" in window.preview_text.get_text()
                        assert "Pending capture" not in window.preview_text.get_text()
                        screenshot("restore-preview-light", window)
                        destination.write_bytes(b"external file replaced after preview")
                        state["editor"].text_view.get_buffer().set_text("Latest edit after preview")
                        state["old_panel"] = app.main_window
                        state["old_service"] = app.note_service
                        state["old_create"] = app.main_window.on_create_note
                        state["queued_tray"] = []
                        with patch.object(GLib, "idle_add", side_effect=lambda callback: state["queued_tray"].append(callback)):
                            app._queue_tray_action("new-note")
                        window.final_restore.emit("clicked")
                    elif step == 11:
                        assert window.confirmation.get_default_response() == "cancel"
                        assert window.confirmation.get_heading() == "Replace all current notes?"
                        assert [dialog for dialog in Gtk.Window.list_toplevels() if isinstance(dialog, Adw.MessageDialog) and dialog.get_visible()] == [window.confirmation]
                        screenshot("restore-confirmation-light", window.confirmation)
                        window.confirmation.response("cancel")
                        window.confirmation.close()
                        assert state["editor"].get_visible()
                        window.final_restore.emit("clicked")
                    elif step == 12:
                        window.confirmation.response("restore")
                        window.confirmation.close()
                    elif step == 13:
                        assert "Library restored" in window.status.get_text(), window.status.get_text()
                        assert app.main_window is not state["old_panel"]
                        assert app.note_windows[state["note"]] is not state["editor"]
                        assert not app.store.get(state["hidden"]).is_open
                        assert state["hidden"] not in app.note_windows
                        recovered = decode(next((root / "backups").glob("pinleaf-recovery-*.pinleaf-backup")).read_bytes()).payload
                        assert next(row for row in recovered["library"]["notes"] if row["id"] == state["note"])["content"] == "Latest edit after preview"
                        assert library_digest(read_library(app.store.connection)) == library_digest(state["captured"]["library"])
                        before = read_library(app.store.connection)
                        state["editor"]._save_content(state["note"], "stale autosave")
                        state["editor"]._set_color(NoteColor.PINK)
                        state["editor"]._delete_note()
                        for callback in state["queued_tray"]:
                            callback()
                        try:
                            state["old_create"]()
                        except TransitionError:
                            pass
                        else:
                            raise AssertionError("Stale panel callback accepted")
                        assert read_library(app.store.connection) == before
                        window.create_button.emit("clicked")
                    elif step == 14:
                        assert not window.password_window.protection.get_active()
                        assert not window.password_window.password.get_text()
                        window.password_window.close()
                        Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.FORCE_DARK)
                        keyboard.resize(window, 390, 500)
                    elif step == 15:
                        screenshot("local-backups-narrow-dark", window)
                        assert window.get_width() <= 450
                        keyboard.focus(window)
                        keyboard.key("Escape")
                    elif step == 16:
                        assert app.backup_window is None
                        assert focused_within(app.main_window, app.main_window.profile_button)
                        app.show_backup()
                    elif step == 17:
                        assert window is not None
                        screenshot("local-backups-status-dark", window)
                        app.quit()
                        return False
                state["step"] = step + 1
                return True
            except BaseException:
                errors.append(traceback.format_exc())
                app.quit()
                return False

        def timeout() -> bool:
            errors.append(f"Backup GUI timed out at step {state.get('step')}")
            Gio.Application.get_default().quit()
            return False
        try:
            with patch("pinleaf.app.load_config", return_value=AppConfig(root, path)):
                GLib.timeout_add(350, check)
                watchdog = GLib.timeout_add_seconds(40, timeout)
                code = run(["pinleaf-backup-qa"])
                if not errors:
                    GLib.source_remove(watchdog)
                assert code == 0 or errors, code
            if errors:
                raise AssertionError("\n".join(errors))
        finally:
            keyboard.close()
            for tray in helpers:
                tray.stop()
                if tray._process is not None:
                    tray._process.wait(timeout=5)
                assert not tray.socket_path.exists()
    print(json.dumps({"status": "PASS", "mode": "startup-error" if corrupt else "healthy",
        "large": large, "steps": state.get("step"), "responsive_worker_heartbeats": state.get("heartbeats", 0)}, indent=2))


if __name__ == "__main__":
    main()
