# Tasks: Pinleaf about and help

## Source

- Spec: `docs/.specs/003-about-help/spec.md`
- Plan: `docs/.specs/003-about-help/plan.md`

## Implementation Tasks

1. Add static metadata constants.
   - Include version and build date placeholders.
   - Include maintainer and website.
   - Validation: unit test constants are populated.

2. Add about dialog helper.
   - Use libadwaita native about UI.
   - Include description, license and bundled font credit.
   - Validation: import test with GTK/libadwaita.

3. Add `About Pinleaf` action to the main panel.
   - Add a header menu button.
   - Wire menu action to the about helper.
   - Validation: manual desktop check.

4. Run final checks.
   - Run unit tests.
   - Run compileall.
   - Update progress notes.

## Progress

- Tasks 1-2: implemented and covered by automated tests.
- Task 3: implemented; pending manual desktop verification.
- Task 4: automated checks passed.
