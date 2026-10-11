"""Reproducible snapshot restore drill using only disposable synthetic data.

Usage: /usr/bin/python3 tests/migration_recovery.py [old-git-revision]
"""
from __future__ import annotations

import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from organization_fixtures import legacy_database
from pinleaf.storage.backup import database_values
from pinleaf.storage.sqlite_store import NoteStore


revision = sys.argv[1] if len(sys.argv) > 1 else "v0.8.0"
source = subprocess.run(["git", "show", f"{revision}:pinleaf/storage/migrations.py"], check=True,
                        capture_output=True, text=True).stdout
old = {}
exec(compile(source, "old-migrations.py", "exec"), old)
old_version = old["CURRENT_SCHEMA_VERSION"]
assert old_version in (4, 5)
with tempfile.TemporaryDirectory(prefix="pinleaf-recovery-") as directory:
    root = Path(directory)
    path = root / "pinleaf.sqlite3"
    columns, original_notes = legacy_database(path, 4)
    if old_version == 5:
        with sqlite3.connect(path) as connection:
            old["_migrate_v4_to_v5"](connection)
            connection.execute("UPDATE schema_version SET version=5")
    with sqlite3.connect(path) as connection:
        original = database_values(connection)
    store = NoteStore(path)
    current_version = store.connection.execute("SELECT version FROM schema_version").fetchone()[0]
    store.close()
    with sqlite3.connect(path) as connection:
        upgraded = database_values(connection)
        try:
            old["migrate"](connection)
        except RuntimeError:
            pass
        else:
            raise AssertionError("Old binary accepted newer schema")
        assert database_values(connection) == upgraded
    # Abrupt termination retains a real WAL recovery set containing newer work.
    child = '''import os,sys
from pinleaf.storage.sqlite_store import NoteStore
from pinleaf.services.note_service import NoteService
store=NoteStore(sys.argv[1])
store.connection.execute("PRAGMA journal_mode=WAL")
NoteService(store).create_note()
os._exit(17)
'''
    assert subprocess.run([sys.executable, "-c", child, str(path)]).returncode == 17
    assert Path(str(path) + "-wal").exists()
    recovery = root / "newer-recovery"
    recovery.mkdir(mode=0o700)
    preserved = []
    for candidate in [path, *[Path(str(path) + suffix) for suffix in ("-wal", "-shm", "-journal")]]:
        if candidate.exists():
            shutil.move(candidate, recovery / candidate.name)
            preserved.append(candidate.name)
    snapshot = next((root / "backups").glob("*.sqlite3"))
    shutil.copy2(snapshot, path)
    with sqlite3.connect(path) as connection:
        old["migrate"](connection)
        assert connection.execute("SELECT version FROM schema_version").fetchone()[0] == old_version
        assert database_values(connection) == original
        assert tuple(connection.execute(f"SELECT {','.join(columns)} FROM notes ORDER BY id")) == original_notes
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    with sqlite3.connect(recovery / path.name) as connection:
        assert connection.execute("SELECT version FROM schema_version").fetchone()[0] == current_version
        assert connection.execute("SELECT COUNT(*) FROM notes").fetchone()[0] == len(original_notes) + 1
    print(f"PASS: schema-{old_version} reader {revision} rejects v{current_version} without mutation")
    print(f"PASS: snapshot restored {len(original_notes)} exact rows; newer work preserved in recovery set: {', '.join(preserved)}")
