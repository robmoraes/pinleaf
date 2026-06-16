from __future__ import annotations

from collections.abc import Callable
from uuid import uuid4

from pinleaf.appearance import TextAppearance
from pinleaf.models import Note, NoteColor, utc_now_iso
from pinleaf.storage.sqlite_store import NoteStore


class NoteService:
    def __init__(
        self,
        store: NoteStore,
        *,
        id_factory: Callable[[], str] | None = None,
        clock: Callable[[], str] | None = None,
    ) -> None:
        self.store = store
        self.id_factory = id_factory or (lambda: str(uuid4()))
        self.clock = clock or utc_now_iso

    def create_note(self) -> Note:
        appearance = self.store.get_default_text_appearance()
        return self.store.create(
            Note.new(
                self.id_factory(),
                now=self.clock(),
                font_family=appearance.font_family,
                font_size=appearance.font_size,
                text_color=appearance.text_color,
            )
        )

    def list_notes(self) -> list[Note]:
        return self.store.list_notes()

    def get_note(self, note_id: str) -> Note | None:
        return self.store.get(note_id)

    def update_content(self, note_id: str, content: str) -> Note:
        return self.store.update_content(note_id, content, now=self.clock())

    def update_color(self, note_id: str, color: str | NoteColor) -> Note:
        return self.store.update_color(note_id, color, now=self.clock())

    def update_font_family(self, note_id: str, font_family: str | None) -> Note:
        return self.store.update_font_family(note_id, font_family, now=self.clock())

    def update_text_appearance(
        self,
        note_id: str,
        *,
        font_family: str | None,
        font_size: int | str | None,
        text_color: str | None,
    ) -> Note:
        return self.store.update_text_appearance(
            note_id,
            font_family=font_family,
            font_size=font_size,
            text_color=text_color,
            now=self.clock(),
        )

    def get_default_font_family(self) -> str | None:
        return self.store.get_default_font_family()

    def set_default_font_family(self, font_family: str | None) -> str | None:
        return self.store.set_default_font_family(font_family)

    def get_default_text_appearance(self) -> TextAppearance:
        return self.store.get_default_text_appearance()

    def set_default_text_appearance(
        self,
        *,
        font_family: str | None,
        font_size: int | str | None,
        text_color: str | None,
    ) -> TextAppearance:
        return self.store.set_default_text_appearance(
            font_family=font_family,
            font_size=font_size,
            text_color=text_color,
        )

    def close_note(
        self,
        note_id: str,
        *,
        width: int,
        height: int,
        position_x: int | None = None,
        position_y: int | None = None,
    ) -> Note:
        return self.store.update_window_state(
            note_id,
            width=width,
            height=height,
            position_x=position_x,
            position_y=position_y,
            is_open=False,
            now=self.clock(),
        )

    def save_open_note_window(
        self,
        note_id: str,
        *,
        width: int,
        height: int,
        position_x: int | None = None,
        position_y: int | None = None,
    ) -> Note:
        return self.store.update_window_state(
            note_id,
            width=width,
            height=height,
            position_x=position_x,
            position_y=position_y,
            is_open=True,
            now=self.clock(),
        )

    def reopen_note(self, note_id: str) -> Note:
        note = self.store.get(note_id)
        if note is None:
            raise KeyError(f"Note {note_id!r} does not exist.")
        return self.store.update_window_state(
            note_id,
            width=note.width,
            height=note.height,
            position_x=note.position_x,
            position_y=note.position_y,
            is_open=True,
            now=self.clock(),
        )

    def delete_note(self, note_id: str) -> None:
        self.store.soft_delete(note_id, now=self.clock())
