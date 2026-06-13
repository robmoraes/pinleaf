# Plan: Persist note window position

## Spec Link

- Source spec: `docs/.specs/005-note-window-position/spec.md`

## Approach

Use the window geometry fields that already exist on `Note` and in the SQLite
`notes` table:

```text
width
height
position_x
position_y
```

The current app already restores note size with `set_default_size()` and saves
size on close. This change should keep that path robust and preserve note
position values only when GTK and the desktop environment expose usable
coordinates.

Position support is best-effort. On the validated GNOME/Wayland environment,
GTK 4/libadwaita does not expose reliable public APIs to capture or force exact
top-level window placement, so Pinleaf must keep opening notes normally when
only size restoration is possible.

## Implementation Notes

- Keep storage schema version unchanged unless implementation proves a new field
  is required.
- Add a small geometry helper around GTK window APIs so unsupported position
  behavior is isolated from note UI code.
- Preserve the existing close flow in `NoteWindow._on_close_request()`.
- Save valid size through `NoteService.close_note()`.
- Preserve existing position values when no capture API is available.
- Restore saved size first; restore position only when a supported GTK API is
  available for the current session.
- Clamp or ignore invalid geometry so a note cannot become permanently
  unreachable.
- Avoid frequent database writes during live dragging/resizing unless a reliable
  debounce path is added. Closing the note is enough for the first iteration.

## Files

Expected code areas:

- `pinleaf/ui/note_window.py`: capture and apply note window geometry.
- `pinleaf/services/note_service.py`: keep existing geometry contract intact.
- `pinleaf/storage/sqlite_store.py`: no schema change expected; tests may be
  extended if behavior changes.
- `tests/`: add focused non-GUI tests for validation helpers or service/storage
  behavior where practical.

Expected documentation areas:

- `README.md`: add a short known limitation if position restore is compositor
  dependent.
- `docs/.specs/005-note-window-position/tasks.md`: record manual GTK validation.

## Validation

Automated:

- run unit tests;
- run Python compile checks;
- add focused tests for geometry validation if helper logic is introduced.

Manual:

- create multiple notes;
- move and resize each note;
- close note windows and reopen them;
- quit and restart Pinleaf;
- confirm note sizes restore;
- confirm note positions restore where the current desktop environment allows;
- confirm GNOME/Wayland opens notes at compositor-chosen positions without
  errors;
- confirm unsupported exact placement does not produce tracebacks or broken
  windows.

## Risks

- GTK4/libadwaita on Wayland may not provide or honor absolute window
  coordinates.
- Saving position only on close means a crash may lose the last move, but avoids
  noisy writes and keeps the first implementation simple.
- Multi-monitor changes can make previously valid coordinates unusable; Pinleaf
  should prefer opening the note at a safe default over preserving a bad
  position.
