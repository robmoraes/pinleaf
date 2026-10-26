"""Inspect backup controls through real AT-SPI on an isolated bus, not Orca speech."""
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


def inspect(pid: int, phase: int) -> None:
    gi.require_version("Atspi", "2.0")
    from gi.repository import Atspi
    Atspi.init()
    desktop = Atspi.get_desktop(0)
    application = next(child for index in range(desktop.get_child_count())
                       if (child := desktop.get_child_at_index(index)).get_process_id() == pid)
    nodes = []
    def walk(node, depth=0):
        assert depth < 40 and len(nodes) < 2000
        nodes.append({"name": node.get_name(), "role": node.get_role_name(),
                      "focusable": node.get_state_set().contains(Atspi.StateType.FOCUSABLE)})
        for index in range(node.get_child_count()):
            walk(node.get_child_at_index(index), depth + 1)
    walk(application)
    expected = ("Create Backup…", "Restore Backup…") if phase == 0 else (
        "Protect with password", "Backup password", "Confirm backup password", "Choose Location…", "Cancel")
    for name in expected:
        assert any(node["name"] == name and node["focusable"] for node in nodes), (name, nodes)
    print(json.dumps({"phase": phase, "controls": [node for node in nodes if node["name"] in expected]}))
    Atspi.exit()


def main() -> None:
    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1")
    from gi.repository import Gio, GLib
    from pinleaf.app import run
    from pinleaf.config import AppConfig
    state, errors, results, helpers = {}, [], [], []
    with tempfile.TemporaryDirectory(prefix="pinleaf-backup-a11y-") as directory:
        root = Path(directory)
        def check() -> bool:
            app = Gio.Application.get_default()
            try:
                child = state.get("child")
                if child:
                    if child.poll() is None:
                        assert time.monotonic() - state["started"] < 12
                        return True
                    output, error = child.communicate()
                    assert child.returncode == 0, error
                    results.append(json.loads(output))
                    state["child"] = None
                    if state["phase"] == 1:
                        app.quit()
                        return False
                    app.backup_window.create_button.emit("clicked")
                    app.backup_window.password_window.protection.set_active(True)
                    state["phase"] = 1
                    return True
                if "phase" not in state:
                    assert app.startup_error is None
                    helpers.append(app.tray)
                    app.show_backup()
                    state["phase"] = 0
                    return True
                state["started"] = time.monotonic()
                state["child"] = subprocess.Popen([sys.executable, __file__, "--inspect", str(os.getpid()), str(state["phase"])],
                                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                return True
            except BaseException:
                errors.append(traceback.format_exc())
                app.quit()
                return False
        def timeout() -> bool:
            errors.append("Backup accessibility timed out")
            Gio.Application.get_default().quit()
            return False
        try:
            with patch("pinleaf.app.load_config", return_value=AppConfig(root, root / "notes.sqlite3")):
                GLib.timeout_add(300, check)
                watchdog = GLib.timeout_add_seconds(30, timeout)
                code = run(["pinleaf-backup-a11y"])
                if not errors:
                    GLib.source_remove(watchdog)
            assert code == 0 and not errors, errors
        finally:
            if state.get("child") and state["child"].poll() is None:
                state["child"].terminate()
                state["child"].wait(timeout=3)
            for tray in helpers:
                tray.stop()
                if tray._process is not None:
                    tray._process.wait(timeout=5)
    print(json.dumps({"status": "PASS", "phases": results}, indent=2))


if __name__ == "__main__":
    if "--inspect" in sys.argv:
        inspect(int(sys.argv[2]), int(sys.argv[3]))
    else:
        main()
