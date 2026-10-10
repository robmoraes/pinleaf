from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, TypeVar

from pinleaf.models import Note
from pinleaf.services.note_service import NoteService


class TransitionError(RuntimeError):
    pass


class NoteEditor(Protocol):
    def flush_for_transition(self) -> bool: ...
    def capture_state(self) -> dict: ...
    def dispose_for_context(self) -> None: ...
    def sync_note(self, note: Note) -> None: ...
    def show_for_context(self) -> None: ...
    def present(self) -> None: ...


T = TypeVar("T")


class ContextController:
    """Own the durable boundary between organization and editor visibility."""

    def __init__(self, service: NoteService, windows: dict[str, NoteEditor],
                 prepare: Callable[[Note], NoteEditor], *,
                 on_context_changed: Callable[[], None] = lambda: None,
                 on_refresh: Callable[[], None] = lambda: None,
                 on_presentation_error: Callable[[], None] = lambda: None) -> None:
        self.service = service
        self.windows = windows
        self.prepare = prepare
        self.on_context_changed = on_context_changed
        self.on_refresh = on_refresh
        self.on_presentation_error = on_presentation_error
        self.busy = False

    def execute(self, action: Callable[[], T], *, affected_ids: set[str] | None = None,
                present_existing: bool = False) -> T:
        if self.busy:
            raise TransitionError("Another change is in progress. Try again.")
        previous = self.service.organization.context.group.id
        self.busy = True
        staged: dict[str, NoteEditor] = {}
        committed = False
        try:
            affected = {key: window for key, window in self.windows.items()
                        if affected_ids is None or key in affected_ids}
            for window in affected.values():
                if not window.flush_for_transition():
                    raise TransitionError("Could not save the latest edits. The current notes remain open; retry after saving.")
            states = {key: window.capture_state() for key, window in affected.items()}
            with self.service.store.transaction():
                for key, state in states.items():
                    self.service.store.save_context_geometry(key, **state)
                result = action()
                context = self.service.organization.context
                desired = {note.id: note for note in self.service.store.list_notes(group_id=context.group.id) if note.is_open}
                # Stage against uncommitted membership, without exposing any windows.
                for key, note in desired.items():
                    if key not in self.windows:
                        staged[key] = self.prepare(note)
            committed = True
            for key in list(self.windows):
                if key not in desired:
                    self.windows.pop(key).dispose_for_context()
            self.windows.update(staged)
            for key, note in desired.items():
                self.windows[key].sync_note(note)
            if context.group.id != previous:
                self.on_context_changed()
            to_present = self.windows if present_existing else staged
            last_key = next(reversed(to_present), None)
            for key, window in to_present.items():
                try:
                    # Map a batch without asking the compositor to focus every
                    # new editor. Explicit single-note opens still present it.
                    if key in staged and key != last_key:
                        window.show_for_context()
                    else:
                        window.present()
                except Exception:
                    self.on_presentation_error()
            return result
        finally:
            if not committed:
                for window in staged.values():
                    window.dispose_for_context()
            self.busy = False
            self.on_refresh()

    def restore(self) -> None:
        self.execute(lambda: None, affected_ids=set(), present_existing=True)
