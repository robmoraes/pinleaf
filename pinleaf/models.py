from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum


DEFAULT_WIDTH = 320
DEFAULT_HEIGHT = 280


class NoteColor(StrEnum):
    YELLOW = "yellow"
    GREEN = "green"
    BLUE = "blue"
    PINK = "pink"


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def validate_color(value: str | NoteColor) -> NoteColor:
    try:
        return NoteColor(value)
    except ValueError as exc:
        supported = ", ".join(color.value for color in NoteColor)
        raise ValueError(f"Unsupported note color {value!r}. Supported: {supported}.") from exc


@dataclass(frozen=True)
class Note:
    id: str
    content: str
    color: NoteColor
    width: int
    height: int
    position_x: int | None
    position_y: int | None
    font_family: str | None
    is_open: bool
    created_at: str
    updated_at: str
    deleted_at: str | None = None

    @classmethod
    def new(
        cls,
        note_id: str,
        now: str | None = None,
        color: str | NoteColor = NoteColor.YELLOW,
        font_family: str | None = None,
    ) -> "Note":
        timestamp = now or utc_now_iso()
        return cls(
            id=note_id,
            content="",
            color=validate_color(color),
            width=DEFAULT_WIDTH,
            height=DEFAULT_HEIGHT,
            position_x=None,
            position_y=None,
            font_family=font_family,
            is_open=True,
            created_at=timestamp,
            updated_at=timestamp,
        )

    def with_content(self, content: str, now: str | None = None) -> "Note":
        return replace(self, content=content, updated_at=now or utc_now_iso())

    def with_color(self, color: str | NoteColor, now: str | None = None) -> "Note":
        return replace(self, color=validate_color(color), updated_at=now or utc_now_iso())
