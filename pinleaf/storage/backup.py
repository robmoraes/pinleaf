from __future__ import annotations

import os
import sqlite3
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass
class Snapshot:
    connection: sqlite3.Connection
    path: Path | None

    def close(self) -> None:
        self.connection.close()


def database_values(connection: sqlite3.Connection) -> tuple:
    """Compare logical snapshots without writing note values to logs/files."""
    schema = tuple(tuple(row) for row in connection.execute(
        "SELECT name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY name"
    ))
    tables = [row[0] for row in connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    )]
    values = []
    for table in tables:
        quoted = '"' + table.replace('"', '""') + '"'
        values.append((table, tuple(tuple(row) for row in connection.execute(
            f"SELECT * FROM {quoted} ORDER BY rowid"
        ))))
    return schema, tuple(values)


def create_snapshot(connection: sqlite3.Connection, version: int) -> Snapshot:
    filename = connection.execute("PRAGMA database_list").fetchone()[2]
    path = None
    if filename:
        directory = Path(filename).parent / "backups"
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        directory.chmod(0o700)
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        descriptor, name = tempfile.mkstemp(
            prefix=f"pinleaf-schema-v{version}-{stamp}-", suffix=".sqlite3", dir=directory
        )
        os.close(descriptor)
        path = Path(name)
        path.chmod(0o600)
    target = sqlite3.connect(str(path) if path else ":memory:")
    try:
        connection.backup(target)
        if target.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("The pre-upgrade backup failed its integrity check.")
        rows = target.execute("SELECT version FROM schema_version").fetchall()
        if len(rows) != 1 or rows[0][0] != version:
            raise RuntimeError("The pre-upgrade backup has an unexpected schema version.")
        return Snapshot(target, path)
    except BaseException:
        target.close()
        raise
