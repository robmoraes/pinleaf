"""Native X11 fault/retry, XTest keyboard, resize and disposal qualification.

Run through gui_session.py --desktop (GNOME) or gui_session.py (nested X11).
Only synthetic data in a new temporary directory is used. No desktop settings
are changed. Optional PINLEAF_QA_SCREENSHOTS captures only this app's windows.
"""
from __future__ import annotations

import ctypes
import json
import os
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("GdkX11", "4.0")
from gi.repository import Adw, GdkX11, Gio, GLib, Gtk

from pinleaf.app import run
from pinleaf.config import AppConfig
from pinleaf.ui.organization_dialogs import DeleteDialog, NameDialog


class XInput:
    def __init__(self) -> None:
        self.x11 = ctypes.CDLL("libX11.so.6")
        self.xtest = ctypes.CDLL("libXtst.so.6")
        self.x11.XOpenDisplay.restype = ctypes.c_void_p
        self.x11.XStringToKeysym.argtypes = [ctypes.c_char_p]
        self.x11.XStringToKeysym.restype = ctypes.c_ulong
        self.x11.XKeysymToKeycode.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        self.x11.XKeysymToKeycode.restype = ctypes.c_uint
        self.x11.XSetInputFocus.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
        self.x11.XResizeWindow.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_uint, ctypes.c_uint]
        self.x11.XFlush.argtypes = [ctypes.c_void_p]
        self.x11.XCloseDisplay.argtypes = [ctypes.c_void_p]
        self.xtest.XTestFakeKeyEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int, ctypes.c_ulong]
        self.display = self.x11.XOpenDisplay(None)
        assert self.display, "X11 display required"

    def focus(self, window: Gtk.Window) -> None:
        xid = GdkX11.X11Surface.get_xid(window.get_surface())
        self.x11.XSetInputFocus(self.display, xid, 2, 0)
        self.x11.XFlush(self.display)

    def key(self, name: str, *, control: bool = False) -> None:
        symbols = ["Control_L", name] if control else [name]
        codes = [self.x11.XKeysymToKeycode(self.display, self.x11.XStringToKeysym(s.encode())) for s in symbols]
        assert all(codes), symbols
        for code in codes:
            self.xtest.XTestFakeKeyEvent(self.display, code, True, 0)
        for code in reversed(codes):
            self.xtest.XTestFakeKeyEvent(self.display, code, False, 0)
        self.x11.XFlush(self.display)

    def resize(self, window: Gtk.Window, width: int, height: int) -> None:
        surface = window.get_surface()
        # Include client-side shadows while requesting a known logical size.
        outer_width = surface.get_width() + width - window.get_width()
        outer_height = surface.get_height() + height - window.get_height()
        self.x11.XResizeWindow(self.display, GdkX11.X11Surface.get_xid(surface), outer_width, outer_height)
        self.x11.XFlush(self.display)

    def close(self) -> None:
        self.x11.XCloseDisplay(self.display)


def focused_within(window: Gtk.Window, widget: Gtk.Widget) -> bool:
    focus = window.get_focus()
    while focus is not None:
        if focus is widget:
            return True
        focus = focus.get_parent()
    return False


def screenshot(name: str, window: Gtk.Window) -> None:
    directory = os.environ.get("PINLEAF_QA_SCREENSHOTS")
    if directory:
        output = Path(directory)
        output.mkdir(parents=True, exist_ok=True)
        xid = GdkX11.X11Surface.get_xid(window.get_surface())
        subprocess.run(["import", "-window", str(xid), str(output / f"{name}.png")], check=True)


