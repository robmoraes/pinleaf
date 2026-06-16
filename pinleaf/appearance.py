from __future__ import annotations

from dataclasses import dataclass
import re


DEFAULT_FONT_SIZE = 17
MIN_FONT_SIZE = 8
MAX_FONT_SIZE = 72
DEFAULT_TEXT_COLOR = "#005BAC"


@dataclass(frozen=True)
class FontOption:
    value: str | None
    label: str
    css_class: str | None


@dataclass(frozen=True)
class TextAppearance:
    font_family: str | None
    font_size: int
    text_color: str


FONT_OPTIONS: tuple[FontOption, ...] = (
    FontOption(None, "Default", None),
    FontOption("cursive", "Cursive", "note-font-cursive"),
    FontOption("sans-serif", "Sans Serif", "note-font-sans-serif"),
    FontOption("monospace", "Monospace", "note-font-monospace"),
    FontOption("Dancing Script", "Dancing Script", "note-font-dancing-script"),
    FontOption("Kavoon", "Kavoon", "note-font-kavoon"),
    FontOption("Londrina Shadow", "Londrina Shadow", "note-font-londrina-shadow"),
    FontOption("Nabla", "Nabla", "note-font-nabla"),
    FontOption("Press Start 2P", "Press Start 2P", "note-font-press-start-2p"),
    FontOption("Style Script", "Style Script", "note-font-style-script"),
)


def font_options() -> tuple[FontOption, ...]:
    return FONT_OPTIONS


def system_font_option_count() -> int:
    return 4


def font_css_classes() -> tuple[str, ...]:
    return tuple(option.css_class for option in FONT_OPTIONS if option.css_class is not None)


def normalize_font_family(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if any(option.value == normalized for option in FONT_OPTIONS):
        return normalized
    return None


def normalize_font_size(value: int | str | None) -> int:
    if value is None:
        return DEFAULT_FONT_SIZE
    try:
        size = int(value)
    except (TypeError, ValueError):
        return DEFAULT_FONT_SIZE
    return min(max(size, MIN_FONT_SIZE), MAX_FONT_SIZE)


def normalize_text_color(value: str | None) -> str:
    if value is None:
        return DEFAULT_TEXT_COLOR
    normalized = value.strip()
    if re.fullmatch(r"#[0-9a-fA-F]{6}", normalized):
        return normalized.upper()
    if re.fullmatch(r"#[0-9a-fA-F]{3}", normalized):
        return "#" + "".join(character * 2 for character in normalized[1:]).upper()
    return DEFAULT_TEXT_COLOR


def normalize_text_appearance(
    *,
    font_family: str | None = None,
    font_size: int | str | None = None,
    text_color: str | None = None,
) -> TextAppearance:
    return TextAppearance(
        font_family=normalize_font_family(font_family),
        font_size=normalize_font_size(font_size),
        text_color=normalize_text_color(text_color),
    )


def font_option_for(value: str | None) -> FontOption:
    normalized = normalize_font_family(value)
    for option in FONT_OPTIONS:
        if option.value == normalized:
            return option
    return FONT_OPTIONS[0]
