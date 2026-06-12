from __future__ import annotations

import sqlite3


CURRENT_SCHEMA_VERSION = 1


def migrate(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_version (
          version INTEGER NOT NULL
        )
        """
    )
    existing = connection.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
    if existing is None:
        _create_v1(connection)
        connection.execute("INSERT INTO schema_version (version) VALUES (?)", (CURRENT_SCHEMA_VERSION,))
        connection.commit()
        return

    version = int(existing[0])
    if version > CURRENT_SCHEMA_VERSION:
        raise RuntimeError(
            f"Database schema version {version} is newer than supported version "
            f"{CURRENT_SCHEMA_VERSION}."
        )
    if version < CURRENT_SCHEMA_VERSION:
        raise RuntimeError(f"No migration path from schema version {version}.")


def _create_v1(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS notes (
          id TEXT PRIMARY KEY,
          content TEXT NOT NULL DEFAULT '',
          color TEXT NOT NULL,
          width INTEGER NOT NULL,
          height INTEGER NOT NULL,
          position_x INTEGER,
          position_y INTEGER,
          is_open INTEGER NOT NULL DEFAULT 1,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          deleted_at TEXT
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_notes_deleted_updated
          ON notes (deleted_at, updated_at)
        """
    )
