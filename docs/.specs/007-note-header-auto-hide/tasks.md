# Tasks: Note header auto-hide

## Source

- Spec: `docs/.specs/007-note-header-auto-hide/spec.md`
- Plan: `docs/.specs/007-note-header-auto-hide/plan.md`

## Implementation Tasks

1. Store note header reference.
   - Keep the existing `Adw.HeaderBar`.
   - Save header controls as instance attributes for visibility updates.
   - Validation: note window still opens.

2. Add focus/active state handler.
   - Connect to `notify::is-active`.
   - Show header controls when the note is active.
   - Hide header controls when the note is inactive.
   - Hide native title and title buttons when the note is inactive.
   - Keep header height stable.
   - Validation: manual focus check.

3. Run checks.
   - Run `/usr/bin/python3 -m unittest discover -s tests`.
   - Run `/usr/bin/python3 -m compileall pinleaf tests`.
   - Validation: both commands pass.

4. Manual acceptance pass.
   - Open a note.
   - Focus away from it.
   - Confirm the header controls hide without moving note content.
   - Focus the note again.
   - Confirm the header reappears and controls still work.

## Progress

- Tasks 1-3: implemented and automated checks passed.
- Task 4: pending manual desktop verification.
