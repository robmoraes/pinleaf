from __future__ import annotations

import unittest

from pinleaf.ui.geometry import (
    MAX_WINDOW_HEIGHT,
    MAX_WINDOW_WIDTH,
    MIN_WINDOW_HEIGHT,
    MIN_WINDOW_WIDTH,
    WindowGeometry,
    apply_window_geometry,
    capture_window_geometry,
    normalize_geometry,
    normalize_position,
    normalize_size,
)


class FakeWindow:
    def __init__(
        self,
        *,
        width: int = 320,
        height: int = 280,
        position: tuple[int, int] | None = None,
        fail_position: bool = False,
        fail_move: bool = False,
    ) -> None:
        self.width = width
        self.height = height
        self.position = position
        self.fail_position = fail_position
        self.fail_move = fail_move
        self.default_size: tuple[int, int] | None = None
        self.moved_to: tuple[int, int] | None = None

    def get_width(self) -> int:
        return self.width

    def get_height(self) -> int:
        return self.height

    def get_position(self) -> tuple[int, int]:
        if self.fail_position or self.position is None:
            raise RuntimeError("position is unavailable")
        return self.position

    def set_default_size(self, width: int, height: int) -> None:
        self.default_size = (width, height)

    def move(self, position_x: int, position_y: int) -> None:
        if self.fail_move:
            raise RuntimeError("move is unavailable")
        self.moved_to = (position_x, position_y)


class SizeOnlyWindow:
    def __init__(self) -> None:
        self.default_size: tuple[int, int] | None = None

    def get_width(self) -> int:
        return 420

    def get_height(self) -> int:
        return 260

    def set_default_size(self, width: int, height: int) -> None:
        self.default_size = (width, height)


class GeometryTests(unittest.TestCase):
    def test_normalize_size_clamps_to_safe_range(self) -> None:
        self.assertEqual(normalize_size(1, 1), (MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT))
        self.assertEqual(
            normalize_size(9999, 9999),
            (MAX_WINDOW_WIDTH, MAX_WINDOW_HEIGHT),
        )

    def test_normalize_position_requires_both_coordinates(self) -> None:
        self.assertEqual(normalize_position(10, 20), (10, 20))
        self.assertEqual(normalize_position(10, None), (None, None))
        self.assertEqual(normalize_position(None, 20), (None, None))

    def test_capture_uses_available_position_api(self) -> None:
        window = FakeWindow(width=500, height=300, position=(15, 25))

        geometry = capture_window_geometry(window)

        self.assertEqual(geometry, WindowGeometry(500, 300, 15, 25))

    def test_capture_preserves_fallback_position_when_position_is_unavailable(self) -> None:
        window = SizeOnlyWindow()

        geometry = capture_window_geometry(
            window,
            fallback_position_x=30,
            fallback_position_y=40,
        )

        self.assertEqual(geometry, WindowGeometry(420, 260, 30, 40))

    def test_apply_geometry_sets_size_and_moves_when_available(self) -> None:
        window = FakeWindow()

        apply_window_geometry(window, normalize_geometry(440, 330, 12, 22))

        self.assertEqual(window.default_size, (440, 330))
        self.assertEqual(window.moved_to, (12, 22))

    def test_apply_geometry_ignores_unsupported_move(self) -> None:
        window = SizeOnlyWindow()

        apply_window_geometry(window, normalize_geometry(440, 330, 12, 22))

        self.assertEqual(window.default_size, (440, 330))


if __name__ == "__main__":
    unittest.main()

