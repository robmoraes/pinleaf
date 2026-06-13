# Tasks: Per-note appearance settings

## Source

- Spec: `docs/.specs/006-note-appearance-per-note/spec.md`
- Plan: `docs/.specs/006-note-appearance-per-note/plan.md`

## Implementation Tasks

1. Add font catalog.
   - Define supported font options, including the default option.
   - Provide validation and lookup helpers.
   - Validation: unit tests cover known, default and invalid values.

2. Add persistence field.
   - Add `font_family: str | None` to `Note`.
   - Add SQLite migration for nullable `font_family`.
   - Update insert/read row conversion.
   - Validation: migration and store tests pass.

3. Add service update method.
   - Expose a method to update a note's font family.
   - Normalize default selection to `None`.
   - Reject or normalize unsupported values through the catalog.
   - Validation: service tests cover update and fallback behavior.

4. Add note editor font styling.
   - Add CSS classes for supported bundled fonts.
   - Ensure only one explicit font class is active on each editor.
   - Keep `.note-editor` as the default fallback.
   - Validation: compile check plus manual GTK check.

5. Add note window font control.
   - Add a compact native selector near existing note controls.
   - Reflect the persisted font when the note opens.
   - Apply and persist changes immediately.
   - Show errors through existing dialog path if saving fails.
   - Validation: manual note UI check.

6. Run automated checks.
   - Run `/usr/bin/python3 -m unittest discover -s tests`.
   - Run `/usr/bin/python3 -m compileall pinleaf tests`.
   - Validation: both commands pass.

7. Manual acceptance pass.
   - Create at least two notes.
   - Select different fonts per note.
   - Restart Pinleaf.
   - Confirm each note restores its own font.
   - Confirm the default option returns a note to the global default font.
   - Confirm no tracebacks are printed.

## Progress

- Tasks 1-6: implemented and automated checks passed.
- Task 7: pending manual desktop verification.
