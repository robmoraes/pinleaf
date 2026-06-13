# Plan: Note header auto-hide

## Spec Link

- Source spec: `docs/.specs/007-note-header-auto-hide/spec.md`

## Approach

Use the GTK window active state to control note header visibility.

`Gtk.Window`/`Adw.ApplicationWindow` exposes `is_active()`, and GTK emits
property notifications for active state changes. The note window can connect to
`notify::is-active` and set the existing header controls visible only while the
note is active.

The `Adw.HeaderBar` itself should remain visible so the editor content does not
shift vertically when controls appear or disappear. Hide the added controls,
native title and native title buttons while preserving the header container.

## Implementation Notes

- Store the note header controls as instance attributes.
- Connect `notify::is-active` in `NoteWindow`.
- Keep the header area visible at all times.
- Toggle `show-title`, `show-start-title-buttons` and
  `show-end-title-buttons` with active state.
- Do not alter persistence, note controls or content autosave.
- Do not add hover reveal in this iteration.

## Files

Expected code areas:

- `pinleaf/ui/note_window.py`: focus notification and header visibility.
- `docs/.specs/007-note-header-auto-hide/tasks.md`: validation status.

## Validation

Automated:

- run unit tests;
- run Python compile checks.

Manual:

- open a note;
- confirm the header is visible while focused;
- focus another window;
- confirm the header hides;
- click the note again;
- confirm the header returns and Color/Font controls still work.

## Risks

- Header hiding changes available drag/titlebar area while unfocused.
- Some window managers may report active state changes differently.
