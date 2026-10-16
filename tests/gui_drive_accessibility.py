"""Inspect Drive controls with a separate AT-SPI client on a private QA bus."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path
from threading import Event
from unittest.mock import patch
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

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
        assert depth < 40 and len(nodes) < 2500
        states = node.get_state_set()
        nodes.append({"name": node.get_name(), "description": node.get_description(), "role": node.get_role_name(),
                      "focusable": states.contains(Atspi.StateType.FOCUSABLE)})
        for index in range(node.get_child_count()):
            walk(node.get_child_at_index(index), depth + 1)
    walk(application)
    expected = {
        0: ("Connect Google Drive…", "Connect for this session only (do not save access)", "Forget Saved Access"),
        1: ("Save Backup to Drive…", "Refresh Drive Copies", "Disconnect This Session"),
        2: ("Backup password", "Unlock", "Cancel"),
        3: ("Restore This Backup…", "Cancel Preview"),
        4: ("Restore", "Cancel"),
    }[phase]
    controls = [node for node in nodes if node["focusable"] and node["name"] in expected]
    for name in expected:
        assert any(node["name"] == name for node in controls), (name, nodes)
    if phase == 1:
        selected = [node for node in nodes if node["focusable"] and
                    (node["name"] == "Preview & Restore…" or node["name"].startswith("Preview and restore Drive backup "))]
        assert len(selected) == 1, selected
        assert selected[0]["description"].startswith("Restore preview for pinleaf-"), selected
        controls.extend(selected)
    if phase == 2:
        assert not any(node["name"].startswith("Source: Google Drive") for node in nodes)
    print(json.dumps({"phase": phase, "controls": controls}))
    Atspi.exit()


def main() -> None:
    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1")
    from gi.repository import Gio, GLib
    from pinleaf.app import run
    from pinleaf.config import AppConfig
    from pinleaf.backup_format import encode
    from pinleaf.services.drive_auth import DriveConnection
    from pinleaf.services.drive_backup import DriveDestination, UploadAttempt
    from pinleaf.storage.library_backup import read_library
    from test_drive_backup import FakeDrive
    payload = json.loads((ROOT / "specs/015-local-backup-and-google-drive/contracts/examples/valid-unprotected.pinleaf-backup").read_bytes())["payload"]
    provider = FakeDrive()
    destination = DriveDestination(provider)
    selected = destination.upload(UploadAttempt(("client", "test@example.org"), payload["created_at"], True,
                                                encode(payload, "synthetic-a11y-password")), Event())
    state, errors, results, helpers = {"phase": 0, "prepared": False}, [], [], []
    with tempfile.TemporaryDirectory(prefix="pinleaf-drive-a11y-") as directory:
        root = Path(directory)
        def check() -> bool:
            app = Gio.Application.get_default()
            state["app"] = app
            try:
                if app.backup_service.busy:
                    return True
                child = state.get("child")
                if child:
                    if child.poll() is None:
                        assert time.monotonic() - state["started"] < 12
                        return True
                    output, error = child.communicate()
                    assert child.returncode == 0, error
                    results.append(json.loads(output))
                    state["child"] = None
                    if state["phase"] == 4:
                        app.backup_window.confirmation.response("cancel")
                        app.backup_window.cancel_preview.emit("clicked")
                        assert read_library(app.store.connection) == state["original"]
                        app.quit()
                        return False
                    state["phase"] += 1
                    state["prepared"] = False
                    return True
                if not state["prepared"]:
                    if state["phase"] == 0:
                        assert app.startup_error is None
                        helpers.append(app.tray)
                        state["original"] = read_library(app.store.connection)
                        app.show_backup()
                    elif state["phase"] == 1:
                        app.backup_service.drive_auth.connection = DriveConnection("test@example.org", True)
                        app.backup_service.drive_auth.client_id = "client"
                        app.backup_service.drive = destination
                        app.backup_window._drive_status()
                        app.backup_window.refresh_drive.emit("clicked")
                    elif state["phase"] == 2:
                        app.backup_window._download_drive(selected)
                    elif state["phase"] == 3:
                        app.backup_window.password_window.password.set_text("synthetic-a11y-password")
                        app.backup_window.password_window.confirm.emit("clicked")
                    elif state["phase"] == 4:
                        app.backup_window._confirm_restore()
                        assert app.backup_window.confirmation.get_default_response() == "cancel"
                    state["prepared"] = True
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
            errors.append("Drive accessibility timed out")
            Gio.Application.get_default().quit()
            return False
        try:
            with patch("pinleaf.app.load_config", return_value=AppConfig(root, root / "notes.sqlite3")), \
                 patch("pinleaf.app.APP_ID", "dev.pinleaf.DriveA11y" + uuid4().hex):
                GLib.timeout_add(250, check)
                watchdog = GLib.timeout_add_seconds(45, timeout)
                code = run(["pinleaf-drive-a11y"])
                if not errors:
                    GLib.source_remove(watchdog)
            assert code == 0 and not errors, errors
        finally:
            child = state.get("child")
            if child and child.poll() is None:
                child.terminate()
                child.wait(timeout=3)
            app = state.get("app")
            if app and app.backup_service.thread:
                app.backup_service.thread.join(3)
            for tray in helpers:
                tray.stop()
                if tray._process is not None:
                    tray._process.wait(timeout=5)
    report = {"status": "PASS", "phases": results, "scope": "AT-SPI names, roles and focusable states; not Orca speech"}
    if path := os.environ.get("PINLEAF_QA_A11Y_REPORT"):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    if "--inspect" in sys.argv:
        inspect(int(sys.argv[2]), int(sys.argv[3]))
    else:
        main()
