"""Inspect real AT-SPI names/states from a separate process on a private bus.

Usage: python3 tests/gui_session.py --a11y python3 tests/gui_accessibility.py
This checks the data assistive tools receive, not Orca speech or human usability.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import gi

gi.require_version("Atspi", "2.0")
from gi.repository import Atspi


def inspect(pid: int, phase: int) -> None:
    Atspi.init()
    desktop = Atspi.get_desktop(0)
    application = None
    for _ in range(40):
        for index in range(desktop.get_child_count()):
            child = desktop.get_child_at_index(index)
            if child.get_process_id() == pid:
                application = child
                break
        if application is not None:
            break
        time.sleep(0.1)
    assert application is not None, f"Application {pid} missing from private AT-SPI desktop"
    nodes = []

    def walk(accessible, depth=0):
        assert depth < 40 and len(nodes) < 2000, "Unexpected accessibility tree size"
        states = accessible.get_state_set()
        nodes.append({"name": accessible.get_name(), "role": accessible.get_role_name(),
                      "expanded": states.contains(Atspi.StateType.EXPANDED),
                      "focusable": states.contains(Atspi.StateType.FOCUSABLE)})
        for index in range(accessible.get_child_count()):
            walk(accessible.get_child_at_index(index), depth + 1)

    walk(application)
    names = [node["name"] for node in nodes]
    assert "Switch profile, Pessoal" in names, names
    if phase == 0:
        assert any(name.startswith("Hidden note. Hidden budget") for name in names), names
        assert any(node["name"] == "G" * 80 and node["expanded"] for node in nodes), nodes
        assert any("Active" in name for name in names), names
    elif phase == 1:
        assert any(node["name"] == "Search scope" and node["role"] == "combo box" for node in nodes), nodes
        assert "All profiles" in names, names
        assert any(name.startswith("Hidden note. Hidden budget") and "Pessoal / General" in name for name in names), names
    else:
        assert any(node["name"] == "Profile" and node["role"] == "combo box" for node in nodes), nodes
        assert any(node["name"] == "Group" and node["role"] == "combo box" for node in nodes), nodes
        assert "G" * 80 in names, names
    print(json.dumps({"phase":phase,"nodes":nodes},ensure_ascii=False))
    Atspi.exit()


def main() -> int:
    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1")
    from gi.repository import Gio, GLib
    from pinleaf.app import run
    from pinleaf.config import AppConfig
    from pinleaf.ui.organization_dialogs import MoveDialog

    state = {"phase":0}
    errors = []
    results = []
    with tempfile.TemporaryDirectory(prefix="pinleaf-atspi-qa-") as directory:
        config = AppConfig(Path(directory),Path(directory)/"notes.sqlite3")

        def check() -> bool:
            app = Gio.Application.get_default()
            try:
                org = app._service().organization
                panel = app.main_window
                if "initialized" not in state:
                    app.execute_command(lambda: org.rename("profile",org.context.profile.id,"Pessoal"),affected_ids=set())
                    state["general"] = org.context.group.id
                    app.create_note()
                    state["hidden"] = next(iter(app.note_windows))
                    app.note_windows[state["hidden"]].text_view.get_buffer().set_text("Hidden budget")
                    app.hide_note(state["hidden"])
                    state["long"] = app.execute_command(lambda: org.create_group("G"*80))
                    app.execute_command(lambda: org.activate_group(state["general"]))
                    panel.group_rows[state["long"].id].set_expanded(True)
                    state["initialized"] = True
                    return True
                if "child" not in state:
                    output = Path(directory)/f"phase-{state['phase']}.json"
                    state["output"] = output
                    with output.open("w") as stream:
                        state["child"] = subprocess.Popen(
                            [sys.executable,__file__,"--inspect",str(os.getpid()),str(state["phase"])],
                            stdout=stream,stderr=subprocess.STDOUT)
                    state["child_started"] = time.monotonic()
                    return True
                child = state["child"]
                if child.poll() is None:
                    assert time.monotonic()-state["child_started"] < 15, "AT-SPI inspection timeout"
                    return True
                output = state["output"].read_text()
                assert child.returncode == 0, output
                results.append(json.loads(output))
                del state["child"]
                if state["phase"] == 0:
                    panel.search_entry.set_text("hidden")
                    panel.scope.set_selected(2)
                    panel.refresh()
                elif state["phase"] == 1:
                    dialog = MoveDialog(panel,org,panel.execute,state["hidden"])
                    dialog.picker.group.set_selected(next(i for i,g in enumerate(dialog.picker.groups) if g.id == state["long"].id))
                    panel._present_dialog(dialog)
                    state["dialog"] = dialog
                else:
                    state["dialog"].close()
                    app.quit()
                    return False
                state["phase"] += 1
                return True
            except BaseException:
                errors.append(traceback.format_exc())
                if "child" in state and state["child"].poll() is None:
                    state["child"].terminate()
                    state["child"].wait(timeout=3)
                app.quit()
                return False

        GLib.timeout_add(400,check)
        with patch("pinleaf.app.load_config",return_value=config):
            code = run(["pinleaf-accessibility-qa"])
    if errors:
        raise AssertionError("\n".join(errors))
    assert code == 0
    print(json.dumps({"atspi_phases":[{"phase":r["phase"],"node_count":len(r["nodes"])} for r in results],
                      "profile_hidden_expanded_long_name_scope_destination":"passed",
                      "orca_speech":"not tested"},indent=2))
    return 0


if __name__ == "__main__":
    if len(sys.argv)>1 and sys.argv[1] == "--inspect":
        inspect(int(sys.argv[2]),int(sys.argv[3]))
    else:
        raise SystemExit(main())
