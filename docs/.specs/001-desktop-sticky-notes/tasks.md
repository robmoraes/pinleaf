# Tasks: Pinleaf MVP - notas post-it para desktop

## Source

- Spec: `docs/.specs/001-desktop-sticky-notes/spec.md`
- Plan: `docs/.specs/001-desktop-sticky-notes/plan.md`

## Progress

- Task 1: implemented scaffold and entrypoint; GTK dependencies are available through `/usr/bin/python3`, while the `mise` Python does not have PyGObject.
- Tasks 2-7: implemented and covered by `unittest`.
- Tasks 8-10: implemented and manually verified on a desktop session.
- Task 12: startup restore path implemented and manually verified on a desktop session.
- Task 13: startup storage and GUI initialization failures now fail cleanly; corrupt database behavior still needs explicit verification.
- Task 14: CSS/resource loading implemented and manually verified after polish for note contrast and panel row layout.
- Task 11: implemented through a separate GTK3 Ayatana tray helper process to avoid GTK3/GTK4 conflicts; tray actions manually verified on a desktop session.
- Task 15: acceptance examples manually verified except explicit corrupt database recovery.
- Task 16: final quality pass partially complete; automated tests pass and manual smoke test passed.

## Verification Notes

- Manual desktop smoke test passed for opening the panel, creating notes, opening note windows, note editing and tray/status actions.
- Note body contrast and panel note list layout were polished and manually accepted.
- Accepted limitation: when the panel is minimized, `Show Pinleaf` from tray may surface Ubuntu's `"Pinleaf" is ready` notification before the panel is focused.
- Accepted limitation: when the panel is closed and reopened through tray, GTK may warn `A window is shown after it has been destroyed`; this is accepted for the MVP because the panel still returns and no user-visible failure was observed.

## Implementation Tasks

1. Scaffold the Python package and development entrypoint.
   - Create the initial `pinleaf/` package, `python -m pinleaf` entrypoint and minimal project metadata.
   - Add a placeholder `Adw.Application` startup path that can open an empty main window.
   - Validation: run the app from the development environment and confirm it starts without import errors.

2. Add configuration and local data path resolution.
   - Implement XDG-compatible data directory resolution for the SQLite database.
   - Ensure the data directory can be created with user-appropriate permissions.
   - Keep paths centralized so future packaging does not require UI or storage rewrites.
   - Validation: unit test default data path behavior with an isolated environment.

3. Define note domain models and color validation.
   - Add the note model with id, content, color, dimensions, optional position, open state and timestamps.
   - Define supported MVP colors: yellow, green, blue and pink.
   - Reject unsupported color values at the domain/service boundary.
   - Validation: unit tests for default note creation and color validation.

4. Implement SQLite migrations.
   - Create the initial schema with `schema_version` and `notes`.
   - Include the index for normal note listing.
   - Make migration execution idempotent for an empty database.
   - Validation: unit test that a new database contains the expected tables, columns, index and schema version.

5. Implement the SQLite note repository.
   - Add create, update content, update color, update window state, soft delete, get and list operations.
   - Exclude soft-deleted notes from normal reads.
   - Store timestamps as ISO 8601 UTC strings.
   - Validation: unit tests for create, edit, list, soft delete, color update and persisted window fields.

6. Implement the note service layer.
   - Coordinate repository operations for create, edit, close, reopen, delete and list.
   - Generate stable UUID note ids.
   - Keep empty notes valid until explicitly deleted.
   - Validation: service tests covering the spec scenarios that do not require GTK.

7. Add autosave behavior.
   - Debounce content writes after note edits.
   - Provide an explicit flush path for note close and application quit.
   - Track save failures so the UI can report unsaved changes.
   - Validation: unit test debounced save and flush behavior using a controlled timer or test double.

8. Build the main window.
   - Show an empty state with create action when no notes exist.
   - List notes with preview text, color indicator and updated time.
   - Open or focus a note window when a listed note is activated.
   - Expose delete action using the shared confirmation dialog.
   - Validation: manual GTK check for empty state, list rendering and opening an existing note.

9. Build the note window.
   - Open new notes empty and focused for immediate editing.
   - Bind text changes to autosave.
   - Add color selection for the four supported colors.
   - Save width, height and best-effort position state when available.
   - Close the window without deleting the note.
   - Validation: manual GTK check for editing, color change, close and reopen behavior.

10. Add delete confirmation and user-facing error dialogs.
    - Require confirmation before deleting non-empty notes.
    - Allow deleting empty notes without unnecessary friction if the UI flow supports it cleanly.
    - Show clear messages for load and save failures.
    - Validation: manual GTK check for confirm, cancel and error display paths.

11. Add status/tray integration.
    - Implement a tray/status adapter with actions to create note, show/focus main window and quit.
    - Keep the app fully usable through the main window if tray/status support is unavailable.
    - Log unsupported tray/status environments for diagnosis.
    - Validation: manual check on the development desktop for tray actions and fallback behavior.

12. Restore session state on startup.
    - Load non-deleted notes from SQLite.
    - Restore notes marked open.
    - Apply saved window dimensions.
    - Attempt saved position restore only where supported.
    - Validation: manual restart check for content, color, size and open note restoration.

13. Add startup and storage error handling.
    - Prevent automatic overwrite of unreadable or invalid databases.
    - Log exception details to stderr or local logs.
    - Show a clear fatal error when notes cannot be loaded safely.
    - Validation: manual or automated test with a deliberately invalid database file.

14. Add CSS/resources for post-it visual treatment.
    - Style note windows by color without making color the only identifier in the main list.
    - Centralize resource loading so future packaging can replace repository-relative paths.
    - Validation: manual GTK check that all four colors render and text remains readable.

15. Cover acceptance examples with verification.
    - Verify create and persist note.
    - Verify close without delete and reopen from the main window.
    - Verify delete confirmation and cancel flow.
    - Verify color persistence across restart.
    - Verify create note through tray/status action.
    - Verify position restore fallback does not break startup.
    - Verify corrupt storage does not get overwritten.
    - Validation: record automated test output where available and manual verification notes for GTK-only behavior.

16. Final MVP quality pass.
    - Confirm no network calls or telemetry exist.
    - Confirm note content is never executed or auto-opened.
    - Confirm keyboard access for primary actions.
    - Confirm the app remains responsive with 100 short notes and a note with 10,000 characters.
    - Validation: final local run, unit test run and manual smoke test against the spec.

## Suggested Implementation Slices

Slice 1: storage and domain foundation.
- Tasks 1-6.
- Goal: notes can be created, edited, listed and deleted through non-GUI tests.

Slice 2: autosave and core GTK windows.
- Tasks 7-10.
- Goal: users can create, edit, close, reopen, recolor and delete notes through the UI.

Slice 3: lifecycle, tray/status and recovery.
- Tasks 11-14.
- Goal: startup restore, tray/status actions, storage error handling and post-it styling are in place.

Slice 4: acceptance verification.
- Tasks 15-16.
- Goal: MVP behavior is checked against the spec and ready for review.
