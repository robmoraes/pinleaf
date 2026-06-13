# Tasks: Persist note window position

## Source

- Spec: `docs/.specs/005-note-window-position/spec.md`
- Plan: `docs/.specs/005-note-window-position/plan.md`

## Implementation Tasks

1. Confirm available GTK geometry APIs.
   - Verify which window position APIs are available under the GTK/libadwaita
     version used by Pinleaf.
   - Decide whether position restore is supported directly or must remain
     documented as compositor-limited.
   - Validation: GTK 4/libadwaita exposes size APIs but no reliable public
     top-level position APIs in the tested GNOME/Wayland session.

2. Add geometry validation helper if needed.
   - Normalize note width and height to safe positive values.
   - Accept position only when both `position_x` and `position_y` are valid.
   - Ignore invalid or unsupported position values without breaking note open.
   - Validation: focused unit tests if helper logic is non-trivial.

3. Restore saved geometry when opening notes.
   - Keep existing size restoration through `set_default_size()`.
   - Apply saved position only when the current GTK/session supports it.
   - Ensure notes without saved position keep current default placement.
   - Validation: manual desktop check confirms position is compositor-chosen on
     GNOME/Wayland.

4. Capture geometry before note close.
   - Keep flushing note content before closing.
   - Persist current width and height.
   - Persist current position when available; otherwise preserve previously
     stored position values.
   - Persist current width and height during app shutdown while keeping open
     notes marked as open for restart restoration.
   - Validation: inspect SQLite row or reopen note and confirm restored state.

5. Update docs for compositor limitations.
   - Add a short README note if exact position restore is limited by the
     desktop environment.
   - Keep the wording practical and user-facing.
   - Validation: README remains accurate for GNOME/Wayland behavior.

6. Run automated checks.
   - Run `python3 -m unittest discover -s tests`.
   - Run `python3 -m compileall pinleaf tests`.
   - Validation: both commands pass.

7. Manual acceptance pass.
   - Create at least two notes.
   - Move and resize each note.
   - Close note windows, reopen them, then quit and restart Pinleaf.
   - Confirm sizes restore.
   - Confirm positions restore where supported, or open at compositor-chosen
     positions where not.
   - Confirm no tracebacks are printed.

## Progress

- Tasks 1-5: implemented.
- Task 6: automated checks passed.
- Task 7: manual desktop verification completed on GNOME/Wayland; exact
  position restore is not supported by the current session, and notes open
  safely at compositor-chosen positions.
