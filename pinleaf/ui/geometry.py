from __future__ import annotations

from dataclasses import dataclass


MIN_WINDOW_WIDTH = 160
MIN_WINDOW_HEIGHT = 120
MAX_WINDOW_WIDTH = 2000
MAX_WINDOW_HEIGHT = 1600


@dataclass(frozen=True)
class WindowGeometry:
    width: int
    height: int
    position_x: int | None = None
    position_y: int | None = None


def normalize_size(width: int, height: int) -> tuple[int, int]:
    return (
        min(max(int(width), MIN_WINDOW_WIDTH), MAX_WINDOW_WIDTH),
        min(max(int(height), MIN_WINDOW_HEIGHT), MAX_WINDOW_HEIGHT),
    )


def normalize_position(position_x: int | None, position_y: int | None) -> tuple[int | None, int | None]:
    if position_x is None or position_y is None:
        return None, None
    return int(position_x), int(position_y)


def normalize_geometry(
    width: int,
    height: int,
    position_x: int | None = None,
    position_y: int | None = None,
) -> WindowGeometry:
    normalized_width, normalized_height = normalize_size(width, height)
    normalized_x, normalized_y = normalize_position(position_x, position_y)
    return WindowGeometry(
        width=normalized_width,
        height=normalized_height,
        position_x=normalized_x,
        position_y=normalized_y,
    )


def capture_window_geometry(
    window: object,
    *,
    fallback_position_x: int | None = None,
    fallback_position_y: int | None = None,
) -> WindowGeometry:
    width = window.get_width() if hasattr(window, "get_width") else MIN_WINDOW_WIDTH
    height = window.get_height() if hasattr(window, "get_height") else MIN_WINDOW_HEIGHT

    position_x = fallback_position_x
    position_y = fallback_position_y
    get_position = getattr(window, "get_position", None)
    if callable(get_position):
        try:
            position_x, position_y = get_position()
        except Exception:
            position_x = fallback_position_x
            position_y = fallback_position_y

    return normalize_geometry(width, height, position_x, position_y)


def apply_window_geometry(window: object, geometry: WindowGeometry) -> None:
    set_default_size = getattr(window, "set_default_size", None)
    if callable(set_default_size):
        set_default_size(geometry.width, geometry.height)

    if geometry.position_x is None or geometry.position_y is None:
        return

    move = getattr(window, "move", None)
    if callable(move):
        try:
            move(geometry.position_x, geometry.position_y)
        except Exception:
            return

