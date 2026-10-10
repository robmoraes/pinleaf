# Feature: Persist note window position

## Intent

Problem:
Pinleaf restores notes after restart, but note windows lose the desktop position
chosen by the user. This makes the app less useful as a desktop post-it system,
because spatial placement is part of the note's meaning.

Users or stakeholders:
Maintainer and early users who keep multiple notes arranged around the desktop.

Desired outcome:
Pinleaf saves each note window's last known geometry and restores it on the next
app launch when the desktop environment allows it.

Validated outcome:
On the current GNOME/Wayland development environment, GTK 4/libadwaita does not
expose reliable public APIs to read or force top-level window coordinates.
Pinleaf can persist and restore note size, but exact desktop position remains a
documented compositor limitation.

Non-goals:

- Cross-monitor layout engine.
- Virtual desktop/workspace management.
- Pixel-perfect restoration on every Linux compositor.
- Cloud sync of window geometry.

## Scope

In scope:

- Persist note window `x`, `y`, `width` and `height` when available.
- Restore note size and position on startup.
- Update stored size after user resize actions.
- Preserve stored position fields when position APIs are unavailable.
- Preserve existing note content, color and panel behavior.
- Document compositor limitations.

Out of scope:

- Dragging notes from the main panel.
- Snap-to-grid or board layout.
- Global layout presets.
- Import/export of layouts.

Assumptions:

- SQLite remains the local persistence layer.
- GTK/libadwaita and the active compositor may not always expose or honor exact
  window positions, especially on Wayland.
- Size restoration is expected to be more reliable than absolute position.

Dependencies:

- Existing note storage schema and migration mechanism.
- Existing note window lifecycle.

## Behavior

1. Each note can store last known window geometry.
2. When a note window opens, Pinleaf applies the saved size.
3. When supported by the desktop environment, Pinleaf applies the saved
   position.
4. When a note window is resized, Pinleaf records the supported geometry.
5. When position capture is unsupported, Pinleaf preserves any existing
   position data instead of replacing it with invalid values.
6. Geometry persistence must not interfere with autosaving note text.
7. Existing notes without geometry continue opening with current defaults.
8. If restoring position is unsupported, Pinleaf still opens the note and
   restores all other persisted data.

## Acceptance Examples

Scenario: restore note size and position
Given a note is open
When the user moves and resizes the note
And closes and reopens Pinleaf
Then the note reopens with its last saved size
And, when supported by the desktop environment, its last saved position.

Scenario: GNOME/Wayland position limitation
Given the desktop environment does not expose top-level window coordinates
When the user moves a note and restarts Pinleaf
Then the note may reopen at a compositor-chosen position
And the app still restores supported note state without errors.

Scenario: existing note without geometry
Given a note was created before geometry persistence existed
When the note is opened
Then it opens with default geometry
And no error is shown.

Scenario: unsupported position restore
Given the desktop environment does not allow explicit window positioning
When Pinleaf opens a note with saved geometry
Then the note still opens normally
And the limitation is documented.

## Data and Contracts

Inputs:

- GTK window size APIs.
- GTK window position APIs only if available in the active session.
- Existing note id.

Outputs:

- Persisted geometry fields per note.

API/schema/event changes:

- SQLite schema may gain nullable geometry columns.

Persistence changes:

- Reuse existing nullable note geometry fields.
- No migration is required for the current implementation.

## Quality Attributes

Security:

- No new external access.

Privacy:

- Geometry data remains local.

Accessibility:

- Restored geometry should not make notes permanently unreachable; fallback
  behavior must remain available.

Reliability:

- Geometry updates should be debounced or written in a way that avoids excessive
  database writes.
- The app must tolerate missing or invalid geometry values.

Observability:

- Developer logs may mention unsupported geometry restore only when useful.

## Rollout and Operations

Migration:

- Add schema migration for geometry fields.

Feature flag or configuration:

- None.

Rollback:

- Ignore geometry fields and keep default note placement.

Monitoring:

- None.
