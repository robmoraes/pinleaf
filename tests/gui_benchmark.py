"""Synthetic local GTK/storage timings; use tests/gui_session.py for isolation."""
from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
import statistics
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, Gtk

from organization_fixtures import legacy_database
from pinleaf.app import run
from pinleaf.models import Note, SearchScope
from pinleaf.services.context_controller import ContextController
from pinleaf.services.note_service import NoteService
from pinleaf.storage.sqlite_store import NoteStore
from pinleaf.ui.main_window import MainWindow
from pinleaf.ui.note_window import NoteWindow


def measure(callback, repeats=5):
    values = []
    for _ in range(repeats):
        start = time.perf_counter()
        callback()
        values.append((time.perf_counter() - start) * 1000)
    return {"median_ms": round(statistics.median(values), 2), "max_ms": round(max(values), 2)}


results = {}
Adw.init()
with tempfile.TemporaryDirectory(prefix="pinleaf-benchmark-") as directory:
    path = Path(directory) / "notes.sqlite3"
    store = NoteStore(path)
    service = NoteService(store)
    org = service.organization
    initial = org.context
    groups = [org.repository.shared(initial.profile.id)]
    with store.transaction():
        for profile_index in range(3):
            if profile_index:
                org.create_profile(f"Profile {profile_index}")
                groups.append(org.repository.shared(org.context.profile.id))
            for index in range(9):
                groups.append(org.create_group(f"Project {index:02d}"))
        for index in range(1000):
            group = groups[index % len(groups)]
            note = Note.new(f"benchmark-{index:04d}", group_id=group.id,
                            now=(datetime(2026, 10, 10, 12, tzinfo=UTC) + timedelta(minutes=index)).isoformat())
            store.create(replace(note, content=f"Café orçamento project {index} ".ljust(128, "."), is_open=index % 4 != 0))
        org.activate_group(groups[1].id)
    results["global_search_1000"] = measure(lambda: service.list_notes("cafe", scope=SearchScope.ALL_PROFILES))
    app = Adw.Application(application_id="dev.pinleaf.Benchmark", flags=Gio.ApplicationFlags.NON_UNIQUE)
    app.register(None)
    panel = MainWindow(application=app, note_service=service, on_create_note=lambda: None,
                       on_open_note=lambda _: None, on_delete_note=lambda _: None)
    panel.refresh()
    def render_search():
        panel._render_signature = None
        panel.search_entry.set_text("cafe")
        panel.scope.set_selected(2)
        panel.refresh()
    results["global_search_panel_1000"] = measure(render_search, repeats=3)
    windows = {}
    controller = ContextController(service, windows, lambda note: NoteWindow(
        application=app, note=note, note_service=service, on_closed=lambda _: None, on_changed=lambda: None))
    controller.restore()
    target = groups[2]
    shared_editors = {key: editor for key, editor in windows.items()
                      if service.get_note(key).group_id == groups[0].id}
    visible_counts = {len(windows)}
    def cycle():
        destination = target if org.context.group_id == groups[1].id else groups[1]
        controller.execute(lambda: org.activate_group(destination.id))
        assert all(windows[key] is editor for key, editor in shared_editors.items())
        visible_counts.add(len(windows))
    results["context_shared_plus_project_native_editors"] = measure(cycle)
    results["fixture"] = {"notes":1000,"groups":30,"shared_groups":3,"ordinary_groups":27,
                          "profiles":3,"note_code_points":128,"hidden_notes":250,
                          "reused_shared_editors":len(shared_editors),"visible_editors_per_context":sorted(visible_counts)}
    for window in windows.values():
        window.dispose_for_context()
    panel.destroy()
    store.close()
    migration_path = Path(directory) / "legacy.sqlite3"
    legacy_database(migration_path, 4)
    def upgrade():
        upgraded = NoteStore(migration_path)
        upgraded.close()
    results["migration_v4_3_notes_with_backup"] = measure(upgrade, repeats=1)

# Include actual application startup/restore for 100 open short notes.
with tempfile.TemporaryDirectory(prefix="pinleaf-startup-") as directory:
    from unittest.mock import patch
    from pinleaf.config import AppConfig
    path = Path(directory) / "notes.sqlite3"
    store = NoteStore(path)
    service = NoteService(store)
    with store.transaction():
        for index in range(100):
            note = service.create_note()
            service.update_content(note.id, f"Short note {index}")
    store.close()
    start = time.perf_counter()
    failures = []
    helpers = []
    def activated():
        application = next(window.get_application() for window in Gtk.Window.list_toplevels()
                           if isinstance(window, MainWindow) and hasattr(window.get_application(), "note_windows"))
        helpers.append(application.tray)
        try:
            assert len(application.note_windows) == 100
            results["startup_100_open_notes_ms"] = round((time.perf_counter() - start) * 1000, 2)
        except BaseException as exc:
            failures.append(exc)
        application.quit()
        return False
    GLib.idle_add(activated)
    with patch("pinleaf.app.load_config", return_value=AppConfig(Path(directory), path)):
        assert run(["pinleaf-benchmark"]) == 0
    for tray in helpers:
        if tray._process is not None:
            tray._process.wait(timeout=5)
    if failures:
        raise failures[0]
print(json.dumps(results, indent=2))
