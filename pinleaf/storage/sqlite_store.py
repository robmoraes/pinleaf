from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from collections.abc import Iterator
from pathlib import Path

from pinleaf.appearance import (
    TextAppearance,
    normalize_font_family,
    normalize_selectable_text_appearance,
    normalize_text_appearance,
)
from pinleaf.models import Note, NoteColor, utc_now_iso, validate_color
from pinleaf.storage.migrations import migrate


DEFAULT_FONT_SETTING = "default_font_family"
DEFAULT_FONT_SIZE_SETTING = "default_font_size"
DEFAULT_TEXT_COLOR_SETTING = "default_text_color"


class NoteStore:
    def __init__(self, database_path: Path | str) -> None:
        self.database_path = Path(database_path)
        self.connection = sqlite3.connect(self.database_path)
        self.connection.row_factory = sqlite3.Row
        self._transaction_depth = 0
        try:
            migrate(self.connection)
            from pinleaf.storage.organization_store import OrganizationStore
            self.organization = OrganizationStore(self)
            self.context_recovered = self.organization.repair_context()
        except BaseException:
            self.connection.close()
            raise

    @contextmanager
    def transaction(self) -> Iterator[None]:
        depth = self._transaction_depth
        self.connection.execute("BEGIN IMMEDIATE" if depth == 0 else f"SAVEPOINT nested_{depth}")
        self._transaction_depth += 1
        try:
            yield
            if depth == 0:
                self.connection.commit()
            else:
                self.connection.execute(f"RELEASE SAVEPOINT nested_{depth}")
        except BaseException:
            if depth == 0:
                self.connection.rollback()
            else:
                self.connection.execute(f"ROLLBACK TO SAVEPOINT nested_{depth}")
                self.connection.execute(f"RELEASE SAVEPOINT nested_{depth}")
            raise
        finally:
            self._transaction_depth = depth

    def _commit(self) -> None:
        if self._transaction_depth == 0:
            try:
                self.connection.commit()
            except BaseException:
                self.connection.rollback()
                raise

    def close(self) -> None:
        self.connection.close()

    def create(self, note: Note) -> Note:
        self.organization.get_group(note.group_id)
        self.connection.execute(
            """
            INSERT INTO notes (
              id, content, color, width, height, position_x, position_y,
              font_family, font_size, text_color, is_open, created_at,
              updated_at, deleted_at, group_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            _to_row_values(note),
        )
        self._commit()
        return note

    def get(self, note_id: str) -> Note | None:
        row = self.connection.execute(
            """SELECT n.* FROM notes n JOIN groups g ON g.id=n.group_id
                JOIN profiles p ON p.id=g.profile_id WHERE n.id=? AND n.deleted_at IS NULL
                AND g.deleted_at IS NULL AND p.deleted_at IS NULL""",
            (note_id,),
        ).fetchone()
        return _from_row(row) if row is not None else None

    def list_notes(self, *, group_id: str | None = None, profile_id: str | None = None) -> list[Note]:
        sql = """SELECT n.* FROM notes n JOIN groups g ON g.id=n.group_id
            JOIN profiles p ON p.id=g.profile_id
            WHERE n.deleted_at IS NULL AND g.deleted_at IS NULL AND p.deleted_at IS NULL"""
        args = []
        if group_id is not None:
            sql += " AND n.group_id=?"
            args.append(group_id)
        if profile_id is not None:
            sql += " AND g.profile_id=?"
            args.append(profile_id)
        rows = self.connection.execute(sql + " ORDER BY n.created_at DESC,n.id DESC", args).fetchall()
        return [_from_row(row) for row in rows]

    def save_context_geometry(self, note_id: str, *, width: int, height: int,
                              position_x: int | None, position_y: int | None) -> None:
        self.connection.execute("""UPDATE notes SET width=?,height=?,position_x=?,position_y=?
            WHERE id=? AND deleted_at IS NULL""", (width, height, position_x, position_y, note_id))
        self._commit()

    def get_default_font_family(self) -> str | None:
        return self.get_default_text_appearance().font_family

    def set_default_font_family(self, font_family: str | None) -> str | None:
        appearance = self.set_default_text_appearance(font_family=font_family)
        return appearance.font_family

    def get_default_text_appearance(self) -> TextAppearance:
        values = self._get_settings(
            DEFAULT_FONT_SETTING,
            DEFAULT_FONT_SIZE_SETTING,
            DEFAULT_TEXT_COLOR_SETTING,
        )
        return normalize_selectable_text_appearance(
            font_family=values.get(DEFAULT_FONT_SETTING),
            font_size=values.get(DEFAULT_FONT_SIZE_SETTING),
            text_color=values.get(DEFAULT_TEXT_COLOR_SETTING),
        )

    def set_default_text_appearance(
        self,
        *,
        font_family: str | None,
        font_size: int | str | None = None,
        text_color: str | None = None,
    ) -> TextAppearance:
        current = self.get_default_text_appearance()
        appearance = normalize_selectable_text_appearance(
            font_family=font_family,
            font_size=font_size if font_size is not None else current.font_size,
            text_color=text_color if text_color is not None else current.text_color,
        )
        self.connection.executemany(
            """
            INSERT INTO app_settings (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (
                (DEFAULT_FONT_SETTING, appearance.font_family),
                (DEFAULT_FONT_SIZE_SETTING, str(appearance.font_size)),
                (DEFAULT_TEXT_COLOR_SETTING, appearance.text_color),
            ),
        )
        self._commit()
        return appearance

    def _get_settings(self, *keys: str) -> dict[str, str | None]:
        placeholders = ", ".join("?" for _ in keys)
        rows = self.connection.execute(
            f"SELECT key, value FROM app_settings WHERE key IN ({placeholders})",
            keys,
        ).fetchall()
        return {row["key"]: row["value"] for row in rows}

    def update_content(self, note_id: str, content: str, now: str | None = None) -> Note:
        timestamp = now or utc_now_iso()
        self.connection.execute(
            """
            UPDATE notes
            SET content = ?, updated_at = ?
            WHERE id = ? AND deleted_at IS NULL
            """,
            (content, timestamp, note_id),
        )
        self._commit()
        return self._require(note_id)

    def update_color(
        self,
        note_id: str,
        color: str | NoteColor,
        now: str | None = None,
    ) -> Note:
        timestamp = now or utc_now_iso()
        validated = validate_color(color)
        self.connection.execute(
            """
            UPDATE notes
            SET color = ?, updated_at = ?
            WHERE id = ? AND deleted_at IS NULL
            """,
            (validated.value, timestamp, note_id),
        )
        self._commit()
        return self._require(note_id)

    def update_font_family(
        self,
        note_id: str,
        font_family: str | None,
        now: str | None = None,
    ) -> Note:
        timestamp = now or utc_now_iso()
        normalized = normalize_font_family(font_family)
        self.connection.execute(
            """
            UPDATE notes
            SET font_family = ?, updated_at = ?
            WHERE id = ? AND deleted_at IS NULL
            """,
            (normalized, timestamp, note_id),
        )
        self._commit()
        return self._require(note_id)

    def update_text_appearance(
        self,
        note_id: str,
        *,
        font_family: str | None,
        font_size: int | str | None,
        text_color: str | None,
        now: str | None = None,
    ) -> Note:
        timestamp = now or utc_now_iso()
        appearance = normalize_text_appearance(
            font_family=font_family,
            font_size=font_size,
            text_color=text_color,
        )
        self.connection.execute(
            """
            UPDATE notes
            SET font_family = ?, font_size = ?, text_color = ?, updated_at = ?
            WHERE id = ? AND deleted_at IS NULL
            """,
            (
                appearance.font_family,
                appearance.font_size,
                appearance.text_color,
                timestamp,
                note_id,
            ),
        )
        self._commit()
        return self._require(note_id)

    def update_window_state(
        self,
        note_id: str,
        *,
        width: int,
        height: int,
        position_x: int | None,
        position_y: int | None,
        is_open: bool,
        now: str | None = None,
    ) -> Note:
        timestamp = now or utc_now_iso()
        self.connection.execute(
            """
            UPDATE notes
            SET width = ?, height = ?, position_x = ?, position_y = ?,
                is_open = ?, updated_at = ?
            WHERE id = ? AND deleted_at IS NULL
            """,
            (width, height, position_x, position_y, int(is_open), timestamp, note_id),
        )
        self._commit()
        return self._require(note_id)

    def soft_delete(self, note_id: str, now: str | None = None) -> None:
        timestamp = now or utc_now_iso()
        self.connection.execute(
            """
            UPDATE notes
            SET deleted_at = ?, updated_at = ?
            WHERE id = ? AND deleted_at IS NULL
            """,
            (timestamp, timestamp, note_id),
        )
        self._commit()

    def _require(self, note_id: str) -> Note:
        note = self.get(note_id)
        if note is None:
            raise KeyError(f"Note {note_id!r} does not exist.")
        return note


def _to_row_values(note: Note) -> tuple[object, ...]:
    return (
        note.id,
        note.content,
        note.color.value,
        note.width,
        note.height,
        note.position_x,
        note.position_y,
        normalize_font_family(note.font_family),
        note.font_size,
        note.text_color,
        int(note.is_open),
        note.created_at,
        note.updated_at,
        note.deleted_at,
        note.group_id,
    )


def _from_row(row: sqlite3.Row) -> Note:
    appearance = normalize_text_appearance(
        font_family=row["font_family"],
        font_size=row["font_size"],
        text_color=row["text_color"],
    )
    return Note(
        id=row["id"],
        group_id=row["group_id"],
        content=row["content"],
        color=validate_color(row["color"]),
        width=row["width"],
        height=row["height"],
        position_x=row["position_x"],
        position_y=row["position_y"],
        font_family=appearance.font_family,
        font_size=appearance.font_size,
        text_color=appearance.text_color,
        is_open=bool(row["is_open"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        deleted_at=row["deleted_at"],
    )
