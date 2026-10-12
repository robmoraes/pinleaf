"""Trusted schema reconstruction and exact logical library preservation."""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from pinleaf import __version__
from pinleaf.backup_format import BackupError, PORTABLE_SETTINGS, library_digest, validate_payload
from pinleaf.storage.migrations import migrate, validate_context, validate_data


COLUMNS = {
    "profiles": ("id", "name", "name_key", "deleted_at"),
    "groups": ("id", "profile_id", "name", "name_key", "is_shared", "deleted_at"),
    "notes": ("id", "group_id", "content", "color", "width", "height", "position_x", "position_y",
              "font_family", "font_size", "text_color", "is_open", "created_at", "updated_at", "deleted_at"),
    "profile_context": ("profile_id", "last_group_id"),
    "app_settings": ("key", "value"),
}


def read_library(connection: sqlite3.Connection) -> dict:
    """Call inside a snapshot transaction. Never use filtered/normalized models."""
    if tuple(tuple(row) for row in connection.execute("SELECT version FROM schema_version")) != ((6,),):
        raise BackupError("Only library schema 6 can be exported by this version.")
    library = {}
    for table, columns in COLUMNS.items():
        where, args = ("", ())
        if table == "app_settings":
            where, args = " WHERE key IN (?,?,?)", PORTABLE_SETTINGS
        query = f"SELECT {','.join(columns)} FROM {table}{where} ORDER BY {columns[0]}"
        library[table] = [dict(zip(columns, row)) for row in connection.execute(query, args)]
    active = connection.execute("SELECT profile_id,group_id FROM active_context WHERE singleton_id=1").fetchall()
    if len(active) != 1:
        raise BackupError("The current working context is unavailable.")
    library["active_context"] = dict(zip(("profile_id", "group_id"), active[0]))
    return library


def capture(connection: sqlite3.Connection) -> dict:
    owns_transaction = not connection.in_transaction
    if owns_transaction:
        connection.execute("BEGIN")
    try:
        library = read_library(connection)
    finally:
        if owns_transaction:
            connection.rollback()  # Read-only snapshot; never commit someone else's writes.
    return {"payload_version": 1, "backup_id": str(uuid4()),
            "created_at": datetime.now(UTC).isoformat(),
            "producer": {"app": "Pinleaf", "version": __version__},
            "library_schema_version": 6, "library": library}


def replace_rows(connection: sqlite3.Connection, library: dict) -> None:
    """Caller owns the transaction and supplies a previously validated payload."""
    if not connection.in_transaction:
        raise RuntimeError("Library replacement requires a transaction.")
    for table in ("active_context", "profile_context", "notes", "groups", "profiles", "migration_notices"):
        connection.execute(f"DELETE FROM {table}")
    connection.execute("DELETE FROM app_settings WHERE key IN (?,?,?)", PORTABLE_SETTINGS)
    for table in ("profiles", "groups", "notes", "profile_context", "app_settings"):
        columns = COLUMNS[table]
        connection.executemany(
            f"INSERT INTO {table} ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})",
            (tuple(row[key] for key in columns) for row in library[table]))
    active = library["active_context"]
    connection.execute("INSERT INTO active_context VALUES (1,?,?)", (active["profile_id"], active["group_id"]))
    validate_context(connection)
    validate_data(connection)
    if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
        raise BackupError("Restored ownership validation failed.")
    if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        raise BackupError("Restored database integrity validation failed.")
    if library_digest(read_library(connection)) != library_digest(library):
        raise BackupError("Restored values did not match the selected backup.")


def build_stage(payload: dict, path: Path) -> None:
    """Create SQLite from application-owned migrations, never input SQL/schema."""
    validate_payload(payload)
    with path.open("xb"):
        pass
    path.chmod(0o600)
    connection = sqlite3.connect(path)
    try:
        migrate(connection)
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("BEGIN IMMEDIATE")
        replace_rows(connection, payload["library"])
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()