def main() -> int:
    state = {"step": 0}
    errors = []
    results = {}
    keyboard = XInput()

    def check() -> bool:
        app = Gio.Application.get_default()
        org = app._service().organization
        panel = app.main_window
        step = state["step"]
        try:
            if step == 0:
                app.execute_command(lambda: org.rename("profile", org.context.profile.id, "Seventh"), affected_ids=set())
                state["source_profile"] = org.context.profile.id
                state["source"] = app.execute_command(lambda: org.create_group("LGPD"))
                app.create_note()
                state["note"] = next(iter(app.note_windows))
                app.create_note()
                state["hidden"] = next(key for key in app.note_windows if key != state["note"])
                app.hide_note(state["hidden"])
                state["agenda"] = app.execute_command(lambda: org.create_group("Agenda"))
                app.create_note()
                state["agenda_note"] = next(iter(app.note_windows))
                state["long"] = app.execute_command(lambda: org.create_group("G" * 80))
                app.execute_command(lambda: org.activate_group(state["source"].id))
                editor = app.note_windows[state["note"]]
                state["editor"] = editor
                editor.text_view.get_buffer().set_text("Pending draft retained after a failed save")
                state["fault"] = patch.object(app.note_service, "update_content", side_effect=OSError("Injected unavailable storage"))
                state["fault"].start()
                panel._perform(lambda: org.activate_group(state["agenda"].id))
                assert org.context.group.id == state["source"].id
                assert app.note_windows[state["note"]] is editor
                assert editor.autosave.has_pending_changes
            elif step == 1:
                dialogs = [window for window in Gtk.Window.list_toplevels()
                           if isinstance(window, Adw.MessageDialog) and window.get_visible()]
                assert len(dialogs) == 1, dialogs
                dialog = dialogs[0]
                assert "Could not complete" in dialog.get_heading()
                assert "latest edits" in dialog.get_body()
                screenshot("save-error-retry", dialog)
                dialog.response("ok")
                dialog.close()
                state.pop("fault").stop()
                panel._perform(lambda: org.activate_group(state["agenda"].id))
                assert org.context.group.id == state["agenda"].id
                assert app.store.get(state["note"]).content == "Pending draft retained after a failed save"
                app.execute_command(lambda: org.activate_group(state["source"].id))
                assert not app.store.get(state["hidden"]).is_open
                results["visible_save_error_buffer_preservation_retry"] = "passed"
                editor = app.note_windows[state["note"]]
                state["original_size"] = (editor.get_width(), editor.get_height())
                keyboard.resize(editor, 480, 360)
            elif step == 2:
                editor = app.note_windows[state["note"]]
                size = (editor.get_width(), editor.get_height())
                assert size != state["original_size"], size
                state["resized"] = size
                results["coordinate_api"] = {"capture": hasattr(editor, "get_position"), "restore": hasattr(editor, "move")}
                app.execute_command(lambda: org.activate_group(state["agenda"].id))
                app.execute_command(lambda: org.activate_group(state["source"].id))
            elif step == 3:
                editor = app.note_windows[state["note"]]
                assert (editor.get_width(), editor.get_height()) == state["resized"]
                saved = app.store.get(state["note"])
                assert (saved.width, saved.height) == state["resized"]
                results["resize_context_restore"] = list(state["resized"])
                panel.present()
                panel.search_entry.set_text("draft")
                panel.profile_button.grab_focus()
                keyboard.focus(panel)
                keyboard.key("f", control=True)
            elif step == 4:
                assert focused_within(panel, panel.search_entry)
                assert panel.search_entry.get_selection_bounds() == (0, 5)
                keyboard.key("Escape")
            elif step == 5:
                assert panel.search_entry.get_text() == ""
                results["xtest_ctrl_f_escape"] = "passed"
                row = panel.group_rows[state["long"].id]
                row.set_expanded(False)
                assert not row.get_expanded()
                assert row.child_focus(Gtk.DirectionType.TAB_FORWARD)
                keyboard.key("space")
            elif step == 6:
                row = panel.group_rows[state["long"].id]
                assert row.get_expanded(), "Space did not expand the inactive group"
                assert org.context.group.id == state["source"].id
                menu = panel.focus_targets[f"group-menu:{state['long'].id}"]
                assert menu.grab_focus()
                keyboard.key("space")
            elif step == 7:
                menu = panel.focus_targets[f"group-menu:{state['long'].id}"]
                assert menu.get_popover().get_visible()
                action = menu.get_popover().get_child().get_first_child()
                assert action.grab_focus()
                keyboard.key("Return")
            elif step == 8:
                dialog = next(window for window in Gtk.Window.list_toplevels()
                              if isinstance(window, NameDialog) and window.get_visible())
                assert dialog.entry.get_text() == "G" * 80
                state["rename"] = dialog
                keyboard.focus(dialog)
                keyboard.key("Escape")
            elif step == 9:
                assert not state["rename"].get_visible()
                menu = panel.focus_targets[f"group-menu:{state['long'].id}"]
                assert focused_within(panel, menu), "Cancel did not restore invoking-control focus"
                assert panel.group_rows[state["long"].id].get_expanded()
                assert org.context.group.id == state["source"].id
                assert org.repository.get_group(state["long"].id).name == "G" * 80
                results["xtest_expand_menu_rename_escape_focus"] = "passed"
                disposable = app.execute_command(lambda: org.create_profile("Disposable"))
                general = org.context.group
                app.execute_command(lambda: org.create_group("Project"))
                app.create_note()
                live = next(iter(app.note_windows))
                app.note_windows[live].text_view.get_buffer().set_text("Disposable open note")
                app.execute_command(lambda: org.move_note(state["hidden"], general.id), affected_ids={state["hidden"]})
                assert not app.store.get(state["hidden"]).is_open
                preview = org.preview_deletion("profile", disposable.id)
                assert preview.note_count == 2
                dialog = DeleteDialog(panel, org, panel.execute, preview)
                dialog.remove.set_active(True)
                dialog.replacement.set_selected(next(i for i,p in enumerate(dialog.replacements) if p.id == state["source_profile"]))
                dialog.present()
                state.update(disposal=dialog, deleted_live=live)
                state["unaffected"] = tuple(app.store.connection.execute("SELECT * FROM notes WHERE id=?", (state["note"],)).fetchone())
            elif step == 10:
                dialog = state["disposal"]
                assert "2 notes" in dialog.summary.get_text()
                assert "2 groups" in dialog.summary.get_text()
                screenshot("delete-profile-hidden", dialog)
                dialog.confirm.emit("clicked")
                assert org.context.profile.id == state["source_profile"]
                assert org.context.group.id == state["source"].id
                hidden = app.store.connection.execute("SELECT is_open,deleted_at FROM notes WHERE id=?", (state["hidden"],)).fetchone()
                assert hidden[0] == 0 and hidden[1] is not None
                assert app.store.get(state["hidden"]) is None and app.store.get(state["deleted_live"]) is None
                assert tuple(app.store.connection.execute("SELECT * FROM notes WHERE id=?", (state["note"],)).fetchone()) == state["unaffected"]
                results["profile_delete_all_including_hidden"] = "passed"
                transfer = app.execute_command(lambda: org.create_profile("Transfer source"))
                app.create_note()
                hidden = next(iter(app.note_windows))
                app.note_windows[hidden].text_view.get_buffer().set_text("Transferred hidden note")
                app.hide_note(hidden)
                app.execute_command(lambda: org.create_group("Other project"))
                app.create_note()
                opened = next(iter(app.note_windows))
                app.note_windows[opened].text_view.get_buffer().set_text("Transferred open note")
                app.note_windows[opened].flush_for_transition()
                state["transferred"] = {
                    key: dict(app.store.connection.execute("SELECT * FROM notes WHERE id=?", (key,)).fetchone())
                    for key in (hidden, opened)}
                preview = org.preview_deletion("profile", transfer.id)
                dialog = DeleteDialog(panel, org, panel.execute, preview)
                dialog.picker.profile.set_selected(next(i for i,p in enumerate(dialog.picker.profiles) if p.id == state["source_profile"]))
                dialog.picker.group.set_selected(next(i for i,g in enumerate(dialog.picker.groups) if g.id == state["agenda"].id))
                dialog.present()
                state["transfer_dialog"] = dialog
            elif step == 11:
                dialog = state["transfer_dialog"]
                assert "2 notes" in dialog.summary.get_text() and "2 groups" in dialog.summary.get_text()
                assert "Seventh / Agenda" in dialog.context_label.get_text()
                dialog.confirm.emit("clicked")
                assert org.context.group.id == state["agenda"].id
                for key, before in state["transferred"].items():
                    after = dict(app.store.connection.execute("SELECT * FROM notes WHERE id=?", (key,)).fetchone())
                    assert after.pop("group_id") == state["agenda"].id
                    before = {name:value for name,value in before.items() if name != "group_id"}
                    # The real compositor may update an open editor's geometry.
                    for field in ("width", "height", "position_x", "position_y"):
                        before.pop(field)
                        after.pop(field)
                    assert before == after, (before, after)
                    assert (key in app.note_windows) == bool(after["is_open"])
                results["profile_transfer_across_groups_including_hidden"] = "passed"
                assert not app.store.connection.execute("PRAGMA foreign_key_check").fetchall()
                assert app.store.connection.execute("PRAGMA quick_check").fetchone()[0] == "ok"
                app.quit()
                return False
            state["step"] += 1
            return True
        except BaseException:
            errors.append(f"Step {step}: {traceback.format_exc()}")
            if "fault" in state:
                state.pop("fault").stop()
            app.quit()
            return False

    with tempfile.TemporaryDirectory(prefix="pinleaf-desktop-qa-") as directory:
        config = AppConfig(Path(directory), Path(directory) / "notes.sqlite3")
        GLib.timeout_add(500, check)
        timeout = GLib.timeout_add_seconds(30, lambda: (errors.append("Desktop QA timeout"), Gio.Application.get_default().quit(), False)[-1])
        try:
            with patch("pinleaf.app.load_config", return_value=config):
                code = run(["pinleaf-desktop-qa"])
        finally:
            GLib.source_remove(timeout)
            keyboard.close()
    if errors:
        raise AssertionError("\n".join(errors))
    assert code == 0, code
    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
