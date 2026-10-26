"""Verify New menu keyboard/focus/layout on isolated X11 with synthetic data.

Usage: tests/gui_session.py /usr/bin/python3 tests/gui_creation_menu.py
Optional PINLEAF_QA_SCREENSHOTS captures only this test app's windows.
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
from pinleaf.config import AppConfig
from pinleaf.ui.organization_dialogs import NameDialog


def main() -> None:
    state, errors, helpers = {}, [], []
    keyboard = XInput()

    def open_menu(panel) -> None:
        panel.present()
        keyboard.focus(panel)
        panel.new_button.grab_focus()
        keyboard.key("Return")

    def check() -> bool:
        app = Gio.Application.get_default()
        try:
            assert app.startup_error is None
            panel, org = app.main_window, app._service().organization
            menu = panel.new_button.get_popover()
            first = menu.get_child().get_first_child()
            second = first.get_next_sibling()
            step = state.get("step", 0)
            if step == 0:
                helpers.append(app.tray)
                state["context"] = org.context
                state["changes"] = app.store.connection.total_changes
                open_menu(panel)
            elif step == 1:
                assert menu.get_visible()
                assert [first.get_child().get_text(), second.get_child().get_text()] == ["New Note", "New Group…"]
                screenshot("new-menu-light", panel)
                screenshot("new-menu-actions-light", menu)
                keyboard.key("Escape")
            elif step == 2:
                assert not menu.get_visible()
                assert app.store.connection.total_changes == state["changes"]
                assert org.context == state["context"]
                assert focused_within(panel, panel.new_button)
                open_menu(panel)
            elif step == 3:
                assert focused_within(panel, first)
                keyboard.key("Return")
            elif step == 4:
                assert len(app.note_windows) == 1
                state["shared_note"] = next(iter(app.note_windows))
                state["shared_editor"] = app.note_windows[state["shared_note"]]
                assert app.store.get(state["shared_note"]).group_id == org.repository.shared(org.context.profile.id).id
                assert org.context == state["context"]
                open_menu(panel)
            elif step == 5:
                assert focused_within(panel, first)
                keyboard.key("Tab")
            elif step == 6:
                assert focused_within(panel, second)
                keyboard.key("Return")
            elif step == 7:
                assert not menu.get_visible()
                dialog = next(w for w in Gtk.Window.list_toplevels() if isinstance(w, NameDialog) and w.get_visible())
                state["dialog"] = dialog
                assert focused_within(dialog, dialog.entry)
                dialog.entry.set_text("Cancelled project")
                keyboard.focus(dialog)
                keyboard.key("Escape")
            elif step == 8:
                assert not state["dialog"].get_visible()
                assert org.context == state["context"]
                assert len(org.list_groups()) == 1
                panel.new_button.popup()
                second.emit("clicked")
                dialog = next(w for w in Gtk.Window.list_toplevels() if isinstance(w, NameDialog) and w.get_visible())
                dialog.entry.set_text("Kubernetes course with a long descriptive title")
                dialog.confirm.emit("clicked")
                assert org.context.profile == state["context"].profile
                assert org.context.group.name.startswith("Kubernetes course")
                assert app.note_windows[state["shared_note"]] is state["shared_editor"]
                panel.new_button.popup()
                first.emit("clicked")
                assert len(app.store.list_notes(group_id=org.context.group_id)) == 1
                assert len(app.note_windows) == 2
                # The scroller takes the former body button's space.
                content = panel.get_content().get_content()
                child = content.get_first_child()
                while child is not None:
                    assert not (isinstance(child, Gtk.Button) and child.get_label() == "New group…")
                    child = child.get_next_sibling()
                Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.FORCE_DARK)
                panel.present()
                keyboard.resize(panel, 390, 540)
            elif step == 9:
                assert panel.get_width() <= 460
                screenshot("new-panel-narrow-dark", panel)
                open_menu(panel)
            elif step == 10:
                assert menu.get_visible()
                screenshot("new-menu-narrow-dark", panel)
                screenshot("new-menu-actions-dark", menu)
                keyboard.key("Escape")
            else:
                assert not menu.get_visible()
                assert focused_within(panel, panel.new_button)
                app.quit()
                return False
            state["step"] = step + 1
            return True
        except BaseException:
            errors.append(traceback.format_exc())
            app.quit()
            return False

    def timeout() -> bool:
        errors.append("Native creation-menu verification timed out")
        Gio.Application.get_default().quit()
        return False

    try:
        with tempfile.TemporaryDirectory(prefix="pinleaf-new-menu-") as directory:
            root = Path(directory)
            with patch("pinleaf.app.load_config", return_value=AppConfig(root, root / "notes.sqlite3")):
                GLib.timeout_add(300, check)
                watchdog = GLib.timeout_add_seconds(20, timeout)
                code = run(["pinleaf-creation-menu-qa"])
                if not errors:
                    GLib.source_remove(watchdog)
                assert code == 0
            if errors:
                raise AssertionError("\n".join(errors))
    finally:
        keyboard.close()
        for tray in helpers:
            tray.stop()
            if tray._process is not None:
                tray._process.wait(timeout=5)
            assert not tray.socket_path.exists()
    print(json.dumps({"status": "PASS", "checks": ["Enter opens New", "Escape returns focus without writes",
        "New Note creates in Shared or the active project", "Tab/Enter selects New Group",
        "group cancellation", "Create and activate", "no persistent creation mode",
        "body space reclaimed", "narrow dark menu", "helper cleanup"]}, indent=2))


if __name__ == "__main__":
    main()
