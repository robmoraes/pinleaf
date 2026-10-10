"""Measure startup against 100 synthetic notes in a fresh process."""
from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gio, GLib
from pinleaf.app import run
from pinleaf.config import AppConfig
from pinleaf.models import Note
from pinleaf.services.note_service import NoteService
from pinleaf.storage.sqlite_store import NoteStore


open_count = int(sys.argv[1]) if len(sys.argv) > 1 else 75
if not 0 <= open_count <= 100:
    raise ValueError("Open count must be between 0 and 100")
with tempfile.TemporaryDirectory(prefix="pinleaf-startup-") as directory:
    path = Path(directory) / "notes.sqlite3"
    store = NoteStore(path)
    service = NoteService(store)
    with store.transaction():
        for index in range(100):
            timestamp = (datetime(2026, 10, 10, 12, tzinfo=UTC) + timedelta(minutes=index)).isoformat()
            note = Note.new(f"startup-{index:03d}", group_id=service.organization.context.group.id, now=timestamp)
            visible = index % 4 != 0 if open_count == 75 else index < open_count
            store.create(replace(note, content=f"Short note {index} ".ljust(128, "."), is_open=visible))
    store.close()
    start = time.perf_counter()
    result = {}
    errors = []
    def activated():
        application = Gio.Application.get_default()
        try:
            assert len(application.note_windows) == open_count
            assert all(window.get_visible() and window.get_mapped()
                       for window in application.note_windows.values())
            result.update(notes=100, note_code_points=128, open_notes=open_count,
                          startup_ms=round((time.perf_counter() - start) * 1000, 2))
        except BaseException as exc:
            errors.append(exc)
        application.quit()
        return False
    GLib.idle_add(activated)
    with patch("pinleaf.app.load_config", return_value=AppConfig(Path(directory), path)):
        assert run(["pinleaf-startup-benchmark"]) == 0
    if errors:
        raise errors[0]
    print(json.dumps(result))
