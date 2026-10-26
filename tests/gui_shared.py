"""Disposable native Shared lifecycle, keyboard, layout and restart checks.

Run with tests/gui_session.py. Optional PINLEAF_QA_SCREENSHOTS captures synthetic
windows only. The real tray helper is stopped and reaped after each app run.
"""
from __future__ import annotations

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
from gi.repository import Adw, GdkX11, Gio, GLib

from gui_desktop_qualification import XInput, focused_within
from pinleaf.app import run
from pinleaf.config import AppConfig


def screenshot(name, window):
    if directory := os.environ.get("PINLEAF_QA_SCREENSHOTS"):
        output = Path(directory)
        output.mkdir(parents=True, exist_ok=True)
        xid = GdkX11.X11Surface.get_xid(window.get_surface())
        subprocess.run(["import", "-window", str(xid), str(output / f"{name}.png")], check=True)


def main():
    state, errors, helpers = {}, [], []
    keyboard = XInput()
    with tempfile.TemporaryDirectory(prefix="pinleaf-shared-native-") as directory:
        config = AppConfig(Path(directory), Path(directory) / "notes.sqlite3")

        def check():
            app = Gio.Application.get_default()
            try:
                assert app.startup_error is None
                org, panel = app._service().organization, app.main_window
                step = state.get("step", 0)
                if step == 0:
                    helpers.append(app.tray)
                    app.execute_command(lambda: org.rename("profile", org.context.profile.id, "Pessoal"))
                    state["profile"] = org.context.profile.id
                    state["shared"] = org.repository.shared(org.context.profile.id)
                    # Header/tray creation falls back to Shared in the nullable context.
                    app._handle_tray_action("new-note")
                    state["aws"] = next(iter(app.note_windows))
                    app.note_windows[state["aws"]].text_view.get_buffer().set_text("AWS tags\nProject=training\nOwner=platform")
                    state["kube"] = app.execute_command(lambda: org.create_group("Kubernetes course"))
                    app.create_note()
                    state["course"] = next(key for key in app.note_windows if key != state["aws"])
                    app.note_windows[state["course"]].text_view.get_buffer().set_text("Study Kubernetes Services and Ingress")
                    app.note_windows[state["course"]].flush_for_transition()
                    state["editor"] = app.note_windows[state["aws"]]
                    panel.present()
                elif step == 1:
                    assert all(w.get_mapped() for w in app.note_windows.values())
                    screenshot("shared-panel", panel)
                    screenshot("shared-note", state["editor"])
                    state["swarm"] = app.execute_command(lambda: org.create_group("Docker Swarm channel"))
                    assert app.note_windows[state["aws"]] is state["editor"]
                    assert state["course"] not in app.note_windows
                    panel.focus_targets[f"shared-create:{state['shared'].id}"].emit("clicked")
                    state["extra"] = next(key for key in app.note_windows if key != state["aws"])
                    assert app.store.get(state["extra"]).group_id == state["shared"].id
                    assert org.context.group_id == state["swarm"].id
                    app.note_windows[state["extra"]].text_view.get_buffer().set_text("Shared reminder: review resource tags")
                    app.hide_note(state["extra"])
                    panel.present()
                    keyboard.focus(panel)
                    keyboard.key("f", control=True)
                elif step == 2:
                    assert focused_within(panel, panel.search_entry)
                    if not state.get("search_ready"):
                        panel.search_entry.set_text("AWS")
                        panel.refresh()
                        state["search_ready"] = True
                        return True
                    assert panel.list_box.get_first_child().note_id == state["aws"]
                    screenshot("shared-search", panel)
                    keyboard.key("Escape")
                elif step == 3:
                    assert panel.search_entry.get_text() == ""
                    row = panel.focus_targets[f"note:{state['extra']}"]
                    row.grab_focus()
                    keyboard.focus(panel)
                    keyboard.key("Return")
                elif step == 4:
                    assert state["extra"] in app.note_windows
                    assert org.context.group_id == state["swarm"].id
                    app.hide_note(state["extra"])
                    app.execute_command(lambda: org.activate_group(state["kube"].id))
                    assert set(app.note_windows) == {state["aws"], state["course"]}
                    foreign = app.execute_command(lambda: org.create_profile("Freelancer"))
                    app.create_note()
                    foreign_note = next(iter(app.note_windows))
                    app.note_windows[foreign_note].text_view.get_buffer().set_text("Shared client reminder")
                    app.open_note(state["aws"])
                    assert org.context.group_id == state["kube"].id
                    app.open_note(foreign_note)
                    assert org.context.identity == (foreign.id, None)
                    preview = org.preview_deletion("profile", foreign.id)
                    from pinleaf.ui.organization_dialogs import DeleteDialog
                    dialog = DeleteDialog(panel, org, app.execute_command, preview)
                    assert "Kubernetes course" in dialog.context_label.get_text()
                    dialog.present()
                    state["dialog"] = dialog
                elif step == 5:
                    screenshot("shared-delete-profile", state["dialog"])
                    state["dialog"].confirm.emit("clicked")
                    assert org.context.identity == (state["profile"], state["kube"].id)
                    assert not app.store.get(state["extra"]).is_open
                    state["expected"] = set(app.note_windows)
                    Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.FORCE_DARK)
                    panel.present()
                    keyboard.resize(panel, 390, 540)
                elif step == 6:
                    assert panel.get_width() <= 460, panel.get_width()
                    screenshot("shared-panel-narrow-dark", panel)
                    app.quit()
                    return False
                state["step"] = step + 1
                return True
            except BaseException:
                errors.append(traceback.format_exc())
                app.quit()
                return False

        try:
            with patch("pinleaf.app.load_config", return_value=config):
                timer = GLib.timeout_add(400, check)
                assert run(["pinleaf-shared-native"]) == 0
                if errors:
                    raise AssertionError("\n".join(errors))
                saved = Path(directory) / "expected.json"
                saved.write_text(json.dumps({"profile": state["profile"], "group": state["kube"].id,
                    "notes": sorted(state["expected"]), "hidden": state["extra"], "aws": state["aws"]}))
                subprocess.run([sys.executable, __file__, "--restart", directory], check=True, timeout=20)
        finally:
            keyboard.close()
            for tray in helpers:
                tray.stop()
                if tray._process is not None:
                    tray._process.wait(timeout=5)
                assert not tray.socket_path.exists()
    print(json.dumps({"status": "PASS", "checks": ["Shared creation", "window identity across projects",
        "Ctrl+F/Escape/Enter", "hidden Shared explicit open", "profile isolation", "profile transfer to Shared",
        "narrow dark layout", "restart", "tray helper cleanup"]}, indent=2))


def restart(directory):
    root = Path(directory)
    saved = json.loads((root / "expected.json").read_text())
    errors, helpers = [], []
    def check():
        app = Gio.Application.get_default()
        helpers.append(app.tray)
        try:
            assert app.startup_error is None
            assert app._service().organization.context.identity == (saved["profile"], saved["group"])
            assert set(app.note_windows) == set(saved["notes"])
            assert not app.store.get(saved["hidden"]).is_open
            assert app.store.get(saved["aws"]).content.startswith("AWS tags")
        except BaseException:
            errors.append(traceback.format_exc())
        app.quit()
        return False
    try:
        with patch("pinleaf.app.load_config", return_value=AppConfig(root, root / "notes.sqlite3")):
            GLib.timeout_add(400, check)
            assert run(["pinleaf-shared-restart"]) == 0
        if errors:
            raise AssertionError("\n".join(errors))
    finally:
        for tray in helpers:
            tray.stop()
            if tray._process is not None:
                tray._process.wait(timeout=5)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--restart":
        restart(sys.argv[2])
    else:
        main()
