"""Isolated native-app smoke test. Run under a separate D-Bus session.

XDG_DATA_HOME=/tmp/pinleaf-qa dbus-run-session -- /usr/bin/python3 tests/gui_lifecycle.py
Set PINLEAF_QA_SCREENSHOTS to an output directory to capture synthetic UI images.
"""
from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib

from pinleaf.app import run
from pinleaf.config import load_config


assert os.environ.get("XDG_DATA_HOME", "").startswith("/tmp/"), "QA requires isolated /tmp data"
scenario = sys.argv[1] if len(sys.argv) > 1 else "lifecycle"
state = {}
errors = []


def screenshot(name: str, window=None) -> None:
    output = os.environ.get("PINLEAF_QA_SCREENSHOTS")
    if output:
        directory = Path(output)
        directory.mkdir(parents=True, exist_ok=True)
        gi.require_version("GdkX11", "4.0")
        from gi.repository import GdkX11
        app = Gio.Application.get_default()
        target = window or app.main_window or app.error_window
        xid = GdkX11.X11Surface.get_xid(target.get_surface())
        subprocess.run(["import", "-window", str(xid), str(directory / f"{name}.png")], check=True)


def check() -> bool:
    app = Gio.Application.get_default()
    try:
        org = app._service().organization if scenario != "startup-error" else None
        step = state.get("step", 0)
        if scenario.startswith("layout"):
            if step == 0:
                Adw.StyleManager.get_default().set_color_scheme(
                    Adw.ColorScheme.FORCE_DARK if scenario == "layout-dark" else Adw.ColorScheme.FORCE_LIGHT)
                app.execute_command(lambda: org.create_profile("Perfil profissional e pessoal com um nome bastante longo para verificar o painel"))
                app.execute_command(lambda: org.create_group("Financeiro" * 8))
                app.create_note()
                note_id = next(iter(app.note_windows))
                app.note_windows[note_id].text_view.get_buffer().set_text("Uma nota de teste para verificar ações e contraste.")
                app.hide_note(note_id)
                app.main_window.set_default_size(360, 500)
                app.main_window.present()
                state["step"] = 1
                return True
            if step == 1:
                assert app.main_window.get_width() <= 460, app.main_window.get_width()
                screenshot(scenario)
                from pinleaf.ui.organization_dialogs import MoveDialog
                dialog = MoveDialog(app.main_window, org, app.execute_command, app.store.list_notes()[0].id)
                dialog.present()
                state["dialog"] = dialog
                state["step"] = 2
                return True
            if step == 2:
                screenshot(scenario + "-move", state["dialog"])
                state["dialog"].cancel.emit("clicked")
                app.main_window.search_entry.set_text("nota")
                app.main_window.scope.set_selected(2)
                app.main_window.refresh()
                state["step"] = 3
                return True
            assert app.main_window.get_width() <= 460, app.main_window.get_width()
            screenshot(scenario + "-search")
            app.quit()
            return False
        if scenario == "startup-error":
            assert app.startup_error is not None
            assert app.error_window is not None and app.error_window.get_visible()
            assert app.main_window is None and not app.note_windows
            screenshot("startup-error")
            app.quit()
            return False
        if scenario == "restart":
            assert org.context.group.name == "Financeiro"
            all_notes = app.store.list_notes()
            expected = {note.id for note in all_notes if note.id in {n.id for n in app._service().list_notes()} and note.is_open}
            assert set(app.note_windows) == expected and len(expected) == 1
            assert any(not note.is_open for note in all_notes)
            before = dict(app.note_windows)
            app.do_activate()
            assert app.note_windows == before
            screenshot("restart")
            app.quit()
            return False
        if step == 0:
            app.execute_command(lambda: org.create_group("General"))
            state["initial"] = org.context
            app.create_note()
            note_id = next(iter(app.note_windows))
            state["first"] = note_id
            app.note_windows[note_id].text_view.get_buffer().set_text("Revisar orçamento de outubro\nConferir despesas e investimentos.")
            finance = app.execute_command(lambda: org.create_group("Financeiro"))
            state["finance"] = finance
            assert not app.note_windows
            assert app.store.get(note_id).content.startswith("Revisar orçamento")
            assert app.store.get(note_id).is_open
            app._handle_tray_action("new-note")
            visible = next(iter(app.note_windows))
            state["visible"] = visible
            assert app.store.get(visible).group_id == finance.id
            app.note_windows[visible].text_view.get_buffer().set_text("Pagar cartão até sexta-feira")
            app.create_note()
            hidden = next(note_id for note_id in app.note_windows if note_id != visible)
            app.note_windows[hidden].text_view.get_buffer().set_text("Reserva de emergência")
            app.hide_note(hidden)
            assert not app.store.get(hidden).is_open
            app.execute_command(lambda: org.create_group("Exercícios"))
            app.create_note()
            exercise = next(iter(app.note_windows))
            app.note_windows[exercise].text_view.get_buffer().set_text("Treino: caminhada de 30 minutos")
            app.execute_command(lambda: org.activate_group(finance.id))
            assert set(app.note_windows) == {visible}
            app.main_window.group_rows[org.repository.last_group(org.context.profile.id).id].set_expanded(True)
            # Independent expansion only browses the other groups.
            for row in app.main_window.group_rows.values():
                row.set_expanded(True)
            app.main_window.present()
            state["step"] = 1
            return True
        if step == 1:
            screenshot("panel-groups")
            before = dict(app.note_windows)
            app.main_window.close()
            assert not app.main_window.get_visible()
            app._handle_tray_action("show-main")
            assert app.main_window.get_visible() and app.note_windows == before
            state["other"] = app.execute_command(lambda: org.create_profile("Freelancer"))
            app.create_note()
            other_note = next(iter(app.note_windows))
            app.note_windows[other_note].text_view.get_buffer().set_text("Proposta para Empresa X")
            app.execute_command(lambda: org.activate_group(state["finance"].id))
            app.main_window.search_entry.set_text("proposta")
            app.main_window.scope.set_selected(2)
            app.main_window.refresh()
            assert app.main_window.list_box.get_first_child().note_id == other_note
            assert org.context.group.id == state["finance"].id
            state["step"] = 2
            return True
        if step == 2:
            screenshot("global-search")
            row = app.main_window.list_box.get_first_child()
            menu = app.main_window.focus_targets[f"note-menu:{row.note_id}"]
            menu.popup()
            action = menu.get_popover().get_child().get_first_child()
            assert action.get_child().get_text().startswith("Switch profile and open")
            action.emit("clicked")
            assert org.context.profile.id == state["other"].id
            assert app.main_window.search_entry.get_text() == "" and app.main_window.scope.get_selected() == 0
            app.execute_command(lambda: org.activate_group(state["finance"].id))
            app.main_window.search_entry.set_text("")
            app.main_window.refresh()
            from pinleaf.ui.organization_dialogs import DeleteDialog
            preview = org.preview_deletion("profile", state["other"].id)
            dialog = DeleteDialog(app.main_window, org, app.execute_command, preview)
            dialog.present()
            state["dialog"] = dialog
            state["step"] = 3
            return True
        screenshot("delete-profile", state["dialog"])
        state["dialog"].cancel.emit("clicked")
        assert org.context.group.id == state["finance"].id
        assert len(org.list_profiles()) == 2
        app.quit()
        return False
    except BaseException:
        errors.append(traceback.format_exc())
        app.quit()
        return False


if scenario == "startup-error":
    config = load_config()
    config.data_dir.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(config.database_path) as connection:
        connection.execute("CREATE TABLE schema_version(version INTEGER)")
        connection.execute("INSERT INTO schema_version VALUES (99)")
GLib.timeout_add(700, check)
GLib.timeout_add_seconds(20, lambda: (errors.append("GUI timeout"), Gio.Application.get_default().quit(), False)[-1])
code = run(["pinleaf-qa"])
if errors:
    print("\n".join(errors), file=sys.stderr)
    raise SystemExit(1)
assert code == (1 if scenario == "startup-error" else 0), code
print(f"PASS: native application {scenario}")
