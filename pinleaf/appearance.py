from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FontOption:
    value: str | None
    label: str
    css_class: str | None


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


def font_option_for(value: str | None) -> FontOption:
    normalized = normalize_font_family(value)
    for option in FONT_OPTIONS:
        if option.value == normalized:
            return option
    return FONT_OPTIONS[0]
