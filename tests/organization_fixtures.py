from __future__ import annotations

import sqlite3
from pathlib import Path


def legacy_database(path: Path, version: int) -> tuple[list[str], tuple]:
    connection = sqlite3.connect(path)
    try:
        connection.execute("CREATE TABLE schema_version(version INTEGER NOT NULL)")
        connection.execute("INSERT INTO schema_version VALUES (?)", (version,))
        columns = """id TEXT PRIMARY KEY, content TEXT NOT NULL, color TEXT NOT NULL,
            width INTEGER NOT NULL, height INTEGER NOT NULL, position_x INTEGER, position_y INTEGER,
            is_open INTEGER NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, deleted_at TEXT"""
        if version >= 2:
            columns += ",font_family TEXT"
        if version >= 4:
            columns += ",font_size INTEGER,text_color TEXT"
        connection.execute(f"CREATE TABLE notes({columns})")
        for index in range(3):
            row = [f"legacy-{index}", f"Café {index}\n完整文本", ("yellow", "blue", "pink")[index],
                   320 + index, 280 + index, None if index == 0 else index, None if index == 0 else index * 2,
                   int(index != 1), f"2026-10-10T12:0{index}:00+00:00", "2026-10-10T13:00:00+00:00",
                   "2026-10-10T14:00:00+00:00" if index == 2 else None]
            if version >= 2:
                row.append("Kavoon" if index else None)
            if version >= 4:
                row.extend([None if index == 0 else 24, None if index == 0 else "#123ABC"])
            connection.execute(f"INSERT INTO notes VALUES ({','.join('?' for _ in row)})", row)
        if version >= 2:
            connection.execute("CREATE INDEX idx_notes_deleted_updated ON notes(deleted_at,updated_at)")
        if version >= 3:
            connection.execute("CREATE TABLE app_settings(key TEXT PRIMARY KEY,value TEXT)")
            connection.execute("INSERT INTO app_settings VALUES ('default_font_family','Kavoon')")
        connection.commit()
        names = [row[1] for row in connection.execute("PRAGMA table_info(notes)")]
        values = tuple(tuple(row) for row in connection.execute("SELECT * FROM notes ORDER BY id"))
        return names, values
    finally:
        connection.close()
