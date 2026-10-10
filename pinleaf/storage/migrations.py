from __future__ import annotations

import sqlite3
from uuid import uuid4

from pinleaf.organization import initial_profile_name, name_key
from pinleaf.storage.backup import create_snapshot, database_values


CURRENT_SCHEMA_VERSION = 5


def migrate(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA foreign_keys = ON")
    tables = {row[0] for row in connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )}
    version = 0
    if tables:
        if "schema_version" not in tables:
            raise RuntimeError("Unversioned database: storage was not changed.")
        rows = connection.execute("SELECT version FROM schema_version").fetchall()
        if len(rows) != 1 or not isinstance(rows[0][0], int) or rows[0][0] < 1:
            raise RuntimeError("Invalid database schema version: storage was not changed.")
        version = rows[0][0]
    if version > CURRENT_SCHEMA_VERSION:
        raise RuntimeError(
            f"Database schema version {version} is newer than supported version "
            f"{CURRENT_SCHEMA_VERSION}."
        )
    if version == CURRENT_SCHEMA_VERSION:
        validate_data(connection)
        return
    if version:
        _validate_legacy(connection, version, tables)
    snapshot = create_snapshot(connection, version) if version else None
    try:
        connection.execute("BEGIN IMMEDIATE")
        if snapshot is not None and database_values(connection) != database_values(snapshot.connection):
            raise RuntimeError("The library changed during backup. Retry the upgrade.")
        original_columns = [row[1] for row in connection.execute("PRAGMA table_info(notes)")]
        original_notes = _note_values(connection, original_columns) if version else ()
        original_settings = tuple(tuple(row) for row in connection.execute(
            "SELECT key,value FROM app_settings ORDER BY key")) if version >= 3 else ()
        if not version:
            connection.execute("CREATE TABLE schema_version (version INTEGER NOT NULL)")
            _create_v1(connection)
        if version < 2:
            _migrate_v1_to_v2(connection)
        if version < 3:
            _migrate_v2_to_v3(connection)
        if version < 4:
            _migrate_v3_to_v4(connection)
        _migrate_v4_to_v5(connection)
        if version and original_notes != _note_values(connection, original_columns):
            raise RuntimeError("Note preservation validation failed; upgrade rolled back.")
        if original_settings != tuple(tuple(row) for row in connection.execute("SELECT key,value FROM app_settings ORDER BY key")):
            raise RuntimeError("Settings preservation validation failed; upgrade rolled back.")
        validate_data(connection)
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("Database integrity validation failed; upgrade rolled back.")
        if version:
            connection.execute("UPDATE schema_version SET version=?", (CURRENT_SCHEMA_VERSION,))
        else:
            connection.execute("INSERT INTO schema_version VALUES (?)", (CURRENT_SCHEMA_VERSION,))
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
    finally:
        if snapshot is not None:
            snapshot.close()


def _note_values(connection: sqlite3.Connection, columns: list[str]) -> tuple:
    names = ", ".join('"' + column.replace('"', '""') + '"' for column in columns)
    return tuple(tuple(row) for row in connection.execute(f"SELECT {names} FROM notes ORDER BY id"))


def _validate_legacy(connection: sqlite3.Connection, version: int, tables: set[str]) -> None:
    expected = {"schema_version", "notes"}
    if version >= 3:
        expected.add("app_settings")
    if tables != expected:
        raise RuntimeError("Unexpected legacy database tables; storage was not changed.")
    required = {"id", "content", "color", "width", "height", "position_x", "position_y",
                "is_open", "created_at", "updated_at", "deleted_at"}
    if version >= 2:
        required.add("font_family")
    if version >= 4:
        required.update({"font_size", "text_color"})
    columns = {row[1] for row in connection.execute("PRAGMA table_info(notes)")}
    if columns != required:
        raise RuntimeError("Unexpected legacy note columns; storage was not changed.")
    if version >= 3 and {row[1] for row in connection.execute("PRAGMA table_info(app_settings)")} != {"key", "value"}:
        raise RuntimeError("Unexpected legacy settings columns; storage was not changed.")
    objects = connection.execute("""SELECT type,name FROM sqlite_master
        WHERE type IN ('view','trigger','index') AND name NOT LIKE 'sqlite_%'""").fetchall()
    if any(kind != "index" or name != "idx_notes_deleted_updated" for kind, name in objects):
        raise RuntimeError("Unexpected legacy database objects; storage was not changed.")


