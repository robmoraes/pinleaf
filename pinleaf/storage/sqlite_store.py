from __future__ import annotations

import sqlite3
from pathlib import Path

from pinleaf.models import Note, NoteColor, utc_now_iso, validate_color
from pinleaf.storage.migrations import migrate


class NoteStore:
    def __init__(self, database_path: Path | str) -> None:
        self.database_path = Path(database_path)
        self.connection = sqlite3.connect(self.database_path)
        self.connection.row_factory = sqlite3.Row
        migrate(self.connection)

    def close(self) -> None:
        self.connection.close()

    def create(self, note: Note) -> Note:
        self.connection.execute(
            """
            INSERT INTO notes (
              id, content, color, width, height, position_x, position_y,
              is_open, created_at, updated_at, deleted_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            _to_row_values(note),
        )
        self.connection.commit()
        return note

    def get(self, note_id: str) -> Note | None:
        row = self.connection.execute(
            "SELECT * FROM notes WHERE id = ? AND deleted_at IS NULL",
            (note_id,),
        ).fetchone()
        return _from_row(row) if row is not None else None

    def list_notes(self) -> list[Note]:
        rows = self.connection.execute(
            """
            SELECT * FROM notes
            WHERE deleted_at IS NULL
            ORDER BY updated_at DESC, created_at DESC
            """
        ).fetchall()
        return [_from_row(row) for row in rows]

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
        self.connection.commit()
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
        self.connection.commit()
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
        self.connection.commit()
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
        self.connection.commit()

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
        int(note.is_open),
        note.created_at,
        note.updated_at,
        note.deleted_at,
    )


def _from_row(row: sqlite3.Row) -> Note:
    return Note(
        id=row["id"],
        content=row["content"],
        color=validate_color(row["color"]),
        width=row["width"],
        height=row["height"],
        position_x=row["position_x"],
        position_y=row["position_y"],
        is_open=bool(row["is_open"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        deleted_at=row["deleted_at"],
    )
