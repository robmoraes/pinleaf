from __future__ import annotations

import unittest
from collections.abc import Callable

from pinleaf.services.autosave import Autosave


class FakeScheduledCall:
    def __init__(self, callback: Callable[[], None]) -> None:
        self.callback = callback
        self.cancelled = False

    def cancel(self) -> None:
        self.cancelled = True

    def run(self) -> None:
        self.callback()


class FakeScheduler:
    def __init__(self) -> None:
        self.calls: list[FakeScheduledCall] = []

    def __call__(self, delay_seconds: float, callback: Callable[[], None]) -> FakeScheduledCall:
        call = FakeScheduledCall(callback)
        self.calls.append(call)
        return call


class AutosaveTests(unittest.TestCase):
    def test_schedule_debounces_previous_save(self) -> None:
        scheduler = FakeScheduler()
        saved: list[tuple[str, str]] = []
        autosave = Autosave(lambda note_id, content: saved.append((note_id, content)), scheduler=scheduler)

        autosave.schedule("note-1", "first")
        autosave.schedule("note-1", "second")
        scheduler.calls[-1].run()

        self.assertTrue(scheduler.calls[0].cancelled)
        self.assertEqual(saved, [("note-1", "second")])
        self.assertFalse(autosave.has_pending_changes)

    def test_flush_writes_pending_content_immediately(self) -> None:
        scheduler = FakeScheduler()
        saved: list[tuple[str, str]] = []
        autosave = Autosave(lambda note_id, content: saved.append((note_id, content)), scheduler=scheduler)

        autosave.schedule("note-1", "Comprar cafe")

        self.assertTrue(autosave.flush())
        self.assertEqual(saved, [("note-1", "Comprar cafe")])
        self.assertTrue(scheduler.calls[0].cancelled)

    def test_failed_save_keeps_pending_content(self) -> None:
        scheduler = FakeScheduler()
        error = RuntimeError("disk full")

        def fail(_: str, __: str) -> None:
            raise error

        autosave = Autosave(fail, scheduler=scheduler)

        autosave.schedule("note-1", "Comprar cafe")

        self.assertFalse(autosave.flush())
        self.assertTrue(autosave.has_pending_changes)
        self.assertIs(autosave.last_error, error)


if __name__ == "__main__":
    unittest.main()
