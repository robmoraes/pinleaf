from __future__ import annotations

import sqlite3


CURRENT_SCHEMA_VERSION = 3


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
        _migrate_v1_to_v2(connection)
        _migrate_v2_to_v3(connection)
        connection.execute("INSERT INTO schema_version (version) VALUES (?)", (CURRENT_SCHEMA_VERSION,))
        connection.commit()
        return

    version = int(existing[0])
    if version > CURRENT_SCHEMA_VERSION:
        raise RuntimeError(
            f"Database schema version {version} is newer than supported version "
            f"{CURRENT_SCHEMA_VERSION}."
        )
    if version < 2:
        _migrate_v1_to_v2(connection)
        version = 2
    if version < 3:
        _migrate_v2_to_v3(connection)
        version = 3
    if version < CURRENT_SCHEMA_VERSION:
        raise RuntimeError(f"No migration path from schema version {version}.")
    connection.execute("UPDATE schema_version SET version = ?", (CURRENT_SCHEMA_VERSION,))
    connection.commit()


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


def _migrate_v1_to_v2(connection: sqlite3.Connection) -> None:
    columns = {
        row[1]
        for row in connection.execute("PRAGMA table_info(notes)").fetchall()
    }
    if "font_family" not in columns:
        connection.execute("ALTER TABLE notes ADD COLUMN font_family TEXT")
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_notes_deleted_updated
          ON notes (deleted_at, updated_at)
        """
    )


def _migrate_v2_to_v3(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS app_settings (
          key TEXT PRIMARY KEY,
          value TEXT
        )
        """
    )