def validate_data(connection: sqlite3.Connection) -> None:
    if connection.execute("SELECT COUNT(*) FROM profiles WHERE deleted_at IS NULL").fetchone()[0] == 0:
        raise RuntimeError("The library has no live profile.")
    invalid = connection.execute("""
        SELECT p.id FROM profiles p LEFT JOIN groups g
          ON g.profile_id=p.id AND g.is_general=1 AND g.deleted_at IS NULL
        WHERE p.deleted_at IS NULL GROUP BY p.id HAVING COUNT(g.id) != 1
    """).fetchone()
    orphan = connection.execute("""
        SELECT n.id FROM notes n LEFT JOIN groups g ON n.group_id=g.id
        LEFT JOIN profiles p ON g.profile_id=p.id
        WHERE g.id IS NULL OR p.id IS NULL OR
          (n.deleted_at IS NULL AND (g.deleted_at IS NOT NULL OR p.deleted_at IS NOT NULL))
        LIMIT 1
    """).fetchone()
    if invalid is not None or orphan is not None:
        raise RuntimeError("Organization integrity validation failed; notes were not changed.")


def _migrate_v4_to_v5(connection: sqlite3.Connection) -> None:
    statements = [
        """CREATE TABLE profiles (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, name_key TEXT NOT NULL, deleted_at TEXT)""",
        "CREATE UNIQUE INDEX idx_profiles_live_name ON profiles(name_key) WHERE deleted_at IS NULL",
        """CREATE TABLE groups (
            id TEXT PRIMARY KEY, profile_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE RESTRICT,
            name TEXT NOT NULL, name_key TEXT NOT NULL, is_general INTEGER NOT NULL CHECK(is_general IN (0,1)),
            deleted_at TEXT, UNIQUE(id, profile_id))""",
        "CREATE UNIQUE INDEX idx_groups_live_name ON groups(profile_id,name_key) WHERE deleted_at IS NULL",
        "CREATE UNIQUE INDEX idx_groups_general ON groups(profile_id) WHERE is_general=1 AND deleted_at IS NULL",
        "CREATE INDEX idx_groups_profile ON groups(profile_id)",
        """CREATE TABLE profile_context (
            profile_id TEXT PRIMARY KEY REFERENCES profiles(id) ON DELETE RESTRICT,
            last_group_id TEXT NOT NULL,
            FOREIGN KEY(last_group_id,profile_id) REFERENCES groups(id,profile_id) ON DELETE RESTRICT)""",
        """CREATE TABLE active_context (
            singleton_id INTEGER PRIMARY KEY CHECK(singleton_id=1),
            group_id TEXT NOT NULL REFERENCES groups(id) ON DELETE RESTRICT)""",
    ]
    for statement in statements:
        connection.execute(statement)
    profile_id, group_id = str(uuid4()), str(uuid4())
    name = initial_profile_name()
    connection.execute("INSERT INTO profiles(id,name,name_key) VALUES (?,?,?)", (profile_id, name, name_key(name)))
    connection.execute("INSERT INTO groups(id,profile_id,name,name_key,is_general) VALUES (?,?,'General','general',1)",
                       (group_id, profile_id))
    connection.execute("INSERT INTO profile_context VALUES (?,?)", (profile_id, group_id))
    connection.execute("INSERT INTO active_context VALUES (1,?)", (group_id,))
    connection.execute("""CREATE TABLE notes_new (
        id TEXT PRIMARY KEY, content TEXT NOT NULL DEFAULT '', color TEXT NOT NULL,
        width INTEGER NOT NULL, height INTEGER NOT NULL, position_x INTEGER, position_y INTEGER,
        is_open INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
        deleted_at TEXT, font_family TEXT, font_size INTEGER, text_color TEXT,
        group_id TEXT NOT NULL REFERENCES groups(id) ON DELETE RESTRICT)""")
    columns = "id,content,color,width,height,position_x,position_y,is_open,created_at,updated_at,deleted_at,font_family,font_size,text_color"
    connection.execute(f"INSERT INTO notes_new({columns},group_id) SELECT {columns},? FROM notes", (group_id,))
    connection.execute("DROP TABLE notes")
    connection.execute("ALTER TABLE notes_new RENAME TO notes")
    connection.execute("CREATE INDEX idx_notes_deleted_updated ON notes(deleted_at,updated_at)")
    connection.execute("CREATE INDEX idx_notes_group_created ON notes(group_id,created_at DESC,id DESC) WHERE deleted_at IS NULL")
    if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
        raise RuntimeError("Database foreign-key validation failed; upgrade rolled back.")


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


def _migrate_v3_to_v4(connection: sqlite3.Connection) -> None:
    columns = {
        row[1]
        for row in connection.execute("PRAGMA table_info(notes)").fetchall()
    }
    if "font_size" not in columns:
        connection.execute("ALTER TABLE notes ADD COLUMN font_size INTEGER")
    if "text_color" not in columns:
        connection.execute("ALTER TABLE notes ADD COLUMN text_color TEXT")
