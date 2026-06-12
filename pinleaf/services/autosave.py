from __future__ import annotations

from collections.abc import Callable
from threading import Timer
from typing import Protocol, TypeAlias


class ScheduledCall(Protocol):
    def cancel(self) -> None: ...


Scheduler: TypeAlias = Callable[[float, Callable[[], None]], ScheduledCall]
SaveCallback: TypeAlias = Callable[[str, str], None]


class ThreadingScheduler:
    def __call__(self, delay_seconds: float, callback: Callable[[], None]) -> ScheduledCall:
        timer = Timer(delay_seconds, callback)
        timer.daemon = True
        timer.start()
        return timer


class Autosave:
    def __init__(
        self,
        save: SaveCallback,
        *,
        delay_seconds: float = 0.5,
        scheduler: Scheduler | None = None,
    ) -> None:
        self.save = save
        self.delay_seconds = delay_seconds
        self.scheduler = scheduler or ThreadingScheduler()
        self._scheduled: ScheduledCall | None = None
        self._pending: tuple[str, str] | None = None
        self.last_error: Exception | None = None

    @property
    def has_pending_changes(self) -> bool:
        return self._pending is not None

    def schedule(self, note_id: str, content: str) -> None:
        self._pending = (note_id, content)
        self.last_error = None
        if self._scheduled is not None:
            self._scheduled.cancel()
        self._scheduled = self.scheduler(self.delay_seconds, self._run_scheduled)

    def flush(self) -> bool:
        if self._scheduled is not None:
            self._scheduled.cancel()
            self._scheduled = None
        return self._save_pending()

    def _run_scheduled(self) -> None:
        self._scheduled = None
        self._save_pending()

    def _save_pending(self) -> bool:
        if self._pending is None:
            return True

        note_id, content = self._pending
        try:
            self.save(note_id, content)
        except Exception as exc:
            self.last_error = exc
            return False

        self._pending = None
        self.last_error = None
        return True

    def cancel(self) -> None:
        if self._scheduled is not None:
            self._scheduled.cancel()
            self._scheduled = None
